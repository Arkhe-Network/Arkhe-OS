#!/bin/sh
# scripts/backup.sh
# Automated backup script for Cathedral ARKHE database (PostgreSQL) and Redis
# Designed to be run via cronjob

set -e

BACKUP_DIR="/mnt/persist/backups"
DB_CONTAINER="cathedral-postgres"
REDIS_CONTAINER="cathedral-redis"
DB_USER="cathedral"
DB_NAME="cathedral"

DATE=$(date +%Y%m%d_%H%M%S)

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

mkdir -p "$BACKUP_DIR/postgres"
mkdir -p "$BACKUP_DIR/redis"

log "Starting backup process..."

# 1. PostgreSQL Backup
log "Backing up PostgreSQL database ($DB_NAME)..."
if docker exec "$DB_CONTAINER" pg_dump -U "$DB_USER" -d "$DB_NAME" -F c -f "/tmp/pg_backup_$DATE.dump"; then
    docker cp "$DB_CONTAINER:/tmp/pg_backup_$DATE.dump" "$BACKUP_DIR/postgres/pg_backup_$DATE.dump"
    docker exec "$DB_CONTAINER" rm "/tmp/pg_backup_$DATE.dump"
    log "✅ PostgreSQL backup successful: pg_backup_$DATE.dump"
else
    log "❌ PostgreSQL backup failed!"
fi

# 2. Redis Backup (RDB)
log "Backing up Redis datastore..."
if docker exec "$REDIS_CONTAINER" redis-cli SAVE; then
    docker cp "$REDIS_CONTAINER:/data/dump.rdb" "$BACKUP_DIR/redis/redis_backup_$DATE.rdb"
    log "✅ Redis backup successful: redis_backup_$DATE.rdb"
else
    log "❌ Redis backup failed!"
fi

# 3. Clean up old backups (keep last 7 days)
log "Cleaning up backups older than 7 days..."
find "$BACKUP_DIR/postgres" -type f -name "pg_backup_*.dump" -mtime +7 -exec rm {} \;
find "$BACKUP_DIR/redis" -type f -name "redis_backup_*.rdb" -mtime +7 -exec rm {} \;

log "Backup process completed."
