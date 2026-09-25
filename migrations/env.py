from alembic import context
from lattice_core.db import engine, Base
import lattice_core.models  # noqa: F401


def run():
    with engine.connect() as conn:
        context.configure(connection=conn, target_metadata=Base.metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()


run()
