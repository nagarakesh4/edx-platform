from nodebb.models import DiscussionCommunity
from model_utils.models import TimeStampedModel

from django.contrib.auth.models import User
from django.db import models


class DiscussionCommunityMembership(TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    community = models.ForeignKey(DiscussionCommunity, on_delete=models.CASCADE)

    class Meta:
        unique_together = (("user", "community"),)
