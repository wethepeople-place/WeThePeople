"""Isolated canonical migration environment for new databases only."""

import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from models.database import Base  # noqa: E402
import models.act_models  # noqa: E402,F401 -- register ACT tables in Base.metadata
from alembic_canonical.defaults import compare_server_default  # noqa: E402

config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name)

database_url = os.getenv("WTP_CANONICAL_DB_URL")
if not database_url:
    raise RuntimeError(
        "WTP_CANONICAL_DB_URL is required for canonical migrations; "
        "the runtime WTP_DB_URL is intentionally ignored"
    )
config.set_main_option("sqlalchemy.url", database_url)

target_metadata = Base.metadata
VERSION_TABLE = "alembic_version_canonical"
def run_migrations_offline() -> None:
    context.configure(
        url=database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=compare_server_default,
        version_table=VERSION_TABLE,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=compare_server_default,
            render_as_batch=connection.dialect.name == "sqlite",
            version_table=VERSION_TABLE,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
