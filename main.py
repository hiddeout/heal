import dotenv
from tools.heal import Heal
import datetime
import asyncio
from quart import Quart, jsonify, Request, Response
from aiohttp import web
import time

app = Quart(__name__)
bot = Heal()


@app.route("/status")
async def status(request: Request) -> Response:
    return web.json_response(
        {
            "shards": [
                {
                    "guilds": f"{len([guild for guild in bot.guilds if guild.shard_id == shard.id])}",
                    "id": f"{shard.id}",
                    "ping": f"{(shard.latency * 1000):.2f}ms",
                    "uptime": f"{int(bot.uptime)}",
                    "users": f"{len([user for guild in bot.guilds for user in guild.members if guild.shard_id == shard.id])}",
                }
                for shard in bot.shards.values()
            ]
        }
    )


dotenv.load_dotenv()


async def run_bot():
    await bot.start("")


async def run_quart():
    await app.run_task(host="127.0.0.1", port=5000)  # can change if needed


async def main():
    await asyncio.gather(run_bot(), run_quart())


if __name__ == "__main__":
    asyncio.run(main())
