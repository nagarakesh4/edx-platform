# -*- coding: utf-8 -*-
# Generated by Django 1.11.21 on 2020-05-04 09:45
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('job_board', '0004_auto_20200429_0526'),
    ]

    operations = [
        migrations.AlterField(
            model_name='job',
            name='compensation',
            field=models.CharField(choices=[(b'volunteer', b'Volunteer'), (b'hourly', b'Hourly'), (b'salaried', b'Salaried (Yearly)')], default='volunteer', help_text='Please select the type of compensation you are offering for this job.', max_length=255, verbose_name='Compensation'),
        ),
    ]
