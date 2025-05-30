#!/bin/bash

# Delete database file (if exists)
rm -f app.db

# Remove migrations folder (if exists)
rm -rf migrations/

# Remove __pycache__ folders (recursively)
find . -type d -name "__pycache__" -exec rm -r {} +

# Initialize and run migrations
flask db init && flask db migrate && flask db upgrade