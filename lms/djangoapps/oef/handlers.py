from django.db.models.signals import post_save
from django.dispatch import receiver

from lms.djangoapps.oef.models import OrganizationOefScore, OrganizationOefUpdatePrompt
from lms.djangoapps.onboarding.helpers import convert_date_to_utcdatetime, its_been_year


@receiver(post_save, sender=OrganizationOefScore)
def update_oef_prompts(instance, **kwargs):
    this_oef_prompts = OrganizationOefUpdatePrompt.objects.filter(org_id=instance.org_id).first()

    # Prepare date for prompt against this save in Organization Metric
    finish_date = instance.finish_date

    # oef is not yet completed
    if not finish_date:
        return

    responsible_user = instance.org.admin or instance.user
    org = instance.org

    latest_finish_date = convert_date_to_utcdatetime(finish_date)
    year = its_been_year(latest_finish_date)

    # If prompts against this Oef already exists, update that prompt
    if this_oef_prompts:
        this_oef_prompts.responsible_user = responsible_user
        this_oef_prompts.latest_finish_date = latest_finish_date
        this_oef_prompts.year = year
        this_oef_prompts.save()
    else:
        # ceate a new prompt and save it
        prompt = OrganizationOefUpdatePrompt(responsible_user=responsible_user,
                                             org=org,
                                             latest_finish_date=finish_date,
                                             year=year
                                            )
        prompt.save()