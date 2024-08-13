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

@app.on_message(filters.video)
async def handle_video(client, message):
    await message.reply_text("Video received. Processing will begin shortly.")
    await video_queue.put(message)

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
            return

        try:
            await status_message.edit_text("Generating screenshots...")
            screenshots = await generate_screenshots(video_path, 10, temp_dir)

            if not screenshots:
                await status_message.edit_text("Failed to generate screenshots. The video might be corrupted or in an unsupported format.")
                return

            await status_message.edit_text("Creating collage...")
            collage_path = os.path.join(temp_dir, "collage.jpg")
            create_collage(screenshots, collage_path)

            await status_message.edit_text("Uploading collage...")
            graph_url = await asyncio.to_thread(upload_to_graph, collage_path)

            await message.reply_text(
                f"Here is your collage of 10 screenshots: {graph_url}",
                reply_to_message_id=message.id
            )

            await status_message.edit_text("Processing completed.")

        except Exception as e:
            logger.error(f"Error processing video: {e}")
            await status_message.edit_text(f"An error occurred while processing. The video might be corrupted or in an unsupported format.")

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
            await asyncio.sleep(e.x)

    await message.download(file_name=file_path, progress=progress)

async def generate_screenshots(video_path: str, num_screenshots: int, output_dir: str) -> List[str]:
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
        
        clip.close()
        return screenshots
    except Exception as e:
        logger.error(f"Error generating screenshots: {e}")
        return []

def create_collage(image_paths: List[str], collage_path: str):
    images = [Image.open(image) for image in image_paths]
    
    rows, cols = 3, 4
    cell_width = 400
    cell_height = 300
    
    collage_width = cell_width * cols
    collage_height = cell_height * rows
    collage = Image.new('RGB', (collage_width, collage_height))
    
    for i, img in enumerate(images):
        img_resized = img.resize((cell_width, cell_height), Image.LANCZOS)
        x = (i % 4) * cell_width
        y = (i // 4) * cell_height
        collage.paste(img_resized, (x, y))
    
    collage.save(collage_path, quality=95)

def upload_to_graph(image_path):
    url = "https://graph.org/upload"
    
    with open(image_path, "rb") as file:
        files = {"file": file}
        response = requests.post(url, files=files)
    
    if response.status_code == 200:
        data = response.json()
        if data[0].get("src"):
            return f"https://graph.org{data[0]['src']}"
    
    raise Exception("Upload failed")

@app.on_message(filters.text & ~filters.command(["start", "help"]))
async def handle_text(client, message):
    await message.reply_text("I can only process videos. Please send me a video file or use /help for more information.")

async def main():
    await app.start()
    logger.info("Bot started. Listening for messages...")
    asyncio.create_task(process_video_queue())
    await idle()

if __name__ == "__main__":
    app.run(main())
