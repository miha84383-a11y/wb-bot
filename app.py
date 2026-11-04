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