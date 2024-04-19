import telebot
import os
from moviepy.editor import VideoFileClip

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
    # Check if file size exceeds the maximum allowed size
    if message.video.file_size > MAX_FILE_SIZE:
        bot.send_message(message.chat.id, "Sorry, I can only process videos up to 20 MB.")
        return

    bot.send_message(message.chat.id, "Processing the video...")

    # Get video file ID
    file_id = message.video.file_id

    # Download the video file in chunks
    # Download the video file in chunks
downloaded_file = b''
offset = 0
chunk_size = 64 * 1024  # 64 KB

while offset < file_size:
    new_chunk = bot.download_file(file_path)
    downloaded_file += new_chunk
    offset += len(new_chunk)


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

    # Ask user to add caption
    caption_msg = "Please add a caption for the GIF."
    bot.send_message(message.chat.id, caption_msg)

    # Store user chat ID, GIF filename, and video filename in user_data
    user_data[message.chat.id] = {'gif': gif_filename, 'video': video_filename}

# Handler to handle the caption provided by the user
@bot.message_handler(func=lambda message: True)
def handle_caption(message):
    # Retrieve user data
    user_id = message.chat.id
    if user_id in user_data:
        gif_filename = user_data[user_id]['gif']
        video_filename = user_data[user_id]['video']  # Retrieve video filename

        # Save the caption provided by the user
        caption = message.text

        # Add "@NeonGhost_Networks" at the beginning of the caption
        caption_with_tag = "@NeonGhost_Networks\n" + caption

        # Update user_data with modified caption
        user_data[user_id]['caption'] = caption_with_tag

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
        gif_filename = user_data[user_id]['gif']
        caption = user_data[user_id]['caption']
        video_filename = user_data[user_id]['video']  # Retrieve video filename

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
