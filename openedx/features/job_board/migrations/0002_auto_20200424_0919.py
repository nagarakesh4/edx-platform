# -*- coding: utf-8 -*-
# Generated by Django 1.11.21 on 2020-04-24 13:19
from __future__ import unicode_literals

import django.core.validators
from django.db import migrations, models
import django_countries.fields
import openedx.features.job_board.helpers


class Migration(migrations.Migration):

    dependencies = [
        ('job_board', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='job',
            name='application_link',
            field=models.URLField(blank=True, help_text='Please share a link to the job application', max_length=255, null=True, verbose_name='Application Link'),
        ),
        migrations.AlterField(
            model_name='job',
            name='city',
            field=models.CharField(max_length=255, verbose_name='City'),
        ),
        migrations.AlterField(
            model_name='job',
            name='company',
            field=models.CharField(max_length=255, verbose_name='Organization Name'),
        ),
        migrations.AlterField(
            model_name='job',
            name='compensation',
            field=models.CharField(choices=[(b'volunteer', b'Volunteer'), (b'hourly', b'Hourly'), (b'salaried', b'Salaried')], default='volunteer', help_text='Please select the type of compensation you are offering for this job.', max_length=255, verbose_name='Compensation'),
        ),
        migrations.AlterField(
            model_name='job',
            name='contact_email',
            field=models.EmailField(help_text='Please share a contact email for this job.', max_length=255, verbose_name='Contact Email'),
        ),
        migrations.AlterField(
            model_name='job',
            name='country',
            field=django_countries.fields.CountryField(max_length=2, verbose_name='Country'),
        ),
        migrations.AlterField(
            model_name='job',
            name='description',
            field=models.TextField(help_text='Please share a brief description of the job.', verbose_name='Job Description'),
        ),
        migrations.AlterField(
            model_name='job',
            name='function',
            field=models.TextField(default='', help_text='Please share details about the expected functions associated with the job.', verbose_name='Job Function'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='job',
            name='hours',
            field=models.CharField(choices=[(b'fulltime', b'Full Time'), (b'parttime', b'Part Time'), (b'freelance', b'Freelance')], default='fulltime', help_text='Please select the expected number of working hours required for this job.', max_length=255, verbose_name='Job Hours'),
        ),
        migrations.AlterField(
            model_name='job',
            name='logo',
            field=models.ImageField(blank=True, help_text="Please upload a file with your company's logo. (maximum 2MB)", null=True, upload_to='job-board/uploaded-logos/', validators=[django.core.validators.FileExtensionValidator([b'jpg', b'png']), openedx.features.job_board.helpers.validate_file_size], verbose_name='Company Logo'),
        ),
        migrations.AlterField(
            model_name='job',
            name='responsibilities',
            field=models.TextField(default='', help_text='Please share the responsibilities associated with the job.', verbose_name='Job Responsibilities'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='job',
            name='title',
            field=models.CharField(max_length=255, verbose_name='Job Title'),
        ),
        migrations.AlterField(
            model_name='job',
            name='type',
            field=models.CharField(choices=[(b'remote', b'Remote'), (b'onsite', b'Onsite')], default='remote', help_text='Please select whether the job is onsite or can be done remotely.', max_length=255, verbose_name='Job Type'),
        ),
        migrations.AlterField(
            model_name='job',
            name='website_link',
            field=models.URLField(blank=True, max_length=255, null=True, verbose_name='Website Link'),
        ),
    ]
