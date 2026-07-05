# file: /positive-proxy/ledger/api/database.py
copyright = """
    Positive Proxy is a bill-making and voting system that allows voters to pass their ballot to trusted parties to vote on their behalf.
    Copyright (C) 2026  Joel Spector

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as
    published by the Free Software Foundation, either version 3 of the
    License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>."""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
import os
from sqlalchemy import text

from ledger.api.config import settings

# 1. Create the asynchronous database engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=True,  # Set to False in production; True logs all raw SQL scripts being executed
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
    sql_path = os.path.join(base_dir, "scripts", "init_db.sql") #warning: this path is hardcoded
    
    if not os.path.exists(sql_path):
        print(f"⚠️ Warning: Initialization script not found at {sql_path}")
        return

    #print("🚀 Initializing Positive Proxy database schema...")
    with open(sql_path, "r") as f:
        sql_script = f.read()

    try:
        async with engine.begin() as conn:
            await conn.execute(text(sql_script))
        print("✅ Database schema initialization complete.")
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        print("Continuing server startup, but database may be incomplete.")

### EOF: /positive-proxy/ledger/api/database.py ###