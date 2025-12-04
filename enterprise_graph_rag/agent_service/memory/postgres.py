from contextlib import contextmanager
from psycopg_pool import ConnectionPool
from langgraph.checkpoint.postgres import PostgresSaver
from agent_service.core.config import agent_settings

class PersistenceManager:
    _pool = None

    @classmethod
    def get_pool(cls):
        if cls._pool is None:
            cls._pool = ConnectionPool(
                conninfo=agent_settings.POSTGRES_URI,
                max_size=20,
                kwargs={"autocommit": True}
            )
        return cls._pool

    @classmethod
    def setup_tables(cls):
        """Ensures the necessary tables exist in Postgres."""
        pool = cls.get_pool()
        with pool.connection() as conn:
            # PostgresSaver automatically creates tables on first use, 
            # but we initialize the checkpoint saver to trigger it.
            checkpointer = PostgresSaver(conn)
            checkpointer.setup()