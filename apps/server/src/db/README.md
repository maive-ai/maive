# Database Layer Documentation

Complete guide to working with PostgreSQL, SQLAlchemy, and Alembic in the Maive application.

## Overview

### Architecture

The database layer uses a modern, production-ready stack:

- **PostgreSQL 17** - Relational database (AWS RDS)
- **SQLAlchemy 2.0** - Python ORM for object-relational mapping
- **Alembic** - Database migration tool (version control for schema)
- **Pydantic Settings** - Configuration management
- **Repository Pattern** - Clean abstraction for database operations

### Key Concepts

**ORM (Object-Relational Mapper)**
- Maps Python classes to database tables
- Write Python code instead of SQL
- Type-safe database operations

**Migrations**
- Version-controlled schema changes
- Track database evolution over time
- Safe upgrades and rollbacks

**Repository Pattern**
- Encapsulates database logic
- Single responsibility principle
- Easy to test and maintain

## Folder Structure

```
src/db/
├── calls/                      # Folder-per-table pattern
│   ├── __init__.py            # Exports Call and CallRepository
│   ├── model.py               # SQLAlchemy Call model (schema)
│   ├── repository.py          # CallRepository (CRUD operations)
│   └── test_repository.py     # Unit tests
├── config.py                   # Pydantic database settings
├── database.py                 # Connection & session management
├── dependencies.py             # FastAPI dependency injection
├── dynamodb_client.py          # DynamoDB utilities (kept for other uses)
├── models.py                   # DynamoDB helper functions
└── README.md                   # This file

alembic/
├── env.py                      # Alembic configuration
├── script.py.mako             # Migration template
└── versions/                   # Migration files (version controlled!)
    └── ba8c60a76780_create_calls_table.py
```

### Why Folder-per-Table?

As your app grows, you'll add more tables:

```
src/db/
├── calls/
│   ├── model.py
│   └── repository.py
├── projects/              # Future table
│   ├── model.py
│   └── repository.py
└── users/                 # Future table
    ├── model.py
    └── repository.py
```

This keeps related code together and prevents a cluttered `db/` folder.

## Quick Start

### First Time Setup

After deploying your RDS instance with Pulumi, run the initial migration:

```bash
cd apps/server/

# Using Pulumi ESC for environment variables
esc run maive-infra/<your-stack> -- pnpm db:migrate

# Verify it worked
esc run maive-infra/<your-stack> -- pnpm db:status
# Should show: ba8c60a76780 (head)
```

This creates the `calls` table and all indexes in your database.

## Common Operations

### Command Reference

| Command | Description | When to Use |
|---------|-------------|-------------|
| `pnpm db:migrate` | Apply all pending migrations | After pulling code with new migrations |
| `pnpm db:migrate:create "message"` | Create new migration | After modifying models |
| `pnpm db:status` | Show current migration version | Check what's applied |
| `pnpm db:history` | List all migrations | View migration timeline |
| `pnpm db:migrate:down` | Rollback one migration | Undo last migration (rare) |

**Note:** Always use `esc run maive-infra/<your-stack> --` prefix to load database credentials!

### Examples

```bash
# Check current database version
esc run maive-infra/will-dev -- pnpm db:status

# View all migrations
esc run maive-infra/will-dev -- pnpm db:history

# Create a new migration after changing models
esc run maive-infra/will-dev -- pnpm db:migrate:create "Add email field to users"

# Apply pending migrations
esc run maive-infra/will-dev -- pnpm db:migrate

# Rollback if something went wrong
esc run maive-infra/will-dev -- pnpm db:migrate:down
```

## Development Workflow

### Adding a New Column

**Scenario:** Add a `duration_seconds` field to the Call model.

#### Step 1: Update the Model

Edit `src/db/calls/model.py`:

```python
from sqlalchemy import Integer

class Call(Base):
    __tablename__ = "calls"

    # ... existing fields ...

    duration_seconds: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Call duration in seconds"
    )
```

#### Step 2: Generate Migration

```bash
esc run maive-infra/will-dev -- pnpm db:migrate:create "Add duration_seconds to calls"
```

This creates: `alembic/versions/<hash>_add_duration_seconds_to_calls.py`

#### Step 3: Review the Migration

**ALWAYS review auto-generated migrations!**

```python
def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('calls',
        sa.Column('duration_seconds', sa.Integer(), nullable=True)
    )

def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('calls', 'duration_seconds')
```

Looks good? Great!

#### Step 4: Apply Migration

```bash
esc run maive-infra/will-dev -- pnpm db:migrate
```

#### Step 5: Commit

```bash
git add alembic/versions/<hash>_add_duration_seconds_to_calls.py
git add src/db/calls/model.py
git commit -m "feat: add duration tracking to calls"
```

### Creating a New Table

**Scenario:** Add a `projects` table.

#### Step 1: Create Folder Structure

```bash
mkdir -p src/db/projects
touch src/db/projects/__init__.py
touch src/db/projects/model.py
touch src/db/projects/repository.py
```

#### Step 2: Define the Model

`src/db/projects/model.py`:

```python
from sqlalchemy import String, Integer
from sqlalchemy.orm import Mapped, mapped_column

from src.db.database import Base

class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # ... more fields
```

#### Step 3: Create Repository

`src/db/projects/repository.py`:

```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.db.projects.model import Project

class ProjectRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, project_id: int) -> Project | None:
        stmt = select(Project).where(Project.id == project_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
```

#### Step 4: Update Alembic env.py

Import the model so Alembic can detect it:

```python
# alembic/env.py
from src.db.calls.model import Call  # noqa: F401
from src.db.projects.model import Project  # noqa: F401  ← Add this
```

#### Step 5: Generate & Apply Migration

```bash
esc run maive-infra/will-dev -- pnpm db:migrate:create "Create projects table"
esc run maive-infra/will-dev -- pnpm db:migrate
```

### Adding an Index

**Scenario:** Add an index to improve query performance.

Edit your model:

```python
class Call(Base):
    # ... existing fields ...

    __table_args__ = (
        # Existing indexes
        Index("idx_user_active", "user_id", "is_active"),

        # New index for phone number lookups
        Index("idx_phone_number", "phone_number"),  # ← Add this
    )
```

Generate and apply:

```bash
esc run maive-infra/will-dev -- pnpm db:migrate:create "Add phone number index"
esc run maive-infra/will-dev -- pnpm db:migrate
```

### Data Migrations

**Scenario:** Populate a new field based on existing data.

Sometimes autogenerate isn't enough - you need to run custom logic.

#### Step 1: Create Empty Migration

```bash
esc run maive-infra/will-dev -- pnpm db:migrate:create "Populate duration from call data"
```

#### Step 2: Add Custom Logic

Edit the generated file:

```python
from alembic import op
import sqlalchemy as sa

def upgrade() -> None:
    """Populate duration_seconds from existing call data."""
    # Custom SQL or Python logic
    op.execute("""
        UPDATE calls
        SET duration_seconds =
            EXTRACT(EPOCH FROM (ended_at - started_at))::integer
        WHERE ended_at IS NOT NULL
        AND duration_seconds IS NULL
    """)

def downgrade() -> None:
    """Clear populated data."""
    op.execute("UPDATE calls SET duration_seconds = NULL")
```

#### Step 3: Apply

```bash
esc run maive-infra/will-dev -- pnpm db:migrate
```

## Production Workflow

### Pre-Deployment Checklist

Before deploying migrations to production:

- [ ] Migration reviewed and tested locally
- [ ] Backwards compatible (if possible)
- [ ] Database backup taken
- [ ] Downgrade path tested
- [ ] Team notified of downtime (if any)
- [ ] Migration committed to version control

### Deploying Migrations

**Option 1: Manual (Recommended for Now)**

```bash
# SSH to production server or use ECS exec
esc run maive-infra/prod -- pnpm db:migrate
```

**Option 2: Automated (Future)**

Add to your deployment pipeline:

```yaml
# Example CI/CD step
- name: Run Migrations
  run: |
    esc run maive-infra/prod -- pnpm db:migrate
```

**Option 3: Container Startup (Advanced)**

Modify your Dockerfile to run migrations on startup:

```dockerfile
CMD ["sh", "-c", "alembic upgrade head && uvicorn src.main:app --host 0.0.0.0 --port 8080"]
```

⚠️ **Warning:** This can cause issues with multiple containers starting simultaneously!

### Safe Migration Strategies

#### Making Columns Non-Nullable Safely

**DON'T:**
```python
# ❌ This will fail if there's existing data
op.add_column('calls', Column('new_field', String(), nullable=False))
```

**DO:**
```python
# Migration 1: Add nullable
op.add_column('calls', Column('new_field', String(), nullable=True))

# Migration 2: Populate data
op.execute("UPDATE calls SET new_field = 'default'")

# Migration 3: Make non-nullable
op.alter_column('calls', 'new_field', nullable=False)
```

#### Renaming Columns Safely

**DON'T:**
```python
# ❌ Breaks running application
op.alter_column('calls', 'old_name', new_column_name='new_name')
```

**DO:**
```python
# Migration 1: Add new column
op.add_column('calls', Column('new_name', String()))

# Migration 2: Copy data
op.execute("UPDATE calls SET new_name = old_name")

# Deploy new code that uses new_name

# Migration 3: Drop old column (later)
op.drop_column('calls', 'old_name')
```

## Troubleshooting

### "Target database is not up to date"

**Problem:** Alembic thinks the database is behind.

**Solution:**
```bash
# Check current version
esc run maive-infra/will-dev -- pnpm db:status

# Check expected version
esc run maive-infra/will-dev -- uv run alembic show head

# Apply missing migrations
esc run maive-infra/will-dev -- pnpm db:migrate
```

### "Can't connect to database"

**Problem:** Environment variables not set.

**Solution:**
```bash
# Verify ESC environment
esc run maive-infra/will-dev -- env | grep DB_

# Should show:
# DB_HOST=<rds-endpoint>
# DB_PORT=5432
# DB_NAME=maive_will_dev
# DB_USER=maive_app
# DB_PASSWORD=***
```

### "Migration conflict"

**Problem:** Two developers created migrations at the same time.

**Solution:**
```bash
# Alembic shows this as a "multiple heads" error
# Merge the branches:
alembic merge heads -m "Merge migrations"
```

### "Migration failed halfway"

**Problem:** Migration crashed mid-execution.

**Solution:**
```bash
# Check database state
esc run maive-infra/will-dev -- pnpm db:status

# If marked as complete but actually failed:
# Manually fix the database, then:
alembic stamp <correct_version>

# If need to rollback:
esc run maive-infra/will-dev -- pnpm db:migrate:down
```

### "Connection refused" or "Timeout"

**Problem:** Network/security group issue.

**Solution:**
- Verify RDS security group allows traffic from ECS
- Check RDS is in correct VPC subnets
- Verify environment variables match actual RDS endpoint

## Best Practices

### Migration Naming

Be descriptive:

```bash
# ✅ Good
pnpm db:migrate:create "Add email field to users table"
pnpm db:migrate:create "Create projects table with indexes"

# ❌ Bad
pnpm db:migrate:create "update"
pnpm db:migrate:create "fix"
```

### When to Use Autogenerate

**Use autogenerate for:**
- Adding/removing columns
- Creating new tables
- Adding indexes
- Changing column types

**Write manually for:**
- Data migrations
- Complex multi-step changes
- Custom SQL operations
- Renaming columns/tables (requires special handling)

### Version Control

**Always commit:**
- Migration files (`alembic/versions/*.py`)
- Model changes (`src/db/*/model.py`)

**Never commit:**
- `__pycache__/`
- `*.pyc`
- Database files (`.db`)

### Testing Migrations

**Before committing:**

```bash
# Test upgrade
esc run maive-infra/will-dev -- pnpm db:migrate

# Test your application works

# Test downgrade
esc run maive-infra/will-dev -- pnpm db:migrate:down

# Test upgrade again
esc run maive-infra/will-dev -- pnpm db:migrate
```

### Backwards Compatibility

When possible, make migrations backwards compatible:

**Example:** Adding a column
```python
# ✅ Old code continues working
op.add_column('calls', Column('new_field', String(), nullable=True))

# ❌ Old code breaks
op.add_column('calls', Column('new_field', String(), nullable=False))
```

This allows you to:
1. Deploy migration
2. Deploy new code
3. No downtime!

### Never Edit Applied Migrations

Once a migration is applied to production:

- ❌ **DON'T** edit the file
- ✅ **DO** create a new migration to fix issues

**Why?** Other developers and servers have already applied it. Editing creates version mismatches.

## Additional Resources

### Documentation

- [SQLAlchemy 2.0 Docs](https://docs.sqlalchemy.org/en/20/)
- [Alembic Tutorial](https://alembic.sqlalchemy.org/en/latest/tutorial.html)
- [PostgreSQL 17 Docs](https://www.postgresql.org/docs/17/)

### Useful Alembic Commands

```bash
# Create empty migration for manual changes
uv run alembic revision -m "Custom migration"

# Show specific migration
uv run alembic show <revision>

# Upgrade to specific version
uv run alembic upgrade <revision>

# Downgrade to specific version
uv run alembic downgrade <revision>

# Generate SQL without applying
uv run alembic upgrade head --sql

# Show migration history with details
uv run alembic history --verbose
```

### SQL Access (Emergency)

If you need direct database access:

```bash
# Using Pulumi ESC variables
esc run maive-infra/will-dev -- psql \
  -h $DB_HOST \
  -U $DB_USER \
  -d $DB_NAME

# Or construct connection string
psql postgresql://$DB_USER:$DB_PASSWORD@$DB_HOST:$DB_PORT/$DB_NAME
```

## Need Help?

- Check [Troubleshooting](#troubleshooting) section above
- Review Alembic command output for hints
- Check CloudWatch logs in AWS Console
- Ask the team!
