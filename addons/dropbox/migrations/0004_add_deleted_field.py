# -*- coding: utf-8 -*-
# Generated by Django 1.11.7 on 2018-01-16 20:50
from __future__ import unicode_literals

from django.db import migrations
import osf.utils.fields


class Migration(migrations.Migration):

    dependencies = [
        ('addons_dropbox', '0003_auto_20170713_1125'),
    ]

    operations = [
        migrations.RenameField(
            model_name='nodesettings',
            old_name='deleted',
            new_name='is_deleted',
        ),
        migrations.RenameField(
            model_name='usersettings',
            old_name='deleted',
            new_name='is_deleted',
        ),
        migrations.AddField(
            model_name='nodesettings',
            name='deleted',
            field=osf.utils.fields.NonNaiveDateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='usersettings',
            name='deleted',
            field=osf.utils.fields.NonNaiveDateTimeField(blank=True, null=True),
        ),
        migrations.RunSQL([
            """
            UPDATE addons_dropbox_nodesettings
            SET deleted='epoch' WHERE deleted IS NULL AND is_deleted=True;
            """,
            """
            UPDATE addons_dropbox_usersettings
            SET deleted='epoch' WHERE deleted IS NULL AND is_deleted=True;
            """
        ], [])
    ]