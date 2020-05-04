"""
    Models related to nodeBB integrations
"""
from django.contrib.auth.models import User
from django.db import models
from model_utils.models import TimeStampedModel
from django.conf import settings

from lms.djangoapps.teams.models import CourseTeam
from openedx.core.djangoapps.xmodule_django.models import CourseKeyField


class DiscussionCommunity(TimeStampedModel):
    """
        Model to store each course related communities
    """

    course_id = CourseKeyField(max_length=255, db_index=True)
    community_url = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return "%s" % self.community_url


class TeamGroupChat(TimeStampedModel):
    """
        Model to store team related group chats/discussion categories
    """

    team = models.ForeignKey(CourseTeam, related_name='team')
    room_id = models.IntegerField()
    slug = models.CharField(max_length=255, blank=True, default='')

    def __str__(self):
        return "%s" % self.room_id


class DiscussionCommunityThrough(TimeStampedModel):
    community = models.ForeignKey(DiscussionCommunity)
    membership = models.ForeignKey('DiscussionCommunityMembership')


class DiscussionCommunityMembership(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, primary_key=True)
    communities = models.ManyToManyField(DiscussionCommunity, through=DiscussionCommunityThrough)

    def __str__(self):
        return "%s" % self.user
