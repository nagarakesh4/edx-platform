""" Views for a student's account information. """

import datetime
import logging

import analytics
import third_party_auth

from openedx.core.lib.request_utils import safe_get_host
from django.conf import settings
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.core.exceptions import NON_FIELD_ERRORS
from django.core.urlresolvers import resolve, reverse
from django.core.validators import validate_email, ValidationError, validate_slug
from django.db import IntegrityError, transaction
from django.db.models.signals import post_save
from django.http import HttpRequest
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext as _, get_language
from django.views.decorators.csrf import csrf_exempt
from eventtracking import tracker
from notification_prefs.views import enable_notifications
from pytz import UTC
from requests import HTTPError
from social_core.exceptions import AuthException, AuthAlreadyAssociated
from mailchimp_pipeline.signals.handlers import task_send_account_activation_email
from openedx.core.djangoapps.user_authn.cookies import set_logged_in_cookies

from student.models import Registration, UserProfile
from third_party_auth import pipeline, provider
from util.json_request import JsonResponse
from lms.djangoapps.onboarding.models import EmailPreference, Organization, RegistrationType, UserExtendedProfile

from social_django import utils as social_utils
from openedx.core.djangoapps.user_authn.views.register import REGISTER_USER, record_registration_attributions
from openedx.core.djangoapps.lang_pref import LANGUAGE_KEY
from openedx.core.djangoapps.user_api.accounts.api import check_account_exists
from openedx.core.djangoapps.user_api.preferences import api as preferences_api
from openedx.core.djangoapps.user_api.views import RegistrationView
from openedx.core.djangoapps.user_api.api import RegistrationFormFactory
from openedx.core.djangoapps.user_api.helpers import FormDescription

from .helpers import get_register_form_data_override
from .forms import AccountCreationForm

log = logging.getLogger("edx.student")
AUDIT_LOG = logging.getLogger("audit")


def local_server_get(url, session):
    """Simulate a server-server GET request for an in-process API.

    Arguments:
        url (str): The URL of the request (excluding the protocol and domain)
        session (SessionStore): The session of the original request,
            used to get past the CSRF checks.

    Returns:
        str: The content of the response

    """
    # Since the user API is currently run in-process,
    # we simulate the server-server API call by constructing
    # our own request object.  We don't need to include much
    # information in the request except for the session
    # (to get past through CSRF validation)
    request = HttpRequest()
    request.method = "GET"
    request.session = session

    # Call the Django view function, simulating
    # the server-server API call
    view, args, kwargs = resolve(url)
    response = view(request, *args, **kwargs)

    # Return the content of the response
    return response.content


def _do_create_account_custom(form):
    """
    Given cleaned post variables, create the User and UserProfile objects, as well as the
    registration for this user.

    Returns a tuple (User, UserProfile, Registration).

    Note: this function is also used for creating test users.
    """

    from openedx.core.djangoapps.user_api.errors import AccountValidationError

    errors = {}
    errors.update(form.errors)

    if errors:
        raise ValidationError(errors)

    user = User(
        username=form.cleaned_data.get("username"),
        email=form.cleaned_data.get("email"),
        is_active=False,
        first_name=form.cleaned_data.get("first_name"),
        last_name=form.cleaned_data.get("last_name")
    )
    user.set_password(form.cleaned_data["password"])
    registration = Registration()

    # TODO: Rearrange so that if part of the process fails, the whole process fails.
    # Right now, we can have e.g. no registration e-mail sent out and a zombie account
    try:
        with transaction.atomic():
            user.save()
    except IntegrityError:
        # Figure out the cause of the integrity error
        if len(User.objects.filter(username=user.username)) > 0:
            raise AccountValidationError(
                _("An account with the Public Username '{username}' already exists.").format(username=user.username),
                field="username"
            )
        elif len(User.objects.filter(email=user.email)) > 0:
            raise AccountValidationError(
                _("An account with the Email '{email}' already exists.").format(email=user.email),
                field="email"
            )
        else:
            raise

    registration.register(user)

    profile = UserProfile(user=user)
    try:
        profile.save()
    except Exception:  # pylint: disable=broad-except
        log.exception("UserProfile creation failed for user {id}.".format(id=user.id))
        raise

    org_name = form.cleaned_data.get("org_name")
    org_type = form.cleaned_data.get('org_type')
    user_extended_profile_data = {}

    if org_name:
        user_organization, org_created = Organization.objects.get_or_create(label=org_name)
        org_size = form.cleaned_data.get('org_size')
        if org_created:
            user_organization.total_employees = org_size
            user_organization.org_type = org_type
            user_organization.save()
            user_extended_profile_data = {
                'is_first_learner': True,
                "organization_id": user_organization.id
            }
        else:
            if org_size:
                user_organization.total_employees = org_size

            if org_type:
                user_organization.org_type = org_type

            user_organization.save()

            user_extended_profile_data = {
                "organization_id": user_organization.id
            }

    # create User Extended Profile
    user_extended_profile = UserExtendedProfile.objects.create(user=user, **user_extended_profile_data)
    post_save.send(UserExtendedProfile, instance=user_extended_profile, created=False)

    # create user email preferences object
    EmailPreference.objects.create(user=user, opt_in=form.cleaned_data.get('opt_in'))

    return (user, profile, registration)


def create_account_with_params_custom(request, params):
    """
    Given a request and a dict of parameters (which may or may not have come
    from the request), create an account for the requesting user, including
    creating a comments service user object and sending an activation email.
    This also takes external/third-party auth into account, updates that as
    necessary, and authenticates the user for the request's session.

    Does not return anything.

    Raises AccountValidationError if an account with the username or email
    specified by params already exists, or ValidationError if any of the given
    parameters is invalid for any other reason.

    Issues with this code:
    * It is not transactional. If there is a failure part-way, an incomplete
      account will be created and left in the database.
    * Third-party auth passwords are not verified. There is a comment that
      they are unused, but it would be helpful to have a sanity check that
      they are sane.
    * It is over 300 lines long (!) and includes disprate functionality, from
      registration e-mails to all sorts of other things. It should be broken
      up into semantically meaningful functions.
    * The user-facing text is rather unfriendly (e.g. "Username must be a
      minimum of two characters long" rather than "Please use a username of
      at least two characters").
    """
    # Copy params so we can modify it; we can't just do dict(params) because if
    # params is request.POST, that results in a dict containing lists of values
    params = dict(params.items())

    if third_party_auth.is_enabled() and pipeline.running(request):
        running_pipeline = pipeline.get(request)

        if running_pipeline.get('backend'):
            params['provider'] = running_pipeline.get('backend')

        params['access_token'] = running_pipeline['kwargs']['response']['access_token']

    # Boolean of whether a 3rd party auth provider and credentials were provided in
    # the API so the newly created account can link with the 3rd party account.
    #
    # Note: this is orthogonal to the 3rd party authentication pipeline that occurs
    # when the account is created via the browser and redirect URLs.
    should_link_with_social_auth = third_party_auth.is_enabled() and 'provider' in params

    # if doing signup for an external authorization, then get email, password, name from the eamap
    # don't use the ones from the form, since the user could have hacked those
    # unless originally we didn't get a valid email or name from the external auth
    # TODO: We do not check whether these values meet all necessary criteria, such as email length
    do_external_auth = 'ExternalAuthMap' in request.session
    if do_external_auth:
        eamap = request.session['ExternalAuthMap']
        try:
            validate_email(eamap.external_email)
            params["email"] = eamap.external_email
        except ValidationError:
            pass
        if eamap.external_name.strip() != '':
            params["name"] = eamap.external_name
        params["password"] = eamap.internal_password
        log.debug(u'In create_account with external_auth: user = %s, email=%s', params["name"], params["email"])

    registration_fields = getattr(settings, 'REGISTRATION_EXTRA_FIELDS', {})

    params['name'] = "{} {}".format(
        params.get('first_name', '').encode('utf-8'), params.get('last_name', '').encode('utf-8')
    )

    form = AccountCreationForm(data=params, do_third_party_auth=do_external_auth)

    # Perform operations within a transaction that are critical to account creation
    with transaction.atomic():
        # first, create the account
        (user, profile, registration) = _do_create_account_custom(form)
        # next, link the account with social auth, if provided via the API.
        # (If the user is using the normal register page, the social auth pipeline does the linking, not this code)
        if should_link_with_social_auth:
            backend_name = params['provider']
            request.social_strategy = social_utils.load_strategy(request)
            redirect_uri = reverse('social:complete', args=(backend_name, ))
            request.backend = social_utils.load_backend(request.social_strategy, backend_name, redirect_uri)
            social_access_token = params.get('access_token')
            if not social_access_token:
                raise ValidationError({
                    'access_token': [
                        _("An access_token is required when passing value ({}) for provider.").format(
                            params['provider']
                        )
                    ]
                })
            request.session[pipeline.AUTH_ENTRY_KEY] = pipeline.AUTH_ENTRY_REGISTER_API
            pipeline_user = None
            error_message = ""
            try:
                pipeline_user = request.backend.do_auth(social_access_token, user=user)
            except AuthAlreadyAssociated:
                error_message = _("The provided access_token is already associated with another user.")
            except (HTTPError, AuthException):
                error_message = _("The provided access_token is not valid.")
            if not pipeline_user or not isinstance(pipeline_user, User):
                # Ensure user does not re-enter the pipeline
                request.social_strategy.clean_partial_pipeline()
                raise ValidationError({'access_token': [error_message]})

    # Perform operations that are non-critical parts of account creation
    preferences_api.set_user_preference(user, LANGUAGE_KEY, get_language())

    if settings.FEATURES.get('ENABLE_DISCUSSION_EMAIL_DIGEST'):
        try:
            enable_notifications(user)
        except Exception:  # pylint: disable=broad-except
            log.exception("Enable discussion notifications failed for user {id}.".format(id=user.id))

    # If the user is registering via 3rd party auth, track which provider they use
    third_party_provider = None
    running_pipeline = None
    if third_party_auth.is_enabled() and pipeline.running(request):
        running_pipeline = pipeline.get(request)
        third_party_provider = provider.Registry.get_from_pipeline(running_pipeline)
        # Store received data sharing consent field values in the pipeline for use
        # by any downstream pipeline elements which require them.
        running_pipeline['kwargs']['data_sharing_consent'] = form.cleaned_data.get('data_sharing_consent', None)

    # Track the user's registration
    if hasattr(settings, 'LMS_SEGMENT_KEY') and settings.LMS_SEGMENT_KEY:
        tracking_context = tracker.get_tracker().resolve_context()
        identity_args = [
            user.id,  # pylint: disable=no-member
            {
                'email': user.email,
                'username': user.username,
                'name': profile.name,
                # Mailchimp requires the age & yearOfBirth to be integers, we send a sane integer default if falsey.
                'age': profile.age or -1,
                'yearOfBirth': profile.year_of_birth or datetime.datetime.now(UTC).year,
                'education': profile.level_of_education_display,
                'address': profile.mailing_address,
                'gender': profile.gender_display,
                'country': unicode(profile.country),
            }
        ]

        if hasattr(settings, 'MAILCHIMP_NEW_USER_LIST_ID'):
            identity_args.append({
                "MailChimp": {
                    "listId": settings.MAILCHIMP_NEW_USER_LIST_ID
                }
            })

        analytics.identify(*identity_args)

        analytics.track(
            user.id,
            "edx.bi.user.account.registered",
            {
                'category': 'conversion',
                'label': params.get('course_id'),
                'provider': third_party_provider.name if third_party_provider else None
            },
            context={
                'ip': tracking_context.get('ip'),
                'Google Analytics': {
                    'clientId': tracking_context.get('client_id')
                }
            }
        )

    # Announce registration
    REGISTER_USER.send(sender=None, user=user, registration=registration)

    # Don't send email if we are:
    #
    # 1. Doing load testing.
    # 2. Random user generation for other forms of testing.
    # 3. External auth bypassing activation.
    # 4. Have the platform configured to not require e-mail activation.
    # 5. Registering a new user using a trusted third party provider (with skip_email_verification=True)
    #
    # Note that this feature is only tested as a flag set one way or
    # the other for *new* systems. we need to be careful about
    # changing settings on a running system to make sure no users are
    # left in an inconsistent state (or doing a migration if they are).
    send_email = (
        not settings.FEATURES.get('SKIP_EMAIL_VALIDATION', None) and
        not settings.FEATURES.get('AUTOMATIC_AUTH_FOR_TESTING') and
        not (do_external_auth and settings.FEATURES.get('BYPASS_ACTIVATION_EMAIL_FOR_EXTAUTH')) and
        not (
            third_party_provider and third_party_provider.skip_email_verification and
            user.email == running_pipeline['kwargs'].get('details', {}).get('email')
        )
    )
    if send_email:
        data = get_params_for_activation_email(request, registration, user)
        task_send_account_activation_email.delay(data)
    else:
        registration.activate()

    # Immediately after a user creates an account, we log them in. They are only
    # logged in until they close the browser. They can't log in again until they click
    # the activation link from the email.
    new_user = authenticate(username=user.username, password=params['password'])
    login(request, new_user)
    request.session.set_expiry(0)

    try:
        record_registration_attributions(request, new_user)
    # Don't prevent a user from registering due to attribution errors.
    except Exception:   # pylint: disable=broad-except
        log.exception('Error while attributing cookies to user registration.')

    # TODO: there is no error checking here to see that the user actually logged in successfully,
    # and is not yet an active user.
    if new_user is not None:
        AUDIT_LOG.info(u"Login success on new account creation - {0}".format(new_user.username))

    if do_external_auth:
        eamap.user = new_user
        eamap.dtsignup = datetime.datetime.now(UTC)
        eamap.save()
        AUDIT_LOG.info(u"User registered with external_auth %s", new_user.username)
        AUDIT_LOG.info(u'Updated ExternalAuthMap for %s to be %s', new_user.username, eamap)

        if settings.FEATURES.get('BYPASS_ACTIVATION_EMAIL_FOR_EXTAUTH'):
            log.info('bypassing activation email')
            new_user.is_active = True
            new_user.save()
            AUDIT_LOG.info(u"Login activated on extauth account - {0} ({1})".format(new_user.username, new_user.email))

    return new_user


def get_params_for_activation_email(request, registration, user):
    activation_link = '{protocol}://{site}/activate/{key}'.format(
        protocol='https' if request.is_secure() else 'http',
        site=safe_get_host(request),
        key=registration.activation_key
    )
    data = {
        "activation_link": activation_link,
        "user_email": user.email,
        'first_name': user.first_name,
    }

    return data


# noinspection PyMethodMayBeStatic
class RegistrationViewCustom(RegistrationView):
    """HTTP custom end-points for creating a new user. """
    THIRD_PARTY_OVERRIDE_FIELDS = RegistrationFormFactory.DEFAULT_FIELDS + ["first_name", "last_name"]

    @method_decorator(csrf_exempt)
    def post(self, request):
        """Create the user's account.

        You must send all required form fields with the request.

        You can optionally send a "course_id" param to indicate in analytics
        events that the user registered while enrolling in a particular course.

        Arguments:
        request (HTTPRequest)

        Returns:
        HttpResponse: 200 on success
        HttpResponse: 400 if the request is not valid.
        HttpResponse: 409 if an account with the given username or email
        address already exists
        """
        data = request.POST.copy()

        email = data.get('email')
        username = data.get('username')

        # Handle duplicate email/username
        conflicts = check_account_exists(email=email, username=username)
        if conflicts:
            conflict_messages = {
                "email": _(
                    # Translators: This message is shown to users who attempt to create a new
                    # account using an email address associated with an existing account.
                    u"It looks like {email_address} belongs to an existing account. "
                    u"Try again with a different email address."
                ).format(email_address=email),
                "username": _(
                    # Translators: This message is shown to users who attempt to create a new
                    # account using a username associated with an existing account.
                    u"The username you entered is already being used. Please enter another username."
                ).format(username=username),
            }
            errors = {
                field: [{"user_message": conflict_messages[field]}]
                for field in conflicts
            }
            return JsonResponse(errors, status=409)

        try:
            user = create_account_with_params_custom(request, data)
            self.save_user_utm_info(user)
        except ValidationError as err:
            # Should only get non-field errors from this function
            assert NON_FIELD_ERRORS not in err.message_dict
            # Only return first error for each field
            errors = {
                field: [{"user_message": error} for error in error_list]
                for field, error_list in err.message_dict.items()
            }
            return JsonResponse(errors, status=400)

        RegistrationType.objects.create(choice=1, user=request.user)
        response = JsonResponse({"success": True})
        set_logged_in_cookies(request, response, user)
        return response

    def save_user_utm_info(self, user):

        """
        :param user:
            user for which utm params are being saved + request to get all utm related params
        :return:
        """
        def extract_param_value(request, param_name):
            utm_value = request.POST.get(param_name, None)

            if not utm_value and param_name in request.session:
                utm_value = request.session[param_name]
                del request.session[param_name]

            return utm_value

        try:
            utm_source = extract_param_value(self.request, "utm_source")
            utm_medium = extract_param_value(self.request, "utm_medium")
            utm_campaign = extract_param_value(self.request, "utm_campaign")
            utm_content = extract_param_value(self.request, "utm_content")
            utm_term = extract_param_value(self.request, "utm_term")

            from openedx.features.user_leads.models import UserLeads
            UserLeads.objects.create(
                utm_source=utm_source,
                utm_medium=utm_medium,
                utm_campaign=utm_campaign,
                utm_content=utm_content,
                utm_term=utm_term,
                user=user
            )
        except Exception as ex:
            log.error("There is some error saving UTM {}".format(str(ex)))
            pass

    def _apply_third_party_auth_overrides(self, request, form_desc):
        """Modify the registration form if the user has authenticated with a third-party provider.
        If a user has successfully authenticated with a third-party provider,
        but does not yet have an account with PhilU, we want to fill in
        the registration form with any info that we get from the
        provider.
        Arguments:
            request (HttpRequest): The request for the registration form, used
                to determine if the user has successfully authenticated
                with a third-party provider.
            form_desc (FormDescription): The registration form description
        """
        if third_party_auth.is_enabled():
            running_pipeline = third_party_auth.pipeline.get(request)
            if running_pipeline:
                current_provider = third_party_auth.provider.Registry.get_from_pipeline(running_pipeline)

                if current_provider:
                    # Override username / email / full name
                    field_overrides = get_register_form_data_override(
                        running_pipeline.get('kwargs')
                    )

                    for field_name in self.THIRD_PARTY_OVERRIDE_FIELDS:
                        if field_name in field_overrides:

                            if field_name == 'username':
                                try:
                                    validate_slug(field_overrides[field_name])
                                except ValidationError:
                                    continue

                            form_desc.override_field_properties(
                                field_name, default=field_overrides[field_name]
                            )
