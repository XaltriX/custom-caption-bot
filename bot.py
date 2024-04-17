import telebot
from telebot import types
import os
from io import BytesIO
from moviepy.video.io.VideoFileClip import VideoFileClip

# Your Telegram Bot API token
TOKEN = '6317227210:AAGpjnW4q6LBrpYdFNN1YrH62NcH9r_z03Q'

# Initialize bot
bot = telebot.TeleBot(TOKEN)

# Dictionary to store user data
user_data = {}

@bot.message_handler(commands=['start'])
def start_message(message):
    bot.send_message(message.chat.id, "Welcome! Please send a video.")

@bot.message_handler(content_types=['video'])
def handle_video(message):
    bot.send_message(message.chat.id, "Processing the video...")

    # Get video file ID
    video_file_id = message.video.file_id

    # Get video file info
    file_info = bot.get_file(video_file_id)
    video_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_info.file_path}"

    # Extract thumbnail from the video
    clip = VideoFileClip(video_url)
    thumbnail_filename = 'thumbnail.jpg'
    clip.save_frame(thumbnail_filename, t=0)

    # Ask user to add caption
    caption_msg = "Please add a caption for the thumbnail."
    bot.send_message(message.chat.id, caption_msg)

    # Store user chat ID and thumbnail filename in user_data
    user_data[message.chat.id] = {'thumbnail': thumbnail_filename}

@bot.message_handler(func=lambda message: True)
def handle_caption(message):
    # Retrieve user data
    user_id = message.chat.id
    if user_id in user_data:
        thumbnail_filename = user_data[user_id]['thumbnail']

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
        # If user data is not found, ask the user to send a video first
        bot.send_message(message.chat.id, "Please send a video first.")

def handle_link(message):
    # Retrieve user data
    user_id = message.chat.id
    if user_id in user_data:
        thumbnail_filename = user_data[user_id]['thumbnail']
        caption = user_data[user_id]['caption']
        
        # Save the link provided by the user
        link = message.text

        # Send back the thumbnail with caption and link embedded
        with open(thumbnail_filename, 'rb') as photo:
            bot.send_photo(message.chat.id, photo, caption=f"{caption}\n\n{link}")

        # Cleanup user_data
        del user_data[user_id]
    else:
        # If user data is not found, ask the user to send a video first
        bot.send_message(message.chat.id, "Please send a video first.")

bot.polling()
