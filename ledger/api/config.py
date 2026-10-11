# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Joel Spector

from pathlib import Path

import dotenv
from pydantic_settings import BaseSettings

base_dir = Path(__file__).resolve().parent
env_path = str(base_dir / ".env")
env = dotenv.load_dotenv(env_path)


class Settings(BaseSettings):
    DATABASE_URL: str | None = None

    class Config:
        env_file = env_path


settings = Settings()

### EOF: /positive-proxy/ledger/api/config.py ###
