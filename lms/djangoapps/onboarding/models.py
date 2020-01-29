import logging
import uuid
from datetime import datetime

import re
from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator, URLValidator
from django.db import models
from django.utils.translation import ugettext_noop
from model_utils.models import TimeStampedModel
from pytz import utc
from simple_history import register
from simple_history.models import HistoricalRecords
from student.models import UserProfile

from constants import ORG_PARTNERSHIP_END_DATE_PLACEHOLDER, REMIND_ME_LATER_KEY, REMIND_ME_LATER_VAL, \
    TAKE_ME_THERE_KEY, TAKE_ME_THERE_VAL, NOT_INTERESTED_KEY, NOT_INTERESTED_VAL

log = logging.getLogger("edx.onboarding")


# register User and UserProfile models for django-simple-history module
register(User, app=__package__, table_name='auth_historicaluser')
register(UserProfile, table_name='auth_historicaluserprofile')


class SchemaOrNoSchemaURLValidator(URLValidator):
    regex = re.compile(
        r'((([A-Za-z]{3,9}:(?:\/\/)?)(?:[-;:&=\+\$,\w]+@)?[A-Za-z0-9.-]'
        r'+|(?:www.|[-;:&=\+\$,\w]+@)[A-Za-z0-9.-]+)((?:\/[\+~%\/.\w-]*)'
        r'?\??(?:[-\+=&;%@.\w_]*)#?(?:[\w]*))?)',
        re.IGNORECASE
    )


class OrgSector(models.Model):
    """
    Specifies what sector the organization is working in.
    """
    order = models.SmallIntegerField(unique=True, null=True)
    code = models.CharField(max_length=10, unique=True)
    label = models.CharField(max_length=256)

    def __str__(self):
        return self.label

    @classmethod
    def get_map(cls):
        return {os.code: os.label for os in cls.objects.all()}

    class Meta:
        ordering = ['order']


class OperationLevel(models.Model):
    """
    Specifies the level of organization like national, international etc.
    """
    order = models.SmallIntegerField(unique=True, null=True)
    code = models.CharField(max_length=10, unique=True)
    label = models.CharField(max_length=256)

    def __str__(self):
        return self.label

    class Meta:
        ordering = ['order']


class FocusArea(models.Model):
    """
    The are of focus of an organization.
    """
    order = models.SmallIntegerField(unique=True, null=True)
    code = models.CharField(max_length=10, unique=True)
    label = models.CharField(max_length=256)

    def __str__(self):
        return self.label

    @classmethod
    def get_map(cls):
        return {fa.code: fa.label for fa in cls.objects.all()}

    class Meta:
        ordering = ['order']


class TotalEmployee(models.Model):
    """
    Total employees in an organization.
    """
    order = models.SmallIntegerField(unique=True, null=True)
    code = models.CharField(max_length=10, unique=True)
    label = models.CharField(max_length=256)

    def __str__(self):
        return self.label

    class Meta:
        ordering = ['order']


class PartnerNetwork(models.Model):
    """
    Specifies about the partner network being used in an organization.
    """

    NON_PROFIT_ORG_TYPE_CODE = "NPORG"

    order = models.SmallIntegerField(unique=True, null=True)
    code = models.CharField(max_length=10, unique=True)
    label = models.CharField(max_length=255)

    is_partner_affiliated = models.BooleanField(default=False)

    show_opt_in = models.BooleanField(default=False)
    affiliated_name = models.CharField(max_length=32, null=True, blank=True)
    program_name = models.CharField(max_length=64, null=True, blank=True)

    def __str__(self):
        return self.label

    class Meta:
        ordering = ['order']


class Currency(models.Model):
    country = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    alphabetic_code = models.CharField(max_length=255)
    number = models.CharField(max_length=255)
    minor_units = models.CharField(max_length=255)

    def __str__(self):
        return "%s %s %s" % (self.country, self.name, self.alphabetic_code if self.alphabetic_code else "N/A")


class EducationLevel(models.Model):
    """
    Models education level of the user
    """
    order = models.SmallIntegerField(unique=True, null=True)
    code = models.CharField(max_length=10, unique=True)
    label = models.CharField(max_length=256)

    def __str__(self):
        return self.label

    class Meta:
        ordering = ['order']


class EnglishProficiency(models.Model):
    """
    Models english proficiency level of the user.
    """
    order = models.SmallIntegerField(unique=True, null=True)
    code = models.CharField(max_length=10, unique=True)
    label = models.CharField(max_length=256)

    def __str__(self):
        return self.label

    class Meta:
        ordering = ['order']


class FunctionArea(models.Model):
    order = models.SmallIntegerField(unique=True, null=True)
    code = models.CharField(max_length=10, unique=True)
    label = models.CharField(max_length=255)

    def __str__(self):
        return self.label

    class Meta:
        ordering = ['order']


class Organization(TimeStampedModel):
    """
    Represents an organization.
    """

    label = models.CharField(max_length=255, db_index=True)
    admin = models.ForeignKey(User, related_name='organization', blank=True, null=True, on_delete=models.SET_NULL)
    country = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=255, blank=True, null=True)
    unclaimed_org_admin_email = models.EmailField(unique=True, blank=True, null=True)
    url = models.URLField(max_length=255, blank=True, null=True, validators=[SchemaOrNoSchemaURLValidator])
    founding_year = models.PositiveSmallIntegerField(blank=True, null=True)
    registration_number = models.CharField(max_length=30, blank=True, null=True)

    org_type = models.CharField(max_length=10, blank=True, null=True)
    level_of_operation = models.CharField(max_length=10, blank=True, null=True)
    focus_area = models.CharField(max_length=10, blank=True, null=True)
    total_employees = models.CharField(max_length=10, blank=True, null=True)

    alternate_admin_email = models.EmailField(blank=True, null=True)

    # If organization has affiliation with some affiliated partners,
    # this flag will be True
    has_affiliated_partner = models.BooleanField(default=False)

    history = HistoricalRecords()

    def users_count(self):
        """
        :return: Users count in an organization
        """
        return UserExtendedProfile.objects.filter(organization=self).count()

    @staticmethod
    def is_non_profit(user_extended_profile):
        """
        :return: Organization NP status
        """
        return True if user_extended_profile.organization and \
            user_extended_profile.organization.org_type == PartnerNetwork.NON_PROFIT_ORG_TYPE_CODE else False

    def admin_info(self):
        """
        :return: Information about the current admin of organization
        """
        return "%s" % self.admin.email if self.admin else "Administrator not assigned yet."

    def get_active_partners(self):
        """ Return list of active organization partners"""
        return self.organization_partners.filter(end_date__gt=datetime.utcnow()).values_list('partner', flat=True)

    def __unicode__(self):
        return self.label


class OrganizationPartner(models.Model):
    """
    The model to save the organization partners.
    """
    organization = models.ForeignKey(Organization, related_name='organization_partners')
    partner = models.CharField(max_length=10)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()

    def __unicode__(self):
        return "%s - %s" % (self.organization, self.partner)

    @classmethod
    def update_organization_partners(cls, organization, partners, removed_partners):
        """
        Add/Update partners data or an organization
        """

        # Set unchecked partners end date to today
        cls.objects.filter(organization=organization,
            partner__in=removed_partners, end_date__gt=datetime.utcnow()).update(
            end_date=datetime.now(utc))

        # Mark removed partner affliation flag to False if not selected in any organization
        _removed_partners = PartnerNetwork.objects.filter(code__in=removed_partners)
        for partner in _removed_partners:
            p = cls.objects.filter(partner=partner.code).first()
            if not p:
                partner.is_partner_affiliated = False
                partner.save()

        # Get already added partners for an organization
        no_updated_selections = cls.objects.filter(organization=organization,
            partner__in=partners, end_date__gt=datetime.utcnow()).values_list('partner', flat=True)

        # Filter out new/reselected Partners
        new_selections = [p for p in partners if p not in no_updated_selections]
        _partners = PartnerNetwork.objects.filter(code__in=new_selections)

        # Add new/reselected Partners and mark network as affiliated
        lst_to_create = []
        for partner in _partners:
            start_date = datetime.now()
            end_date = ORG_PARTNERSHIP_END_DATE_PLACEHOLDER
            obj = cls(organization=organization, partner=partner.code, start_date=start_date, end_date=end_date)
            lst_to_create.append(obj)

        cls.objects.bulk_create(lst_to_create)
        _partners.update(is_partner_affiliated=True)

        # Check if organization has any active grantee partners
        opted_partners = PartnerNetwork.objects.filter(
            show_opt_in=True
        ).values_list('code', flat=True)
        org_active_partners = organization.get_active_partners()
        has_affiliated_partner = True if list(set(opted_partners) & set(org_active_partners)) else False

        organization.has_affiliated_partner = has_affiliated_partner
        organization.save()


class GranteeOptIn(models.Model):
    agreed = models.BooleanField()
    organization_partner = models.ForeignKey(OrganizationPartner, related_name='grantee_opt_in')
    user = models.ForeignKey(User, related_name='grantee_opt_in')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return '%s-%s' % (self.user, self.created_at)


class RoleInsideOrg(models.Model):
    """
    Specifies what is the role of a user inside the organization.
    """
    order = models.SmallIntegerField(unique=True, null=True)
    code = models.CharField(max_length=10, unique=True)
    label = models.CharField(max_length=256)

    def __str__(self):
        return self.label

    class Meta:
        ordering = ['order']


class OrganizationAdminHashKeys(TimeStampedModel):
    """
    Model to hold hash keys for users that are suggested as admin for an organization
    """
    organization = models.ForeignKey(Organization, related_name='suggested_admins')
    suggested_by = models.ForeignKey(User)
    suggested_admin_email = models.EmailField()
    is_hash_consumed = models.BooleanField(default=False)
    activation_hash = models.CharField(max_length=32)

    def __str__(self):
        return "%s-%s" % (self.suggested_admin_email, self.activation_hash)

    @classmethod
    def assign_hash(cls, organization, suggested_by, suggested_admin_email):
        """
        Link a hash key to a user for administrator role confirmation
        """
        return cls.objects.create(organization=organization, suggested_by=suggested_by,
                                  suggested_admin_email=suggested_admin_email, activation_hash=uuid.uuid4().hex)


class UserExtendedProfile(TimeStampedModel):
    """
    Extra profile fields that we don't want to enter in user_profile to avoid code conflicts at edx updates
    """

    SURVEYS_LIST = ["user_info", "interests", "organization", "org_detail_survey"]
    SURVEYS_LIST_V2 = ["step1", "step2"]
    ORG_SURVEYS_LIST_V2 = ["step3", "step4", "step5"]

    FUNCTIONS_LABELS = {
        "0=function_strategy_planning": "Strategy and planning",
        "1=function_leadership_governance": "Leadership and governance",
        "2=function_program_design": "Program design and development",
        "3=function_measurement_eval": "Measurement, evaluation, and learning",
        "4=function_stakeholder_engagement": "External relations and partnerships",
        "5=function_human_resource": "Human resource management",
        "6=function_financial_management": "Financial management",
        "7=function_fundraising": "Fundraising and resource mobilization",
        "8=function_marketing_communication": "Marketing, communications, and PR",
        "9=function_system_tools": "Systems, tools, and processes",
    }

    INTERESTS_LABELS = {
        "0=interest_strategy_planning": "Strategy and planning",
        "1=interest_leadership_governance": "Leadership and governance",
        "2=interest_program_design": "Program design and development",
        "3=interest_measurement_eval": "Measurement, evaluation, and learning",
        "4=interest_stakeholder_engagement": "External relations and partnerships",
        "5=interest_human_resource": "Human resource management",
        "6=interest_financial_management": "Financial management",
        "7=interest_fundraising": "Fundraising and resource mobilization",
        "8=interest_marketing_communication": "Marketing, communications, and PR",
        "9=interest_system_tools": "Systems, tools, and processes",
    }

    INTERESTED_LEARNERS_LABELS = {
        "0=learners_same_region": "Learners from my region or country",
        "1=learners_similar_oe_interest": "Learners interested in same areas of organization effectiveness",
        "2=learners_similar_org": "Learners working for similar organizations",
        "3=learners_diff_who_are_different": "Learners who are different from me"
    }

    GOALS_LABELS = {
        "0=goal_contribute_to_org": "Help improve my organization",
        "1=goal_gain_new_skill": "Develop new skills",
        "2=goal_improve_job_prospect": "Get a job",
        "3=goal_relation_with_other": "Build relationships with other nonprofit leaders"
    }

    HEAR_ABOUT_PHILANTHROPY_LABELS = {
        "0=hear_about_philanthropy_partner": "A Philanthropy University Partner (Global Giving, +Acumen or another)",
        "1=hear_about_colleague_same_organization": "A Colleague From My Organization",
        "2=hear_about_friend_new_organization": "A Friend Or Colleague (Not From My Organization)",
        "3=hear_about_interest_search": "An Internet Search",
        "4=hear_about_linkedIn_advertisement": "A LinkedIn Advertisement",
        "5=hear_about_facebook_advertisement": "A Facebook Advertisement",
        "6=hear_about_twitter_not_colleague": "Twitter (Not From A Colleague)",
        "7=hear_about_other": "Other"
    }

    user = models.OneToOneField(User, unique=True, db_index=True, related_name='extended_profile')
    organization = models.ForeignKey(Organization, related_name='extended_profile', blank=True, null=True,
                                     on_delete=models.SET_NULL)
    country_of_employment = models.CharField(max_length=255, null=True)
    not_listed_gender = models.CharField(max_length=255, null=True, blank=True)
    city_of_employment = models.CharField(max_length=255, null=True)
    english_proficiency = models.CharField(max_length=10, null=True)
    start_month_year = models.CharField(max_length=100, null=True)
    role_in_org = models.CharField(max_length=10, null=True)
    hours_per_week = models.PositiveIntegerField("Typical Number of Hours Worked per Week*", default=0,
                                                 validators=[MaxValueValidator(168)], null=True)
    hear_about_philanthropy = models.CharField(max_length=255, null=True, blank=True)
    hear_about_philanthropy_other = models.CharField(max_length=255, default=None, null=True)

    # User functions related fields
    function_strategy_planning = models.SmallIntegerField(FUNCTIONS_LABELS["0=function_strategy_planning"], default=0)
    function_leadership_governance = models.SmallIntegerField(FUNCTIONS_LABELS["1=function_leadership_governance"], default=0)
    function_program_design = models.SmallIntegerField(FUNCTIONS_LABELS["2=function_program_design"], default=0)
    function_measurement_eval = models.SmallIntegerField(FUNCTIONS_LABELS["3=function_measurement_eval"], default=0)
    function_stakeholder_engagement = models.SmallIntegerField(FUNCTIONS_LABELS["4=function_stakeholder_engagement"], default=0)
    function_human_resource = models.SmallIntegerField(FUNCTIONS_LABELS["5=function_human_resource"], default=0)
    function_financial_management = models.SmallIntegerField(FUNCTIONS_LABELS["6=function_financial_management"], default=0)
    function_fundraising = models.SmallIntegerField(FUNCTIONS_LABELS["7=function_fundraising"], default=0)
    function_marketing_communication = models.SmallIntegerField(FUNCTIONS_LABELS["8=function_marketing_communication"], default=0)
    function_system_tools = models.SmallIntegerField(FUNCTIONS_LABELS["9=function_system_tools"], default=0)

    # User interests related fields
    interest_strategy_planning = models.SmallIntegerField(INTERESTS_LABELS["0=interest_strategy_planning"], default=0)
    interest_leadership_governance = models.SmallIntegerField(INTERESTS_LABELS["1=interest_leadership_governance"], default=0)
    interest_program_design = models.SmallIntegerField(INTERESTS_LABELS["2=interest_program_design"], default=0)
    interest_measurement_eval = models.SmallIntegerField(INTERESTS_LABELS["3=interest_measurement_eval"], default=0)
    interest_stakeholder_engagement = models.SmallIntegerField(INTERESTS_LABELS["4=interest_stakeholder_engagement"], default=0)
    interest_human_resource = models.SmallIntegerField(INTERESTS_LABELS["5=interest_human_resource"], default=0)
    interest_financial_management = models.SmallIntegerField(INTERESTS_LABELS["6=interest_financial_management"], default=0)
    interest_fundraising = models.SmallIntegerField(INTERESTS_LABELS["7=interest_fundraising"], default=0)
    interest_marketing_communication = models.SmallIntegerField(INTERESTS_LABELS["8=interest_marketing_communication"], default=0)
    interest_system_tools = models.SmallIntegerField(INTERESTS_LABELS["9=interest_system_tools"], default=0)

    # Learners related field
    learners_same_region = models.SmallIntegerField(INTERESTED_LEARNERS_LABELS["0=learners_same_region"],
                                                    default=0)
    learners_similar_oe_interest = models.SmallIntegerField(INTERESTED_LEARNERS_LABELS["1=learners_similar_oe_interest"],
                                                            default=0)
    learners_similar_org = models.SmallIntegerField(INTERESTED_LEARNERS_LABELS["2=learners_similar_org"], default=0)
    learners_diff_who_are_different = models.SmallIntegerField(
        INTERESTED_LEARNERS_LABELS["3=learners_diff_who_are_different"], default=0)

    # User goals related fields
    goal_contribute_to_org = models.SmallIntegerField(GOALS_LABELS["0=goal_contribute_to_org"], default=0)
    goal_gain_new_skill = models.SmallIntegerField(GOALS_LABELS["1=goal_gain_new_skill"], default=0)
    goal_improve_job_prospect = models.SmallIntegerField(GOALS_LABELS["2=goal_improve_job_prospect"], default=0)
    goal_relation_with_other = models.SmallIntegerField(GOALS_LABELS["3=goal_relation_with_other"], default=0)

    is_interests_data_submitted = models.BooleanField(default=False)
    is_organization_metrics_submitted = models.BooleanField(default=False)
    is_first_learner = models.BooleanField(default=False)
    is_alquity_user = models.BooleanField(default=False)

    history = HistoricalRecords()

    def __str__(self):
        return str(self.user)

    def get_user_selected_functions(self, _type="labels"):
        """
        :return: Users selected function areas
        :param _type: labels / fields
        :return: list of labels / names of fields
        """
        if _type == "labels":
            return [label for field_name, label in self.FUNCTIONS_LABELS.items() if
                    getattr(self, field_name.split("=")[1]) == 1]
        else:
            return [field_name for field_name, label in self.FUNCTIONS_LABELS.items() if
                    getattr(self, field_name.split("=")[1]) == 1]

    def get_user_selected_interests(self, _type="labels"):
        """
        :return: Users selected interest
        :param _type: labels / fields
        :return: list of labels / names of fields
        """
        if _type == "labels":
            return [label for field_name, label in self.INTERESTS_LABELS.items() if
                    getattr(self, field_name.split("=")[1]) == 1]
        else:
            return [field_name for field_name, label in self.INTERESTS_LABELS.items() if
                    getattr(self, field_name.split("=")[1]) == 1]

    def get_user_selected_interested_learners(self, _type="labels"):
        """
        :return: Users selected interested learners
        :param _type: labels / fields
        :return: list of labels / names of fields
        """

        if _type == "labels":
            return [label for field_name, label in self.INTERESTED_LEARNERS_LABELS.items() if
                    getattr(self, field_name.split("=")[1]) == 1]
        else:
            return [field_name for field_name, label in self.INTERESTED_LEARNERS_LABELS.items() if
                    getattr(self, field_name.split("=")[1]) == 1]

    def get_user_selected_personal_goal(self, _type="labels"):
        """
        :return: Users selected personal goals
        :param _type: labels / fields
        :return: list of labels / names of fields
        """

        if _type == "labels":
            return [label for field_name, label in self.GOALS_LABELS.items() if
                    getattr(self, field_name.split("=")[1]) == 1]
        else:
            return [field_name for field_name, label in self.GOALS_LABELS.items() if
                    getattr(self, field_name.split("=")[1]) == 1]

    def get_user_hear_about_philanthropy(self, _type="labels"):
        """
        :return: Users selected here about philanthropy university
        :param _type: labels / fields
        :return: list of labels / names of fields
        """
        if _type == "labels":
            _field_label_data = [label for field_name, label in self.GOALS_LABELS.items() if
                                 getattr(self, 'hear_about_philanthropy') ==
                                 self.HEAR_ABOUT_PHILANTHROPY_LABELS.get(field_name)]
        else:
            _field_label_data = [field_name for field_name, label in self.HEAR_ABOUT_PHILANTHROPY_LABELS.items() if
                                 getattr(self, 'hear_about_philanthropy') ==
                                 self.HEAR_ABOUT_PHILANTHROPY_LABELS.get(field_name)]
        return _field_label_data if not _field_label_data else _field_label_data[0]

    def save_user_hear_about_philanthropy_result(self, selected_values, _other_field):
        _updated_value_about_philanthropy = None
        _updated_value_about_philanthropy_other = None

        for function_area_field, label in self.HEAR_ABOUT_PHILANTHROPY_LABELS.items():
            _function_area_field = function_area_field.split("=")[1]
            if _function_area_field in selected_values:
                _updated_value_about_philanthropy = self.HEAR_ABOUT_PHILANTHROPY_LABELS.get(function_area_field)
            if _function_area_field == 'hear_about_other' and _other_field:
                _updated_value_about_philanthropy_other = _other_field[0]

        self.__setattr__('hear_about_philanthropy', _updated_value_about_philanthropy)
        self.__setattr__('hear_about_philanthropy_other', _updated_value_about_philanthropy_other)

    def save_user_function_areas(self, selected_values):
        """
        Save users selected function areas
        :param selected_values: selected values list
        """

        for function_area_field, label in self.FUNCTIONS_LABELS.items():
            function_area_field = function_area_field.split("=")[1]
            if function_area_field in selected_values:
                _updated_value = 1
            else:
                _updated_value = 0

            self.__setattr__(function_area_field, _updated_value)

    def save_user_interests(self, selected_values):
        """
        Save users selected interests
        :param selected_values: selected values list
        """

        for interest_field, label in self.INTERESTS_LABELS.items():
            interest_field = interest_field.split("=")[1]
            if interest_field in selected_values:
                _updated_value = 1
            else:
                _updated_value = 0

            self.__setattr__(interest_field, _updated_value)

    def save_user_interested_learners(self, selected_values):
        """
        Save users selected interested learners
        :param selected_values: selected values list
        """

        for interested_learner_field, label in self.INTERESTED_LEARNERS_LABELS.items():
            interested_learner_field = interested_learner_field.split("=")[1]
            if interested_learner_field in selected_values:
                _updated_value = 1
            else:
                _updated_value = 0

            self.__setattr__(interested_learner_field, _updated_value)

    def is_organization_data_filled(self):
        """
        Return status for registration third step completion
        """
        return self.organization.org_type and self.organization.focus_area and self.organization.level_of_operation \
               and self.organization.total_employees

    def is_organization_details_filled(self):
        """
        :return: Status for registration fourth step completion
        """
        return self.is_organization_metrics_submitted

    def save_user_personal_goals(self, selected_values):
        """
        Save data for users personal goals
        :param selected_values: list of selected goals
        """

        for goal_field, label in self.GOALS_LABELS.items():
            goal_field = goal_field.split("=")[1]
            if goal_field in selected_values:
                _updated_value = 1
            else:
                _updated_value = 0

            self.__setattr__(goal_field, _updated_value)

    def get_normal_user_attend_surveys(self):
        """
        :return: List of attended surveys that a simple learner can attend
        """
        attended_list = []

        if (not self.organization and self.user.profile.level_of_education and self.english_proficiency) or (
                self.organization and self.user.profile.level_of_education and self.start_month_year and
                self.english_proficiency):
            attended_list.append(self.SURVEYS_LIST[0])
        if self.is_interests_data_submitted:
            attended_list.append(self.SURVEYS_LIST[1])

        return attended_list

    def get_normal_user_attend_surveys_v2(self):
        """
        :return: List of attended surveys that a simple learner can attend
        """
        attended_list = []

        if self.user.profile.level_of_education and self.english_proficiency:
            attended_list.append(self.SURVEYS_LIST_V2[0])
        if self.is_interests_data_submitted:
            attended_list.append(self.SURVEYS_LIST_V2[1])

        return attended_list

    def get_admin_or_first_user_attend_surveys(self):
        """
        :return: List of attended surveys that a first learner OR admin can attend
        """
        attended_list = self.get_normal_user_attend_surveys()

        if self.is_organization_data_filled():
            attended_list.append(self.SURVEYS_LIST[2])
        if self.is_organization_details_filled() \
                and self.organization.org_type == PartnerNetwork.NON_PROFIT_ORG_TYPE_CODE:
            attended_list.append(self.SURVEYS_LIST[3])

        return attended_list

    def get_org_normal_user_attend_surveys(self):
        """
        :return: List of attended surveys that a simple learner can attend
        """
        attended_list = []

        if not self.organization:
            return self.ORG_SURVEYS_LIST_V2

        if self.organization and self.start_month_year:
            attended_list.append(self.ORG_SURVEYS_LIST_V2[0])

        return attended_list

    def get_org_admin_or_first_user_attend_surveys(self):
        """
        :return: List of attended surveys that a first learner OR admin can attend
        """
        attended_list = self.get_org_normal_user_attend_surveys()

        if self.is_organization_data_filled():
            attended_list.append(self.ORG_SURVEYS_LIST_V2[1])
        if self.is_organization_details_filled() \
                and self.organization.org_type == PartnerNetwork.NON_PROFIT_ORG_TYPE_CODE:
            attended_list.append(self.ORG_SURVEYS_LIST_V2[2])

        return attended_list

    def surveys_to_attend(self):
        """
        :return: List of survey for a user to attend depending on the user type (admin/first user in org/non-admin)
        """
        surveys_to_attend = self.SURVEYS_LIST[:2]
        if self.organization and (self.is_organization_admin or self.is_first_signup_in_org):
            surveys_to_attend = self.SURVEYS_LIST[:3]

        if self.organization and self.organization.org_type == PartnerNetwork.NON_PROFIT_ORG_TYPE_CODE \
                and (self.is_organization_admin or self.is_first_signup_in_org):
            surveys_to_attend = self.SURVEYS_LIST

        return surveys_to_attend

    def attended_surveys(self):
        """
        :return: List of user's attended on-boarding surveys
        """

        if not (self.organization and (self.is_organization_admin or self.is_first_signup_in_org)):
            attended_list = self.get_normal_user_attend_surveys()
        else:
            attended_list = self.get_admin_or_first_user_attend_surveys()

        return attended_list

    def unattended_surveys(self, _type="map"):
        """
        :return: Mapping of user's unattended on-boarding surveys
        """

        surveys_to_attend = self.surveys_to_attend()

        if _type == "list":
            return [s for s in surveys_to_attend if s not in self.attended_surveys()]

        return {s: True if s in self.attended_surveys() else False for s in surveys_to_attend}

    def surveys_to_attend_v2(self):
        """
        :return: List of survey for a user to attend depending on the user type (admin/first user in org/non-admin)
        """
        return self.SURVEYS_LIST_V2

    def org_surveys_to_attend(self):
        """
        :return: List of survey for a user to attend depending on the user type (admin/first user in org/non-admin)
        """
        surveys_to_attend = []

        if self.organization:
            surveys_to_attend.append(self.ORG_SURVEYS_LIST_V2[0])

        if self.is_first_signup_in_org:
            surveys_to_attend.append(self.ORG_SURVEYS_LIST_V2[1])

        if self.is_organization_admin and self.organization.org_type == PartnerNetwork.NON_PROFIT_ORG_TYPE_CODE:
            surveys_to_attend.append(self.ORG_SURVEYS_LIST_V2[2])

        return surveys_to_attend

    def attended_surveys_v2(self):
        """
        :return: List of user's attended on-boarding surveys
        """
        return self.get_normal_user_attend_surveys_v2()

    def org_attended_surveys(self):
        """
        :return: List of user's attended on-boarding surveys
        """

        if not (self.organization and (self.is_organization_admin or self.is_first_signup_in_org)):
            attended_list = self.get_org_normal_user_attend_surveys()
        else:
            attended_list = self.get_org_admin_or_first_user_attend_surveys()

        return attended_list

    def unattended_surveys_v2(self, _type="map"):
        """
        :return: Mapping of user's unattended on-boarding surveys
        """

        surveys_to_attend = self.surveys_to_attend_v2()
        attended_surveys = self.attended_surveys_v2()

        if _type == "list":
            return [s for s in surveys_to_attend if s not in attended_surveys]

        return {s: True if s in attended_surveys else False for s in surveys_to_attend}

    def org_unattended_surveys_v2(self, _type="map"):
        """
        :return: Mapping of user's unattended on-boarding surveys
        """

        surveys_to_attend = self.org_surveys_to_attend()
        org_attended_surveys = self.org_attended_surveys()

        if _type == "list":
            return [s for s in surveys_to_attend if s not in org_attended_surveys]

        return {s: True if s in org_attended_surveys else False for s in surveys_to_attend}

    @property
    def is_organization_admin(self):
        """
        :return: User organization administration status
        """
        if self.organization:
            return self.user == self.organization.admin

        return False

    def admin_has_pending_admin_suggestion_request(self):
        pending_suggestion_request = OrganizationAdminHashKeys.objects.filter(organization=self.organization,
                                                                               suggested_by=self.user,
                                                                               is_hash_consumed=False).first()
        return bool(self.is_organization_admin and pending_suggestion_request)

    @property
    def is_first_signup_in_org(self):
        """
        :return: User is first learner OR not
        """
        return self.is_first_learner

    def has_submitted_oef(self):
        """
        :return: User has taken OEF OR not
        """
        taken_oef = False

        if self.organization:
            taken_oef = bool(self.user.organization_oef_scores.filter(org=self.organization, user=self.user).exclude(
                finish_date__isnull=True))

        return self.organization and taken_oef


class EmailPreference(TimeStampedModel):
    user = models.OneToOneField(User, related_name="email_preferences")
    opt_in = models.CharField(max_length=5, default=None, null=True, blank=True)

    def __str__(self):
        return "%s %s" % (self.user.email, self.opt_in)


class OrganizationMetric(TimeStampedModel):
    """
    Model to save organization metrics
    """
    ACTUAL_DATA_CHOICES = (
        (0, "Estimated - My answers are my best guesses based on my knowledge of the organization"),
        (1, "Actual - My answers come directly from my organization's official documentation")
    )

    org = models.ForeignKey(Organization, related_name="organization_metrics")
    user = models.ForeignKey(User, related_name="organization_metrics")
    submission_date = models.DateTimeField(auto_now_add=True)
    actual_data= models.NullBooleanField(choices=ACTUAL_DATA_CHOICES, blank=True, null=True)
    effective_date = models.DateField(blank=True, null=True)
    total_clients = models.PositiveIntegerField(blank=True, null=True)
    total_employees = models.PositiveIntegerField(blank=True, null=True)
    local_currency = models.CharField(max_length=10, blank=True, null=True)
    total_revenue = models.BigIntegerField(blank=True, null=True)
    total_donations = models.BigIntegerField(blank=True, null=True)
    total_expenses = models.BigIntegerField(blank=True, null=True)
    total_program_expenses = models.BigIntegerField(blank=True, null=True)


class OrganizationMetricUpdatePrompt(models.Model):
    org = models.ForeignKey(Organization, related_name="organization_metrics_update_prompts")
    responsible_user = models.ForeignKey(User, related_name="organization_metrics_update_prompts")
    latest_metric_submission = models.DateTimeField()
    year = models.BooleanField(default=False)
    year_month = models.BooleanField(default=False)
    year_three_month = models.BooleanField(default=False)
    year_six_month = models.BooleanField(default=False)
    # None(Python)/Null(MySQL): we can remind learner, True: learner clicked `Remind Me Later`,
    # False:  learner clicked `No Thanks`
    remind_me_later = models.NullBooleanField()

    def __unicode__(self):
        return '{}, {}'.format(self.responsible_user.username, self.org.label.encode('utf-8'))


class MetricUpdatePromptRecord(TimeStampedModel):
    prompt = models.ForeignKey(OrganizationMetricUpdatePrompt, on_delete=models.CASCADE,
                               related_name="metrics_update_prompt_records")
    CLICK_CHOICES = (
        (REMIND_ME_LATER_KEY, ugettext_noop(REMIND_ME_LATER_VAL)),
        (TAKE_ME_THERE_KEY, ugettext_noop(TAKE_ME_THERE_VAL)),
        (NOT_INTERESTED_KEY, ugettext_noop(NOT_INTERESTED_VAL))
    )
    click = models.CharField(
        null=True, max_length=3, db_index=True, choices=CLICK_CHOICES
    )


class RegistrationType(models.Model):
    user = models.OneToOneField(
        User,
        unique=True,
        db_index=True,
        on_delete=models.CASCADE,
        related_name='registration_type'
    )
    choice = models.SmallIntegerField(default=1, null=False)

class LinkedInEducation(models.Model):
    """
    Model to store user education information from linkedin
    """
    user = models.ForeignKey(User, related_name='linkedin_education')
    school_name = models.CharField(max_length=100, null=True, blank=True)
    degree_name = models.CharField(max_length=100, null=True, blank=True)
    start_month_year = models.DateField(null=True, blank=True)
    end_month_year = models.DateField(null=True, blank=True)
    description = models.CharField(max_length=500, blank=True, null=True)


class LinkedInExperience(models.Model):
    """
    Model to store user experience from linkedin
    """
    user = models.ForeignKey(User, related_name='linkedin_experience')
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    is_current = models.BooleanField(default=False)
    title = models.CharField(max_length=50, null=True, blank=True)
    company = models.CharField(max_length=100, null=True, blank=True)
    summary = models.CharField(max_length=500, null=True, blank=True)


class LinkedInSkills(models.Model):
    """
    Model to store user skills from linkedin
    """
    user = models.ForeignKey(User, related_name='linkedin_skills')
    name = models.CharField(max_length=50, null=True, blank=True)
