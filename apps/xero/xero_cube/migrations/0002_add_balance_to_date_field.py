# Generated manually to add balance_to_date field for P&L YTD calculation

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('xero_cube', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='xerotrailbalance',
            name='balance_to_date',
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text='Year-to-date balance for P&L accounts (cumulative sum of all previous months)',
                max_digits=30,
                null=True
            ),
        ),
    ]

