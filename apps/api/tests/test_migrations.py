"""Migrations apply, roll back and re-apply cleanly, and match the models (needs TEST_DATABASE_URL)."""

from alembic import command
from tests.conftest import alembic_config


def test_upgrade_downgrade_upgrade_and_no_model_drift(engine) -> None:  # type: ignore[no-untyped-def]
    cfg = alembic_config()
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    command.check(cfg)  # raises if autogenerate would produce changes
