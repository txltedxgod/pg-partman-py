"""Safe SQL DDL generation and identifier validation for PostgreSQL partitions."""

from __future__ import annotations

import re
from datetime import datetime, timedelta

_IDENT_PART_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]{0,62}$")


def parse_table_ref(table_ref: str) -> tuple[str | None, str]:
    """Validate and split an optional schema-qualified PostgreSQL identifier."""
    cleaned = (table_ref or "").strip()
    parts = cleaned.split(".")
    if len(parts) == 1 and _IDENT_PART_RE.match(parts[0]):
        return None, parts[0]
    if len(parts) == 2 and all(_IDENT_PART_RE.match(p) for p in parts):
        return parts[0], parts[1]
    raise ValueError(
        f"Invalid PostgreSQL table identifier: {table_ref!r}. "
        "Only alphanumeric/underscore names with optional schema prefix are allowed."
    )


def format_qualified_ident(schema: str | None, table: str) -> str:
    """Safely quote a validated table identifier for PostgreSQL DDL."""
    if schema:
        return f'"{schema}"."{table}"'
    return f'"{table}"'


def get_daily_partition_ddl(parent_table: str, date: datetime) -> tuple[str, str]:
    """Build daily range partition name and CREATE TABLE DDL."""
    schema, table = parse_table_ref(parent_table)
    part_short = f"{table}_p{date.strftime('%Y%m%d')}"
    part_ref = f"{schema}.{part_short}" if schema else part_short
    start_date = date.strftime("%Y-%m-%d")
    end_date = (date + timedelta(days=1)).strftime("%Y-%m-%d")

    parent_sql = format_qualified_ident(schema, table)
    part_sql = format_qualified_ident(schema, part_short)
    ddl = (
        f"CREATE TABLE IF NOT EXISTS {part_sql} PARTITION OF {parent_sql}\n"
        f"FOR VALUES FROM ('{start_date}') TO ('{end_date}');"
    )
    return part_ref, ddl


def get_monthly_partition_ddl(parent_table: str, year: int, month: int) -> tuple[str, str]:
    """Build monthly range partition name and CREATE TABLE DDL."""
    if not (1 <= month <= 12):
        raise ValueError(f"Month must be between 1 and 12, got {month}.")
    if not (1970 <= year <= 9999):
        raise ValueError(f"Year out of valid range: {year}.")

    schema, table = parse_table_ref(parent_table)
    part_short = f"{table}_p{year}{month:02d}"
    part_ref = f"{schema}.{part_short}" if schema else part_short
    start_date = f"{year}-{month:02d}-01"
    end_date = f"{year + 1}-01-01" if month == 12 else f"{year}-{month + 1:02d}-01"

    parent_sql = format_qualified_ident(schema, table)
    part_sql = format_qualified_ident(schema, part_short)
    ddl = (
        f"CREATE TABLE IF NOT EXISTS {part_sql} PARTITION OF {parent_sql}\n"
        f"FOR VALUES FROM ('{start_date}') TO ('{end_date}');"
    )
    return part_ref, ddl
