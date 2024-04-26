import telebot
import os
from moviepy.editor import VideoFileClip

# Your Telegram Bot API token
TOKEN = '6317227210:AAGpjnW4q6LBrpYdFNN1YrH62NcH9r_z03Q'

# Maximum allowed file size in bytes (adjust as needed)
MAX_FILE_SIZE_BYTES = 15 * 1024 * 1024  # 15 MB

# Initialize bot
bot = telebot.TeleBot(TOKEN)

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

# Handler to start the bot and process videos
@bot.message_handler(content_types=['video'])
def handle_video(message):
    bot.send_message(message.chat.id, "Processing the video...")
    file_id = message.video.file_id
    file_info = bot.get_file(file_id)

    if file_info.file_size > MAX_FILE_SIZE_BYTES:
        bot.send_message(message.chat.id, "The file size is too large. Downloading the first 14 MB...")
        file_data = download_partial_video(file_id)
        with open(file_data['file_path'], 'rb') as video_file:
            bot.send_video(message.chat.id, video_file)
        os.remove(file_data['file_path'])  # Delete the downloaded file after use
    else:
        bot.send_message(message.chat.id, "File size is within limits. Processing as usual...")
        process_video(file_info, message.chat.id)

# Function to download the first 14 MB of a large video file
def download_partial_video(file_id):
    file_info = bot.get_file(file_id)
    with bot.download_file(file_info.file_path, limit=14*1024*1024) as file_data:
        return file_data

# Function to process the video (extracting a middle segment)
def process_video(file_info, chat_id):
    file = bot.download_file(file_info.file_path)
    video_filename = f"video_{file_info.file_id}.mp4"
    with open(video_filename, 'wb') as f:
        f.write(file)
    try:
        # Extract the middle segment from the video
        middle_segment = extract_middle_segment(video_filename)
        # Send the extracted middle segment to the user
        with open(middle_segment, 'rb') as video_file:
            # Add custom caption and link
            caption = "Check out this amazing video!"
            link = "https://example.com"
            formatted_caption = f"@neonghost_networks\n\n🚨 {caption} 🚨\n\n🔗 Video Link is Given Below 👇😏👇\n\n{link}\n"
            bot.send_video(chat_id, video_file, caption=formatted_caption)
    except Exception as e:
        bot.send_message(chat_id, f"Sorry, there was an error processing your video: {e}")
    finally:
        # Cleanup local files
        os.remove(video_filename)
        os.remove(middle_segment)

# Start polling for messages
bot.polling()
