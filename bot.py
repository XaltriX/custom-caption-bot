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
        bot.register_next_step_handler(message, handle_image)
    else:
        bot.send_message(message.chat.id, "Please choose a valid option from the menu.")

# Handler to process images for TeraBox Editor
def handle_image(message):
    user_id = message.chat.id
    if message.content_type == 'photo':
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
        bot.register_next_step_handler(message, detect_terabox_link)
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
            # Proceed with the detected TeraBox link
            # Add your logic here, e.g., formatting the caption with the TeraBox link
        else:
            bot.send_message(user_id, "No valid TeraBox link found in the caption. Please start again by typing /start.")
            return

        # Cleanup user_data and remove local files
        os.remove(image_filename)
        del user_data[user_id]

# Start polling for messages
bot.polling()
