import telebot
from pymongo import MongoClient
from gridfs import GridFS
from moviepy.editor import VideoFileClip
import os

# Your Telegram Bot API token
TOKEN = '6317227210:AAGpjnW4q6LBrpYdFNN1YrH62NcH9r_z03Q'

# Initialize bot
bot = telebot.TeleBot(TOKEN)

# Connect to MongoDB
mongo_url = "mongodb+srv://ytviralverse:2VPjBQ95DDnmVFu8@streamify.dvncffo.mongodb.net/?retryWrites=true&w=majority&appName=streamify"
client = MongoClient(mongo_url)
db = client["ngcustombot"]
fs = GridFS(db)

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

    try:
        # Get video file ID
        file_id = message.video.file_id

        # Download the video file in chunks
        file_path = bot.get_file(file_id).file_path
        file_size = bot.get_file(file_id).file_size
        downloaded_file = b''
        offset = 0
        chunk_size = 64 * 1024  # 64 KB

        while offset < file_size:
            new_chunk = bot.download_file(file_path, offset, chunk_size)
            downloaded_file += new_chunk
            offset += len(new_chunk)

        # Save the video file in MongoDB using GridFS
        video_id = fs.put(downloaded_file, filename=f"video_{file_id}.mp4")

        # Get video duration
        with fs.get(video_id) as video_data:
            clip = VideoFileClip(video_data)
            duration = min(clip.duration, 5)  # Limit duration to 5 seconds
            middle_time = clip.duration / 2  # Get the middle time of the video

        # Calculate start and end times for the segment
        start_time = max(middle_time - (duration / 2), 0)
        end_time = min(middle_time + (duration / 2), clip.duration)

        # Extract segment from the middle of the video and save as GIF
        with fs.get(video_id) as video_data:
            clip = VideoFileClip(video_data).subclip(start_time, end_time)
            gif_filename = f"video_{file_id}.gif"
            clip.write_gif(gif_filename, fps=10)  # Save as GIF

        # Ask user to add caption
        caption_msg = "Please add a caption for the GIF."
        bot.send_message(message.chat.id, caption_msg)

        # Store user chat ID, GIF filename, and video ID in user_data
        user_data[message.chat.id] = {'gif': gif_filename, 'video_id': video_id}

    except Exception as e:
        # Handle errors
        bot.send_message(message.chat.id, f"An error occurred while processing the video: {str(e)}")
        bot.send_message(message.chat.id, "Please try again.")

# Handler to handle the caption provided by the user
@bot.message_handler(func=lambda message: True)
def handle_caption(message):
    # Retrieve user data
    user_id = message.chat.id
    if user_id in user_data:
        gif_filename = user_data[user_id]['gif']
        video_id = user_data[user_id]['video_id']

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
        video_id = user_data[user_id]['video_id']

        # Save the link provided by the user
        link = message.text

        # Send back the GIF with caption and link embedded
        with open(gif_filename, 'rb') as gif:
            bot.send_document(message.chat.id, gif, caption=f"{caption}\n\n{link}")

        # Cleanup user_data and remove files from MongoDB
        del user_data[user_id]
        fs.delete(video_id)  # Delete video file from GridFS
        os.remove(gif_filename)  # Remove GIF file

    else:
        # If user data is not found, ask the user to send a video first.
        bot.send_message(message.chat.id, "Please send a video first.")

# Start polling for messages
bot.polling()
