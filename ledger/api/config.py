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
import dotenv
from pathlib import Path

base_dir = Path(__file__).resolve().parent
env_path = str(base_dir / ".env")
env = dotenv.load_dotenv(env_path)


class Settings(BaseSettings):
    DATABASE_URL: str | None = None

    class Config:
        env_file = env_path


settings = Settings()

### EOF: /positive-proxy/ledger/api/config.py ###
