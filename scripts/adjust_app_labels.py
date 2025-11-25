#!/usr/bin/env python
"""
Adjust app labels in exported JSON data from v2 to v3 structure.
"""
import json
import sys

# Mapping of old model paths to new model paths
MODEL_MAPPING = {
    'apps.xero.xerotenant': 'apps.xero.xero_core.xerotenant',
    'apps.xero.xeroclientcredentials': 'apps.xero.xero_auth.xeroclientcredentials',
    'apps.xero.xerotenanttoken': 'apps.xero.xero_auth.xerotenanttoken',
    'apps.xero.xeroauthsettings': 'apps.xero.xero_auth.xeroauthsettings',
    'apps.xero.xerolastupdate': 'apps.xero.xero_sync.xerolastupdate',
    'apps.xero.xerotenantschedule': 'apps.xero.xero_sync.xerotenantschedule',
    'apps.xero.xerotaskexecutionlog': 'apps.xero.xero_sync.xerotaskexecutionlog',
    'apps.xero.xerobusinessunits': 'apps.xero.xero_metadata.xerobusinessunits',
    'apps.xero.xeroaccount': 'apps.xero.xero_metadata.xeroaccount',
    'apps.xero.xerotracking': 'apps.xero.xero_metadata.xerotracking',
    'apps.xero.xerocontacts': 'apps.xero.xero_metadata.xerocontacts',
    'apps.xero.xerotransactionsource': 'apps.xero.xero_data.xerotransactionsource',
    'apps.xero.xerojournalssource': 'apps.xero.xero_data.xerojournalssource',
    'apps.xero.xerojournals': 'apps.xero.xero_data.xerojournals',
    'apps.xero.xerotrailbalance': 'apps.xero.xero_cube.xerotrailbalance',
    'apps.xero.xerobalancesheet': 'apps.xero.xero_cube.xerobalancesheet',
}

def adjust_app_labels(input_file, output_file):
    """Adjust app labels in JSON dump file."""
    print(f"Reading {input_file}...")
    with open(input_file, 'r') as f:
        data = json.load(f)
    
    print(f"Found {len(data)} objects")
    adjusted = []
    skipped = []
    
    for obj in data:
        old_model = obj.get('model', '')
        if old_model in MODEL_MAPPING:
            obj['model'] = MODEL_MAPPING[old_model]
            adjusted.append(obj)
        else:
            skipped.append(old_model)
    
    print(f"Adjusted {len(adjusted)} objects")
    if skipped:
        print(f"Skipped {len(set(skipped))} unknown models: {', '.join(set(skipped))}")
    
    print(f"Writing to {output_file}...")
    with open(output_file, 'w') as f:
        json.dump(adjusted, f, indent=2)
    
    print("Done!")

if __name__ == '__main__':
    input_file = sys.argv[1] if len(sys.argv) > 1 else '/tmp/v2_xero_all.json'
    output_file = sys.argv[2] if len(sys.argv) > 2 else '/tmp/v3_xero_data.json'
    adjust_app_labels(input_file, output_file)

