#!/usr/bin/env python
"""
Script to migrate data from v2 to v3 database.
Exports data from v2 and imports into v3 with app label adjustments.
"""
import os
import sys
import django
import json
import subprocess

# Setup v2 Django environment
v2_path = '/Users/mcdippenaar/PycharmProjects/klikk_financials_v2/klikk_business_intelligence'
sys.path.insert(0, v2_path)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'klikk_business_intelligence.settings')
django.setup()

from django.core.management import call_command
from io import StringIO

# Export data from v2
print("Exporting data from v2...")
output = StringIO()

# Export xero app data
try:
    call_command('dumpdata', 'apps.xero', '--natural-foreign', '--natural-primary', stdout=output)
    v2_xero_data = output.getvalue()
    print(f"Exported {len(v2_xero_data)} bytes of xero data")
except Exception as e:
    print(f"Error exporting xero data: {e}")
    v2_xero_data = None

# Save to file
if v2_xero_data:
    with open('/tmp/v2_xero_data.json', 'w') as f:
        f.write(v2_xero_data)
    print("Data exported to /tmp/v2_xero_data.json")
    
    # Now adjust app labels for v3
    print("Adjusting app labels for v3...")
    data = json.loads(v2_xero_data)
    
    # Map old app labels to new app labels
    app_label_mapping = {
        'apps.xero': {
            'xerotenant': 'apps.xero.xero_core.xerotenant',
            'xeroclientcredentials': 'apps.xero.xero_auth.xeroclientcredentials',
            'xerotenanttoken': 'apps.xero.xero_auth.xerotenanttoken',
            'xeroauthsettings': 'apps.xero.xero_auth.xeroauthsettings',
            'xerolastupdate': 'apps.xero.xero_sync.xerolastupdate',
            'xerotenantschedule': 'apps.xero.xero_sync.xerotenantschedule',
            'xerotaskexecutionlog': 'apps.xero.xero_sync.xerotaskexecutionlog',
            'xerobusinessunits': 'apps.xero.xero_metadata.xerobusinessunits',
            'xeroaccount': 'apps.xero.xero_metadata.xeroaccount',
            'xerotracking': 'apps.xero.xero_metadata.xerotracking',
            'xerocontacts': 'apps.xero.xero_metadata.xerocontacts',
            'xerotransactionsource': 'apps.xero.xero_data.xerotransactionsource',
            'xerojournalssource': 'apps.xero.xero_data.xerojournalssource',
            'xerojournals': 'apps.xero.xero_data.xerojournals',
            'xerotrailbalance': 'apps.xero.xero_cube.xerotrailbalance',
            'xerobalancesheet': 'apps.xero.xero_cube.xerobalancesheet',
        }
    }
    
    adjusted_data = []
    for obj in data:
        model_name = obj['model'].split('.')[-1].lower()
        old_app = obj['model'].split('.')[0]
        
        if old_app in app_label_mapping and model_name in app_label_mapping[old_app]:
            new_model_path = app_label_mapping[old_app][model_name]
            obj['model'] = new_model_path.lower()
        adjusted_data.append(obj)
    
    # Save adjusted data
    with open('/tmp/v3_xero_data.json', 'w') as f:
        json.dump(adjusted_data, f, indent=2)
    print("Adjusted data saved to /tmp/v3_xero_data.json")
    print(f"Adjusted {len(adjusted_data)} objects")
else:
    print("No data to export")

