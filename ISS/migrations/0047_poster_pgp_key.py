# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2018-08-06 06:13
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ISS', '0046_poster_theme'),
    ]

    operations = [
        migrations.AddField(
            model_name='poster',
            name='pgp_key',
            field=models.TextField(default=b''),
        ),
    ]
