# Generated manually to create ProcessTree model

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('xero_sync', '0003_alter_xerolastupdate_date_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProcessTree',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='Unique name for the process tree', max_length=100, unique=True)),
                ('description', models.TextField(blank=True, help_text='Description of what this process tree does')),
                ('process_tree_data', models.JSONField(help_text='Process tree definition (processes, dependencies, etc.)')),
                ('response_variables', models.JSONField(blank=True, default=dict, help_text='Response variable definitions')),
                ('cache_enabled', models.BooleanField(default=True, help_text='Whether caching is enabled')),
                ('enabled', models.BooleanField(default=True, help_text='Whether this process tree is enabled')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('dependent_trees', models.ManyToManyField(blank=True, help_text='Process trees that run after this one completes', related_name='parent_trees', to='xero_sync.processtree')),
                ('sibling_trees', models.ManyToManyField(blank=True, help_text='Process trees that run in parallel with this one', symmetrical=True, to='xero_sync.processtree')),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.AddIndex(
            model_name='processtree',
            index=models.Index(fields=['name', 'enabled'], name='process_tree_name_enabled_idx'),
        ),
    ]

