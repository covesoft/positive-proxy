# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Joel Spector
# file: /positive-proxy/ledger/api/database.py

import os
import traceback
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from ledger.api.config import settings

# 1. Create the asynchronous database engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,  # Set to False in production; True logs all raw SQL scripts being executed
    future=True
)

# 2. Build an async session manager
async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# 3. Create the FastAPI Dependency Provider
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that yields an asynchronous database session scope.
    Ensures connections are automatically closed and returned to the pool after requests complete.
    """
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()

# 4. Initialize the DB schema
async def initialize_db_schema() -> None:
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sql_path = os.path.join(base_dir, "scripts", "init_db.sql")

    if not os.path.exists(sql_path):
        print(f"⚠️ Warning: Initialization script not found at {sql_path}")
        return

    with open(sql_path, "r") as f:
        sql_script = f.read()

    try:
        # 1. Acquire a raw connection out of the SQLAlchemy engine pool
        async with engine.begin() as conn:
            # 2. Extract the underlying raw psycopg connection object
            raw_conn = await conn.get_raw_connection()

            # 3. Open a native psycopg async cursor to run the multi-statement script safely
            # pyrefly: ignore [missing-attribute]
            async with raw_conn.driver_connection.cursor() as cursor:
                await cursor.execute(sql_script)

        print("✅ Database schema initialization complete.")
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        traceback.print_exc()
        print("Continuing server startup, but database may be incomplete.")

### EOF: /positive-proxy/ledger/api/database.py ###