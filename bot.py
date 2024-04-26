import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackContext, MessageHandler, Filters, CallbackQueryHandler
import subprocess
import os
import random

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Your Telegram Bot API token
TOKEN = '6317227210:AAGpjnW4q6LBrpYdFNN1YrH62NcH9r_z03Q'

# Maximum allowed file size in bytes (adjust as needed)
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB

# Initialize bot
updater = Updater(TOKEN)
dispatcher = updater.dispatcher

# Dictionary to store user data
user_data = {}

# Function to extract segments from the video
def extract_segments(video_filename):
    clip = VideoFileClip(video_filename)
    duration = min(clip.duration, 5)  # Limit duration to 5 seconds
    
    # List to store start times
    start_times = []
    
    # Add start time from the beginning
    start_times.append(0)
    
    # Add start time from the middle
    start_times.append(max(clip.duration / 2 - duration / 2, 0))
    
    # Add start time from the ending
    start_times.append(max(clip.duration - duration, 0))
    
    # Add start time from randomly anywhere
    random_start_time = random.uniform(0, max(clip.duration - duration, 0))
    start_times.append(random_start_time)
    
    segments = []
    for start_time in start_times:
        end_time = min(start_time + duration, clip.duration)  # End time for segment
        segment = clip.subclip(start_time, end_time)
        segments.append(segment)
    
    return segments

# Function to start the bot and process videos
def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text("Welcome! Please send a video🤝")

# Function to handle video messages
def handle_video(update: Update, context: CallbackContext) -> None:
    video = update.message.video
    
    # Check file size
    if video.file_size > MAX_FILE_SIZE_BYTES:
        update.message.reply_text("Sorry, the file size is too large. Please try with a smaller video.")
        return

    file_id = video.file_id
    file_info = context.bot.get_file(file_id)
    file = context.bot.download_file(file_info.file_path)
    video_filename = f"video_{file_id}.mp4"

    with open(video_filename, 'wb') as f:
        f.write(file)

    # Extract segments and send one at a time
    segments = extract_segments(video_filename)
    for idx, segment in enumerate(segments):
        segment_filename = f"segment_{idx + 1}_{file_id}.mp4"
        segment.write_videofile(segment_filename, codec="libx264", fps=24)  # Save as mp4
        context.bot.send_video(update.message.chat_id, video=open(segment_filename, 'rb'), caption="Is this segment suitable?", reply_markup=confirmation_keyboard())
        # Store user chat ID and extracted filename in user_data
        user_data[update.message.chat_id] = {"extracted_filename": segment_filename}
        os.remove(segment_filename)

    # Cleanup files
    os.remove(video_filename)

# Keyboard markup for confirmation
def confirmation_keyboard():
    keyboard = [
        [InlineKeyboardButton("Yes", callback_data="yes"), InlineKeyboardButton("No", callback_data="no")]
    ]
    return InlineKeyboardMarkup(keyboard)

# Function to handle confirmation of the video segment
def handle_confirmation(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    user_choice = query.data
    user_id = query.message.chat_id
    
    if user_id in user_data:
        extracted_filename = user_data[user_id]["extracted_filename"]
        if user_choice == "yes":
            query.message.reply_text("Great! Please provide a custom caption for the video.")
            user_data[user_id]["approval"] = True
        else:
            query.message.reply_text("Let's try another segment.")
            # Remove the current extracted file
            os.remove(extracted_filename)
            # Extract a new segment and send it for confirmation
            segments = extract_segments(video_filename)
            new_segment = random.choice(segments)
            new_segment_filename = f"new_segment_{file_id}.mp4"
            new_segment.write_videofile(new_segment_filename, codec="libx264", fps=24)  # Save as mp4
            context.bot.send_video(user_id, video=open(new_segment_filename, 'rb'), caption="Is this segment suitable?", reply_markup=confirmation_keyboard())
            # Update user_data with the new filename
            user_data[user_id]["extracted_filename"] = new_segment_filename
    else:
        query.message.reply_text("Please send a video first.")

# Function to handle the custom caption provided by the user
def handle_caption(update: Update, context: CallbackContext) -> None:
    user_id = update.message.chat_id
    if user_id in user_data and "approval" in user_data[user_id]:
        caption = update.message.text
        user_data[user_id]["caption"] = caption
        update.message.reply_text("Please provide a link to add in the caption.")
        context.user_data["approval"] = False
    else:
        update.message.reply_text("Please send a video first.")

# Function to handle the link provided by the user
def handle_link(update: Update, context: CallbackContext) -> None:
    user_id = update.message.chat_id
    if user_id in user_data and not user_data[user_id]["approval"]:
        extracted_filename = user_data[user_id]["extracted_filename"]
        caption = user_data[user_id]["caption"]
        link = update.message.text

        # Format the caption with the link
        formatted_caption = f"@NeonGhost_Networks\n\n🚨{caption}🚨\n\n🔗 Video Link is Given Below 👇😏👇\n{link}"

        # Send back the video with caption and link embedded
        try:
            with open(extracted_filename, 'rb') as video:
                context.bot.send_video(user_id, video, caption=formatted_caption)
        except FileNotFoundError:
            update.message.reply_text("Sorry, there was an error processing your request.")
        finally:
            # Cleanup user_data and remove local files
            os.remove(extracted_filename)
            del user_data[user_id]
    else:
        update.message.reply_text("Please provide a custom caption first.")

# Register handlers
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(MessageHandler(Filters.video, handle_video))
dispatcher.add_handler(CallbackQueryHandler(handle_confirmation))
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_caption))
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_link))

# Start the bot
updater.start_polling()
updater.idle()