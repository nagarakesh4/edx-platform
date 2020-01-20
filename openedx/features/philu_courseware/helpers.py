from logging import getLogger

from django.conf import settings
from django.core.urlresolvers import reverse

from openedx.core.djangoapps.site_configuration import helpers as configuration_helpers
from xmodule.modulestore.django import modulestore
from .models import CompetencyAssessmentRecord
from . import constants

log = getLogger(__name__)


def get_nth_chapter_link(course, chapter_index=0):
    course_chapters = modulestore().get_items(
        course.id,
        qualifiers={'category': 'course'}
    )
    if not course_chapters:
        log.info("%s Course dont have any chapters", course.display_name)


    try:
        chapter = course_chapters[0].children[chapter_index]
    except IndexError:
        return ""

    subsection = modulestore().get_item(chapter).children[0]

    course_target = reverse(
        'courseware_section',
        args=[course.id.to_deprecated_string(),
              chapter.block_id,
              subsection.block_id]
    )

    base_url = settings.LMS_ROOT_URL

    return base_url + course_target


def get_competency_assessments_score(user, chapter_id):
    """
    Return competency assessments scores of user in chapter of specified course

    :param user: user
    :param chapter_id: chapter url_name.
    :return: assessments score dictionary
    :raises:
        NotFound: if chapter, pre or post assessment not found
    """

    pre_assessment_attempted = None
    pre_assessment_score = post_assessment_score = 0
    attempted_pre_assessments = attempted_post_assessments = 0

    COMPETENCY_ASSESSMENT_RECORD_QUERY_FORMAT = 'SELECT MAX(id) AS id, COUNT(assessment_type) AS assessments_count, ' \
                                      'assessment_type, correctness FROM philu_courseware_competencyassessmentrecord' \
                                      ' WHERE id IN (SELECT MAX(id) FROM philu_courseware_competencyassessmentrecord' \
                                      ' WHERE chapter_id = "{chapter_id}" and user_id = {user_id} ' \
                                      'GROUP BY problem_id) GROUP BY correctness, assessment_type'

    assessments_record = CompetencyAssessmentRecord.objects.raw(
        COMPETENCY_ASSESSMENT_RECORD_QUERY_FORMAT.format(chapter_id=chapter_id, user_id=user.id))

    """
        Sample result of upper query. This Query will return results of problems from latest attempt
        for both "Pre" and "Post" assessments. All attempts are saved in our table and we are concerned only with the
        latest one, hence sub query provide us the latest attempt of all problems

        |  id   | assessment_count | assessment_type   |  correctness  |
        +-------+------------------+-------------------+---------------+
        |  231  |         4        |       post        |   correct     |
        |  229  |         4        |       pre         |   correct     |
        |  232  |         1        |       post        |   incorrect   |
        |  233  |         1        |       pre         |   incorrect   |
    """

    for assessment in assessments_record:
        if assessment.assessment_type == constants.PRE_ASSESSMENT_KEY:
            pre_assessment_attempted = True
            if assessment.correctness == constants.CORRECT_ASSESSMENT_KEY:
                pre_assessment_score = assessment.assessments_count
            attempted_pre_assessments += assessment.assessments_count

        else:
            if assessment.correctness == constants.CORRECT_ASSESSMENT_KEY:
                post_assessment_score = assessment.assessments_count
            attempted_post_assessments += assessment.assessments_count

    return {
        'pre_assessment_score': pre_assessment_score,
        'post_assessment_score': post_assessment_score,
        'pre_assessment_attempted': pre_assessment_attempted,
        'all_pre_assessment_attempted': attempted_pre_assessments == constants.COMPETENCY_ASSESSMENT_DEFAULT_PROBLEMS_COUNT,
        'all_post_assessment_attempted': attempted_post_assessments == constants.COMPETENCY_ASSESSMENT_DEFAULT_PROBLEMS_COUNT,
    }


def is_pre_assessment(section):
    return get_section_format(section) == constants.PRE_ASSESSMENT_FORMAT


def is_post_assessment(section):
    return get_section_format(section) == constants.POST_ASSESSMENT_FORMAT


def get_section_format(section):
    return section.format.lower() if section and section.format else ''
