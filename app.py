#!/usr/bin/env python3
"""
Скрипт для генерации продающего описания товара на Wildberries с использованием API Groq.

Получите ключ на https://console.groq.com/keys и вставьте его в переменную GROQ_API_KEY
или задайте её в окружении перед запуском скрипта.

Требуемые зависимости:
    pip install requests
"""

import os
import sys

# -------------------- Конфигурация --------------------
# 👇 Вставьте сюда ключ, который получили с console.groq.com
# Или задайте переменную окружения: GROQ_API_KEY=ваш_ключ
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# Эндпоинт Groq (API полностью совместим с форматом OpenAI)
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

# Бесплатная и мощная модель
GROQ_MODEL = "openai/gpt-oss-20b"


# -------------------- Формирование промпта --------------------
def build_prompt(product_name: str) -> str:
    """
    Возвращает промпт для генерации описания товара.
    """
    return f"""
    Напиши продающее описание для товара на маркетплейсе.
    Товар: {product_name}.
    Описание должно быть привлекательным, коротким (около 3-5 предложений),
    содержать основные преимущества и вызвать желание купить.
    Пиши на русском языке.
    """


# -------------------- Вызов API Groq --------------------
def generate_description(product_name: str) -> str:
    """
    Отправляет запрос к API Groq и возвращает сгенерированное описание.
    """
    # Простая проверка ключа — если вы оставили placeholder, выдадим подсказку
    if not GROQ_API_KEY.strip() or GROQ_API_KEY == "gsk_votre_cle_groq_ici":
        return (
            "⚠️ У вас не указан API-ключ Groq. "
            "Получите его на https://console.groq.com/keys и "
            "вставьте в переменную GROQ_API_KEY или задайте её в окружении перед запуском скрипта."
        )

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
        return f"❌ Ошибка при запросе к Groq: {e}"


def generate_full_package(product_name: str) -> str:
    """Отправляет запрос к API Groq и возвращает полный пакет для карточки товара.

    Формат возвращаемого текста:
    Заголовок (до 50 символов)
    Описание (продающее, с преимуществами)
    Ключевые слова (5-7 штук)
    Хэштеги (3-5 штук)
    """
    if not GROQ_API_KEY.strip() or GROQ_API_KEY == "gsk_votre_cle_groq_ici":
        return (
            "⚠️ У вас не указан API-ключ Groq. "
            "Получите его на https://console.groq.com/keys и "
            "вставьте в переменную GROQ_API_KEY или задайте её в окружении перед запуском скрипта."
        )

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
        if choices and "message" in choices[0]:
            raw = choices[0]["message"]["content"].strip()
            # Парсим ответ
            header = ""
            description = ""
            keywords = ""
            hashtags = ""
            for line in raw.splitlines():
                line = line.strip()
                if line.lower().startswith("[header]") or line.lower().startswith("header:"):
                    header = line.split(":", 1)[1].strip() if ":" in line else ""
                elif line.lower().startswith("[description]") or line.lower().startswith("description:"):
                    description = line.split(":", 1)[1].strip() if ":" in line else ""
                elif line.lower().startswith("[keywords]") or line.lower().startswith("keywords:"):
                    keywords = line.split(":", 1)[1].strip() if ":" in line else ""
                elif line.lower().startswith("[hashtags]") or line.lower().startswith("hashtags:"):
                    hashtags = line.split(":", 1)[1].strip() if ":" in line else ""
            # Формируем итоговый текст с разделителями
            # Ограничиваем заголовок до 50 символов
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
        else:
            return "❗️ Неожиданный формат ответа от Groq."
    except Exception as e:
        return f"❌ Ошибка при запросе к Groq: {e}"


# -------------------- Точка входа --------------------
def main():
    product_input = input("Введите название товара (или нажмите Enter для использования значения по умолчанию): ").strip()
    if not product_input:
        product_input = "Кружка керамическая с принтом Кот-программист"
    product = product_input
    print(f"🔍 Генерация описания для товара: {product}\n")
    description = generate_description(product)
    print("=== Генерированное описание ===")
    print(description)


if __name__ == "__main__":
    main()
