import telebot
import os
import random
from moviepy.editor import VideoFileClip

# Your Telegram Bot API token
TOKEN = '6317227210:AAGpjnW4q6LBrpYdFNN1YrH62NcH9r_z03Q'

# Permanent thumbnail URL
THUMBNAIL_URL = 'https://telegra.ph/file/cab0b607ce8c4986e083c.jpg'

# Initialize bot
bot = telebot.TeleBot(TOKEN)

# Dictionary to store user data
user_data = {}

# Handler to start the bot and present the initial choice
@bot.message_handler(commands=['start'])
def start_message(message):
    bot.send_message(message.chat.id, "Welcome! What would you like to do?", reply_markup=initial_choice_inline_keyboard())

# Inline keyboard for the initial choice
def initial_choice_inline_keyboard():
    keyboard = telebot.types.InlineKeyboardMarkup()
    keyboard.add(telebot.types.InlineKeyboardButton("Extract Video Segment", callback_data="extract_segment"),
                 telebot.types.InlineKeyboardButton("Add Custom Caption", callback_data="custom_caption"))
    return keyboard

# Callback handler for the initial choice
@bot.callback_query_handler(func=lambda call: call.data in ["extract_segment", "custom_caption"])
def handle_initial_choice(call):
    if call.data == "extract_segment":
        bot.send_message(call.message.chat.id, "Please send a video for segment extraction.")
        bot.register_next_step_handler(call.message, handle_video_for_segment)
    elif call.data == "custom_caption":
        bot.send_message(call.message.chat.id, "Please provide a custom preview link.")
        bot.register_next_step_handler(call.message, handle_preview_link)

# Function to extract a 5-second segment from the video
def extract_segment(video_filename):
    with VideoFileClip(video_filename) as clip:
        duration = min(clip.duration, 5)  # Limit duration to 5 seconds
        start_time = random.uniform(0, max(clip.duration - duration, 0))  # Start time for segment
        end_time = min(start_time + duration, clip.duration)  # End time for segment
        segment = clip.subclip(start_time, end_time)
        extracted_filename = f"extracted_{os.path.basename(video_filename)}"
        segment.write_videofile(extracted_filename, codec="libx264", fps=24, verbose=False, audio_codec='aac')  # Save as mp4
    return extracted_filename

# Handler to process video for segment extraction
def handle_video_for_segment(message):
    file_id = message.video.file_id
    file_info = bot.get_file(file_id)
    
    if file_info.file_size > 100 * 1024 * 1024:  # 100 MB
        bot.send_message(message.chat.id, "Sorry, the file size is too large. Please try with a smaller video.")
        return

    bot.send_message(message.chat.id, "Processing the video...")

    file = bot.download_file(file_info.file_path)
    video_filename = f"video_{file_id}.mp4"

    with open(video_filename, 'wb') as f:
        f.write(file)

    try:
        # Extract a new 5-second segment and send it to the user
        extracted_filename = extract_segment(video_filename)
        with open(extracted_filename, 'rb') as video:
            bot.send_video(message.chat.id, video, caption="Here is your 5-second video segment.")
        
        # Remove the extracted segment file
        os.remove(extracted_filename)
    except Exception as e:
        bot.send_message(message.chat.id, f"Sorry, there was an error processing your video: {e}")
    finally:
        os.remove(video_filename)
    
    # Return to the start
    start_message(message)

# Handler to process the preview link for custom caption
def handle_preview_link(message):
    user_id = message.chat.id
    preview_link = message.text
    user_data[user_id] = {"preview_link": preview_link}
    bot.send_message(user_id, "Please provide a custom caption for the video.")
    bot.register_next_step_handler(message, handle_caption)

# Handler to handle the custom caption provided by the user
def handle_caption(message):
    user_id = message.chat.id
    if user_id in user_data:
        caption = message.text
        user_data[user_id]["caption"] = caption
        bot.send_message(message.chat.id, "Please provide a link to add in the caption.")
        bot.register_next_step_handler(message, handle_link)
    else:
        bot.send_message(message.chat.id, "Please start the process again by typing /start.")

# Handler to handle the link provided by the user
def handle_link(message):
    user_id = message.chat.id
    if user_id in user_data:
        preview_link = user_data[user_id]["preview_link"]
        caption = user_data[user_id]["caption"]
        link = message.text

        # Format the caption with the preview link and the custom link
        formatted_caption = f"\n@NeonGhost_Networks\n\n🚨 {caption} 🚨\n\n🔗 Preview Link: {preview_link}\n🔗 Video Link: {link}\n"

        # Inline keyboard for additional links
        keyboard = telebot.types.InlineKeyboardMarkup()
        keyboard.add(telebot.types.InlineKeyboardButton("Button 1", url="https://example.com/1"),
                     telebot.types.InlineKeyboardButton("Button 2", url="https://example.com/2"),
                     telebot.types.InlineKeyboardButton("Button 3", url="https://example.com/3"))

        # Send back the cover photo with the custom caption and buttons
        try:
            bot.send_photo(user_id, THUMBNAIL_URL, caption=formatted_caption, reply_markup=keyboard)
        except Exception as e:
            bot.send_message(user_id, f"Sorry, there was an error processing your request: {e}")
        finally:
            # Cleanup user_data
            del user_data[user_id]
    else:
        bot.send_message(message.chat.id, "Please start the process again by typing /start.")

# Start polling for messages
bot.polling()
