#!/usr/bin/env python3
import os
import asyncio
import aiohttp
import re
import json

# Ключи из переменных окружения Render
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
ZAI_API_KEY = os.getenv("ZAI_API_KEY", "")
CLOUDFLARE_API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN", "")
CLOUDFLARE_ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID", "")

# Настройки провайдеров
PROVIDERS = [
    {
        "name": "Groq",
        "url": "https://api.groq.com/openai/v1/chat/completions",
        "key": GROQ_API_KEY,
        "model": "openai/gpt-oss-120b",
        "headers": {"Authorization": f"Bearer {GROQ_API_KEY}"}
    },
    {
        "name": "Z.ai",
        "url": "https://api.z.ai/api/paas/v4/chat/completions",
        "key": ZAI_API_KEY,
        "model": "glm-4.5-flash",
        "headers": {"Authorization": f"Bearer {ZAI_API_KEY}"}
    },
    {
        "name": "Cloudflare",
        "url": f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/ai/run/@cf/meta/llama-3.3-70b-instruct-fp8-fast",
        "key": CLOUDFLARE_API_TOKEN,
        "model": None,
        "headers": {"Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}"}
    }
]

async def _make_request(provider: dict, prompt: str) -> str:
    headers = {
        "Content-Type": "application/json",
        **provider["headers"]
    }
    
    if provider["name"] == "Cloudflare":
        payload = {
            "messages": [
                {"role": "system", "content": "Ты помощник, который генерирует рекламные тексты для товаров."},
                {"role": "user", "content": prompt},
            ]
        }
    else:
        payload = {
            "model": provider["model"],
            "messages": [
                {"role": "system", "content": "Ты помощник, который генерирует рекламные тексты для товаров."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.7,
        }

    async with aiohttp.ClientSession() as session:
        async with session.post(provider["url"], headers=headers, json=payload, timeout=120) as resp:
            if resp.status == 429:
                raise Exception(f"RATE_LIMIT_{provider['name']}")
            resp.raise_for_status()
            data = await resp.json()
    
    if provider["name"] == "Cloudflare":
        if "result" in data and "response" in data["result"]:
            return data["result"]["response"].strip()
        else:
            raise Exception(f"EMPTY_RESPONSE_{provider['name']}")
    
    choices = data.get("choices", [])
    if not choices or "message" not in choices[0]:
        raise Exception(f"EMPTY_RESPONSE_{provider['name']}")
    
    return choices[0]["message"]["content"].strip()


async def generate_full_package(product_name: str) -> dict:
    prompt = (
        "You are a helpful assistant. Generate strictly a JSON object with the following keys: "
        "\"header\" (up to 50 characters), \"description\" (3-5 sentences), "
        "\"keywords\" (comma-separated list, 5-7 keywords), \"hashtags\" (comma-separated list of hashtags starting with #). "
        f"Product: {product_name}. "
        "Return ONLY the JSON object, no extra text, no markdown fences."
    )

    last_error = None

    for attempt in range(5):
        for provider in PROVIDERS:
            if not provider["key"].strip():
                continue
            
            try:
                print(f"Попытка использовать {provider['name']} (круг {attempt+1})...")
                raw = await _make_request(provider, prompt)
                print(f"УСПЕХ: {provider['name']} ответил.")
                
                # Пытаемся распарсить JSON
                data = None
                try:
                    data = json.loads(raw)
                except Exception:
                    start = raw.find("{")
                    end = raw.rfind("}")
                    if start != -1 and end != -1 and end > start:
                        json_candidate = raw[start:end+1]
                        try:
                            data = json.loads(json_candidate)
                        except Exception:
                            data = None
                    if data is None:
                        raise ValueError("No valid JSON found in response")

                header = data.get("header", "")[:50]
                description = data.get("description", "")
                keywords = data.get("keywords", "")
                hashtags = data.get("hashtags", "")

                return {
                    "header": header,
                    "description": description,
                    "keywords": keywords,
                    "hashtags": hashtags
                }

            except Exception as e:
                last_error = e
                error_str = str(e)
                
                if "RATE_LIMIT_Z.ai" in error_str:
                    print(f"Лимит Z.ai! Ждем 60 секунд...")
                    await asyncio.sleep(60)
                elif "RATE_LIMIT_Groq" in error_str:
                    print(f"Лимит Groq! Ждем 10 секунд...")
                    await asyncio.sleep(10)
                elif "RATE_LIMIT_Cloudflare" in error_str:
                    print(f"Лимит Cloudflare! Ждем 10 секунд...")
                    await asyncio.sleep(10)
                else:
                    print(f"ОШИБКА {provider['name']}: {e}. Пробуем следующего...")
                    await asyncio.sleep(2)

    return {"error": f"All providers failed. Last error: {last_error}"}
