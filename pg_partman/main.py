import click
import yaml
import time
import schedule
from .manager import PartitionManager


def run_maintenance(config: dict):
    db_url = config["database_url"]
    manager = PartitionManager(db_url)

    for table_conf in config.get("tables", []):
        table_name = table_conf["name"]
        premake = table_conf.get("premake_days", 7)
        retention = table_conf.get("retention_days", 60)

        print(f"[*] Running partition maintenance for '{table_name}'...")
        manager.create_future_partitions(table_name, premake)
        manager.drop_old_partitions(table_name, retention)


@click.command()
@click.option("-c", "--config", "config_file", default="config.yaml", help="Path to config yaml")
@click.option("--once", is_flag=True, help="Run maintenance once and exit")
def main(config_file: str, once: bool):
    """PostgreSQL timeseries partition manager."""
    with open(config_file) as f:
        config = yaml.safe_load(f)

    if once:
        run_maintenance(config)
        return

    schedule.every().day.at("01:00").do(run_maintenance, config=config)
    print("[*] pg-partman daemon started. Running daily partition maintenance at 01:00 UTC.")

    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    main()
