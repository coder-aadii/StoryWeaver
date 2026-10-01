"""Docker-free PostgreSQL 16 + pgvector for development (via the `pgserver` wheel).

Run: cd apps/api && uv run --with pgserver python ../../scripts/dev_postgres.py
Data lives in data/temporary/pgdata (git-ignored). The server keeps running after this exits;
stop it with `pg_ctl`-equivalent: rerun with --stop.
"""

import sys
from pathlib import Path

import pgserver

PGDATA = Path(__file__).resolve().parents[1] / "data" / "temporary" / "pgdata"
db = pgserver.get_server(PGDATA, cleanup_mode="stop" if "--stop" in sys.argv else None)
if "--stop" in sys.argv:
    db.cleanup()
    print("stopped")
    raise SystemExit
for name in ("storyweaver", "storyweaver_test"):
    exists = db.psql(f"SELECT 1 FROM pg_database WHERE datname='{name}';")
    if "(0 rows)" in exists:
        db.psql(f"CREATE DATABASE {name};")
sock = db.get_uri().split("host=")[1]
for name, var in (("storyweaver", "DATABASE_URL"), ("storyweaver_test", "TEST_DATABASE_URL")):
    print(f"{var}=postgresql+psycopg://postgres@/{name}?host={sock}")
print("\nExport those variables (or put DATABASE_URL in .env), then: make db-migrate")
