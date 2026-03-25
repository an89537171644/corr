# Database Migrations

The project uses Alembic for schema versioning.

## Files

- `alembic.ini`
- `alembic/env.py`
- `alembic/versions/20260325_0001_initial_schema.py`

## Initialization modes

The application reads `DB_SCHEMA_MODE` during startup:

- `auto`
- `create_all`
- `migrate`
- `skip`

Recommended usage:

- local temporary SQLite: `create_all` or `auto`
- PostgreSQL development and deployment: `migrate`

## Commands

Upgrade to the latest revision:

```powershell
.venv\Scripts\alembic upgrade head
```

Create a new revision after model changes:

```powershell
.venv\Scripts\alembic revision -m "describe change"
```

Upgrade or downgrade to a specific revision:

```powershell
.venv\Scripts\alembic upgrade 20260325_0001
.venv\Scripts\alembic downgrade -1
```

## Docker behavior

`docker-compose.yml` sets:

- `DATABASE_URL=postgresql+psycopg://corrosion:corrosion@postgres:5432/corrosion_mvp`
- `DB_SCHEMA_MODE=migrate`

The API waits for PostgreSQL health and then upgrades the schema on startup.
