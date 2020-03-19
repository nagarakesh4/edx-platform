from django.contrib.auth.models import User
from django.db import models
from jsonfield.fields import JSONField
from model_utils import Choices
from model_utils.models import TimeStampedModel

from .constants import PARTNER_USER_STATUS_WAITING, PARTNER_USER_STATUS_APPROVED

class Partner(TimeStampedModel):
    """
    This model represents white-labelled partners.
    """
    performance_url = models.URLField(blank=True, default=None)
    label = models.CharField(max_length=100)
    main_logo = models.CharField(max_length=255)
    small_logo = models.CharField(max_length=255)
    slug = models.CharField(max_length=100, unique=True)
    configuration = JSONField(null=False, blank=False, default='{}')

    def __unicode__(self):
        return '{}'.format(self.label)

    class Meta:
        verbose_name = "Partner"
        verbose_name_plural = "Partners"


class PartnerUser(TimeStampedModel):
    """
    This model represents all the users that are associated to a partner.
    """

    USER_STATUS = Choices(PARTNER_USER_STATUS_WAITING, PARTNER_USER_STATUS_APPROVED)

    user = models.ForeignKey(User, db_index=True, on_delete=models.CASCADE, related_name="partner_user")
    partner = models.ForeignKey(Partner, db_index=True, on_delete=models.CASCADE, related_name="partner")
    status = models.CharField(choices=USER_STATUS)

    def __unicode__(self):
        return '{partner}-{user}'.format(partner=self.partner.label, user=self.user.username)

    class Meta:
        unique_together = ('user', 'partner')


class PartnerCommunity(models.Model):
    community_id = models.IntegerField()
    partner = models.ForeignKey(Partner, db_index=True, on_delete=models.CASCADE, related_name='communities')

    class Meta:
        unique_together = ('community_id', 'partner')

