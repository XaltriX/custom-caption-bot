import os
import asyncio
import logging
from typing import List
import tempfile

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from pyrogram.errors import MessageNotModified
from moviepy.editor import VideoFileClip
import aiohttp

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

        # Download the video
        status_message = await message.reply_text("Downloading video...")
        try:
            await app.download_media(message, file_name=video_path)
        except Exception as e:
            logger.error(f"Error downloading video: {e}")
            await status_message.edit_text("Failed to download the video. Please try again.")
            return

        # Ask user for number of screenshots
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("5 screenshots", callback_data=f"ss_5_{file_id}"),
             InlineKeyboardButton("10 screenshots", callback_data=f"ss_10_{file_id}")]
        ])
        await status_message.edit_text("How many screenshots do you want?", reply_markup=keyboard)

@app.on_callback_query()
async def handle_screenshot_choice(client: Client, callback_query: CallbackQuery):
    data = callback_query.data.split('_')
    num_screenshots = int(data[1])
    file_id = data[2]
    file_name = f"{file_id}.mp4"

    await callback_query.answer()
    status_message = await callback_query.message.edit_text(f"Generating {num_screenshots} screenshots...")

    with tempfile.TemporaryDirectory() as temp_dir:
        video_path = os.path.join(temp_dir, file_name)

        # Download the video if it's not already downloaded
        if not os.path.exists(video_path):
            try:
                await app.download_media(file_id, file_name=video_path)
            except Exception as e:
                logger.error(f"Error downloading video: {e}")
                await status_message.edit_text("Failed to download the video. Please try again.")
                return

        # Generate screenshots
        try:
            screenshots = generate_screenshots(video_path, num_screenshots, temp_dir)
        except Exception as e:
            logger.error(f"Error generating screenshots: {e}")
            await status_message.edit_text("Failed to generate screenshots. Please try again.")
            return

        await status_message.edit_text("Uploading screenshots...")

        # Upload screenshots to graph.org
        try:
            graph_url = await upload_to_graph_org(screenshots)
        except Exception as e:
            logger.error(f"Error uploading to graph.org: {e}")
            await status_message.edit_text("Failed to upload screenshots. Please try again.")
            return

        # Get video thumbnail
        thumbnail_path = os.path.join(temp_dir, "thumbnail.jpg")
        try:
            await app.download_media(file_id, file_name=thumbnail_path, thumb=1)
        except Exception as e:
            logger.error(f"Error downloading thumbnail: {e}")
            thumbnail_path = None

        # Send result to user
        try:
            if thumbnail_path and os.path.exists(thumbnail_path):
                await callback_query.message.reply_photo(
                    photo=thumbnail_path,
                    caption=f"Here are your {num_screenshots} screenshots: {graph_url}"
                )
            else:
                await callback_query.message.reply_text(
                    f"Here are your {num_screenshots} screenshots: {graph_url}"
                )
        except Exception as e:
            logger.error(f"Error sending result: {e}")
            await status_message.edit_text("An error occurred while sending the result. Please try again.")

    await status_message.edit_text("Processing completed.")

def generate_screenshots(video_path: str, num_screenshots: int, output_dir: str) -> List[str]:
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

async def upload_to_graph_org(image_paths: List[str]) -> str:
    # This is a placeholder function. You need to implement the actual upload to graph.org
    # For demonstration purposes, we'll simulate an upload with a delay
    await asyncio.sleep(2)  # Simulate upload time
    return "https://graph.org/your-screenshots"

async def main():
    await app.start()
    logger.info("Bot started. Listening for messages...")
    await idle()

if __name__ == "__main__":
    app.run(main())
