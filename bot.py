import telebot
import os
import random
from moviepy.editor import VideoFileClip
from PIL import Image, ImageFilter
import io

# Your Telegram Bot API token
TOKEN = '6317227210:AAGpjnW4q6LBrpYdFNN1YrH62NcH9r_z03Q'

# Maximum allowed file size in bytes (adjust as needed)
MAX_FILE_SIZE_BYTES = 100 * 1024 * 1024  # 50 MB

# Initialize bot
bot = telebot.TeleBot(TOKEN)

# Dictionary to store user data
user_data = {}

# Function to extract a 5-second segment from the video
def extract_segment(video_filename):
    clip = VideoFileClip(video_filename)
    duration = min(clip.duration, 5)  # Limit duration to 5 seconds
    start_time = random.uniform(0, max(clip.duration - duration, 0))  # Start time for segment
    end_time = min(start_time + duration, clip.duration)  # End time for segment
    segment = clip.subclip(start_time, end_time)
    extracted_filename = f"extracted_{os.path.basename(video_filename)}"
    segment.write_videofile(extracted_filename, codec="libx264", fps=24, verbose=False)  # Save as mp4
    return extracted_filename

# Function to extract and blur the cover photo from the video
def blur_cover_photo(video_filename):
    clip = VideoFileClip(video_filename)
    frame = clip.get_frame(0)  # Get the first frame
    image = Image.fromarray(frame)
    blurred_image = image.filter(ImageFilter.GaussianBlur(15))
    blurred_image_io = io.BytesIO()
    blurred_image.save(blurred_image_io, format='JPEG')
    blurred_image_io.seek(0)
    return blurred_image_io

# Handler to start the bot and process videos
@bot.message_handler(commands=['start'])
def start_message(message):
    bot.send_message(message.chat.id, "Welcome! Please send a video🤝")

@bot.message_handler(content_types=['video'])
def handle_video(message):
    file_id = message.video.file_id
    file_info = bot.get_file(file_id)
    
    if file_info.file_size > MAX_FILE_SIZE_BYTES:
        bot.send_message(message.chat.id, "Sorry, the file size is too large. Please try with a smaller video.")
        return

    bot.send_message(message.chat.id, "Processing the video...")

    file = bot.download_file(file_info.file_path)
    video_filename = f"video_{file_id}.mp4"

    with open(video_filename, 'wb') as f:
        f.write(file)

    try:
        # Extract a new 5-second segment
        extracted_filename = extract_segment(video_filename)
        
        # Blur the cover photo
        blurred_cover_photo = blur_cover_photo(extracted_filename)
        
        # Store user chat ID and extracted filename in user_data
        user_data[message.chat.id] = {"extracted_filename": extracted_filename}

        # Send video with blurred cover photo and buttons
        bot.send_photo(message.chat.id, blurred_cover_photo, caption="Here's the video segment. Is it suitable?", reply_markup=confirmation_keyboard())
    except Exception as e:
        bot.send_message(message.chat.id, f"Sorry, there was an error processing your video: {e}")

# Keyboard markup for confirmation
def confirmation_keyboard():
    keyboard = telebot.types.InlineKeyboardMarkup()
    keyboard.add(telebot.types.InlineKeyboardButton("Yes", callback_data="yes"))
    keyboard.add(telebot.types.InlineKeyboardButton("No", callback_data="no"))
    return keyboard

# Handler to process confirmation of the video segment
@bot.callback_query_handler(func=lambda call: True)
def handle_confirmation(call):
    user_id = call.message.chat.id
    if user_id in user_data:
        extracted_filename = user_data[user_id]["extracted_filename"]
        if call.data == "yes":
            bot.send_message(call.message.chat.id, "Great! Please provide a custom caption for the video.")
            bot.register_next_step_handler(call.message, handle_caption)
        else:
            # Extract a new segment and send it to the user
            extracted_filename = extract_segment(extracted_filename)
            blurred_cover_photo = blur_cover_photo(extracted_filename)
            bot.send_photo(call.message.chat.id, blurred_cover_photo, caption="Is this segment suitable?", reply_markup=confirmation_keyboard())
            user_data[user_id]["extracted_filename"] = extracted_filename  # Update extracted filename in user_data
    else:
        bot.send_message(call.message.chat.id, "Please send a video first.")

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
        formatted_caption = f"\n@NeonGhost_Networks\n\n🚨 {caption} 🚨\n\n🔗 Video Link is Given Below 👇🫣​⚡​👇\n\n{link}\n"

        # Create inline keyboard with buttons
        keyboard = telebot.types.InlineKeyboardMarkup()
        button1 = telebot.types.InlineKeyboardButton(" More Videos🔞", url="https://t.me/+vgOaudZKle0zNmE0")
        button2 = telebot.types.InlineKeyboardButton("Update Channel🔥​👑​ℹ️​ ", url="https://t.me/leaktapesx")
        keyboard.add(button1, button2)

        # Send back the video with caption and link embedded
        try:
            with open(extracted_filename, 'rb') as video:
                bot.send_video(user_id, video, caption=formatted_caption, reply_markup=keyboard)
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
