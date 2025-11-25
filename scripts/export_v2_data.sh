#!/bin/bash
# Export data from v2 using Django dumpdata

cd /Users/mcdippenaar/PycharmProjects/klikk_financials_v2/klikk_business_intelligence

# Export all xero data
python3 manage.py dumpdata apps.xero --natural-foreign --natural-primary --indent 2 > /tmp/v2_xero_all.json 2>&1

# Export user data if needed
python3 manage.py dumpdata auth.User --natural-foreign --natural-primary --indent 2 > /tmp/v2_users.json 2>&1

echo "Data exported to /tmp/v2_xero_all.json and /tmp/v2_users.json"

