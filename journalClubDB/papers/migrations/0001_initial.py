# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Citation',
            fields=[
                ('id', models.AutoField(serialize=False, auto_created=True, verbose_name='ID', primary_key=True)),
                ('title', models.TextField()),
                ('author', models.TextField()),
                ('journal', models.TextField()),
                ('volume', models.PositiveSmallIntegerField()),
                ('number', models.PositiveSmallIntegerField()),
                ('pages', models.TextField()),
                ('year', models.PositiveSmallIntegerField()),
                ('publisher', models.TextField()),
            ],
        ),
    ]
