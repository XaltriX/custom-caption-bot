import telebot
import os
import random
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

    # Check if start_time and end_time are valid
    if start_time < 0 or end_time > clip.duration or start_time > end_time:
        print(f"Error: Invalid start_time ({start_time}) or end_time ({end_time})")
        return None

    # Create the subclip and check if it was created successfully
    segment = None
    try:
        segment = clip.subclip(start_time, end_time)
    except Exception as e:
        print(f"Error: Failed to create subclip from {start_time} to {end_time}: {e}")

    extracted_filename = f"extracted_{os.path.basename(video_filename)}"
    if segment is not None:
        try:
            segment.write_videofile(extracted_filename, codec="libx264", fps=24)  # Save as mp4
        except BrokenPipeError:
            raise Exception("Error occurred while processing the video segment.")

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
        # Extract a segment from the middle of the video
        middle_start = random.uniform(0.25, 0.5) * VideoFileClip(video_filename).duration
        middle_end = min(middle_start + 5, VideoFileClip(video_filename).duration)
        extracted_filename = extract_segment(video_filename, middle_start, middle_end)

        # Ask the user for confirmation
        bot.send_video(message.chat.id, open(extracted_filename, 'rb'), caption="Is this segment suitable?", reply_markup=confirmation_keyboard())

        # Store user chat ID, extracted filename, and start/end times in user_data
        user_data[message.chat.id] = {"extracted_filename": extracted_filename, "start_time": middle_start, "end_time": middle_end}
    except Exception as e:
        bot.send_message(message.chat.id, f"Sorry, there was an error processing your video: {e}")

# Keyboard markup for confirmation
def confirmation_keyboard():
    keyboard = telebot.types.ReplyKeyboardMarkup(row_width=2)
    keyboard.add(telebot.types.KeyboardButton("Yes"), telebot.types.KeyboardButton("No"))
    return keyboard

# Handler to process confirmation of the video segment
@bot.message_handler(func=lambda message: True)
def handle_confirmation(message):
    user_id = message.chat.id
    if user_id in user_data:
        extracted_filename = user_data[user_id]["extracted_filename"]
        start_time = user_data[user_id]["start_time"]
        end_time = user_data[user_id]["end_time"]
        if message.text.lower() == "yes":
            bot.send_message(message.chat.id, "Great! Please provide a custom caption for the video.")
            bot.register_next_step_handler(message, handle_caption)
        else:
            # Extract a new segment
            clip_duration = VideoFileClip(extracted_filename).duration
            if end_time + 5 <= clip_duration:
                new_start = end_time
                new_end = min(new_start + 5, clip_duration)
                extracted_filename = extract_segment(extracted_filename, new_start, new_end)
                bot.send_video(message.chat.id, open(extracted_filename, 'rb'), caption="Is this segment suitable?", reply_markup=confirmation_keyboard())
                user_data[user_id]["extracted_filename"] = extracted_filename
                user_data[user_id]["start_time"] = new_start
                user_data[user_id]["end_time"] = new_end
            elif start_time - 5 >= 0:
                new_end = start_time
                new_start = max(new_end - 5, 0)
                extracted_filename = extract_segment(extracted_filename, new_start, new_end)
                bot.send_video(message.chat.id, open(extracted_filename, 'rb'), caption="Is this segment suitable?", reply_markup=confirmation_keyboard())
                user_data[user_id]["extracted_filename"] = extracted_filename
                user_data[user_id]["start_time"] = new_start
                user_data[user_id]["end_time"] = new_end
            else:
                bot.send_message(message.chat.id, "Sorry, we've reached the limit. Please send another video.")
    else:
        bot.send_message(message.chat.id, "Please send a video first.")

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
        extracted_filename = user_data[user_id]["extracted_filename"]
        caption = user_data[user_id]["caption"]
        link = message.text

        # Format the caption with the link
        formatted_caption = f"@NeonGhost_Networks\n\n🚨 {caption} 🚨\n\n🔗 Video Link is Given Below 👇😏👇\n{link}"

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
