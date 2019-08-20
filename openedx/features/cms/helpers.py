from pytz import utc
from django.contrib.auth.models import User

from dateutil.parser import parse
from courseware.courses import get_course_by_id
from openassessment.xblock.defaults import DEFAULT_START, DEFAULT_DUE
from xmodule.course_module import CourseFields
from xmodule.modulestore.django import modulestore
from custom_settings.models import CustomSettings
from models.settings.course_metadata import CourseMetadata

MODULE_DATE_FORMAT = '%Y-%m-%dT%H:%M:%S%z'


def initialize_course_settings(source_course, re_run_course, skip_open_date=True):
    """
    When ever a new course is created
    1: We add a default entry for the given course in the CustomSettings Model
    2: We add a an honor mode for the given course so students can view certificates
       on their dashboard and progress page
    3: set rerun course's course open date that exists in the course custom settings
       on the basis of delta from the source_course start date with the source_course course open date

    """

    if not source_course:
        return

    _settings = CustomSettings.objects.filter(id=source_course.id).first()
    tags = _settings.tags

    source_course_open_date = _settings.course_open_date

    if source_course_open_date and not skip_open_date:
        rerun_course_open_date = calculate_date_by_delta(source_course_open_date,
                                                         source_course.start, re_run_course.start)
        CustomSettings.objects.filter(id=re_run_course.id).update(tags=tags, course_open_date=rerun_course_open_date)
    else:
        CustomSettings.objects.filter(id=re_run_course.id).update(tags=tags)


def apply_post_rerun_creation_tasks(source_course_key, destination_course_key, user_id):
    """
    This method is responsible for applying all the tasks after re-run creation has successfully completed

    :param source_course_key: source course key (from which the course was created)
    :param destination_course_key: re run course key (key of the re run created)
    :param user_id: user that created this course
    """
    user = User.objects.get(id=user_id)

    re_run = get_course_by_id(destination_course_key)
    source_course = get_course_by_id(source_course_key)

    # If re run has the default start date, it was created from old flow
    is_default_re_run = re_run.start == CourseFields.start.default

    # initialize course custom settings
    initialize_course_settings(source_course, re_run, is_default_re_run)

    if is_default_re_run:
        return

    # Set course re-run module start and due dates according to the source course
    set_rerun_course_dates(source_course, re_run, user)


def set_rerun_course_dates(source_course, re_run, user):
    """
    This method is responsible for updating all required dates for the re-run course according to
    source course.
    """
    source_course_start_date = source_course.start
    re_run_start_date = re_run.start

    source_course_sections = source_course.get_children()
    source_course_subsections = [sub_section for s in source_course_sections for sub_section in s.get_children()]
    re_run_sections = re_run.get_children()
    re_run_subsections = [sub_section for s in re_run_sections for sub_section in s.get_children()]

    # If there are no sections ignore setting dates
    if not re_run_sections:
        return

    re_run_modules = re_run_sections + re_run_subsections
    source_course_modules = source_course_sections + source_course_subsections

    set_rerun_schedule_dates(re_run, source_course, user)
    set_advanced_settings_due_date(re_run, source_course, user)

    set_rerun_module_dates(re_run_modules, source_course_modules, source_course_start_date, re_run_start_date, user)

    set_rerun_ora_dates(re_run_subsections, re_run_start_date, source_course_start_date, user)


def set_rerun_schedule_dates(re_run_course, source_course, user):
    """
    This methods sets rerun course's enrollment start date, enrollment end date and course end date on the basis
    of delta from the source course's start date
    """
    re_run_course.end = calculate_date_by_delta(source_course.end, source_course.start, re_run_course.start)

    re_run_course.enrollment_start = calculate_date_by_delta(source_course.enrollment_start,
                                                             source_course.start, re_run_course.start)

    re_run_course.enrollment_end = calculate_date_by_delta(source_course.enrollment_end,
                                                           source_course.start, re_run_course.start)

    modulestore().update_item(re_run_course, user.id)


def set_advanced_settings_due_date(re_run_course, source_course, user):
    """
    This methods sets rerun course's due date that exists in the course advanced settings
    on the basis of delta from the source_course start date with the source_course due date

    """
    source_due_date = source_course.due

    if not source_due_date:
        return

    re_run_due_date = calculate_date_by_delta(source_due_date, source_course.start, re_run_course.start)
    CourseMetadata.update_from_dict({'due': re_run_due_date}, re_run_course, user)


def set_rerun_module_dates(re_run_sections, source_course_sections, source_course_start_date, re_run_start_date, user):
    """
    This method is responsible for updating all section and subsection start and due dates for the re-run
    according to source course. This is achieved by calculating the delta between a source section/subsection's
    relevant date and start date, and then adding that delta to the start_date of the re-run course.
    """
    from cms.djangoapps.contentstore.views.item import _save_xblock

    for source_xblock, re_run_xblock in zip(source_course_sections, re_run_sections):
        meta_data = dict()

        meta_data['start'] = calculate_date_by_delta(source_xblock.start, source_course_start_date, re_run_start_date)

        if source_xblock.due:
            meta_data['due'] = calculate_date_by_delta(source_xblock.due, source_course_start_date, re_run_start_date)

        _save_xblock(user, re_run_xblock, metadata=meta_data)


def set_rerun_ora_dates(re_run_subsections, re_run_start_date, source_course_start_date, user):
    """
    This method is responsible for updating all dates in ORA i.e submission, start, due etc, for
    the re-run according to source course. This is achieved by calculating new dates for ORA based
    on delta value.
    :param re_run_subsections: list of subsection in a (re-run) course
    :param re_run_start_date: course start date of source course
    :param source_course_start_date: course start date of source course
    :param user: user that created this course
    """
    def compute_ora_date_by_delta(date_to_update, default_date, date_update_flags):
        """
        Method to calculate new date, on re-run, corresponding to previous value. The delta
        is calculated from course start date of source course and re-run course. Delta is then
        added to previous date in ORA. If date to update is default date then same date is
        returned with negative flag, indicating no need to update date.
        :param date_to_update: submission, start or due date from ORA
        :param default_date: DEFAULT_START or DEFAULT_DUE dates for ORA
        :param date_update_flags: list containing flags, indicating corresponding date changes or not
        :return: date string and boolean flag indicating need for updating ORA date
        """
        date_update_required = date_to_update and not date_to_update.startswith(default_date)
        updated_date = date_to_update

        if date_update_required:
            updated_date = calculate_date_by_delta(parse(date_to_update), source_course_start_date,
                                                   re_run_start_date)
            updated_date = updated_date.strftime(MODULE_DATE_FORMAT)

        date_update_flags.append(date_update_required)
        return updated_date

    # flat sub-sections to the level of components and pick ORA only
    re_run_ora_list = [
        component
        for subsection in re_run_subsections
        for unit in subsection.get_children()
        for component in unit.get_children()
        if component.category == 'openassessment'
    ]

    for ora in re_run_ora_list:
        date_update_flags = list()
        ora.submission_start = compute_ora_date_by_delta(ora.submission_start, DEFAULT_START, date_update_flags)
        ora.submission_due = compute_ora_date_by_delta(ora.submission_due, DEFAULT_DUE, date_update_flags)

        for assessment in ora.rubric_assessments:
            if 'start' in assessment:
                assessment['start'] = compute_ora_date_by_delta(assessment['start'], DEFAULT_START, date_update_flags)
            if 'due' in assessment:
                assessment['due'] = compute_ora_date_by_delta(assessment['due'], DEFAULT_DUE, date_update_flags)

        # If all dates in ORA are default then no need to update it during re-run process
        if not any(date_update_flags):
            continue

        component_update(ora, user)


def component_update(descriptor, user):
    """
    This method is responsible for updating provided component i.e. peer assessment
    :param descriptor: component to update
    :param user: user that is updating component
    """
    from cms.djangoapps.contentstore.views.item import StudioEditModuleRuntime

    descriptor.xmodule_runtime = StudioEditModuleRuntime(user)
    modulestore().update_item(descriptor, user.id)


def calculate_date_by_delta(date, source_date, destination_date):
    """
    This method is used to compute a date with a delta based on the difference of source_date and date
    and adding that delta to the destination date
    :param date: date for which delta is to be calculated
    :param source_date: date from which delta is to be calculated
    :param destination_date: date into which delta is to be added
    """

    # Sometimes date is coming without timezone (primarily in case of ORA)
    # Hence we'll be adding default timezone i.e. UTC to the datetime object passed
    if not date.tzinfo:
        date = date.replace(tzinfo=utc)

    date_delta = source_date - date
    return destination_date - date_delta
