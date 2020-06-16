from celery.task import task
from django.conf import settings

from common.lib.mandrill_client.client import MandrillClient


@task(routing_key=settings.HIGH_PRIORITY_QUEUE)
def task_send_referral_and_toolkit_emails(contact_emails, user_email):
    """Send initial referral email to all contact emails and send toolkit email to referrer."""
    mandrill_client = MandrillClient()

    for email in contact_emails:
        mandrill_client.send_mail(MandrillClient.REFERRAL_INITIAL_EMAIL, email, context={
            'root_url': settings.LMS_ROOT_URL,
        })

    mandrill_client.send_mail(MandrillClient.REFERRAL_SOCIAL_IMPACT_TOOLKIT, user_email, context={})
