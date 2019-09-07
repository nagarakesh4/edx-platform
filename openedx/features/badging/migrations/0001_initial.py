# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Badge',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=255)),
                ('description', models.CharField(max_length=255, null=True, blank=True)),
                ('threshold', models.IntegerField()),
                ('type', models.CharField(max_length=100, choices=[(b'Conversationalist', b'Conversationalist'), (b'Team Player', b'Team Player')])),
                ('image', models.CharField(max_length=255)),
                ('date_created', models.DateTimeField(auto_now=True)),
            ],
        ),
    ]
