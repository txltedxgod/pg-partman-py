# pg-partman-py

> Automated **timeseries table partitioning and retention lifecycle daemon** for **PostgreSQL 14+** in Python.

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat-square&logo=python)](https://python.org)
[![PostgreSQL](https://img.shields.io/badge/Database-PostgreSQL_14%2B-336791?style=flat-square&logo=postgresql)](https://postgresql.org)
[![CI](https://img.shields.io/badge/CI-Passing-238636?style=flat-square&logo=githubactions)](https://github.com/txltedxgod/pg-partman-py/actions)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=flat-square&logo=docker)](https://docker.com)
[![License](https://img.shields.io/badge/License-MIT-blue?style=flat-square)](LICENSE)

`#postgresql` `#partitioning` `#timeseries` `#database-admin` `#devops` `#python` `#maintenance`

---

## 🏛️ Timeseries Partitioning Lifecycle

```mermaid
graph LR
    Master[Master Table: http_logs] -->|Range: 2026-08-15| P1[http_logs_p20260815]
    Master -->|Range: 2026-08-16| P2[http_logs_p20260816]
    Master -->|Range: 2026-08-17 (Today)| P3[http_logs_p20260817 Active]
    Master -->|Range: 2026-08-18 (Future)| P4[http_logs_p20260818 Pre-created]

    Daemon((pg-partman Daemon)) -->|1. Pre-make +7 days ahead| P4
    Daemon -->|2. Drop partitions > retention_days| Dropped[(Deleted Old Tables)]
```

---

## Features

- **Automated Partition Pre-Creation:** Automatically calculates date ranges and runs `CREATE TABLE ... PARTITION OF` days in advance.
- **Configurable Retention:** Prunes tables older than `retention_days` to reclaim disk space automatically.
- **Zero Query Interruption:** Uses native PostgreSQL declarative partitioning.

## Quick Start

```bash
# 1. Install CLI
pip install -r requirements.txt
pip install -e .

# 2. Run maintenance once
pg-partman --config=config.example.yaml --once

# 3. Run as continuous daily daemon
pg-partman --config=config.example.yaml
```
