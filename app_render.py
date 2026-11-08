import os
import asyncio
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from bot import dp, bot

# URL вашего сервиса на Render
BASE_WEBHOOK_URL = "https://wb-bot-g44p.onrender.com"
WEBHOOK_PATH = "/webhook"
WEBHOOK_SECRET = "my-secret-token"

async def on_startup(bot: Bot) -> None:
    await bot.set_webhook(f"{BASE_WEBHOOK_URL}{WEBHOOK_PATH}", secret_token=WEBHOOK_SECRET)

async def main():
    app = web.Application()

    webhook_requests_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
        secret_token=WEBHOOK_SECRET,
    )
    webhook_requests_handler.register(app, path=WEBHOOK_PATH)

    async def healthcheck(request):
        return web.Response(text="OK")
    app.router.add_get("/", healthcheck)

    setup_application(app, dp, bot=bot)
    app.on_startup.append(on_startup)

    port = int(os.environ.get("PORT", 10000))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"Webhook server started on port {port}")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
