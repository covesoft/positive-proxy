# file: /positive-proxy/ledger/api/config.py
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

from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Default local development connection string pointing to PostgreSQL
    # Using 'postgresql+asyncpg' as the driver for non-blocking I/O
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/positive_proxy_db"

    class Config:
        env_file = ".env"

settings = Settings()

### EOF: /positive-proxy/ledger/api/config.py ###