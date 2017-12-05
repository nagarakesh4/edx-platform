from datetime import datetime

import pytz
from celery.schedules import crontab
from celery.task import periodic_task

from common.lib.surveygizmo_client.client import SurveyGizmoClient
from lms.djangoapps.third_party_surveys.models import ThirdPartySurvey


@periodic_task(run_every=crontab(minute=1, hour=12))
def get_third_party_surveys():
    """
    Periodic Task that will run on daily basis and will sync the response data
    of all surveys thorough Survey Gizmo APIs
    """
    try:
        last_survey = ThirdPartySurvey.objects.latest('request_date')
        filters = [('datesubmitted', '>', last_survey.request_date)]
    except ThirdPartySurvey.DoesNotExist:
        filters = []

    survey_responses = SurveyGizmoClient().get_filtered_survey_responses(survey_filters=filters)
    save_responses(survey_responses)


def save_responses(survey_responses):
    for response in survey_responses:
        if not response.get('[url("sguid")]'):
            continue

        date = datetime.strptime(response['datesubmitted'], "%Y-%m-%d %H:%M:%S")
        date = pytz.utc.localize(date)

        third_party_survey = ThirdPartySurvey(
            response=response,
            user_id=response['[url("sguid")]'],
            request_date=date
        )
        third_party_survey.save()
