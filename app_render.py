import os
import asyncio
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from bot import dp, bot

# ИСПРАВЛЕНО: адрес нового сервиса с ботом
BASE_WEBHOOK_URL = "https://wb-bot-telegram.onrender.com"
WEBHOOK_PATH = "/webhook"
WEBHOOK_SECRET = "my-secret-token"

async def on_startup(bot: Bot):
    await bot.set_webhook(
        f"{BASE_WEBHOOK_URL}{WEBHOOK_PATH}",
        secret_token=WEBHOOK_SECRET,
        drop_pending_updates=True  # полезно при переключении с polling
    )
    print("Webhook set successfully")

async def main():
    app = web.Application()

    # Регистрируем on_startup через dispatcher
    dp.startup.register(on_startup)

    webhook_requests_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
        secret_token=WEBHOOK_SECRET,
    )
    webhook_requests_handler.register(app, path=WEBHOOK_PATH)

    async def healthcheck(request):
        return web.Response(text="OK")
    app.router.add_get("/", healthcheck)

    # setup_application сам подключает startup/shutdown диспетчера
    setup_application(app, dp, bot=bot)

    port = int(os.environ.get("PORT", 10000))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"Webhook server started on port {port}")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
