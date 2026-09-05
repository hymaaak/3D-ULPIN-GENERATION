"""Initial schema revision — executes the full Section 6 DDL (same source file
that docker-compose mounts into postgres as an init script: alembic/init.sql).
"""
from pathlib import Path

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

DDL_PATH = Path(__file__).resolve().parents[1] / "init.sql"


def _split_sql(sql: str) -> list[str]:
    """Split SQL on semicolons, ignoring those inside $$ ... $$ bodies."""
    statements: list[str] = []
    current: list[str] = []
    in_dollar = False
    i = 0
    while i < len(sql):
        if sql[i : i + 2] == "$$":
            in_dollar = not in_dollar
            current.append("$$")
            i += 2
            continue
        if sql[i] == ";" and not in_dollar:
            statement = "".join(current).strip()
            if statement:
                statements.append(statement)
            current = []
        else:
            current.append(sql[i])
        i += 1
    tail = "".join(current).strip()
    if tail:
        statements.append(tail)
    return statements


def upgrade() -> None:
    sql = DDL_PATH.read_text(encoding="utf-8")
    for statement in _split_sql(sql):
        op.execute(statement)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trigger_parcels_updated_at ON parcels")
    op.execute("DROP FUNCTION IF EXISTS update_updated_at")
    op.execute("DROP FUNCTION IF EXISTS detect_3d_conflicts(UUID)")
    for table in (
        "conflict_alerts",
        "processing_jobs",
        "data_sources",
        "ownership_records",
        "units",
        "buildings",
        "parcels",
        "owners",
        "users",
    ):
        op.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
    for enum_type in (
        "alert_status",
        "severity_level",
        "conflict_type",
        "job_status",
        "job_type",
        "processing_status",
        "source_type",
        "owner_type",
        "rights_type",
        "unit_type",
        "building_type",
        "parcel_status",
        "parcel_type",
        "user_role",
    ):
        op.execute(f"DROP TYPE IF EXISTS {enum_type}")
