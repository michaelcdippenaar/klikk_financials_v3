# Generated manually to add journal_type field

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('xero_data', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='xerojournalssource',
            name='journal_type',
            field=models.CharField(
                choices=[('journal', 'Journal'), ('manual_journal', 'Manual Journal')],
                default='journal',
                help_text='Type of journal: regular journal or manual journal',
                max_length=20
            ),
        ),
        migrations.AlterUniqueTogether(
            name='xerojournalssource',
            unique_together={('organisation', 'journal_id', 'journal_type')},
        ),
        migrations.AddIndex(
            model_name='xerojournalssource',
            index=models.Index(fields=['organisation', 'journal_type'], name='jrnl_src_org_type_idx'),
        ),
    ]

