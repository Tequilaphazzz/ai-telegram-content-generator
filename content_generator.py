import os
import openai
import google.generativeai as genai
import requests
from PIL import Image, ImageDraw, ImageFont
from telethon.sync import TelegramClient

# Загрузка конфигурации из .env файла
openai.api_key = os.getenv("OPENAI_API_KEY")
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))


# --- Функции для работы с ChatGPT ---

def generate_post_text(topic):
    """Генерирует текст поста с помощью ChatGPT."""
    print("🤖 Запрос к ChatGPT на генерацию текста поста...")
    try:
        response = openai.chat.completions.create(
            model="gpt-4o-mini",  # Используем более новую и экономичную модель
            messages=[
                {"role": "system",
                 "content": "Ты — талантливый копирайтер, который пишет короткие, смешные и увлекательные посты на русском языке."},
                {"role": "user",
                 "content": f"Придумай текст для поста в Telegram на тему '{topic}'. Требования: не более 1000 символов, легко читаемый стиль, хороший русский юмор и короткий, привлекательный заголовок в самом начале."}
            ],
            temperature=0.7,
            max_tokens=300
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Ошибка при генерации текста: {e}")
        return None


def generate_image_prompt(post_text):
    """На основе текста поста генерирует промт для изображения."""
    print("🤖 Запрос к ChatGPT на генерацию промта для изображения...")
    try:
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system",
                 "content": "Ты — креативный ассистент, который создает промты для генерации изображений."},
                {"role": "user",
                 "content": f"На основе этого текста для поста: '{post_text}', напиши короткий, но детальный промт на английском языке для генерации фотореалистичного изображения. Промт должен быть сфокусирован на главной идее текста. Пример: 'Photorealistic shot of a red cat programmer typing on a glowing keyboard, cinematic lighting, high detail'."}
            ],
            temperature=0.8,
            max_tokens=100
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Ошибка при генерации промта для изображения: {e}")
        return None


def generate_story_headline(post_text):
    """Генерирует короткий заголовок для сториз."""
    print("🤖 Запрос к ChatGPT на генерацию заголовка для сториз...")
    try:
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Ты — мастер коротких и броских заголовков."},
                {"role": "user",
                 "content": f"На основе этого текста: '{post_text}', придумай очень короткий заголовок (не более 5 слов) для сториз в Telegram. Он должен быть интригующим или смешным."}
            ],
            temperature=0.7,
            max_tokens=20
        )
        return response.choices[0].message.content.strip().replace('"', '')
    except Exception as e:
        print(f"Ошибка при генерации заголовка для сториз: {e}")
        return None


# --- Функции для работы с Gemini и Pillow ---

def generate_image(prompt, output_path):
    """Генерирует изображение с помощью OpenAI DALL-E 3 и сохраняет его."""
    print("🎨 Запрос к OpenAI DALL-E 3 на генерацию изображения...")

    try:
        # 1. Выполняем запрос на генерацию к API OpenAI
        response = openai.images.generate(
            model="dall-e-3",  # Используем самую качественную модель
            prompt=prompt,
            size="1024x1024",  # Стандартный размер, можно выбрать 1792x1024 или 1024x1792
            quality="hd",  # "hd" для большей детализации, "standard" для скорости
            n=1,  # Генерируем одно изображение
        )

        # 2. Получаем URL сгенерированного изображения из ответа
        image_url = response.data[0].url
        print(f"Изображение сгенерировано. URL: {image_url}")

        # 3. Скачиваем изображение по этому URL
        print("📥 Скачивание изображения...")
        image_response = requests.get(image_url)
        # Проверяем, что запрос на скачивание прошел успешно
        image_response.raise_for_status()

        # 4. Сохраняем скачанное изображение в файл
        with open(output_path, 'wb') as f:
            f.write(image_response.content)

        print(f"Изображение успешно сохранено в {output_path}")
        return output_path

    except openai.APIError as e:
        print(f"❌ Ошибка OpenAI API: {e}")
        return None
    except requests.RequestException as e:
        print(f"❌ Ошибка при скачивании изображения: {e}")
        return None
    except Exception as e:
        print(f"❌ Произошла непредвиденная ошибка: {e}")
        return None


def create_story_image(original_image_path, headline, output_path):
    """Обрезает изображение под сториз и накладывает заголовок."""
    print("🖼️ Обработка изображения для сториз...")
    try:
        with Image.open(original_image_path) as img:
            # 1. Обрезка под формат 9:16
            original_width, original_height = img.size
            target_ratio = 9.0 / 16.0

            if (original_width / original_height) > target_ratio:
                # Изображение шире, чем нужно. Обрезаем по горизонтали.
                new_width = int(target_ratio * original_height)
                left = (original_width - new_width) / 2
                top = 0
                right = (original_width + new_width) / 2
                bottom = original_height
            else:
                # Изображение выше, чем нужно. Обрезаем по вертикали.
                new_height = int(original_width / target_ratio)
                left = 0
                top = (original_height - new_height) / 2
                right = original_width
                bottom = (original_height + new_height) / 2

            cropped_img = img.crop((left, top, right, bottom))

            # 2. Наложение текста
            draw = ImageDraw.Draw(cropped_img)

            # Шрифт и размер (убедитесь, что файл шрифта Arial.ttf находится в папке static/fonts)
            font_path = os.path.join('static', 'fonts', 'Arial.ttf')
            font_size = int(cropped_img.width / 10)  # Размер шрифта зависит от ширины картинки
            try:
                font = ImageFont.truetype(font_path, font_size)
            except IOError:
                print("Шрифт не найден! Используется шрифт по умолчанию.")
                font = ImageFont.load_default()

            # Позиция текста (по центру)
            text_bbox = draw.textbbox((0, 0), headline, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
            position = ((cropped_img.width - text_width) / 2, cropped_img.height * 0.8)  # В нижней части изображения

            # Добавляем тень для читаемости
            draw.text((position[0] + 2, position[1] + 2), headline, font=font, fill="black")
            # Сам текст
            draw.text(position, headline, font=font, fill="white")

            cropped_img.save(output_path)
            print(f"Изображение для сториз сохранено в {output_path}")
            return output_path
    except Exception as e:
        print(f"Ошибка при обработке изображения: {e}")
        return None


# --- Функция для публикации в Telegram ---

async def publish_to_telegram(text, post_image_path, story_image_path):
    """Публикует пост и сториз в Telegram-канал."""
    print("🚀 Публикация в Telegram...")
    api_id = os.getenv("TELEGRAM_API_ID")
    api_hash = os.getenv("TELEGRAM_API_HASH")
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    channel_id = int(os.getenv("TELEGRAM_CHANNEL_ID"))

    # Инициализируем клиент вне блока try, чтобы он был доступен в finally
    client = TelegramClient('bot_session', api_id, api_hash)

    try:
        # 1. Запускаем клиент и АВТОРИЗУЕМСЯ с токеном бота.
        #    Вот то самое место, где нужно было `await`.
        await client.start(bot_token=bot_token)

        # 2. Публикуем основной пост (текст + оригинальное изображение)
        await client.send_file(channel_id, post_image_path, caption=text)
        print("✅ Пост успешно опубликован!")

        # 3. Публикуем сториз (обрезанное изображение с текстом)
        await client.send_file(channel_id, story_image_path, is_story=True)
        print("✅ Сториз успешно опубликована!")

        return "Все успешно опубликовано!"

    except Exception as e:
        print(f"Ошибка при публикации в Telegram: {e}")
        return f"Ошибка при публикации: {e}"

    finally:
        # 4. В любом случае (успех или ошибка) отключаемся от Telegram
        print("🔌 Завершение сессии Telegram...")
        await client.disconnect()