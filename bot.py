import telebot
import os
import re

# Your Telegram Bot API token
TOKEN = '6317227210:AAGpjnW4q6LBrpYdFNN1YrH62NcH9r_z03Q'

# Initialize bot
bot = telebot.TeleBot(TOKEN)

# Permanent thumbnail URL for the custom caption feature
THUMBNAIL_URL = 'https://telegra.ph/file/cab0b607ce8c4986e083c.jpg'  # Replace with your actual thumbnail URL

# Dictionary to store user data for custom captions and terabox links
user_data = {}

# Channel ID where posts will be automatically forwarded
AUTO_POST_CHANNEL_ID = -1002070953272  # Replace with your actual channel ID

# Handler to start the bot and choose feature
@bot.message_handler(commands=['start'])
def start_message(message):
    keyboard = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    button1 = telebot.types.KeyboardButton("Single Post")
    button2 = telebot.types.KeyboardButton("Multiple Posts")
    keyboard.add(button1, button2)
    bot.send_message(message.chat.id, "Welcome! Please choose an option for Terabox Editor:", reply_markup=keyboard)

# Handler to process text messages
@bot.message_handler(content_types=['text'])
def handle_text(message):
    if message.text == "Single Post" or message.text == "Multiple Posts":
        bot.send_message(message.chat.id, "Please send one or more images, videos, or GIFs with TeraBox links in the captions.")
    else:
        bot.send_message(message.chat.id, "Please choose a valid option from the menu.")

# Handler to process images, videos, and GIFs with captions
@bot.message_handler(content_types=['photo', 'video', 'document'])
def handle_media(message):
    if message.content_type == 'photo':
        process_media(message, 'photo')
    elif message.content_type == 'video':
        process_media(message, 'video')
    elif message.content_type == 'document':
        # Check if the document is a GIF
        if message.document.mime_type == 'image/gif':
            process_media(message, 'gif')
        else:
            bot.send_message(message.chat.id, "Unsupported document type. Please send images, videos, or GIFs.")

def process_media(message, media_type):
    user_id = message.chat.id

    if media_type == 'photo':
        file_id = message.photo[-1].file_id
    elif media_type == 'video':
        file_id = message.video.file_id
    elif media_type == 'gif':
        file_id = message.document.file_id

    file_info = bot.get_file(file_id)
    downloaded_file = bot.download_file(file_info.file_path)

    # Save the file to a local path
    if media_type == 'photo':
        media_filename = f"media_{file_id}.jpg"
    elif media_type == 'video':
        media_filename = f"media_{file_id}.mp4"
    elif media_type == 'gif':
        media_filename = f"media_{file_id}.gif"

    with open(media_filename, 'wb') as media_file:
        media_file.write(downloaded_file)

    text = message.caption  # Get the caption text

    # Use regex to find any link containing "terabox" in the caption
    terabox_links = re.findall(r'https?://\S*terabox\S*', text, re.IGNORECASE)
    if terabox_links:
        # Store data in user_data for processing after user choice
        user_data[user_id] = {
            "terabox_links": terabox_links,
            "media_filename": media_filename,
            "media_type": media_type
        }

        # Prompt user to enable autopost
        keyboard = telebot.types.InlineKeyboardMarkup()
        button_auto_post = telebot.types.InlineKeyboardButton("Enable Autopost", callback_data="auto_post")
        keyboard.add(button_auto_post)
        bot.send_message(user_id, "Do you want to enable autopost for this content?", reply_markup=keyboard)

    else:
        bot.send_message(user_id, "No valid TeraBox links found in the caption. Please try again.")

# Handler for callback queries (autopost)
@bot.callback_query_handler(func=lambda call: call.data == "auto_post")
def handle_autopost(call):
    user_id = call.message.chat.id

    if user_id in user_data:
        terabox_links = user_data[user_id]["terabox_links"]
        media_filename = user_data[user_id]["media_filename"]
        media_type = user_data[user_id]["media_type"]

        try:
            # Simulate posting process (replace with actual posting logic)
            if media_type == 'photo':
                bot.send_photo(user_id, open(media_filename, 'rb'))
            elif media_type == 'video':
                bot.send_video(user_id, open(media_filename, 'rb'))
            elif media_type == 'gif':
                bot.send_document(user_id, open(media_filename, 'rb'))

            bot.send_message(user_id, "Post successfully created!")

            # If autopost is enabled, post to the designated channel
            keyboard = telebot.types.InlineKeyboardMarkup()
            button_post_channel = telebot.types.InlineKeyboardButton("Post to Channel", callback_data="post_to_channel")
            keyboard.add(button_post_channel)
            bot.send_message(user_id, "Do you want to post this to the channel?", reply_markup=keyboard)

        except Exception as e:
            bot.send_message(user_id, f"Error creating post: {e}")

        finally:
            # Cleanup user_data and remove local file
            if os.path.exists(media_filename):
                os.remove(media_filename)
            del user_data[user_id]

    else:
        bot.send_message(user_id, "No media found for autopost.")

# Handler for callback queries (post to channel)
@bot.callback_query_handler(func=lambda call: call.data == "post_to_channel")
def handle_post_to_channel(call):
    user_id = call.message.chat.id

    try:
        # Forward the message to the specified channel
        formatted_caption = "Caption for the channel post"  # Replace with your actual caption
        media_filename = user_data[user_id]["media_filename"]
        media_type = user_data[user_id]["media_type"]

        with open(media_filename, 'rb') as media:
            if media_type == 'photo':
                bot.send_photo(AUTO_POST_CHANNEL_ID, media, caption=formatted_caption)
            elif media_type == 'video':
                bot.send_video(AUTO_POST_CHANNEL_ID, media, caption=formatted_caption)
            elif media_type == 'gif':
                bot.send_document(AUTO_POST_CHANNEL_ID, media, caption=formatted_caption)

        bot.send_message(user_id, "Successfully posted to the channel!")

    except Exception as e:
        bot.send_message(user_id, f"Error posting to channel: {e}")

    finally:
        # Cleanup user_data and remove local file
        if os.path.exists(media_filename):
            os.remove(media_filename)
        del user_data[user_id]

# Start polling for messages
bot.polling()
