import os
import asyncio
import logging
from typing import List
import tempfile
import math
from PIL import Image
import requests

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from pyrogram.errors import MessageNotModified
try:
    from pyrogram.idle import idle
except ImportError:
    from pyrogram import idle
from moviepy.editor import VideoFileClip
import aiohttp
from aiohttp import web

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
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
async def start_command(client: Client, message: Message):
    await message.reply_text("Welcome! Send me a video, and I'll generate screenshots for you.")

@app.on_message(filters.video)
async def handle_video(client: Client, message: Message):
    await message.reply_text("Video received. Adding to processing queue...")
    await video_queue.put(message)

    if video_queue.qsize() == 1:
        asyncio.create_task(process_video_queue())

async def process_video_queue():
    while not video_queue.empty():
        message = await video_queue.get()
        try:
            await process_video(message)
        except Exception as e:
            logger.error(f"Error processing video: {e}")
            await message.reply_text("An error occurred while processing your video. Please try again later.")
        finally:
            video_queue.task_done()

async def process_video(message: Message):
    video = message.video
    file_id = video.file_id
    file_name = f"{file_id}.mp4"

    with tempfile.TemporaryDirectory() as temp_dir:
        video_path = os.path.join(temp_dir, file_name)

        # Download the video with progress
        status_message = await message.reply_text("Downloading video: 0%")
        try:
            await download_video_with_progress(message, file_id, video_path, status_message)
        except Exception as e:
            logger.error(f"Error downloading video: {e}")
            await status_message.edit_text("Failed to download the video. Please try again.")
            return

        # Ask user for number of screenshots
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("5 screenshots", callback_data=f"ss_5_{message.id}"),
             InlineKeyboardButton("10 screenshots", callback_data=f"ss_10_{message.id}")]
        ])
        await status_message.edit_text("How many screenshots do you want?", reply_markup=keyboard)

async def download_video_with_progress(message: Message, file_id: str, file_path: str, status_message: Message):
    async def progress(current, total):
        percent = (current / total) * 100
        bar = create_progress_bar(percent)
        try:
            await status_message.edit_text(f"Downloading video: {bar} {percent:.1f}%")
        except MessageNotModified:
            pass

    await app.download_media(message, file_name=file_path, progress=progress)

def create_progress_bar(percent):
    completed = '▰' * int(percent / 10)
    remaining = '╍' * (10 - int(percent / 10))
    return f"{completed}{remaining}"

@app.on_callback_query()
async def handle_screenshot_choice(client: Client, callback_query: CallbackQuery):
    data = callback_query.data.split('_')
    num_screenshots = int(data[1])
    message_id = int(data[2])
    
    # Retrieve the original message
    message = await app.get_messages(callback_query.message.chat.id, message_id)
    
    file_id = message.video.file_id
    file_name = f"{file_id}.mp4"

    await callback_query.answer()
    status_message = await callback_query.message.edit_text(f"Generating {num_screenshots} screenshots: 0%")

    with tempfile.TemporaryDirectory() as temp_dir:
        video_path = os.path.join(temp_dir, file_name)

        # Download the video if it's not already downloaded
        if not os.path.exists(video_path):
            try:
                await download_video_with_progress(message, file_id, video_path, status_message)
            except Exception as e:
                logger.error(f"Error downloading video: {e}")
                await status_message.edit_text("Failed to download the video. Please try again.")
                return

        try:
            # Generate screenshots with progress
            screenshots = await generate_screenshots_with_progress(video_path, num_screenshots, temp_dir, status_message)

            await status_message.edit_text("Creating collage...")

            # Create collage
            collage_path = os.path.join(temp_dir, "collage.jpg")
            create_collage(screenshots, collage_path)

            await status_message.edit_text("Uploading collage...")

            # Upload collage to graph.org
            graph_url = upload_to_graph(collage_path, callback_query.from_user.id, message_id)

            # Send result to user
            await callback_query.message.reply_text(
                f"Here is your collage of {num_screenshots} screenshots: {graph_url}",
                reply_to_message_id=message_id
            )

            await status_message.edit_text("Processing completed.")

        except Exception as e:
            logger.error(f"Error processing video: {e}")
            await status_message.edit_text("An error occurred while processing. Please try again.")

        finally:
            # Clean up: delete the video file
            if os.path.exists(video_path):
                os.remove(video_path)
                logger.info(f"Deleted video file: {video_path}")

async def generate_screenshots_with_progress(video_path: str, num_screenshots: int, output_dir: str, status_message: Message) -> List[str]:
    clip = VideoFileClip(video_path)
    duration = clip.duration
    interval = duration / (num_screenshots + 1)
    
    screenshots = []
    for i in range(1, num_screenshots + 1):
        time = i * interval
        screenshot_path = os.path.join(output_dir, f"screenshot_{i}.jpg")
        clip.save_frame(screenshot_path, t=time)
        screenshots.append(screenshot_path)
        
        percent = (i / num_screenshots) * 100
        bar = create_progress_bar(percent)
        try:
            await status_message.edit_text(f"Generating {num_screenshots} screenshots: {bar} {percent:.1f}%")
        except MessageNotModified:
            pass
    
    clip.close()
    return screenshots

def create_collage(image_paths: List[str], collage_path: str):
    images = [Image.open(image) for image in image_paths]
    widths, heights = zip(*(i.size for i in images))

    total_width = sum(widths)
    max_height = max(heights)

    collage = Image.new('RGB', (total_width, max_height))

    x_offset = 0
    for im in images:
        collage.paste(im, (x_offset, 0))
        x_offset += im.width

    collage.save(collage_path)

def upload_to_graph(image_path, user_id, message_id):
    url = "https://graph.org/upload"
    
    with open(image_path, "rb") as file:
        files = {"file": file}
        response = requests.post(url, files=files)
    
    if response.status_code == 200:
        data = response.json()
        if data[0].get("src"):
            return f"https://graph.org{data[0]['src']}"
        else:
            raise Exception("Unable to retrieve image link from response")
    else:
        raise Exception(f"Upload failed with status code {response.status_code}")

async def handle(request):
    return web.Response(text="Bot is running!")

async def run_web_server():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", int(os.environ.get("PORT", 8080)))
    await site.start()

async def main():
    await app.start()
    asyncio.create_task(run_web_server())
    logger.info("Bot started. Listening for messages...")
    await idle()

if __name__ == "__main__":
    app.run(main())
