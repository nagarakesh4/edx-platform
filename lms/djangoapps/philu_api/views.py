"""
restAPI Views
"""
import json
import logging
import requests
import urllib

from rest_framework import status
from rest_framework.views import APIView
from util.json_request import expect_json
from wsgiref.util import FileWrapper

from django.conf import settings
from django.http import JsonResponse, HttpResponse, Http404
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt

from celery.result import AsyncResult
from common.lib.mandrill_client.client import MandrillClient
from openedx.core.djangoapps.site_configuration import helpers as configuration_helpers
from openedx.features.badging.models import Badge, UserBadge

from lms.djangoapps.oef.decorators import eligible_for_oef
from lms.djangoapps.onboarding.helpers import get_org_metric_update_prompt
from lms.djangoapps.onboarding.models import MetricUpdatePromptRecord
from lms.djangoapps.philu_api.helpers import get_encoded_token
from lms.djangoapps.third_party_surveys.tasks import get_third_party_surveys_task

from mailchimp_pipeline.tasks import update_enrollments_completions_at_mailchimp
from student.models import User
from philu_overrides.helpers import reactivation_email_for_user_custom


log = logging.getLogger("edx.philu_api")


class MailChimpDataSyncAPI(APIView):

    def get(self, request):
        """ Send data shared between platform & community """
        #
        if request.GET.get('task_id'):

            res = AsyncResult(request.GET.get('task_id'))

            return JsonResponse({
                'state': res.state,
                'task_id': request.GET.get('task_id')
            }, status=status.HTTP_200_OK)

        x = update_enrollments_completions_at_mailchimp.delay(settings.MAILCHIMP_LEARNERS_LIST_ID)

        return JsonResponse({
            'state': "STARTED",
            'task_id': x.task_id
        }, status=status.HTTP_200_OK)


class ThirdPartyResultDataSyncAPI(APIView):

    def get(self, request):
        """ Get data shared between platform & community """

        if request.GET.get('task_id'):

            res = AsyncResult(request.GET.get('task_id'))

            return JsonResponse({
                'state': res.state,
                'task_id': request.GET.get('task_id')
            }, status=status.HTTP_200_OK)

        x = get_third_party_surveys_task.delay()

        return JsonResponse({
            'state': "STARTED",
            'task_id': x.task_id
        }, status=status.HTTP_200_OK)


class PlatformSyncService(APIView):

    def get(self, request):
        """ Send data shared between platform & community """

        username = request.GET.get("username")
        email = request.GET.get("email")

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return JsonResponse({"message": "User does not exist for provided username"},
                                status=status.HTTP_400_BAD_REQUEST)

        _id = user.id

        token = request.META["HTTP_X_CSRFTOKEN"]
        if not token == get_encoded_token(username, email, _id):
            return JsonResponse({"message": "Invalid Session token"}, status=status.HTTP_400_BAD_REQUEST)

        user_extended_profile = user.extended_profile
        return JsonResponse({
            "is_admin": user_extended_profile.is_organization_admin,
            "eligible_for_oef": eligible_for_oef(user_extended_profile),
            "help_center": configuration_helpers.get_value('SUPPORT_SITE_LINK', settings.SUPPORT_SITE_LINK)
        }, status=status.HTTP_200_OK)

    def post(self, request):
        """ Update provided information in openEdx received from nodeBB client """

        username = request.GET.get("username")
        email = request.GET.get("email")

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return JsonResponse({"message": "User does not exist for provided username"}, status=status.HTTP_400_BAD_REQUEST)

        _id = user.id

        token = request.META["HTTP_X_CSRFTOKEN"]
        if not token == get_encoded_token(username, email, _id):
            return JsonResponse({"message": "Invalid Session token"}, status=status.HTTP_400_BAD_REQUEST)

        userprofile = user.profile
        data = request.data

        try:
            first_name = data.get('first_name', user.first_name)
            last_name = data.get('last_name', user.last_name)
            birthday = data.get('birthday')

            about_me = data.get('aboutme', userprofile.bio)

            if birthday:
                birthday_year = birthday.split("/")[2]
            else:
                birthday_year = userprofile.year_of_birth

            user.first_name = first_name
            user.last_name = last_name

            user.profile.bio = about_me

            if birthday:
                userprofile.year_of_birth = int(birthday_year)

            user.save()
            userprofile.save()

            return JsonResponse({"message": "user info updated successfully"}, status=status.HTTP_200_OK)
        except Exception as ex:
            return JsonResponse({"message": str(ex.args)}, status=status.HTTP_400_BAD_REQUEST)


class UpdatePromptClickRecord(APIView):
    def post(self, request):
        user = request.user
        # make sure user is responsible for some organization
        metric_update_prompt = get_org_metric_update_prompt(request.user)
        if (metric_update_prompt):
            click = request.POST.get('click', None)
            if click in dict(MetricUpdatePromptRecord.CLICK_CHOICES):
                record = MetricUpdatePromptRecord()
                record.prompt = metric_update_prompt
                record.click = click
                record.save()
                return JsonResponse({'success': True})
        return JsonResponse({'success': False}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)


@require_POST
@expect_json
@csrf_exempt
def assign_user_badge(request):
    data = json.loads(request.body)
    user_id = data.get('user_id')
    badge_id = data.get('badge_id')
    community_id = data.get('community_id')
    master_token = data.get('token')

    if not master_token == settings.NODEBB_MASTER_TOKEN:
        return JsonResponse({'success': False, 'message': 'Invalid master token'},
                            status=status.HTTP_403_FORBIDDEN)

    try:
        UserBadge.assign_badge(user_id=user_id,
                               badge_id=badge_id,
                               community_id=community_id)
        return JsonResponse({'success': True})
    except Exception as e:
        logging.exception(e)
        return JsonResponse({'success': False, 'message': str(e)},
                            status=status.HTTP_400_BAD_REQUEST)


def get_user_chat(request):
    """ Get recent chats of the user from NodeBB """
    chat_endpoint = settings.NODEBB_ENDPOINT + '/api/v2/users/chats'
    username = request.user.username
    headers = {'Authorization': 'Bearer ' + settings.NODEBB_MASTER_TOKEN}
    response = requests.post(chat_endpoint,
        data={'_uid': 1, 'username': username},
        headers=headers)
    return JsonResponse(response.json())


def mark_user_chat_read(request):
    """ Mark all chats of the user as read """
    chat_endpoint = settings.NODEBB_ENDPOINT + '/api/v2/users/chats'
    username = request.user.username
    headers = {'Authorization': 'Bearer ' + settings.NODEBB_MASTER_TOKEN}
    response = requests.patch(chat_endpoint,
        data={'_uid': 1, 'username': username},
        headers=headers)
    return JsonResponse(response.json())


def get_user_data(request):
    """ Get the user profile data from NodeBB for current user """
    data_endpoint = settings.NODEBB_ENDPOINT + '/api/v2/users/data'
    username = request.POST.get("username")
    headers = {'Authorization': 'Bearer ' + settings.NODEBB_MASTER_TOKEN}
    response = requests.post(data_endpoint,
        data={'_uid': 1, 'username': username},
        headers=headers)
    return JsonResponse(response.json())


def download_pdf_file(request):
    """ Download pdf file (Worksheet) instead of opening in the browser """
    query_string = request.META.get('QUERY_STRING')
    page_url = query_string.split('page_url=')[-1]
    if page_url and request.GET:
        filename = page_url.split("/")[-1]
        filename = filename.replace(" ", "_")
        result = urllib.urlopen(page_url)
        response = HttpResponse(FileWrapper(result.fp), content_type='application/pdf')
        response['Content-Length'] = result.headers['content-length']
        response['Content-Disposition'] = "attachment; filename={}".format(filename)
        return response
    else:
        raise Http404


def send_alquity_fake_confirmation_email(request):
    """ Send fake confirmation to current user as as he submit by fake button in last module of a course  """
    success = True
    try:
        ctx = {
            "full_name": request.user.get_full_name(),
            "course_name": request.META.get('HTTP_COURSE_NAME', '')
        }
        MandrillClient().send_mail(MandrillClient.ALQUITY_FAKE_SUBMIT_CONFIRMATION_TEMPLATE, request.user.email, ctx)
    except Exception as ex:
        logging.exception(ex)
        success = False
    return JsonResponse({'success': success})


def resend_activation_email(request):
    user = request.user
    activated = user.is_active
    try:
        if not activated:
            reactivation_email_for_user_custom(request, user)
            return JsonResponse({'success': True, 'email': user.email}, status=status.HTTP_200_OK)
        else:
            # the user's account has already been activated
            return JsonResponse({'success': False}, status=status.HTTP_409_CONFLICT)
    except Exception as ex:
        logging.exception(ex)
        return JsonResponse({'success': False}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
