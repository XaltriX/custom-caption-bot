import telebot
import os
from moviepy.editor import VideoFileClip

# Your Telegram Bot API token
TOKEN = '6317227210:AAGpjnW4q6LBrpYdFNN1YrH62NcH9r_z03Q'

# Maximum allowed file size in bytes (adjust as needed)
MAX_FILE_SIZE_BYTES = 15 * 1024 * 1024  # 15 MB

# Initialize bot
bot = telebot.TeleBot(TOKEN)

# Function to download the first 14 MB of the video file
def download_partial_video(file_id):
    file_info = bot.get_file(file_id)
    file_size = file_info.file_size
    max_size = min(MAX_FILE_SIZE_BYTES, file_size)
    file_path = file_info.file_path

    with bot.download_file(file_path, limit=max_size) as file_data:
        return file_data

# Function to extract a 5-second segment from the middle of the video
def extract_middle_segment(video_filename):
    clip = VideoFileClip(video_filename)
    duration = clip.duration
    start_time = max(0, duration / 2 - 2.5)  # Start 2.5 seconds before the middle
    end_time = min(duration, duration / 2 + 2.5)  # End 2.5 seconds after the middle
    segment = clip.subclip(start_time, end_time)
    extracted_filename = f"extracted_{os.path.basename(video_filename)}"
    try:
        segment.write_videofile(extracted_filename, codec="libx264", fps=24)  # Save as mp4
    except Exception as e:
        raise e
    return extracted_filename

# Dictionary to store user data
user_data = {}

# Handler to start the bot and process videos
@bot.message_handler(commands=['start'])
def start_message(message):
    bot.send_message(message.chat.id, "Welcome! Please send a video🤝")

@bot.message_handler(content_types=['video'])
def handle_video(message):
    bot.send_message(message.chat.id, "Processing the video...")

    # Download the first 14 MB of the video
    file_id = message.video.file_id
    file_data = download_partial_video(file_id)
    video_filename = f"video_{file_id}.mp4"

    with open(video_filename, 'wb') as f:
        f.write(file_data.read())

    try:
        # Extract the middle segment from the video
        middle_segment = extract_middle_segment(video_filename)

        # Send the extracted middle segment to the user
        with open(middle_segment, 'rb') as video_file:
            bot.send_video(message.chat.id, video_file)

        # Ask the user to provide a custom caption
        bot.send_message(message.chat.id, "Please provide a custom caption for the video:")
        user_data[message.chat.id] = {"middle_segment": middle_segment}
        bot.register_next_step_handler(message, handle_caption)
    except Exception as e:
        bot.send_message(message.chat.id, f"Sorry, there was an error processing your video: {e}")
        
# Handler to handle the custom caption provided by the user
def handle_caption(message):
    user_id = message.chat.id
    if user_id in user_data:
        caption = message.text
        user_data[user_id]["caption"] = caption
        bot.send_message(message.chat.id, "Please provide a link to add in the caption.")
        bot.register_next_step_handler(message, handle_link)
    else:
        bot.send_message(message.chat.id, "Please send a video first.")

# Handler to handle the link provided by the user
def handle_link(message):
    user_id = message.chat.id
    if user_id in user_data:
        link = message.text
        middle_segment = user_data[user_id]["middle_segment"]
        caption = user_data[user_id]["caption"]

        # Format the caption with the additional text and the provided link
        formatted_caption = f"@neonghost_networks\n\n🚨 {caption} 🚨\n\n🔗 Video Link is Given Below 👇😏👇\n\n{link}\n"

        # Send back the middle segment with the custom caption and link
        try:
            with open(middle_segment, 'rb') as video:
                bot.send_video(user_id, video, caption=formatted_caption)
        except FileNotFoundError:
            bot.send_message(user_id, "Sorry, there was an error processing your request.")
        finally:
            # Cleanup user_data and remove local files
            os.remove(middle_segment)
            del user_data[user_id]
    else:
        bot.send_message(message.chat.id, "Please send a video first.")

# Start polling for messages
bot.polling()
