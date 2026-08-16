from datetime import datetime, timedelta


def get_daily_partition_ddl(parent_table: str, date: datetime) -> tuple[str, str]:
    part_name = f"{parent_table}_p{date.strftime('%Y%m%d')}"
    start_date = date.strftime("%Y-%m-%d")
    end_date = (date + timedelta(days=1)).strftime("%Y-%m-%d")

    ddl = f"""
    CREATE TABLE IF NOT EXISTS {part_name} PARTITION OF {parent_table}
    FOR VALUES FROM ('{start_date}') TO ('{end_date}');
    """
    return part_name, ddl.strip()


def get_monthly_partition_ddl(parent_table: str, year: int, month: int) -> tuple[str, str]:
    part_name = f"{parent_table}_p{year}{month:02d}"
    start_date = f"{year}-{month:02d}-01"
    if month == 12:
        end_date = f"{year + 1}-01-01"
    else:
        end_date = f"{year}-{month + 1:02d}-01"

    ddl = f"""
    CREATE TABLE IF NOT EXISTS {part_name} PARTITION OF {parent_table}
    FOR VALUES FROM ('{start_date}') TO ('{end_date}');
    """
    return part_name, ddl.strip()
