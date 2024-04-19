import telebot
import os
from moviepy.editor import VideoFileClip
import time

# Your Telegram Bot API token
TOKEN = '6317227210:AAGpjnW4q6LBrpYdFNN1YrH62NcH9r_z03Q'

# Initialize bot
bot = telebot.TeleBot(TOKEN)

# Dictionary to store user data
user_data = {}

# Maximum file size allowed (in bytes)
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB

# Command handler to start the bot
@bot.message_handler(commands=['start'])
def start_message(message):
    bot.send_message(message.chat.id, "Welcome! Please send a video.")

# Handler to process the uploaded video
@bot.message_handler(content_types=['video'])
def handle_video(message):
    bot.send_message(message.chat.id, "Processing the video...")

    # Get video file ID and size
    file_id = message.video.file_id
    file_size = message.video.file_size

    if file_size > MAX_FILE_SIZE:
        bot.send_message(message.chat.id, "Sorry, the file size is too large. Please send a video file smaller than 20 MB.")
        return

    # Retry download up to 3 times with a delay
    retries = 3
    delay = 2  # Delay in seconds
    downloaded_file = None
    while retries > 0:
        try:
            downloaded_file = bot.download_file(file_id)
            break  # Exit loop if download succeeds
        except telebot.apihelper.ApiHTTPException as e:
            # Log the error
            print(f"Download file API error: {e}")
            retries -= 1
            if retries == 0:
                bot.send_message(message.chat.id, "Failed to download the video. Please try again later.")
                return
            time.sleep(delay)  # Wait before retrying

    # Save the video file locally
    video_filename = f"video_{file_id}.mp4"
    with open(video_filename, 'wb') as f:
        f.write(downloaded_file)

    # Get video duration
    clip = VideoFileClip(video_filename)
    duration = min(clip.duration, 5)  # Limit duration to 5 seconds
    middle_time = clip.duration / 2  # Get the middle time of the video

    # Calculate start and end times for the segment
    start_time = max(middle_time - (duration / 2), 0)
    end_time = min(middle_time + (duration / 2), clip.duration)

    # Extract segment from the middle of the video and save as GIF
    clip = clip.subclip(start_time, end_time)
    gif_filename = f"video_{file_id}.gif"
    clip.write_gif(gif_filename, fps=10)  # Save as GIF

    # Ask user to add a caption for the GIF
    bot.send_message(message.chat.id, "Please add a caption for the GIF.")

    # Store user chat ID, GIF filename, and video filename in user_data
    user_data[message.chat.id] = {'gif': gif_filename, 'video': video_filename}

# Handler to handle the caption provided by the user
@bot.message_handler(func=lambda message: True)
def handle_caption(message):
    # Retrieve user data
    user_id = message.chat.id
    if user_id in user_data:
        gif_filename = user_data[user_id]['gif']
        caption = message.text
        caption_with_tag = f"@NeonGhost_Networks\n{caption}"  # Add a tag to the caption

        # Update user data with the caption
        user_data[user_id]['caption'] = caption_with_tag

        # Ask user to provide a link
        bot.send_message(message.chat.id, "Please provide a link to add in the caption.")
        # Move to the next step
        bot.register_next_step_handler(message, handle_link)
    else:
        # If user data is not found, ask the user to send a video first.
        bot.send_message(message.chat.id, "Please send a video first.")

# Handler to handle the link provided by the user
def handle_link(message):
    # Retrieve user data
    user_id = message.chat.id
    if user_id in user_data:
        gif_filename = user_data[user_id]['gif']
        caption = user_data[user_id]['caption']
        video_filename = user_data[user_id]['video']

        # Save the link provided by the user
        link = message.text

        # Send back the GIF with caption and link embedded
        with open(gif_filename, 'rb') as gif:
            bot.send_document(message.chat.id, gif, caption=f"{caption}\n\n{link}")

        # Cleanup user_data and remove local files
        del user_data[user_id]
        os.remove(gif_filename)
        os.remove(video_filename)
    else:
        # If user data is not found, ask the user to send a video first.
        bot.send_message(message.chat.id, "Please send a video first.")

# Start polling for messages
bot.polling()
