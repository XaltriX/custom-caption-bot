import os
import asyncio
import logging
from typing import List
import tempfile
import requests
from PIL import Image
import sys
from pyrogram import Client, filters, idle
from pyrogram.types import Message
from pyrogram.errors import MessageNotModified, FloodWait
from moviepy.editor import VideoFileClip

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Bot configuration
API_ID = 28192191
API_HASH = '663164abd732848a90e76e25cb9cf54a'
BOT_TOKEN = '7147998933:AAGxVDx1pxyM8MVYvrbm3Nb8zK6DgI1H8RU'

# Initialize the Pyrogram client
app = Client("screenshot_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Queue to manage multiple video processing tasks
video_queue = asyncio.Queue()

@app.on_message(filters.command("start"))
async def start_command(client, message):
    await message.reply_text("Welcome! I'm the Screenshot Bot. Send me a video, and I'll generate 10 screenshots for you.")
    logger.info(f"Start command received from user {message.from_user.id}")

@app.on_message(filters.command("help"))
async def help_command(client, message):
    help_text = (
        "Here's how to use me:\n\n"
        "1. Send me a video file.\n"
        "2. I'll create a high-quality collage of 10 screenshots and send it back to you.\n\n"
        "Commands:\n"
        "/start - Start the bot\n"
        "/help - Show this help message"
    )
    await message.reply_text(help_text)
    logger.info(f"Help command received from user {message.from_user.id}")

@app.on_message(filters.video)
async def handle_video(client, message):
    await message.reply_text("Video received. Processing will begin shortly.")
    await video_queue.put(message)
    logger.info(f"Video received from user {message.from_user.id}")

async def process_video_queue():
    while True:
        try:
            if not video_queue.empty():
                message = await video_queue.get()
                await process_video(message)
            else:
                await asyncio.sleep(1)
        except Exception as e:
            logger.error(f"Error in process_video_queue: {e}")
            await asyncio.sleep(5)

async def process_video(message: Message):
    video = message.video
    file_id = video.file_id
    file_name = f"{file_id}.mp4"

    with tempfile.TemporaryDirectory() as temp_dir:
        video_path = os.path.join(temp_dir, file_name)
        status_message = await message.reply_text("Downloading video:\n▰▰▰▰▰▰▰▰▰▰ 0%")

        try:
            await download_video_with_progress(message, file_id, video_path, status_message)
        except Exception as e:
            logger.error(f"Error downloading video: {e}")
            await status_message.edit_text(f"Failed to download the video. Please try again.")
            await notify_user(message, "There was an error downloading your video. Please try uploading it again.")
            return

        try:
            await status_message.edit_text("Generating screenshots:\n▰▰▰▰▰▰▰▰▰▰ 0%")
            screenshots = await generate_screenshots_with_progress(video_path, 10, temp_dir, status_message)

            if not screenshots:
                await status_message.edit_text("Failed to generate screenshots. The video might be corrupted or in an unsupported format.")
                await notify_user(message, "There was an error generating screenshots from your video. The video might be corrupted or in an unsupported format.")
                return

            await status_message.edit_text("Creating collage...")
            collage_path = os.path.join(temp_dir, "collage.jpg")
            create_collage(screenshots, collage_path)

            await status_message.edit_text("Uploading collage...")
            graph_url = await asyncio.to_thread(upload_to_envs, collage_path)

            await message.reply_text(
                f"Here is your collage of 10 screenshots: {graph_url}",
                reply_to_message_id=message.id
            )
            await status_message.edit_text("Processing completed.")
            logger.info(f"Video processing completed for user {message.from_user.id}")

        except Exception as e:
            logger.error(f"Error processing video: {e}")
            await status_message.edit_text(f"An error occurred while processing. The video might be corrupted or in an unsupported format.")
            await notify_user(message, "There was an error processing your video. It might be corrupted or in an unsupported format.")

async def download_video_with_progress(message: Message, file_id: str, file_path: str, status_message: Message):
    async def progress(current, total):
        percent = int((current / total) * 100)
        bar_length = 10
        filled_length = int(bar_length * current // total)
        bar = '▰' * filled_length + '═' * (bar_length - filled_length)
        progress_text = f"{bar} {percent}%"

        try:
            await status_message.edit_text(f"Downloading video:\n{progress_text}")
        except MessageNotModified:
            pass
        except FloodWait as e:
            await asyncio.sleep(e.value)

    await message.download(file_name=file_path, progress=progress)
    logger.info(f"Video download completed for user {message.from_user.id}")

async def generate_screenshots_with_progress(video_path: str, num_screenshots: int, output_dir: str, status_message: Message) -> List[str]:
    try:
        clip = VideoFileClip(video_path)
        duration = clip.duration
        interval = duration / (num_screenshots + 1)
        screenshots = []

        for i in range(1, num_screenshots + 1):
            time = i * interval
            screenshot_path = os.path.join(output_dir, f"screenshot_{i}.jpg")
            clip.save_frame(screenshot_path, t=time)
            screenshots.append(screenshot_path)

            percent = int((i / num_screenshots) * 100)
            bar_length = 10
            filled_length = int(bar_length * i // num_screenshots)
            bar = '▰' * filled_length + '═' * (bar_length - filled_length)
            progress_text = f"{bar} {percent}%"

            try:
                await status_message.edit_text(f"Generating screenshots:\n{progress_text}")
            except MessageNotModified:
                pass
            except FloodWait as e:
                await asyncio.sleep(e.value)

            logger.info(f"Generated screenshot {i}/{num_screenshots}")

        clip.close()
        return screenshots
    except Exception as e:
        logger.error(f"Error generating screenshots: {e}")
        return []

def create_collage(image_paths: List[str], collage_path: str):
    images = [Image.open(image) for image in image_paths]
    aspect_ratio = images[0].width / images[0].height
    image_width = 400
    image_height = int(image_width / aspect_ratio)
    collage_width = image_width * 3
    collage_height = image_height * 4
    collage = Image.new('RGB', (collage_width, collage_height), color='white')

    layout = [
        (0, 0), (1, 0), (2, 0),  # First row
        (0, 1), (1, 1), (2, 1),  # Second row
        (0, 2), (1, 2), (2, 2),  # Third row
        (0, 3)                   # Fourth row (single image)
    ]

    border_width = 2
    border_color = (0, 0, 0)  # Black color for the border

    for i, (img, (x, y)) in enumerate(zip(images, layout)):
        if i < 9:  # For the first 9 images
            img_resized = img.resize((image_width - 2 * border_width, image_height - 2 * border_width), Image.LANCZOS)
            x_pos = x * image_width + border_width
            y_pos = y * image_height + border_width
            img_with_border = Image.new('RGB', (image_width, image_height), border_color)
            img_with_border.paste(img_resized, (border_width, border_width))
            collage.paste(img_with_border, (x_pos, y_pos))
        else:  # For the last image (10th screenshot)
            img_resized = img.resize((collage_width - 2 * border_width, image_height - 2 * border_width), Image.LANCZOS)
            img_with_border = Image.new('RGB', (collage_width, image_height), border_color)
            img_with_border.paste(img_resized, (border_width, border_width))
            collage.paste(img_with_border, (border_width, 3 * image_height + border_width))

    collage.save(collage_path, quality=95)
    logger.info("Collage created successfully")

def upload_to_envs(image_path):
    url = "https://envs.sh"
    with open(image_path, "rb") as file:
        files = {"file": file}
        response = requests.post(url, files=files)
    if response.status_code == 200:
        data = response.text.strip()
        logger.info("Collage uploaded successfully")
        return data
    logger.error("Failed to upload collage")
    raise Exception("Upload failed")

async def notify_user(message: Message, notification_text: str):
    try:
        await message.reply_text(notification_text)
    except Exception as e:
        logger.error(f"Failed to notify user: {e}")

@app.on_message(filters.text & ~filters.command(["start", "help"]))
async def handle_text(client, message):
    await message.reply_text("I can only process videos. Please send me a video file or use /help for more information.")
    logger.info(f"Received text message from user {message.from_user.id}")

async def main():
    await app.start()
    logger.info("Bot started. Listening for messages...")
    asyncio.create_task(process_video_queue())
    await idle()

if __name__ == "__main__":
    app.run(main())
