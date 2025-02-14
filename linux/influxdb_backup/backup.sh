#!/bin/bash

# Configuration
INFLUXDB_HOST="http://localhost:8086"
INFLUXDB_ORG="LST"
INFLUXDB_BUCKET="hass"
INFLUXDB_TOKEN="my-token"  # Insert the actual token here
BACKUP_DIR="/opt/influxbu"
ROTATION_WEEKS=1

# Date for the backup
TIMESTAMP=$(date +"%Y-%m-%d")
BACKUP_FILE="$BACKUP_DIR/backup-$TIMESTAMP.tar.gz"

# Ensure the backup directory exists
mkdir -p "$BACKUP_DIR"

# Perform the backup
influx backup --host "$INFLUXDB_HOST" --token "$INFLUXDB_TOKEN" --org "$INFLUXDB_ORG" --bucket "$INFLUXDB_BUCKET" "$BACKUP_DIR/backup-$TIMESTAMP"

# Archive the backup
tar -czf "$BACKUP_FILE" -C "$BACKUP_DIR" "backup-$TIMESTAMP"
rm -rf "$BACKUP_DIR/backup-$TIMESTAMP"

# Delete old backups
find "$BACKUP_DIR" -type f -name "backup-*.tar.gz" -mtime +$((ROTATION_WEEKS * 7)) -exec rm {} \;

# Done
echo "Backup completed: $BACKUP_FILE"
