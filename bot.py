import telebot
import os
import random
from moviepy.editor import VideoFileClip
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# Your Telegram Bot API token
TOKEN = '6317227210:AAGpjnW4q6LBrpYdFNN1YrH62NcH9r_z03Q'

# Initialize bot
bot = telebot.TeleBot(TOKEN)

# Dictionary to store user data
user_data = {}

# Maximum allowed file size in bytes (adjust as needed)
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB

# Command handler to start the bot
@bot.message_handler(commands=['start'])
def start_message(message):
    bot.send_message(message.chat.id, "Welcome! Please send a video🤝")

# Handler to process the uploaded video
@bot.message_handler(content_types=['video'])
def handle_video(message):
    bot.send_message(message.chat.id, "Processing the video...")

    # Get video file ID and download the file
    file_id = message.video.file_id
    file_info = bot.get_file(file_id)

    # Check if file size exceeds the maximum limit
    if file_info.file_size > MAX_FILE_SIZE_BYTES:
        bot.send_message(message.chat.id, "Sorry, the file size is too large. Please restart the bot and send a smaller video.")
        return

    file = bot.download_file(file_info.file_path)

    # Save the video file locally
    video_filename = f"video_{file_id}.mp4"
    with open(video_filename, 'wb') as f:
        f.write(file)

    # Extract segments from the video
    segments = extract_segments(video_filename)
    
    # Present the first segment to the user for confirmation
    present_segment(message.chat.id, segments)

def extract_segments(video_filename):
    """Extract segments from the video."""
    clip = VideoFileClip(video_filename)
    duration = clip.duration

    # Extract a 5-second segment from the beginning
    segments = [(0, min(duration, 5))]

    # Extract a 5-second segment from the middle
    if duration > 10:
        middle_start = max(duration / 2 - 2.5, 0)
        segments.append((middle_start, middle_start + 5))

    # Extract a 5-second segment from the end
    if duration > 5:
        segments.append((duration - 5, duration))

    return segments

def present_segment(chat_id, segments):
    """Present a segment to the user for confirmation."""
    start, end = segments[0]

    # Send the segment to the user
    bot.send_video(chat_id, open(video_filename, 'rb'), caption="Is this segment suitable?",
                   reply_markup=create_confirmation_keyboard())

def create_confirmation_keyboard():
    """Create a keyboard with 'Yes' and 'No' buttons for confirmation."""
    keyboard = InlineKeyboardMarkup(row_width=2)
    yes_button = InlineKeyboardButton("Yes", callback_data="confirm_yes")
    no_button = InlineKeyboardButton("No", callback_data="confirm_no")
    keyboard.add(yes_button, no_button)
    return keyboard

@bot.callback_query_handler(func=lambda call: True)
def handle_confirmation_callback(call):
    """Handle the user's confirmation callback."""
    if call.data == "confirm_yes":
        bot.send_message(call.message.chat.id, "Great! We'll proceed with this segment.")
        # Ask for custom caption
        bot.send_message(call.message.chat.id, "Please provide a custom caption for the video.")
        user_data[call.message.chat.id] = {"segment_index": 0}
    elif call.data == "confirm_no":
        bot.send_message(call.message.chat.id, "Let's try another segment.")
        # Extract and present the next segment
        user_data[call.message.chat.id]["segment_index"] += 1
        if user_data[call.message.chat.id]["segment_index"] < len(segments):
            present_segment(call.message.chat.id, segments[user_data[call.message.chat.id]["segment_index"]])
        else:
            bot.send_message(call.message.chat.id, "Sorry, no more segments available.")
            # Optionally, you can handle this case by asking the user to try again

@bot.message_handler(func=lambda message: True)
def handle_caption(message):
    """Handle the custom caption provided by the user."""
    user_id = message.chat.id
    if user_id in user_data:
        extracted_filename = f"extracted_video_{user_id}.mp4"
        segment_index = user_data[user_id]["segment_index"]
        caption = message.text

        # Add "@NeonGhost_Networks" at the beginning of the caption
        caption_with_tag = "@NeonGhost_Networks\n" + caption

        # Ask user to provide the link
        bot.send_message(message.chat.id, "Please provide a link to add in the caption.")
        # Store the custom caption and segment index in user_data
        user_data[user_id].update({"caption": caption_with_tag, "extracted_filename": extracted_filename})

        # Move to the next step
        bot.register_next_step_handler(message, handle_link)
    else:
        # If user data is not found, ask the user to send a video first.
        bot.send_message(message.chat.id, "Please send a video first.")

def handle_link(message):
    """Handle the link provided by the user."""
    user_id = message.chat.id
    if user_id in user_data:
        extracted_filename = user_data[user_id]['extracted_filename']
        caption = user_data[user_id]['caption']
        link = message.text

        # Format the caption with the link
        caption_with_link = f"{caption}\n\n🔗 Video Link is Given Below 👇😏👇\n{link}"

        # Send back the video with caption and link embedded
        with open(extracted_filename, 'rb') as video:
            bot.send_video(message.chat.id, video, caption=caption_with_link)

        # Cleanup user_data and remove local files
        del user_data[user_id]
        os.remove(extracted_filename)
    else:
        # If user data is not found, ask the user to send a video first.
        bot.send_message(message.chat.id, "Please send a video first.")

# Start polling for messages
bot.polling()
