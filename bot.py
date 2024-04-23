import telebot
import os
from moviepy.editor import VideoFileClip

# Your Telegram Bot API token
TOKEN = '6317227210:AAGpjnW4q6LBrpYdFNN1YrH62NcH9r_z03Q'

# Maximum allowed file size in bytes (adjust as needed)
MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024  # 50 MB

# Initialize bot
bot = telebot.TeleBot(TOKEN)

# Dictionary to store user data
user_data = {}

# Command handler to start the bot
@bot.message_handler(commands=['start'])
def start_message(message):
    bot.send_message(message.chat.id, "Welcome! Please send a video.")

# Handler to process the uploaded video
@bot.message_handler(content_types=['video'])
def handle_video(message):
    bot.send_message(message.chat.id, "Processing the video...")

    # Get video file ID and download the file
    file_id = message.video.file_id
    file_info = bot.get_file(file_id)

    # Check if file size exceeds the maximum limit
    if file_info.file_size > MAX_FILE_SIZE_BYTES:
        bot.send_message(message.chat.id, "Sorry, the file size is too large. Please restart the bot and send a smaller video.")
        return

    file = bot.download_file(file_info.file_path)

    # Save the video file locally
    video_filename = f"video_{file_id}.mp4"
    with open(video_filename, 'wb') as f:
        f.write(file)

    # Get video duration
    clip = VideoFileClip(video_filename)
    duration = min(clip.duration, 6) - 1  # Limit duration to 6 seconds and extract from middle
    middle_time = clip.duration / 2  # Get the middle time of the video

    # Calculate start and end times for the segment
    start_time = max(middle_time - (duration / 2), 0)
    end_time = min(middle_time + (duration / 2), clip.duration)

    # Extract segment from the middle of the video
    clip = clip.subclip(start_time, end_time)
    extracted_filename = f"extracted_{file_id}.mp4"
    clip.write_videofile(extracted_filename, codec="libx264", fps=24)  # Save as mp4

    # Ask user to add caption
    caption_msg = "Please add a caption for the video."
    bot.send_message(message.chat.id, caption_msg)

    # Store user chat ID and extracted filename in user_data
    user_data[message.chat.id] = {'extracted_video': extracted_filename}

# Handler to handle the caption provided by the user
@bot.message_handler(func=lambda message: True)
def handle_caption(message):
    # Retrieve user data
    user_id = message.chat.id
    if user_id in user_data:
        extracted_filename = user_data[user_id]['extracted_video']

        # Save the caption provided by the user
        caption = message.text

        # Add "Video Link is Given Below" before the actual link
        caption_with_link = f"Video Link is Given Below\n{caption}"

        # Ask user to provide the link directly to the caption
        link_msg = "Please provide a link to add in the caption."
        bot.send_message(message.chat.id, link_msg)
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
        extracted_filename = user_data[user_id]['extracted_video']
        caption = message.text

        # Send back the video with caption and link embedded
        with open(extracted_filename, 'rb') as video:
            bot.send_video(message.chat.id, video, caption=caption)

        # Cleanup user_data and remove local files
        del user_data[user_id]
        os.remove(extracted_filename)
    else:
        # If user data is not found, ask the user to send a video first.
        bot.send_message(message.chat.id, "Please send a video first.")

# Start polling for messages
bot.polling()
