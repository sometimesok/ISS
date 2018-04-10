# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2018-04-08 21:04
from __future__ import unicode_literals

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('ISS', '0042_auto_20171230_0158'),
    ]

    operations = [
        migrations.CreateModel(
            name='StaticPage',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('page_id', models.CharField(max_length=1024, unique=True)),
                ('page_title', models.CharField(max_length=1024)),
                ('content', models.TextField()),
            ],
        ),
        migrations.AlterField(
            model_name='postsnapshot',
            name='time',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
    ]