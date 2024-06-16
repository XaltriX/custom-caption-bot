import telebot
import os
import re

# Your Telegram Bot API token
TOKEN = '6317227210:AAGpjnW4q6LBrpYdFNN1YrH62NcH9r_z03Q'

# Initialize bot
bot = telebot.TeleBot(TOKEN)

# Dictionary to store user data
user_data = {}

# Permanent thumbnail URL for the custom caption feature
THUMBNAIL_URL = 'https://telegra.ph/file/cab0b607ce8c4986e083c.jpg'  # Replace with your actual thumbnail URL

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
        bot.register_next_step_handler(message, handle_preview_link)
    elif message.text == "TeraBox Editor":
        bot.send_message(message.chat.id, "Please send an image, video, or GIF with a TeraBox link in the caption.")
        bot.register_next_step_handler(message, handle_media)
    else:
        bot.send_message(message.chat.id, "Please choose a valid option from the menu.")

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
        formatted_caption = f"\n@NeonGhost_Networks\n\n🚨 {caption} 🚨\n\n\n🔗 Preview Link: {preview_link} 💋\n\n 💋 🔗🤞 Full Video Link: {link} 🔞🤤\n\n"

        # Inline keyboard for additional links
        keyboard = telebot.types.InlineKeyboardMarkup()
        keyboard.add(telebot.types.InlineKeyboardButton("18+ Bot🤖🔞", url="https://t.me/new_leakx_mms_bot"))
        keyboard.add(telebot.types.InlineKeyboardButton("More Videos🔞🎥", url="https://t.me/+H6sxjIpsz-cwYjQ0"))
        keyboard.add(telebot.types.InlineKeyboardButton("BackUp Channel🎯", url="https://t.me/+ZgpjbYx8dGZjODI9"))

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

# Handler to process media for TeraBox Editor
def handle_media(message):
    user_id = message.chat.id
    if message.content_type in ['photo', 'video', 'document']:
        file_id = None
        if message.content_type == 'photo':
            file_id = message.photo[-1].file_id
        elif message.content_type == 'video':
            file_id = message.video.file_id
        elif message.content_type == 'document':
            file_id = message.document.file_id

        file_info = bot.get_file(file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        # Save the media to a file
        media_filename = f"media_{file_id}"
        with open(media_filename, 'wb') as media_file:
            media_file.write(downloaded_file)

        # Store the media filename in user_data
        user_data[user_id] = {"media_filename": media_filename, "content_type": message.content_type}
        bot.send_message(user_id, "Please wait while I detect the TeraBox link in the caption...")
        bot.register_next_step_handler(message, detect_terabox_link)
    else:
        bot.send_message(user_id, "Please send an image, video, or GIF with a TeraBox link in the caption.")

# Handler to detect the TeraBox link in the caption
def detect_terabox_link(message):
    user_id = message.chat.id
    if user_id in user_data:
        media_filename = user_data[user_id]["media_filename"]
        content_type = user_data[user_id]["content_type"]
        text = message.caption  # Get the caption text

        if not text:
            bot.send_message(user_id, "No caption provided. Please start again by typing /start.")
            return

        # Use regex to find all links containing "terabox" in the caption
        terabox_links = re.findall(r'https?://\S*terabox\S*', text, re.IGNORECASE)
        if not terabox_links:
            bot.send_message(user_id, "No valid TeraBox link found in the caption. Please start again by typing /start.")
            return

        # Format the caption with the TeraBox links
        formatted_caption = (
            f"⚝──⭒─⭑─⭒──⚝\n"
            "👉 *Welcome!* 👈\n"
            "⚝──⭒─⭑─⭒──⚝\n\n"
            "≿━━━━━━━━━━━━━━━━━━━━━━━༺❀༻━━━━━━━━━━━━━━━━━━━━━━≾\n"
            f"📥  𝐉𝐎𝐈𝐍 𝐔𝐒 :– **@NeonGhost_Networks**\n"
            "≿━━━━━━━━━━━━━━━━━━━━━━━༺❀༻━━━━━━━━━━━━━━━━━━━━━━≾\n\n"
        )

        for idx, link in enumerate(terabox_links, start=1):
            formatted_caption += f"➽────────────❥**🔗Video Link {idx}:🔗** {link}\n"

        formatted_caption += "─────────────  **By NeonGhost_Networks** ────────────"

        # Inline keyboard for additional links
        keyboard = telebot.types.InlineKeyboardMarkup()
        keyboard.add(telebot.types.InlineKeyboardButton("How To Watch & Download 🔞", url="https://t.me/HTDTeraBox/2"))
        keyboard.add(telebot.types.InlineKeyboardButton("Movie Group🔞🎥", url="https://t.me/RequestGroupNG"))
        keyboard.add(telebot.types.InlineKeyboardButton("BackUp Channel🎯", url="https://t.me/+ZgpjbYx8dGZjODI9"))

        # Send back the media with the TeraBox links and buttons
        try:
            with open(media_filename, 'rb') as media:
                if content_type == 'photo':
                    bot.send_photo(user_id, media, caption=formatted_caption, reply_markup=keyboard)
                elif content_type == 'video':
                    bot.send_video(user_id, media, caption=formatted_caption, reply_markup=keyboard)
                elif content_type == 'document':
                    bot.send_document(user_id, media, caption=formatted_caption, reply_markup=keyboard)
        except Exception as e:
            bot.send_message(user_id, f"Sorry, there was an error processing your request: {e}")
        finally:
            # Cleanup user_data and remove local files
            os.remove(media_filename)
            del user_data[user_id]
    else:
        bot.send_message(message.chat.id, "Please start the process again by typing /start.")

# Start polling for messages
bot.polling()
