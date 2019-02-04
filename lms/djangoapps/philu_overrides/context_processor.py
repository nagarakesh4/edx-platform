from django.conf import settings

from lms.djangoapps.onboarding.helpers import get_org_metric_update_prompt, \
    is_org_detail_prompt_available, is_org_detail_platform_overlay_available
from lms.djangoapps.philu_overrides.constants import ACTIVATION_ERROR, ACTIVATION_ALERT_TYPE, \
    ORG_DETAILS_UPDATE_ALERT, ORG_DETAILS_UPDATE_OVERLAY_ALERT


def get_global_alert_messages(request):

    """
    function to get application wide messages
    :param request:
    :return: returns list of global messages"
    """

    alert_messages = []
    overlay_message = None
    metric_update_prompt = get_org_metric_update_prompt(request.user)
    show_org_detail_prompt = metric_update_prompt and is_org_detail_prompt_available(metric_update_prompt)
    if not request.is_ajax():
        if request.user.is_authenticated() and not request.user.is_active and '/activate/' not in request.path:
            alert_messages.append({
                "type": ACTIVATION_ALERT_TYPE,
                "alert": ACTIVATION_ERROR
            })

    if '/organization/details/' in request.path and show_org_detail_prompt:
        alert_messages.append({
            "type": ACTIVATION_ALERT_TYPE,
            "alert": ORG_DETAILS_UPDATE_ALERT
        })

    elif metric_update_prompt and show_org_detail_prompt\
            and is_org_detail_platform_overlay_available(metric_update_prompt):
        overlay_message = {
            "alert": ORG_DETAILS_UPDATE_OVERLAY_ALERT,
        }

    return {"alert_messages": alert_messages, "overlay_message": overlay_message}


def add_nodebb_endpoint(request):
    """
    Add our NODEBB_ENDPOINT to the template context so that it can be referenced by any client side code.
    """
    return { "nodebb_endpoint": settings.NODEBB_ENDPOINT }
