import telebot
import os
import re

# Your Telegram Bot API token
TOKEN = '6317227210:AAGpjnW4q6LBrpYdFNN1YrH62NcH9r_z03Q'

# Initialize bot
bot = telebot.TeleBot(TOKEN)

# Dictionary to store user data
user_data = {}

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
        bot.send_message(message.chat.id, "Please send an image with a TeraBox link in the caption.")
    else:
        bot.send_message(message.chat.id, "Please choose a valid option from the menu.")

# Handler to process images for TeraBox Editor
@bot.message_handler(content_types=['photo'])
def handle_image(message):
    user_id = message.chat.id
    if message.caption:
        file_id = message.photo[-1].file_id
        file_info = bot.get_file(file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        # Save the image to a file
        image_filename = f"image_{file_id}.jpg"
        with open(image_filename, 'wb') as image_file:
            image_file.write(downloaded_file)

        # Store the image filename in user_data
        user_data[user_id] = {"image_filename": image_filename}
        bot.send_message(user_id, "Please wait while I detect the TeraBox link in the caption...")

        # Detect the TeraBox link in the caption
        detect_terabox_link(message)
    else:
        bot.send_message(user_id, "Please send an image with a TeraBox link in the caption.")

# Handler to detect the TeraBox link in the caption
def detect_terabox_link(message):
    user_id = message.chat.id
    if user_id in user_data:
        image_filename = user_data[user_id]["image_filename"]
        caption = message.caption  # Get the caption text

        # Use regex to find any link containing "terabox" in the caption
        terabox_link = re.search(r'https?://\S*terabox\S*', caption, re.IGNORECASE)
        if terabox_link:
            terabox_link = terabox_link.group(0)
            formatted_caption = (
    f"⚝──⭒─⭑─⭒──⚝\n"
    "👉 *Welcome!* 👈\n"
    "⚝──⭒─⭑─⭒──⚝\n\n"
    "≿━━━━━━━━━━༺❀༻━━━━━━━━━≾\n"
    f"📥  𝐉𝐎𝐈𝐍 𝐔𝐒 :– @NeonGhost_Networks \n"
    "≿━━━━━━━━━━༺❀༻━━━━━━━━━≾\n\n"
    f"➽────────❥🔗𝙁𝙪𝙡𝙡 𝙑𝙞𝙙𝙚𝙤 𝙇𝙞𝙣𝙠🔗❥────────➽\n\n"
    f"𝐕𝐢𝐝𝐞𝐨 𝐋𝐢𝐧𝐤:👉🔗 {terabox_link} 🔗👈\n\n"       
    "───────── 𝗕𝘆 @𝗡𝗲𝗼𝗻𝗚𝗵𝗼𝘀𝘁_𝗡𝗲𝘁𝘄𝗼𝗿𝗸𝘀 ─────────"
)

            # Inline keyboard for additional links
            keyboard = telebot.types.InlineKeyboardMarkup()
            keyboard.add(telebot.types.InlineKeyboardButton("How To Watch & Download 🔞", url="https://t.me/HTDTeraBox/2"))
            keyboard.add(telebot.types.InlineKeyboardButton("Movie Group🔞🎥", url="https://t.me/RequestGroupNG"))
            keyboard.add(telebot.types.InlineKeyboardButton("BackUp Channel🎯", url="https://t.me/+ZgpjbYx8dGZjODI9"))

            # Send back the image with the TeraBox link and buttons
            try:
                with open(image_filename, 'rb') as image:
                    bot.send_photo(user_id, image, caption=formatted_caption, reply_markup=keyboard)
            except Exception as e:
                bot.send_message(user_id, f"Sorry, there was an error processing your request: {e}")
            finally:
                # Cleanup user_data and remove local files
                os.remove(image_filename)
                del user_data[user_id]
        else:
            bot.send_message(user_id, "No valid TeraBox link found in the caption. Please start again by typing /start.")

# Start polling for messages
bot.polling()
