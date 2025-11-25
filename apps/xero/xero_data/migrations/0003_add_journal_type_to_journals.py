# Generated manually to add journal_type field to XeroJournals

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('xero_data', '0002_add_journal_type_to_journals_source'),
    ]

    operations = [
        migrations.AddField(
            model_name='xerojournals',
            name='journal_type',
            field=models.CharField(
                choices=[('journal', 'Journal'), ('manual_journal', 'Manual Journal')],
                default='journal',
                help_text='Type of journal: regular journal or manual journal',
                max_length=20
            ),
        ),
        migrations.AddIndex(
            model_name='xerojournals',
            index=models.Index(fields=['organisation', 'journal_type'], name='journals_org_type_idx'),
        ),
    ]

