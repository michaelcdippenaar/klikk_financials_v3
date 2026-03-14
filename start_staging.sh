#!/usr/bin/env bash

# Fail immediately if something goes wrong
set -e

echo "Starting Klikk Financials (staging)..."

# 1. Move to project root
cd "$(dirname "$0")"

# 2. Activate virtual environment
if [ ! -f "venv/bin/activate" ]; then
  echo "❌ Virtual environment not found at venv/bin/activate"
  exit 1
fi

source venv/bin/activate

# 3. Load environment variables
export DJANGO_SETTINGS_MODULE=klikk_business_intelligence.settings.staging
export PYTHONPATH=$(pwd)

# Optional: database env vars if your settings use them
# export DB_NAME=klikk_financials
# export DB_USER=klikk_user
# export DB_PASSWORD=*****
# export DB_HOST=127.0.0.1
# export DB_PORT=5432

echo "Using settings: $DJANGO_SETTINGS_MODULE"
echo "Python: $(which python)"

# 4. Run migrations
python manage.py migrate

# 5. Start Django dev server
python manage.py runserver 0.0.0.0:8000

