#!/usr/bin/env python3
import os
import sys

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "openai/gpt-oss-20b"

def build_prompt(product_name: str) -> str:
    return f"""
    Напиши продающее описание для товара на маркетплейсе.
    Товар: {product_name}.
    Описание должно быть привлекательным, коротким (около 3-5 предложений),
    содержать основные преимущества и вызвать желание купить.
    Пиши на русском языке.
    """

def generate_description(product_name: str) -> str:
    if not GROQ_API_KEY.strip():
        return "⚠️ У вас не указан API-ключ Groq."

    import requests

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {GROQ_API_KEY}",
    }

    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": "Ты полезный ассистент, который пишет рекламные тексты."},
            {"role": "user", "content": build_prompt(product_name)},
        ],
        "temperature": 0.7,
    }

    try:
        response = requests.post(GROQ_URL, headers=headers, json=payload, timeout=15)
        response.raise_for_status()
        data = response.json()
        choices = data.get("choices", [])
        if choices and "message" in choices[0]:
            return choices[0]["message"]["content"].strip()
        else:
            return "❗️ Неожиданный формат ответа от Groq."
    except Exception as e:
        print(f"ОШИБКА generate_description для {product_name}: {type(e).__name__} - {e}")
        return f"❌ Ошибка: {e}"

def generate_full_package(product_name: str) -> str:
    if not GROQ_API_KEY.strip():
        return "⚠️ У вас не указан API-ключ Groq."

    import requests

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {GROQ_API_KEY}",
    }

    prompt = f"""
    Сгенерируй полный пакет для карточки товара на маркетплейсе.
    Товар: {product_name}.

    Предоставь следующую информацию:
    1. Заголовок (максимум 50 символов) — короткий продающий титул.
    2. Описание (продающее текст, 3-5 предложений, с основными преимуществами).
    3. Ключевые слова (5-7 штук, через запятую).
    4. Хэштеги (3-5 штук, начинающихся с #).

    Верни ответ в формате (каждая часть с новой строки, заголовки в квадратных скобках):

    [HEADER]: <заголовок>
    [DESCRIPTION]: <описание>
    [KEYWORDS]: <ключевое1, ключевое2, ...>
    [HASHTAGS]: <хэштег1, хэштег2, ...>
    """

    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": "Ты помощник, который генерирует рекламные тексты для товаров."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.7,
    }

    try:
        response = requests.post(GROQ_URL, headers=headers, json=payload, timeout=15)
        response.raise_for_status()
        data = response.json()
        choices = data.get("choices", [])

        # Проверка на пустой ответ
        if not choices or "message" not in choices[0]:
            print(f"ПУСТОЙ ОТВЕТ Groq для {product_name}: {data}")
            return "❗️ Пустой ответ от Groq."

        raw = choices[0]["message"]["content"].strip()
        print(f"ОТВЕТ Groq для {product_name}: {len(raw)} символов, начало: {raw[:100]}")

        header = ""
        description = ""
        keywords = ""
        hashtags = ""
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            lower = line.lower()
            if lower.startswith("[header]") or lower.startswith("header:"):
                parts = line.split(":", 1)
                header = parts[1].strip() if len(parts) > 1 else ""
            elif lower.startswith("[description]") or lower.startswith("description:"):
                parts = line.split(":", 1)
                description = parts[1].strip() if len(parts) > 1 else ""
            elif lower.startswith("[keywords]") or lower.startswith("keywords:"):
                parts = line.split(":", 1)
                keywords = parts[1].strip() if len(parts) > 1 else ""
            elif lower.startswith("[hashtags]") or lower.startswith("hashtags:"):
                parts = line.split(":", 1)
                hashtags = parts[1].strip() if len(parts) > 1 else ""

        # Логирование ошибки парсинга (если header и description пустые)
        if not header and not description:
            print(f"ОШИБКА ПАРСИНГА для {product_name}: raw={raw[:200]}")
            return "❗️ Ошибка парсинга ответа Groq."

        header = header[:50]
        result = (
            f"--- Заголовок ({len(header)} символов) ---\n"
            f"{header}\n\n"
            f"--- Описание (продающее) ---\n"
            f"{description}\n\n"
            f"--- Ключевые слова ---\n"
            f"{keywords}\n\n"
            f"--- Хэштеги ---\n"
            f"{hashtags}\n"
        )
        return result
    except Exception as e:
        print(f"ОШИБКА Groq для {product_name}: {type(e).__name__} - {e}")
        return f"❌ Ошибка: {e}"

def main():
    product_input = input("Введите название товара (или нажмите Enter для использования значения по умолчанию): ").strip()
    if not product_input:
        product_input = "Кружка керамическая с принтом Кот-программист"
    print(f"🔍 Генерация описания для товара: {product_input}\n")
    description = generate_description(product_input)
    print("=== Генерированное описание ===")
    print(description)

if __name__ == "__main__":
    main()
