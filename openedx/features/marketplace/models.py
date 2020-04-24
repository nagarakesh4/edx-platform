# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.auth.models import User
from django.db import models
from django.utils.translation import ugettext as _

from openedx.custom.db.fields import MultiSelectWithOtherField
from openedx.features.idea.models import VisualAttachment, Location, OrganizationBase
from openedx.features.marketplace.constants import (ORGANIZATION_SECTOR_CHOICES, ORGANIZATIONAL_PROBLEM_CHOICES,
                                                    USER_SERVICES)


class MarketplaceRequest(OrganizationBase, Location, VisualAttachment):
    user = models.ForeignKey(User, related_name='challenges', related_query_name='challenge', on_delete=models.CASCADE)

    organization_sector = MultiSelectWithOtherField(other_max_length=50, choices=ORGANIZATION_SECTOR_CHOICES,
                                                    verbose_name=_('Which sector is your organization working in?'),
                                                    help_text=_('Please select all that apply.'), blank=False)

    organizational_problems = MultiSelectWithOtherField(other_max_length=50, choices=ORGANIZATIONAL_PROBLEM_CHOICES,
                                                        verbose_name=_('Current Organizational Problems'),
                                                        help_text=_(
                                                            'What are the areas that your organizaiton is currently facing a challenge in?  Please select all that apply.'),
                                                        blank=False)

    description = models.TextField(blank=False, verbose_name=_('Brief Description of Challenges'))

    approach_to_address = models.TextField(verbose_name=_(
        'How has your organization already tried to address these challenges?'), blank=True, null=True)

    resources_currently_using = models.TextField(verbose_name=_('What tools or resources are you currently using?'),
                                                 blank=True, null=True)

    user_services = MultiSelectWithOtherField(other_max_length=50, choices=USER_SERVICES,
                                              verbose_name=_('What help can you provide to other organizations?'),
                                              help_text=_('Please select all that apply.'), blank=False)

    brief_services_summery = models.TextField(verbose_name=_(
        'Brief explanation of services that you can provide to others.'), blank=True, null=True)
