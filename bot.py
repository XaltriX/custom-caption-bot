import telebot
import os
import re

# Your Telegram Bot API token
TOKEN = '6317227210:AAGpjnW4q6LBrpYdFNN1YrH62NcH9r_z03Q'

# Initialize bot
bot = telebot.TeleBot(TOKEN)
# Permanent thumbnail URL for the custom caption feature
THUMBNAIL_URL = 'https://telegra.ph/file/cab0b607ce8c4986e083c.jpg'  # Replace with your actual thumbnail URL

# Dictionary to store user data for custom captions
user_data = {}

# Channel ID where posts will be automatically forwarded
AUTO_POST_CHANNEL_ID = -1002070953272  # Replace with your actual channel ID
# Handler to start the bot and choose feature
@bot.message_handler(commands=['start'])
def start_message(message):
    keyboard = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    button1 = telebot.types.KeyboardButton("Custom Caption")
    button2 = telebot.types.KeyboardButton("TeraBox Editor")
    keyboard.add(button1, button2)
    bot.send_message(message.chat.id, "Welcome! Please choose a feature:", reply_markup=keyboard)
# Handler to process text messages
@bot.message_handler(content_types=['text'])
def handle_text(message):
    if message.text == "Custom Caption":
        bot.send_message(message.chat.id, "Please provide the preview link.")
        # Assuming handle_preview_link is not defined, removing next step registration
        # bot.register_next_step_handler(message, handle_preview_link)
    elif message.text == "TeraBox Editor":
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
        # Prompt user to select posting option
        keyboard = telebot.types.InlineKeyboardMarkup()
        button_now = telebot.types.InlineKeyboardButton("Post Now", callback_data="post_now")
        button_schedule = telebot.types.InlineKeyboardButton("Schedule for Later", callback_data="schedule")
        keyboard.row(button_now, button_schedule)
        bot.send_message(user_id, "Choose when you want to post this:", reply_markup=keyboard)

        # Store data in user_data for processing after user choice
        user_data[user_id] = {
            "terabox_links": terabox_links,
            "media_filename": media_filename,
            "media_type": media_type
        }

    else:
        bot.send_message(user_id, "No valid TeraBox links found in the caption. Please try again.")
# Handler for callback queries (post now or schedule)
@bot.callback_query_handler(func=lambda call: True)
def handle_callback_query(call):
    user_id = call.message.chat.id

    if call.data == "post_now":
        terabox_links = user_data[user_id]["terabox_links"]
        media_filename = user_data[user_id]["media_filename"]
        media_type = user_data[user_id]["media_type"]

        # Format the caption with the TeraBox links
        formatted_caption = (
            f"⚝──⭒─⭑─⭒──⚝\n"
            "👉 *Welcome!* 👈\n"
            "⚝──⭒─⭑─⭒──⚝\n\n"
            "≿━━━━━━━━━━━━━━━━━━━━━━━༺❀༻━━━━━━━━━━━━━━━━━━━━━━≾\n"
            f"📥  𝐉𝐎𝐈𝐍 𝐔𝐒 :– **@NeonGhost_Networks**\n"
            "≿━━━━━━━━━━━━━━━━━━━━━━━༺❀༻━━━━━━━━━━━━━━━━━━━━━━≾\n\n"
        )
        for idx, link in enumerate(terabox_links):
            formatted_caption += f"📽️ 𝐋𝐈𝐍𝐊 {idx + 1}:– {link}\n"
        formatted_caption += (
            "─────────────  **By NeonGhost_Networks** ────────────"
        )

        # Inline keyboard for additional links
        keyboard = telebot.types.InlineKeyboardMarkup()
        keyboard.add(telebot.types.InlineKeyboardButton("How To Watch & Download 🔞", url="https://t.me/HTDTeraBox/2"))
        keyboard.add(telebot.types.InlineKeyboardButton("Movie Group🔞🎥", url="https://t.me/RequestGroupNG"))
        keyboard.add(telebot.types.InlineKeyboardButton("BackUp Channel🎯", url="https://t.me/+ZgpjbYx8dGZjODI9"))

        # Send back the media with the TeraBox links and buttons
        try:
            with open(media_filename, 'rb') as media:
                if media_type == 'photo':
                    bot.send_photo(user_id, media, caption=formatted_caption, reply_markup=keyboard)
                elif media_type == 'video':
                    bot.send_video(user_id, media, caption=formatted_caption, reply_markup=keyboard)
                elif media_type == 'gif':
                    bot.send_document(user_id, media, caption=formatted_caption, reply_markup=keyboard)

            # If auto-post to channel is selected
            if call.message.chat.type == 'private':  # Ensure the message is from a private chat
                keyboard = telebot.types.InlineKeyboardMarkup()
                button_auto_post = telebot.types.InlineKeyboardButton("Yes, Post to Channel", callback_data="auto_post")
                button_cancel = telebot.types.InlineKeyboardButton("Cancel", callback_data="cancel")
                keyboard.row(button_auto_post, button_cancel)
                bot.send_message(user_id, "Do you want to automatically post this to the channel?", reply_markup=keyboard)

                # Store data in user_data for processing after user choice
                user_data[user_id]["formatted_caption"] = formatted_caption

        except Exception as e:
            bot.send_message(user_id, f"Sorry, there was an error processing your request: {e}")
        finally:
            # Remove the local file after sending
            os.remove(media_filename)

    elif call.data == "schedule":
        bot.send_message(user_id, "Feature under development. Please choose another option.")

    elif call.data == "auto_post":
    # Forward the message to the specified channel
    formatted_caption = user_data[user_id]["formatted_caption"]
    media_filename = user_data[user_id]["media_filename"]
    media_type = user_data[user_id]["media_type"]

    try:
        with open(media_filename, 'rb') as media:
            if media_type == 'photo':
                bot.send_photo(AUTO_POST_CHANNEL_ID, media, caption=formatted_caption, reply_markup=None)
            elif media_type == 'video':
                bot.send_video(AUTO_POST_CHANNEL_ID, media, caption=formatted_caption, reply_markup=None)
            elif media_type == 'gif':
                bot.send_document(AUTO_POST_CHANNEL_ID, media, caption=formatted_caption, reply_markup=None)

        bot.send_message(user_id, "Successfully posted to the channel!")

    except FileNotFoundError:
        bot.send_message(user_id, "File not found. Cannot post.")
    except Exception as e:
        bot.send_message(user_id, f"Sorry, there was an error processing your request: {e}")
    finally:
        # Remove the local file if it exists
        if os.path.exists(media_filename):
            os.remove(media_filename)
        # Cleanup user_data
        del user_data[user_id]

    elif call.data == "cancel":
        bot.send_message(user_id, "Operation canceled. Please choose another option.")
# Handler for processing errors
@bot.message_handler(func=lambda message: True)
def handle_errors(message):
    bot.send_message(message.chat.id, "Sorry, I didn't understand that command. Please choose a valid option from the menu.")

# Start polling for messages
bot.polling()
