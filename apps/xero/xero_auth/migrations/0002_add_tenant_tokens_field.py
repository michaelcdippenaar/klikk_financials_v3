# Generated manually to add tenant_tokens field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('xero_auth', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='xeroclientcredentials',
            name='tenant_tokens',
            field=models.JSONField(blank=True, default=dict),
        ),
    ]

