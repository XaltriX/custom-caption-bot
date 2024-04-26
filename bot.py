import telebot
import os
from moviepy.editor import VideoFileClip

# Your Telegram Bot API token
TOKEN = '6317227210:AAGpjnW4q6LBrpYdFNN1YrH62NcH9r_z03Q'

# Maximum allowed file size in bytes (adjust as needed)
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB

# Initialize bot
bot = telebot.TeleBot(TOKEN)

# Function to extract a segment from the video based on the start and end times
def extract_segment(video_filename, start_time, end_time):
    clip = VideoFileClip(video_filename)
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
    file_id = message.video.file_id
    file_info = bot.get_file(file_id)

    if file_info.file_size > MAX_FILE_SIZE_BYTES:
        bot.send_message(message.chat.id, "Sorry, the file size is too large. Please try with a smaller video.")
        return

    file = bot.download_file(file_info.file_path)
    video_filename = f"video_{file_id}.mp4"

    with open(video_filename, 'wb') as f:
        f.write(file)

    try:
        # Extract segments from the video: starting, middle, and end
        duration = VideoFileClip(video_filename).duration
        start_segment = extract_segment(video_filename, 0, min(duration, 5))
        middle_segment = extract_segment(video_filename, max(0.25 * duration, 0), min(0.5 * duration, duration))
        end_segment = extract_segment(video_filename, max(duration - 5, 0), duration)

        # Send the extracted segments to the user
        with open(start_segment, 'rb') as video_file:
            bot.send_video(message.chat.id, video_file)
        with open(middle_segment, 'rb') as video_file:
            bot.send_video(message.chat.id, video_file)
        with open(end_segment, 'rb') as video_file:
            bot.send_video(message.chat.id, video_file)

        # Ask the user to choose a segment
        bot.send_message(message.chat.id, "Please choose a segment by sending the corresponding number:\n1. Starting segment\n2. Middle segment\n3. End segment")
        user_data[message.chat.id] = {"start_segment": start_segment, "middle_segment": middle_segment, "end_segment": end_segment}
    except Exception as e:
        bot.send_message(message.chat.id, f"Sorry, there was an error processing your video: {e}")

# Handler to process user's segment choice
@bot.message_handler(func=lambda message: True)
def handle_segment_choice(message):
    user_id = message.chat.id
    if user_id in user_data:
        try:
            choice = int(message.text)
            if choice in [1, 2, 3]:
                segment_key = ""
                if choice == 1:
                    segment_key = "start_segment"
                elif choice == 2:
                    segment_key = "middle_segment"
                else:
                    segment_key = "end_segment"

                extracted_filename = user_data[user_id][segment_key]
                bot.send_message(user_id, f"You've chosen segment {choice}. Processing...")

                # Update user_data with the correct segment filename
                user_data[user_id]["segment_filename"] = extracted_filename

                # Ask for custom caption and link
                bot.send_message(user_id, "Please provide a custom caption for the video:")
                bot.register_next_step_handler(message, handle_caption)
            else:
                bot.send_message(user_id, "Invalid choice. Please choose a segment by sending the corresponding number:\n1. Starting segment\n2. Middle segment\n3. End segment")
        except ValueError:
            bot.send_message(user_id, "Invalid choice. Please choose a segment by sending the corresponding number:\n1. Starting segment\n2. Middle segment\n3. End segment")
    else:
        bot.send_message(user_id, "Please send a video first.")

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
        extracted_filename = user_data[user_id]["segment_filename"]
        caption = user_data[user_id]["caption"]
        link = message.text

        # Format the caption with the link and additional text
        formatted_caption = f"@neonghost_networks\n\n🚨 {caption} 🚨\n\n🔗 Video Link is Given Below 👇😏👇\n\n{link}\n"

        # Send back the video with caption and link embedded
        try:
            with open(extracted_filename, 'rb') as video:
                bot.send_video(user_id, video, caption=formatted_caption)
        except FileNotFoundError:
            bot.send_message(user_id, "Sorry, there was an error processing your request.")
        finally:
            # Cleanup user_data and remove local files
            os.remove(extracted_filename)
            del user_data[user_id]
    else:
        bot.send_message(message.chat.id, "Please send a video first.")

# Start polling for messages
bot.polling()
