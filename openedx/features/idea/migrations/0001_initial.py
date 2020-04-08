# -*- coding: utf-8 -*-
# Generated by Django 1.11.21 on 2020-04-08 13:08
from __future__ import unicode_literals

from django.conf import settings
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import django_countries.fields
import functools
import openedx.features.idea.helpers


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('onboarding', '0029_auto_20200130_0957'),
    ]

    operations = [
        migrations.CreateModel(
            name='Idea',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('country', django_countries.fields.CountryField(max_length=2)),
                ('city', models.CharField(max_length=255)),
                ('video_link', models.URLField(blank=True, null=True)),
                ('image', models.ImageField(blank=True, help_text='Accepted extensions: .jpg, .png', null=True, upload_to=functools.partial(openedx.features.idea.helpers.upload_to_path, *(), **{b'folder': 'images'}), validators=[django.core.validators.FileExtensionValidator(['jpg', 'png'])])),
                ('file', models.FileField(blank=True, help_text='Accepted extensions: .docx, .pdf, .txt', null=True, upload_to=functools.partial(openedx.features.idea.helpers.upload_to_path, *(), **{b'folder': 'files'}), validators=[django.core.validators.FileExtensionValidator(['docx', 'pdf', 'txt'])])),
                ('organization_mission', models.TextField()),
                ('title', models.CharField(max_length=50)),
                ('overview', models.CharField(max_length=150)),
                ('description', models.TextField()),
                ('implementation', models.TextField(blank=True)),
                ('organization', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='idea_ideas', related_query_name='idea_idea', to='onboarding.Organization')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ideas', related_query_name='idea', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
