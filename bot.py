import os
import asyncio
import logging
from typing import List
import tempfile
import requests
from PIL import Image
import cv2
import subprocess

from pyrogram import Client, filters, idle
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from pyrogram.errors import MessageNotModified

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

# Create a persistent temporary directory
temp_dir = tempfile.mkdtemp()

@app.on_message(filters.command("start"))
async def start_command(client, message):
    await message.reply_text("Welcome! I'm the Screenshot Bot. Send me a video, and I'll generate screenshots for you.")

@app.on_message(filters.command("help"))
async def help_command(client, message):
    help_text = (
        "Here's how to use me:\n\n"
        "1. Send me a video file.\n"
        "2. Choose the number of screenshots you want (5 or 10).\n"
        "3. I'll create a high-quality collage of screenshots and send it back to you.\n\n"
        "Commands:\n"
        "/start - Start the bot\n"
        "/help - Show this help message"
    )
    await message.reply_text(help_text)

@app.on_message(filters.video)
async def handle_video(client, message):
    file_id = message.video.file_id
    video_id = message.id

    callback_data_5 = f"ss_5_{video_id}"
    callback_data_10 = f"ss_10_{video_id}"

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("5 screenshots", callback_data=callback_data_5),
         InlineKeyboardButton("10 screenshots", callback_data=callback_data_10)]
    ])
    
    try:
        await message.reply_text("How many screenshots do you want?", reply_markup=keyboard)
    except Exception as e:
        logger.error(f"Error sending message with inline keyboard: {e}")
        await message.reply_text("An error occurred while processing your request. Please try again later.")

@app.on_callback_query()
async def handle_screenshot_choice(client: Client, callback_query: CallbackQuery):
    try:
        data = callback_query.data.split('_')
        num_screenshots = int(data[1])
        video_id = int(data[2])
        
        original_message = await client.get_messages(callback_query.message.chat.id, video_id)
        file_id = original_message.video.file_id
        
        await callback_query.answer()
        status_message = await callback_query.message.reply_text("Processing started. Downloading video: 0%")

        file_name = f"{video_id}.mp4"
        video_path = os.path.join(temp_dir, file_name)

        try:
            await download_video_with_progress(client, file_id, video_path, status_message)

            if not os.path.exists(video_path):
                raise FileNotFoundError(f"Downloaded video file not found: {video_path}")

            logger.info(f"Video downloaded successfully. Path: {video_path}, Size: {os.path.getsize(video_path)} bytes")

            if not is_valid_video(video_path):
                raise ValueError("The video file appears to be corrupt or incomplete. Please try uploading it again.")

            await status_message.edit_text(f"Generating {num_screenshots} screenshots: 0%")
            screenshots = await generate_screenshots_with_progress(video_path, num_screenshots, temp_dir, status_message)

            if len(screenshots) < num_screenshots:
                logger.warning(f"Only {len(screenshots)} screenshots could be generated")

            await status_message.edit_text("Creating high-quality collage...")

            collage_path = os.path.join(temp_dir, f"collage_{file_name}.jpg")
            create_collage(screenshots, collage_path)

            await status_message.edit_text("Uploading collage...")

            graph_url = await asyncio.to_thread(upload_to_graph, collage_path, callback_query.from_user.id, video_id)

            await callback_query.message.reply_text(
                f"Here is your high-quality collage of {len(screenshots)} screenshots: {graph_url}",
                reply_to_message_id=video_id
            )

            await status_message.edit_text("Processing completed.")

        except FileNotFoundError as e:
            logger.error(f"Video file not found: {e}")
            await status_message.edit_text("Error: The video file could not be downloaded. Please try again.")
        except ValueError as e:
            logger.error(f"Error processing video: {e}")
            await status_message.edit_text(f"Error: {str(e)}. Please try a different video.")
        except Exception as e:
            logger.error(f"Unexpected error processing video: {e}", exc_info=True)
            await status_message.edit_text("An unexpected error occurred. Please try again later.")

    except Exception as e:
        logger.error(f"Error in handle_screenshot_choice: {e}", exc_info=True)
        await callback_query.message.reply_text("An unexpected error occurred. Please try again later.")

async def download_video_with_progress(client: Client, file_id: str, file_path: str, status_message: Message):
    async def progress(current, total):
        if total > 0:
            percent = (current / total) * 100
            try:
                await status_message.edit_text(f"Downloading video: {percent:.1f}%")
            except MessageNotModified:
                pass
        else:
            await status_message.edit_text("Downloading video: Size unknown")

    await client.download_media(file_id, file_name=file_path, progress=progress)

def is_valid_video(video_path: str) -> bool:
    try:
        result = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', 
                                 '-count_packets', '-show_entries', 'stream=nb_read_packets', 
                                 '-of', 'csv=p=0', video_path], 
                                capture_output=True, text=True)
        return int(result.stdout.strip()) > 0
    except subprocess.CalledProcessError:
        return False
    except Exception as e:
        logger.error(f"Error validating video: {e}")
        return False

async def generate_screenshots_with_progress(video_path: str, num_screenshots: int, output_dir: str, status_message: Message) -> List[str]:
    try:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError("Unable to open video file")
        
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        duration = total_frames / fps
        
        screenshots = []
        attempts = 0
        max_attempts = num_screenshots * 5

        while len(screenshots) < num_screenshots and attempts < max_attempts:
            time = (attempts + 1) * duration / (max_attempts + 1)
            frame_number = int(time * fps)
            
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            ret, frame = cap.read()
            
            if ret:
                screenshot_path = os.path.join(output_dir, f"screenshot_{len(screenshots)+1}.jpg")
                cv2.imwrite(screenshot_path, frame)
                screenshots.append(screenshot_path)
                
                percent = (len(screenshots) / num_screenshots) * 100
                try:
                    await status_message.edit_text(f"Generating {num_screenshots} screenshots: {percent:.1f}%")
                except MessageNotModified:
                    pass
            else:
                logger.warning(f"Failed to capture frame {frame_number}")
            
            attempts += 1
        
        cap.release()
        
        if not screenshots:
            raise ValueError("No screenshots could be generated. The video might be corrupt or empty.")
        elif len(screenshots) < num_screenshots:
            logger.warning(f"Only {len(screenshots)} out of {num_screenshots} screenshots could be generated.")
        
        return screenshots
    except Exception as e:
        logger.error(f"Error in generate_screenshots_with_progress: {e}", exc_info=True)
        raise

def create_collage(image_paths: List[str], collage_path: str):
    try:
        images = [Image.open(image) for image in image_paths]
        num_images = len(images)
        
        if num_images < 2:
            raise ValueError("At least 2 images are required to create a collage")

        aspect_ratio = images[0].width / images[0].height

        if num_images <= 5:
            rows, cols = 3, 2
            layout = [(0, 0), (1, 0), (0, 1), (1, 1), (0, 2, 2, 1)][:num_images]
        else:
            rows, cols = 3, 4
            layout = [
                (0, 0), (1, 0), (2, 0), (3, 0),
                (0, 1), (1, 1), (2, 1), (3, 1),
                (0, 2, 2, 1), (2, 2, 2, 1)
            ][:num_images]

        max_dimension = 1600
        if aspect_ratio >= 1:
            cell_width = max_dimension // cols
            cell_height = int(cell_width / aspect_ratio)
        else:
            cell_height = max_dimension // rows
            cell_width = int(cell_height * aspect_ratio)

        collage_width = cell_width * cols
        collage_height = cell_height * rows
        collage = Image.new('RGB', (collage_width, collage_height))

        for img, pos in zip(images, layout):
            img_width = cell_width * (pos[2] if len(pos) > 2 else 1)
            img_height = cell_height * (pos[3] if len(pos) > 3 else 1)
            img_resized = img.resize((img_width, img_height), Image.LANCZOS)
            
            x = pos[0] * cell_width
            y = pos[1] * cell_height
            
            collage.paste(img_resized, (x, y))

        collage.save(collage_path, quality=95)
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
    try:
        app.run(main())
    finally:
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)
