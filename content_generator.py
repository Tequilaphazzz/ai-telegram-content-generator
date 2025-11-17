import os
import openai
import google.generativeai as genai
import requests
from PIL import Image, ImageDraw, ImageFont
from telethon.sync import TelegramClient

# Load configuration from .env file
openai.api_key = os.getenv("OPENAI_API_KEY")
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))


# --- ChatGPT Functions ---

def generate_post_text(topic):
    """Generates post text using ChatGPT."""
    print("🤖 Requesting post text generation from ChatGPT...")
    try:
        response = openai.chat.completions.create(
            model="gpt-4o-mini",  # Using a newer, more economical model
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
        print(f"Error during text generation: {e}")
        return None


def generate_image_prompt(post_text):
    """Generates a prompt for an image based on the post text."""
    print("🤖 Requesting image prompt generation from ChatGPT...")
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
        print(f"Error during image prompt generation: {e}")
        return None


def generate_story_headline(post_text):
    """Generates a short headline for a story."""
    print("🤖 Requesting story headline generation from ChatGPT...")
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
        print(f"Error during story headline generation: {e}")
        return None


# --- Functions for working with Gemini and Pillow ---
# Note: The original function name was misleading, this section uses OpenAI and Pillow.
# Keeping the original comment structure.

def generate_image(prompt, output_path):
    """Generates an image using OpenAI DALL-E 3 and saves it."""
    print("🎨 Requesting image generation from OpenAI DALL-E 3...")

    try:
        # 1. Make the generation request to the OpenAI API
        response = openai.images.generate(
            model="dall-e-3",  # Use the highest quality model
            prompt=prompt,
            size="1024x1024",  # Standard size, can also be 1792x1024 or 1024x1792
            quality="hd",  # "hd" for more detail, "standard" for speed
            n=1,  # Generate one image
        )

        # 2. Get the URL of the generated image from the response
        image_url = response.data[0].url
        print(f"Image generated. URL: {image_url}")

        # 3. Download the image from this URL
        print("📥 Downloading image...")
        image_response = requests.get(image_url)
        # Check if the download request was successful
        image_response.raise_for_status()

        # 4. Save the downloaded image to a file
        with open(output_path, 'wb') as f:
            f.write(image_response.content)

        print(f"Image successfully saved to {output_path}")
        return output_path

    except openai.APIError as e:
        print(f"❌ OpenAI API error: {e}")
        return None
    except requests.RequestException as e:
        print(f"❌ Error downloading image: {e}")
        return None
    except Exception as e:
        print(f"❌ An unexpected error occurred: {e}")
        return None


def create_story_image(original_image_path, headline, output_path):
    """Crops the image for a story and overlays the headline."""
    print("🖼️ Processing image for story...")
    try:
        with Image.open(original_image_path) as img:
            # 1. Crop to 9:16 format
            original_width, original_height = img.size
            target_ratio = 9.0 / 16.0

            if (original_width / original_height) > target_ratio:
                # Image is wider than needed. Crop horizontally.
                new_width = int(target_ratio * original_height)
                left = (original_width - new_width) / 2
                top = 0
                right = (original_width + new_width) / 2
                bottom = original_height
            else:
                # Image is taller than needed. Crop vertically.
                new_height = int(original_width / target_ratio)
                left = 0
                top = (original_height - new_height) / 2
                right = original_width
                bottom = (original_height + new_height) / 2

            cropped_img = img.crop((left, top, right, bottom))

            # 2. Overlay text
            draw = ImageDraw.Draw(cropped_img)

            # Font and size (make sure the Arial.ttf font file is in static/fonts)
            font_path = os.path.join('static', 'fonts', 'Arial.ttf')
            font_size = int(cropped_img.width / 10)  # Font size depends on the image width
            try:
                font = ImageFont.truetype(font_path, font_size)
            except IOError:
                print("Font not found! Using default font.")
                font = ImageFont.load_default()

            # Text position (centered)
            text_bbox = draw.textbbox((0, 0), headline, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
            position = ((cropped_img.width - text_width) / 2, cropped_img.height * 0.8)  # In the lower part of the image

            # Add a shadow for readability
            draw.text((position[0] + 2, position[1] + 2), headline, font=font, fill="black")
            # The text itself
            draw.text(position, headline, font=font, fill="white")

            cropped_img.save(output_path)
            print(f"Story image saved to {output_path}")
            return output_path
    except Exception as e:
        print(f"Error processing image: {e}")
        return None


# --- Function for publishing to Telegram ---

async def publish_to_telegram(text, post_image_path, story_image_path):
    """Publishes the post and story to the Telegram channel."""
    print("🚀 Publishing to Telegram...")
    api_id = os.getenv("TELEGRAM_API_ID")
    api_hash = os.getenv("TELEGRAM_API_HASH")
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    channel_id = int(os.getenv("TELEGRAM_CHANNEL_ID"))

    # Initialize the client outside the try block to make it available in finally
    client = TelegramClient('bot_session', api_id, api_hash)

    try:
        # 1. Start the client and AUTHORIZE with the bot token.
        #    This is the exact spot where `await` was needed.
        await client.start(bot_token=bot_token)

        # 2. Publish the main post (text + original image)
        await client.send_file(channel_id, post_image_path, caption=text)
        print("✅ Post published successfully!")

        # 3. Publish the story (cropped image with text)
        await client.send_file(channel_id, story_image_path, is_story=True)
        print("✅ Story published successfully!")

        return "Everything published successfully!"

    except Exception as e:
        print(f"Error publishing to Telegram: {e}")
        return f"Error during publication: {e}"

    finally:
        # 4. In any case (success or error), disconnect from Telegram
        print("🔌 Disconnecting from Telegram session...")
        await client.disconnect()
