# -*- coding: utf-8 -*-
# Generated by Django 1.11.21 on 2020-01-01 17:22
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='PartnerCommunity',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('community_id', models.IntegerField()),
                ('partner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='communities', to='partners.Partner')),
            ],
        ),
        migrations.AlterUniqueTogether(
            name='partnercommunity',
            unique_together=set([('community_id', 'partner')]),
        ),
    ]
