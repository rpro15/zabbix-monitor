#!/bin/bash
set -e

# Создаём дополнительные базы данных, если указаны в переменной окружения
if [ -n "$POSTGRES_MULTIPLE_DATABASES" ]; then
    for db in $(echo $POSTGRES_MULTIPLE_DATABASES | tr ',' ' '); do
        psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL
            CREATE DATABASE $db;
EOSQL
        echo "Database $db created"
    done
fi
