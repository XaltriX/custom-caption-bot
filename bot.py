import telebot
from pymongo import MongoClient
from gridfs import GridFS
from moviepy.editor import VideoFileClip
import io

# Your Telegram Bot API token
TOKEN = '6317227210:AAGpjnW4q6LBrpYdFNN1YrH62NcH9r_z03Q'

# Your MongoDB connection URL
MONGO_URL = 'mongodb+srv://ytviralverse:B5LYq0IPFpDT1mNs@ngcustombot.6ngugfq.mongodb.net/'

# Initialize bot
bot = telebot.TeleBot(TOKEN)

# Connect to MongoDB
client = MongoClient(MONGO_URL)
db = client["ngcustombot"]
fs = GridFS(db)

# Your Telegram channel ID where you want to store metadata
CHANNEL_ID = 'YOUR_TELEGRAM_CHANNEL_ID'

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

        # Save the video file in MongoDB using GridFS
        video_id = fs.put(bot.download_file(file_path), filename=f"video_{file_id}.mp4")

        # Get video duration
        with fs.get(video_id) as video_data:
            clip = VideoFileClip(io.BytesIO(video_data.read()))
            duration = min(clip.duration, 5)  # Limit duration to 5 seconds
            middle_time = clip.duration / 2  # Get the middle time of the video

        # Calculate start and end times for the segment
        start_time = max(middle_time - (duration / 2), 0)
        end_time = min(middle_time + (duration / 2), clip.duration)

        # Extract segment from the middle of the video and save as GIF
        with fs.get(video_id) as video_data:
            clip = VideoFileClip(io.BytesIO(video_data.read())).subclip(start_time, end_time)
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

        # Store metadata in the Telegram channel
        channel_message = bot.send_message(CHANNEL_ID, caption_with_tag)

        # Retrieve the link to the message
        link = f"https://t.me/{CHANNEL_ID}/{channel_message.message_id}"

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
