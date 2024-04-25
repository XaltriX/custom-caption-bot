from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import os
import random

# Your Telegram Bot API token
TOKEN = '6317227210:AAGpjnW4q6LBrpYdFNN1YrH62NcH9r_z03Q'

# Maximum allowed file size in bytes (adjust as needed)
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB

# Initialize bot
updater = Updater(token=TOKEN, use_context=True)
dispatcher = updater.dispatcher

# Command handler to start the bot
def start(update, context):
    update.message.reply_text("Welcome! Please send a video🤝")

# Handler to process the uploaded video
def handle_video(update, context):
    video_file = update.message.video.get_file()
    video_path = f"video_{update.message.chat_id}.mp4"
    video_file.download(video_path)
    extract_sample(update.message.chat_id, video_path)

# Extract a 5-second sample from the video
def extract_sample(chat_id, video_path):
    sample_duration = 5
    command = f"ffmpeg -i {video_path} -ss 0 -t {sample_duration} -async 1 extracted_sample.mp4 -y"
    os.system(command)
    send_sample_confirmation(chat_id, "extracted_sample.mp4")

# Send the sample video for confirmation
def send_sample_confirmation(chat_id, sample_path):
    keyboard = [
        [InlineKeyboardButton("Yes", callback_data='confirm'),
         InlineKeyboardButton("No", callback_data='reject')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    context.bot.send_video(chat_id=chat_id, video=open(sample_path, 'rb'),
                           caption="Is this sample appropriate?",
                           reply_markup=reply_markup)

# Handle user confirmation
def handle_confirmation(update, context):
    query = update.callback_query
    if query.data == 'confirm':
        query.answer()
        query.edit_message_text("Please provide custom text between 🚨🚨 and the link for the caption.")
    elif query.data == 'reject':
        query.answer()
        extract_random_sample(query.message.chat_id, "extracted_sample.mp4")

# Extract a random 5-second sample from the video
def extract_random_sample(chat_id, video_path):
    sample_duration = 5
    total_duration = get_video_duration(video_path)
    if total_duration <= sample_duration:
        send_sample_confirmation(chat_id, video_path)
    else:
        start_time = random.randint(0, total_duration - sample_duration)
        command = f"ffmpeg -i {video_path} -ss {start_time} -t {sample_duration} -async 1 extracted_sample.mp4 -y"
        os.system(command)
        send_sample_confirmation(chat_id, "extracted_sample.mp4")

# Get the duration of the video in seconds
def get_video_duration(video_path):
    command = f"ffprobe -i {video_path} -show_entries format=duration -v quiet -of csv='p=0'"
    result = os.popen(command).read()
    return float(result)

# Handle custom text and link input
def handle_text_and_link(update, context):
    text = update.message.text
    context.user_data['text'] = text
    update.message.reply_text("Please provide the link to include in the caption.")

# Handle link input and generate final caption
def handle_link(update, context):
    link = update.message.text
    text = context.user_data['text']
    caption = f"@NeonGhost_Networks\n🚨🚨 {text} 🚨🚨\n\n🔗 Video Link: {link}"
    context.bot.send_message(update.message.chat_id, "Generating final video with custom caption...")
    send_final_video(update.message.chat_id, "extracted_sample.mp4", caption)

# Send the final video with custom caption
def send_final_video(chat_id, sample_path, caption):
    context.bot.send_video(chat_id=chat_id, video=open(sample_path, 'rb'), caption=caption)

# Set up the handlers
start_handler = CommandHandler('start', start)
video_handler = MessageHandler(Filters.video, handle_video)
confirmation_handler = CallbackQueryHandler(handle_confirmation)
text_handler = MessageHandler(Filters.text & ~Filters.command, handle_text_and_link)
link_handler = MessageHandler(Filters.text & ~Filters.command, handle_link)

dispatcher.add_handler(start_handler)
dispatcher.add_handler(video_handler)
dispatcher.add_handler(confirmation_handler)
dispatcher.add_handler(text_handler)
dispatcher.add_handler(link_handler)

# Start the bot
updater.start_polling()
updater.idle()
