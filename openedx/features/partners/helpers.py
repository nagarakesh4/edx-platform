from datetime import datetime
import pytz

from course_action_state.models import CourseRerunState
from openedx.core.djangoapps.content.course_overviews.models import CourseOverview

from custom_settings.models import CustomSettings

from openedx.features.course_card.helpers import get_related_card_id
from openedx.features.course_card.models import CourseCard


def get_partner_recommended_courses(partner_slug):
    """
    get recommend courses those are tagged with partner's slug
    :param partner_slug: slug of partner with which courses are tagged
    :return: recommended courses
    """
    recommended_courses = []
    current_time = datetime.utcnow().replace(tzinfo=pytz.UTC)

    partner_course_settings = CustomSettings.objects.filter(tags__icontains=partner_slug).all()

    # Make a set of card id's to remove duplication
    partner_course_card_ids = {get_related_card_id(crs_setting.id) for crs_setting in partner_course_settings}

    for course_id in partner_course_card_ids:
        course_reruns = [crs.course_key for crs in CourseRerunState.objects.filter(
            source_course_key=course_id, action="rerun", state="succeeded")]
        course_rerun_states = course_reruns + [course_id]

        if not course_reruns:
            try:
                CourseCard.objects.get(course_id=course_id)
            except CourseCard.DoesNotExist:
                # This is a parent course and it's card isn't added
                continue

        course_rerun_object = CourseOverview.objects.select_related('image_set').filter(
            id__in=course_rerun_states, enrollment_start__lte=current_time, enrollment_end__gte=current_time
        ).order_by('start').first()

        if course_rerun_object:
            recommended_courses.append(course_rerun_object)

    return recommended_courses
