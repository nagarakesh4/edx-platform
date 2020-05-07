from nodebb.models import DiscussionCommunity
from django.contrib.auth.models import User
from django.db import models
from model_utils.models import TimeStampedModel


class DiscussionCommunityMembership(TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    community_url = models.ForeignKey(DiscussionCommunity, on_delete=models.CASCADE)

    class Meta:
        unique_together = (("user", "community_url"),)
