# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Joel Spector

import asyncio
import logging
import os
import traceback
from logging.handlers import RotatingFileHandler
from pathlib import Path

import discord
from beacon import BeaconAutoShardedBot
from config import LOGGING_DEBUG_MODE, PROXY_PASSWORD, PROXY_USERNAME, TOKEN

if not TOKEN:
    raise SystemExit("ERROR: Set DISCORD_TOKEN in a .env in root folder.")

logger = logging.getLogger("discord")
if LOGGING_DEBUG_MODE:
    logger.setLevel(logging.DEBUG)
    print("Running logger in DEBUG mode")
else:
    logger.setLevel(logging.INFO)
    print("Running logger in PRODUCTION mode")
log_path = os.path.join(os.path.dirname(__file__), "discord.log")
handler = RotatingFileHandler(
    filename=log_path,
    encoding="utf-8",
    mode="a",
    maxBytes=1 * 1024 * 1024,
    backupCount=5
)
logger.addHandler(handler)

log_format = '%(asctime)s||%(levelname)s: %(message)s'
date_format = '%H:%M:%S %d-%m'

formatter = logging.Formatter(log_format, datefmt=date_format)

handler.setFormatter(formatter)

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.dm_messages = True

allowed_mentions = discord.AllowedMentions(replied_user=False)
BASE_DIR = Path(__file__).resolve().parent
COGS_DIR = BASE_DIR / "cogs"
proxy = f"http://{PROXY_USERNAME}:{PROXY_PASSWORD}@38.154.185.97:6370/"

async def on_shard_ready(shard_id: int):
    total_shards = bot.shard_count or len(bot.shards)
    activity_name = f"Listening to /dashboard | {shard_id}/{total_shards}"

    await bot.change_presence(
        activity=discord.CustomActivity(name=activity_name),
        shard_id=shard_id
    )


bot = BeaconAutoShardedBot(
    command_prefix="!",
    intents=intents,
    minimal_caching=True,
    allowed_mentions=allowed_mentions,
    version_file="VERSION.txt",
    accent_colour=discord.Colour.from_rgb(112, 206, 24),
    secure_mode=False,
    on_shard_ready_callback=on_shard_ready,
)

if __name__ == "__main__":
    async def main_async():
        try:
            async with bot:
                await bot.start(TOKEN)
        except Exception as e:
            print(f"ERROR: Failed to start the bot: {e}")
            traceback.print_exc()


    asyncio.run(main_async())

### EOF ###