import os
import asyncio
import multiprocessing
from flask import Flask
from bot import dp, bot

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running"

@app.route('/health')
def health():
    return "OK"

def run_bot():
    asyncio.run(dp.start_polling(bot))

if __name__ == "__main__":
    # Запускаем бота в отдельном процессе
    bot_process = multiprocessing.Process(target=run_bot)
    bot_process.start()
    
    # Запускаем Flask
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
