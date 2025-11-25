# Generated manually for Profit and Loss models

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('xero_validation', '0001_initial'),
        ('xero_core', '0001_initial'),
        ('xero_metadata', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='XeroProfitAndLossReport',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('from_date', models.DateField(help_text='Start date of the report period')),
                ('to_date', models.DateField(help_text='End date of the report period')),
                ('periods', models.IntegerField(default=12, help_text='Number of periods in the report')),
                ('timeframe', models.CharField(default='MONTH', help_text='Timeframe (MONTH, QUARTER, YEAR)', max_length=20)),
                ('imported_at', models.DateTimeField(auto_now_add=True, help_text='When this report was imported')),
                ('raw_data', models.JSONField(blank=True, help_text='Raw JSON data from Xero API', null=True)),
                ('organisation', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='xero_pnl_reports', to='xero_core.xerotenant')),
            ],
            options={
                'ordering': ['-to_date', '-imported_at'],
            },
        ),
        migrations.CreateModel(
            name='XeroProfitAndLossReportLine',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('account_code', models.CharField(blank=True, help_text='Account code from Xero', max_length=50)),
                ('account_name', models.CharField(help_text='Account name or section title', max_length=255)),
                ('account_type', models.CharField(blank=True, help_text='Account type from Xero', max_length=50, null=True)),
                ('row_type', models.CharField(help_text='Row type (Header, Section, Row, SummaryRow)', max_length=50)),
                ('section_title', models.CharField(blank=True, help_text="Section title (e.g., 'Income', 'Expenses')", max_length=255)),
                ('period_values', models.JSONField(default=dict, help_text="Dictionary of period values: {'period_0': value, 'period_1': value, ...}")),
                ('raw_cell_data', models.JSONField(blank=True, help_text='Raw cell data from Xero API', null=True)),
                ('account', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='xero_pnl_report_lines', to='xero_metadata.xeroaccount')),
                ('report', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='lines', to='xero_validation.xeroprofitandlossreport')),
            ],
            options={
                'ordering': ['report', 'account_code', 'id'],
            },
        ),
        migrations.CreateModel(
            name='ProfitAndLossComparison',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('period_index', models.IntegerField(help_text='Period index (0-11 for 12 months)')),
                ('period_date', models.DateField(help_text='Date representing this period (first day of month)')),
                ('xero_value', models.DecimalField(decimal_places=2, help_text='Value from Xero P&L report', max_digits=30)),
                ('db_value', models.DecimalField(decimal_places=2, help_text='Value from our database (XeroTrailBalance)', max_digits=30)),
                ('difference', models.DecimalField(decimal_places=2, help_text='Difference (xero_value - db_value)', max_digits=30)),
                ('match_status', models.CharField(choices=[('match', 'Match'), ('mismatch', 'Mismatch'), ('missing_in_db', 'Missing in DB'), ('missing_in_xero', 'Missing in Xero')], help_text='Status of the comparison', max_length=20)),
                ('notes', models.TextField(blank=True, help_text='Additional notes about the comparison')),
                ('compared_at', models.DateTimeField(auto_now_add=True)),
                ('account', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='pnl_comparisons', to='xero_metadata.xeroaccount')),
                ('report', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='comparisons', to='xero_validation.xeroprofitandlossreport')),
            ],
            options={
                'ordering': ['report', 'period_index', 'account__code'],
            },
        ),
        migrations.AddIndex(
            model_name='xeroprofitandlossreport',
            index=models.Index(fields=['organisation', 'from_date', 'to_date'], name='xero_pnl_rpt_org_dates_idx'),
        ),
        migrations.AddIndex(
            model_name='xeroprofitandlossreportline',
            index=models.Index(fields=['report', 'account_code'], name='xero_pnl_rpt_line_code_idx'),
        ),
        migrations.AddIndex(
            model_name='xeroprofitandlossreportline',
            index=models.Index(fields=['report', 'account'], name='xero_pnl_rpt_line_acc_idx'),
        ),
        migrations.AddIndex(
            model_name='xeroprofitandlossreportline',
            index=models.Index(fields=['report', 'row_type'], name='xero_pnl_rpt_line_type_idx'),
        ),
        migrations.AddIndex(
            model_name='profitandlosscomparison',
            index=models.Index(fields=['report', 'period_index', 'match_status'], name='xero_pnl_comp_prd_st_idx'),
        ),
        migrations.AddIndex(
            model_name='profitandlosscomparison',
            index=models.Index(fields=['report', 'account', 'period_index'], name='xero_pnl_comp_acc_prd_idx'),
        ),
        migrations.AlterUniqueTogether(
            name='profitandlosscomparison',
            unique_together={('report', 'account', 'period_index')},
        ),
    ]

