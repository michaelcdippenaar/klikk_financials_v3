# Generated manually to enhance last update tracking

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('xero_sync', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='xerolastupdate',
            name='start_time',
            field=models.DateTimeField(blank=True, help_text='When the update started', null=True),
        ),
        migrations.AddField(
            model_name='xerolastupdate',
            name='end_time',
            field=models.DateTimeField(blank=True, help_text='When the update completed', null=True),
        ),
        migrations.AddField(
            model_name='xerolastupdate',
            name='out_of_sync',
            field=models.BooleanField(default=False, help_text='True if data is out of sync (validation failed or errors occurred)'),
        ),
        migrations.AddField(
            model_name='xerolastupdate',
            name='error_message',
            field=models.TextField(blank=True, help_text='Error message if update failed or validation failed', null=True),
        ),
        migrations.AddIndex(
            model_name='xerolastupdate',
            index=models.Index(fields=['organisation', 'out_of_sync'], name='last_update_org_sync_idx'),
        ),
        migrations.AddIndex(
            model_name='xerolastupdate',
            index=models.Index(fields=['organisation', 'end_point'], name='last_update_org_endpoint_idx'),
        ),
    ]

