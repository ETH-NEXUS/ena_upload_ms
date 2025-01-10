#!/bin/bash

# To dump the database use:
# pg_dump -U ena -Fc ena > /tmp/yyyy-mm-dd_ena.dump

function usage {
    echo "USAGE: $(basename $0) dump-file"
    exit 1
}

# Configuration
DB_USER="ena"
DB_NAME="ena"

if [ $# -lt 1 ]; then
    usage
fi

# Disconnect all users
echo "Disconnecting all users from database '$DB_NAME'..."
psql -U "$DB_USER" -d postgres -c "
SELECT pg_terminate_backend(pg_stat_activity.pid)
FROM pg_stat_activity
WHERE pg_stat_activity.datname = '$DB_NAME'
  AND pid <> pg_backend_pid();
"
if [ $? -ne 0 ]; then
  echo "Failed to disconnect users."
  exit 1
fi

# Drop the database
echo "Dropping database '$DB_NAME'..."
dropdb -U "$DB_USER" "$DB_NAME"
if [ $? -ne 0 ]; then
  echo "Failed to drop the database."
  exit 1
fi

# Recreate the database
echo "Recreating database '$DB_NAME'..."
createdb -U "$DB_USER" "$DB_NAME"
if [ $? -ne 0 ]; then
  echo "Failed to recreate the database."
  exit 1
fi

echo "Database '$DB_NAME' has been reset successfully."

pg_restore -U "$DB_USER" -d "$DB_NAME" "$1"