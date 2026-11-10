"""PostgreSQL partition lifecycle manager for premaking and retention pruning."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import psycopg

from .sql_templates import (
    format_qualified_ident,
    get_daily_partition_ddl,
    parse_table_ref,
)


class PartitionManager:
    """Create upcoming partitions and drop expired daily/monthly partitions."""

    def __init__(self, db_url: str) -> None:
        self.db_url = db_url

    def create_future_partitions(self, parent_table: str, premake_days: int = 7) -> list[str]:
        """Ensure range partitions exist from today UTC through premake_days."""
        if premake_days < 1:
            raise ValueError("premake_days must be >= 1.")
        parse_table_ref(parent_table)

        today = datetime.now(UTC).date()
        created: list[str] = []
        with (
            psycopg.connect(self.db_url, autocommit=True) as conn,
            conn.cursor() as cur,
        ):
            for offset in range(premake_days):
                target_date = datetime.combine(
                    today + timedelta(days=offset), datetime.min.time()
                )
                part_name, ddl = get_daily_partition_ddl(parent_table, target_date)
                cur.execute(ddl)
                created.append(part_name)
                print(f"[+] Ensured partition exists: {part_name}")
        return created

    def drop_old_partitions(self, parent_table: str, retention_days: int = 90) -> list[str]:
        """Drop child daily/monthly partitions strictly older than retention_days."""
        if retention_days < 0:
            raise ValueError("retention_days must be >= 0.")
        parse_table_ref(parent_table)

        cutoff_date = datetime.now(UTC).date() - timedelta(days=retention_days)
        cutoff_daily = cutoff_date.strftime("%Y%m%d")
        cutoff_monthly = cutoff_date.strftime("%Y%m")

        query = """
        SELECT inhrelid::regclass::text AS child
        FROM   pg_inherits
        WHERE  inhparent = %s::regclass;
        """
        dropped: list[str] = []
        with (
            psycopg.connect(self.db_url, autocommit=True) as conn,
            conn.cursor() as cur,
        ):
            cur.execute(query, (parent_table,))
            partitions = [row[0] for row in cur.fetchall()]

            for part in partitions:
                part_str = str(part).replace('"', "")
                if "_p" not in part_str:
                    continue
                suffix = part_str.split("_p")[-1]
                is_expired_daily = suffix.isdigit() and len(suffix) == 8 and suffix < cutoff_daily
                is_expired_monthly = (
                    suffix.isdigit() and len(suffix) == 6 and suffix < cutoff_monthly
                )
                if is_expired_daily or is_expired_monthly:
                    schema, tbl = parse_table_ref(part_str)
                    safe_ident = format_qualified_ident(schema, tbl)
                    cur.execute(f"DROP TABLE IF EXISTS {safe_ident};")
                    dropped.append(part_str)
                    print(f"[-] Dropped expired partition: {part_str}")
        return dropped
