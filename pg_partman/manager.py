from datetime import datetime, timedelta
import psycopg
from .sql_templates import get_daily_partition_ddl


class PartitionManager:
    def __init__(self, db_url: str):
        self.db_url = db_url

    def create_future_partitions(self, parent_table: str, premake_days: int = 7):
        today = datetime.utcnow().date()
        with psycopg.connect(self.db_url, autocommit=True) as conn:
            with conn.cursor() as cur:
                for i in range(premake_days):
                    target_date = datetime.combine(today + timedelta(days=i), datetime.min.time())
                    part_name, ddl = get_daily_partition_ddl(parent_table, target_date)
                    cur.execute(ddl)
                    print(f"[+] Ensured partition exists: {part_name}")

    def drop_old_partitions(self, parent_table: str, retention_days: int = 90):
        cutoff = datetime.utcnow().date() - timedelta(days=retention_days)
        cutoff_str = cutoff.strftime("%Y%m%d")

        query = """
        SELECT inhrelid::regclass AS child
        FROM   pg_inherits
        WHERE  inhparent = %s::regclass;
        """
        with psycopg.connect(self.db_url, autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute(query, (parent_table,))
                partitions = [row[0] for row in cur.fetchall()]

                for part in partitions:
                    if "_p" in part:
                        suffix = part.split("_p")[-1]
                        if suffix.isdigit() and len(suffix) == 8 and suffix < cutoff_str:
                            cur.execute(f"DROP TABLE IF EXISTS {part};")
                            print(f"[-] Dropped expired partition: {part}")
