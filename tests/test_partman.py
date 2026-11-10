"""Unit tests for PostgreSQL DDL templating, identifier validation, and retention pruning."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from pg_partman import main as cli_main
from pg_partman.manager import PartitionManager
from pg_partman.sql_templates import (
    get_daily_partition_ddl,
    get_monthly_partition_ddl,
    parse_table_ref,
)


def test_parse_table_ref_validation() -> None:
    assert parse_table_ref("events") == (None, "events")
    assert parse_table_ref("analytics.metrics_v2") == ("analytics", "metrics_v2")

    for bad in ("", "events; DROP TABLE users;--", "a.b.c", "events-bad", "1starts_digit"):
        with pytest.raises(ValueError):
            parse_table_ref(bad)


def test_daily_and_monthly_ddl_generation() -> None:
    part, ddl = get_daily_partition_ddl("analytics.events", datetime(2026, 11, 10))
    assert part == "analytics.events_p20261110"
    assert 'CREATE TABLE IF NOT EXISTS "analytics"."events_p20261110"' in ddl
    assert 'PARTITION OF "analytics"."events"' in ddl
    assert "FOR VALUES FROM ('2026-11-10') TO ('2026-11-11');" in ddl

    m_part, m_ddl = get_monthly_partition_ddl("logs", 2026, 12)
    assert m_part == "logs_p202612"
    assert "FOR VALUES FROM ('2026-12-01') TO ('2027-01-01');" in m_ddl

    with pytest.raises(ValueError):
        get_monthly_partition_ddl("logs", 2026, 13)


class _FakeCursor:
    def __init__(self, fetched: list[tuple[str]]) -> None:
        self.fetched = fetched
        self.executed: list[tuple[str, tuple | None]] = []

    def __enter__(self) -> _FakeCursor:
        return self

    def __exit__(self, *args) -> None:
        return None

    def execute(self, sql: str, params: tuple | None = None) -> None:
        self.executed.append((sql, params))

    def fetchall(self) -> list[tuple[str]]:
        return self.fetched


class _FakeConn:
    def __init__(self, fetched: list[tuple[str]]) -> None:
        self.cur = _FakeCursor(fetched)

    def __enter__(self) -> _FakeConn:
        return self

    def __exit__(self, *args) -> None:
        return None

    def cursor(self) -> _FakeCursor:
        return self.cur


def test_manager_create_and_drop_partitions(monkeypatch: pytest.MonkeyPatch) -> None:
    today = datetime.now(UTC).date()
    expired_suffix = (today - timedelta(days=120)).strftime("%Y%m%d")
    fresh_suffix = (today - timedelta(days=1)).strftime("%Y%m%d")
    fake_conn = _FakeConn(
        fetched=[
            (f"analytics.events_p{expired_suffix}",),
            (f"analytics.events_p{fresh_suffix}",),
            ("analytics.events_default",),
        ]
    )

    monkeypatch.setattr("pg_partman.manager.psycopg.connect", lambda *a, **kw: fake_conn)
    mgr = PartitionManager("postgresql://localhost/test")

    created = mgr.create_future_partitions("analytics.events", premake_days=2)
    assert len(created) == 2

    dropped = mgr.drop_old_partitions("analytics.events", retention_days=90)
    assert dropped == [f"analytics.events_p{expired_suffix}"]
    assert any(
        f'DROP TABLE IF EXISTS "analytics"."events_p{expired_suffix}";' in sql
        for sql, _ in fake_conn.cur.executed
    )


def test_cli_run_maintenance(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, int]] = []

    monkeypatch.setattr(
        PartitionManager,
        "create_future_partitions",
        lambda self, tbl, premake: calls.append(("create:" + tbl, premake)) or [],
    )
    monkeypatch.setattr(
        PartitionManager,
        "drop_old_partitions",
        lambda self, tbl, ret: calls.append(("drop:" + tbl, ret)) or [],
    )
    cli_main.run_maintenance(
        {
            "database_url": "postgresql://localhost/db",
            "tables": [{"name": "events", "premake_days": 5, "retention_days": 30}],
        }
    )
    assert calls == [("create:events", 5), ("drop:events", 30)]
