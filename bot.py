import os
import asyncio
import logging
from typing import List
import tempfile
import requests
from PIL import Image

from pyrogram import Client, filters, idle
from pyrogram.types import Message
from pyrogram.errors import MessageNotModified
from moviepy.editor import VideoFileClip

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
    await message.reply_text("Video received. It will be processed when it's turn comes.")
    await video_queue.put(message)

    if video_queue.qsize() == 1:
        asyncio.create_task(process_video_queue())

async def process_video_queue():
    while not video_queue.empty():
        message = await video_queue.get()
        try:
            await process_video(message)
        except Exception as e:
            logger.error(f"Error processing video: {e}", exc_info=True)
            await message.reply_text(f"An error occurred while processing your video: {str(e)}. Please try again later.")
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
            logger.error(f"Error downloading video: {e}", exc_info=True)
            await status_message.edit_text(f"Failed to download the video: {str(e)}. Please try again.")
            return

        try:
            await status_message.edit_text("Generating 10 screenshots: 0%")

            # Generate screenshots with progress
            screenshots = await generate_screenshots_with_progress(video_path, 10, temp_dir, status_message)

            await status_message.edit_text("Creating high-quality collage...")

            # Create collage
            collage_path = os.path.join(temp_dir, "collage.jpg")
            create_collage(screenshots, collage_path)

            await status_message.edit_text("Uploading collage...")

            # Upload collage to graph.org
            graph_url = await asyncio.to_thread(upload_to_graph, collage_path, message.from_user.id, message.id)

            # Send result to user
            await message.reply_text(
                f"Here is your high-quality collage of 10 screenshots: {graph_url}",
                reply_to_message_id=message.id
            )

            await status_message.edit_text("Processing completed.")

        except Exception as e:
            logger.error(f"Error processing video: {e}", exc_info=True)
            await status_message.edit_text(f"An error occurred while processing: {str(e)}. Please try again.")

        finally:
            # Clean up: delete the video file
            if os.path.exists(video_path):
                os.remove(video_path)
                logger.info(f"Deleted video file: {video_path}")

async def download_video_with_progress(message: Message, file_id: str, file_path: str, status_message: Message):
    async def progress(current, total):
        percent = (current / total) * 100
        try:
            await status_message.edit_text(f"Downloading video: {percent:.1f}%")
        except MessageNotModified:
            pass

    await message.download(file_name=file_path, progress=progress)

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
            
            percent = (i / num_screenshots) * 100
            try:
                await status_message.edit_text(f"Generating {num_screenshots} screenshots: {percent:.1f}%")
            except MessageNotModified:
                pass
        
        clip.close()
        return screenshots
    except Exception as e:
        logger.error(f"Error in generate_screenshots_with_progress: {e}", exc_info=True)
        raise

def create_collage(image_paths: List[str], collage_path: str):
    try:
        images = [Image.open(image) for image in image_paths]
        num_images = len(images)
        
        # Get the aspect ratio of the first image (assuming all screenshots have the same aspect ratio)
        aspect_ratio = images[0].width / images[0].height

        # Define layout for 10 images
        rows, cols = 3, 4
        layout = [
            (0, 0), (1, 0), (2, 0), (3, 0),
            (0, 1), (1, 1), (2, 1), (3, 1),
            (0, 2, 2, 1), (2, 2, 2, 1)
        ]

        # Calculate cell size based on the aspect ratio
        max_dimension = 1600  # Increased for higher quality
        if aspect_ratio >= 1:  # Landscape or square
            cell_width = max_dimension // cols
            cell_height = int(cell_width / aspect_ratio)
        else:  # Portrait
            cell_height = max_dimension // rows
            cell_width = int(cell_height * aspect_ratio)

        # Create the collage image
        collage_width = cell_width * cols
        collage_height = cell_height * rows
        collage = Image.new('RGB', (collage_width, collage_height))

        # Place images in the collage
        for img, pos in zip(images, layout):
            # Resize image to fit the cell
            img_width = cell_width * (pos[2] if len(pos) > 2 else 1)
            img_height = cell_height * (pos[3] if len(pos) > 3 else 1)
            img_resized = img.resize((img_width, img_height), Image.LANCZOS)
            
            # Calculate position
            x = pos[0] * cell_width
            y = pos[1] * cell_height
            
            # Paste the image
            collage.paste(img_resized, (x, y))

        collage.save(collage_path, quality=95)  # Increased quality
    except Exception as e:
        logger.error(f"Error in create_collage: {e}", exc_info=True)
        raise

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

@app.on_message(filters.text & ~filters.command(["start", "help"]))
async def handle_text(client, message):
    await message.reply_text("I can only process videos. Please send me a video file or use /help for more information.")

async def main():
    await app.start()
    logger.info("Bot started. Listening for messages...")
    await idle()

if __name__ == "__main__":
    app.run(main())
