import os
import asyncio
import logging
from typing import List
import tempfile
import requests
from PIL import Image, ImageDraw, ImageFont
import sys
from math import ceil

from pyrogram import Client, filters, idle
from pyrogram.types import Message
from pyrogram.errors import MessageNotModified, FloodWait
from moviepy.editor import VideoFileClip
from moviepy.video.io.ffmpeg_reader import FFMPEG_VideoReader

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
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
            logger.error(f"Error in process_video_queue: {e}", exc_info=True)
            await asyncio.sleep(5)

async def process_video(message: Message):
    video = message.video
    file_id = video.file_id
    file_name = f"{file_id}.mp4"

    with tempfile.TemporaryDirectory() as temp_dir:
        video_path = os.path.join(temp_dir, file_name)
        logger.debug(f"Temporary video path: {video_path}")

        status_message = await message.reply_text("Downloading video:\n▰▰▰▰▰▰▰▰▰▰ 0%")
        try:
            await download_video_with_progress(message, file_id, video_path, status_message)
            logger.debug("Video downloaded successfully")
        except Exception as e:
            logger.error(f"Error downloading video: {e}", exc_info=True)
            await status_message.edit_text(f"Failed to download the video. Please try again.")
            await notify_user(message, "There was an error downloading your video. Please try uploading it again.")
            return

        try:
            await status_message.edit_text("Generating screenshots:\n▰▰▰▰▰▰▰▰▰▰ 0%")
            logger.debug("Starting screenshot generation")
            
            # Add a timeout for video processing
            try:
                screenshots, video_duration = await asyncio.wait_for(
                    generate_screenshots_with_progress(video_path, 10, temp_dir, status_message),
                    timeout=300  # 5 minutes timeout
                )
            except asyncio.TimeoutError:
                logger.error("Video processing timed out")
                await status_message.edit_text("Video processing timed out. The video might be too long or complex.")
                await notify_user(message, "Video processing timed out. Please try a shorter or simpler video.")
                return
            
            logger.debug(f"Screenshot generation completed. Got {len(screenshots)} screenshots")

            if not screenshots:
                logger.warning("No screenshots were generated")
                await status_message.edit_text("Failed to generate screenshots. The video might be corrupted or in an unsupported format.")
                await notify_user(message, "There was an error generating screenshots from your video. The video might be corrupted or in an unsupported format.")
                return

            await status_message.edit_text("Creating collage...")
            logger.debug("Starting collage creation")
            collage_path = os.path.join(temp_dir, "collage.jpg")
            create_collage(screenshots, collage_path, video.width, video.height, video_duration)
            logger.debug("Collage created successfully")

            await status_message.edit_text("Uploading collage...")
            logger.debug("Starting collage upload")
            graph_url = await asyncio.to_thread(upload_to_graph, collage_path)
            logger.debug(f"Collage uploaded successfully. URL: {graph_url}")

            await message.reply_text(
                f"Here is your collage of 10 screenshots: {graph_url}",
                reply_to_message_id=message.id
            )

            await status_message.edit_text("Processing completed.")
            logger.info(f"Video processing completed for user {message.from_user.id}")

        except Exception as e:
            logger.error(f"Error processing video: {e}", exc_info=True)
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

async def generate_screenshots_with_progress(video_path: str, num_screenshots: int, output_dir: str, status_message: Message) -> tuple[List[str], float]:
    try:
        logger.debug(f"Opening video file: {video_path}")
        clip = VideoFileClip(video_path)
        logger.debug(f"Video clip opened successfully")
        duration = clip.duration
        logger.debug(f"Video duration: {duration}")
        interval = duration / (num_screenshots + 1)
        
        screenshots = []
        for i in range(1, num_screenshots + 1):
            try:
                time = i * interval
                screenshot_path = os.path.join(output_dir, f"screenshot_{i}.jpg")
                logger.debug(f"Attempting to save frame at {time}s to {screenshot_path}")
                
                # Use a timeout for frame extraction
                frame = await asyncio.wait_for(
                    asyncio.to_thread(clip.get_frame, time),
                    timeout=30  # 30 seconds timeout for each frame
                )
                
                Image.fromarray(frame).save(screenshot_path)
                logger.debug(f"Frame saved successfully")
                screenshots.append(screenshot_path)
                
                percent = int((i / num_screenshots) * 100)
                bar_length = 10
                filled_length = int(bar_length * i // num_screenshots)
                bar = '▰' * filled_length + '═' * (bar_length - filled_length)
                progress_text = f"{bar} {percent}%"
                
                try:
                    await status_message.edit_text(f"Generating screenshots:\n{progress_text}")
                    logger.debug(f"Status message updated: {progress_text}")
                except MessageNotModified:
                    logger.debug("Status message not modified (same content)")
                except FloodWait as e:
                    logger.warning(f"FloodWait error, sleeping for {e.value} seconds")
                    await asyncio.sleep(e.value)
                
                logger.info(f"Generated screenshot {i}/{num_screenshots}")
            except asyncio.TimeoutError:
                logger.error(f"Timeout while generating screenshot {i}")
            except Exception as e:
                logger.error(f"Error generating screenshot {i}: {e}", exc_info=True)
        
        clip.close()
        logger.debug("Video clip closed")
        return screenshots, duration
    except Exception as e:
        logger.error(f"Error in generate_screenshots_with_progress: {e}", exc_info=True)
        return [], 0

def create_collage(image_paths: List[str], collage_path: str, video_width: int, video_height: int, video_duration: float):
    try:
        images = [Image.open(image) for image in image_paths]
        
        # Determine orientation
        is_portrait = video_height > video_width
        
        # Set collage dimensions and layout
        if is_portrait:
            cols, rows = 2, 5
            collage_width = 1080
            collage_height = int(collage_width * (video_height / video_width))
        else:
            cols, rows = 3, 4
            collage_height = 1080
            collage_width = int(collage_height * (video_width / video_height))
        
        cell_width = collage_width // cols
        cell_height = collage_height // rows
        
        collage = Image.new('RGB', (collage_width, collage_height), color='white')
        draw = ImageDraw.Draw(collage)
        
        # Load a font (you may need to adjust the path or use a different font)
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
        except IOError:
            font = ImageFont.load_default()
        
        for i, img in enumerate(images):
            # Resize and crop the image to fit the cell while maintaining aspect ratio
            img_ratio = img.width / img.height
            cell_ratio = cell_width / cell_height
            
            if img_ratio > cell_ratio:
                new_height = cell_height
                new_width = int(new_height * img_ratio)
            else:
                new_width = cell_width
                new_height = int(new_width / img_ratio)
            
            img_resized = img.resize((new_width, new_height), Image.LANCZOS)
            img_cropped = img_resized.crop((
                (img_resized.width - cell_width) // 2,
                (img_resized.height - cell_height) // 2,
                (img_resized.width + cell_width) // 2,
                (img_resized.height + cell_height) // 2
            ))
            
            # Calculate position
            x = (i % cols) * cell_width
            y = (i // cols) * cell_height
            
            # Paste image
            collage.paste(img_cropped, (x, y))
            
            # Draw border
            draw.rectangle([x, y, x + cell_width - 1, y + cell_height - 1], outline='white', width=2)
            
            # Add timestamp
            timestamp = f"{ceil((i + 1) * video_duration / (len(images) + 1))}s"
            text_width, text_height = draw.textsize(timestamp, font=font)
            draw.rectangle([x, y, x + text_width + 10, y + text_height + 10], fill='rgba(0, 0, 0, 128)')
            draw.text((x + 5, y + 5), timestamp, font=font, fill='white')
        
        # Add title
        title = "Video Screenshots"
        title_width, title_height = draw.textsize(title, font=font)
        draw.rectangle([0, 0, collage_width, title_height + 20], fill='rgba(0, 0, 0, 128)')
        draw.text(((collage_width - title_width) // 2, 10), title, font=font, fill='white')
        
        collage.save(collage_path, quality=95)
        logger.info("Collage created successfully")
    except Exception as e:
        logger.error(f"Error creating collage: {e}", exc_info=True)

def upload_to_graph(image_path):
    url = "https://graph.org/upload"
    
    with open(image_path, "rb") as file:
        files = {"file": file}
        response = requests.post(url, files=files)
    
    if response.status_code == 200:
        data = response.json()
        if data[0].get("src"):
            logger.info("Collage uploaded successfully")
            return f"https://graph.org{data[0]['src']}"
    
    logger.error("Failed to upload collage")
    raise Exception("Upload failed")

async def notify_user(message: Message, notification_text: str):
    try:
        await message.reply_text(notification_text)
    except Exception as e:
        logger.error(f"Failed to notify user: {e}", exc_info=True)

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
