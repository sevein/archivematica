# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('administration', '0006_use_statement_optional'),
    ]

    # TODO: Migrate config from {ArchivesSpaceConfig,ArchivistsToolkitConfig}
    # to ReplacementDict before they're deleted.

    operations = [
        migrations.DeleteModel(
            name='ArchivesSpaceConfig',
        ),
        migrations.DeleteModel(
            name='ArchivistsToolkitConfig',
        ),
    ]
