# file: /positive-proxy/clients/discord/config.py
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

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Tokens (nom nom nom, tasty 🤤😝)
TOKEN = os.getenv("DISCORD_TOKEN")
DEBUG_MODE = os.getenv("LOGGING_DEBUG_MODE")
ENVIRONMENT = os.getenv("DEVELOPMENT_ENVIRONMENT")
BASE_URL = os.getenv("BASE_URL")
PROXY_USERNAME = os.getenv("PROXY_USERNAME")
PROXY_PASSWORD = os.getenv("PROXY_PASSWORD")
if not DEBUG_MODE is None and DEBUG_MODE.lower() == "true":
    LOGGING_DEBUG_MODE = True
else:
    LOGGING_DEBUG_MODE = False
if not DEBUG_MODE is None and DEBUG_MODE.lower() == "true":
    DEVELOPMENT_ENVIRONMENT = True
else:
    DEVELOPMENT_ENVIRONMENT = False
if DEVELOPMENT_ENVIRONMENT:
    TOKEN = os.getenv("DEVELOPMENT_TOKEN")
if not TOKEN:
    raise SystemExit("Set DISCORD_TOKEN in .env")
# Base directory
BASE_DIR = Path(__file__).resolve().parent

# Database paths

#TBD