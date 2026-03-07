# MongoDB Migrations

This directory contains MongoDB migration scripts for iHhashi.

## Why MongoDB Migrations?

While MongoDB is schemaless, migrations are still useful for:
- **Index Management**: Creating and managing indexes for performance
- **Schema Validation**: Setting up JSON schema validation rules
- **Data Migrations**: Transforming data structure when requirements change
- **Documentation**: Recording schema evolution over time

## Usage

```bash
# Apply all pending migrations
python -m scripts.migrations.migrate --up

# Rollback last migration
python -m scripts.migrations.migrate --down

# Show migration status
python -m scripts.migrations.migrate --status

# Create a new migration
python -m scripts.migrations.migrate --create "add_new_field"
```

## Environment Variables

- `MONGODB_URL`: MongoDB connection string (default: `mongodb://localhost:27017`)
- `DB_NAME`: Database name (default: `ihhashi`)

## Creating a New Migration

1. Run the create command:
   ```bash
   python -m scripts.migrations.migrate --create "your_migration_name"
   ```

2. Edit the generated file in this directory

3. Implement the `up()` and `down()` methods

4. Test locally before deploying

## Best Practices

1. **Always test migrations** in a staging environment first
2. **Write idempotent migrations** that can be run multiple times safely
3. **Implement down migrations** for rollback capability
4. **Use moderate validation level** to avoid breaking existing data
5. **Back up data** before running destructive migrations
