import telebot
import os
import random
from moviepy.editor import VideoFileClip

# Your Telegram Bot API token
TOKEN = '6317227210:AAGpjnW4q6LBrpYdFNN1YrH62NcH9r_z03Q'

# Maximum allowed file size in bytes (adjust as needed)
MAX_FILE_SIZE_BYTES = 2 * 1024 * 1024 * 1024  # 2 GB

# Initialize bot
bot = telebot.TeleBot(TOKEN)

# Dictionary to store user data
user_data = {}

# Command handler to start the bot
@bot.message_handler(commands=['start'])
def start_message(message):
    bot.send_message(message.chat.id, "Welcome! Please send a video.")

# Handler to process the uploaded video
@bot.message_handler(content_types=['video'])
def handle_video(message):
    bot.send_message(message.chat.id, "Processing the video...")

    # Get video file ID and download the file
    file_id = message.video.file_id
    file_info = bot.get_file(file_id)

    # Check if file size exceeds the maximum limit
    if file_info.file_size > MAX_FILE_SIZE_BYTES:
        bot.send_message(message.chat.id, "Sorry, the file size is too large. Please send a smaller video.")
        return

    file = bot.download_file(file_info.file_path)

    # Save the video file locally
    video_filename = f"video_{file_id}.mp4"
    with open(video_filename, 'wb') as f:
        f.write(file)

    # Get video duration
    clip = VideoFileClip(video_filename)
    total_duration = clip.duration

    # Define segment duration (5 seconds)
    segment_duration = 5

    # Initialize segment start time
    start_time = 0

    # Initialize loop counter
    loop_counter = 1

    # Loop to extract and send segments until user approves or end of video reached
    while start_time + segment_duration < total_duration:
        bot.send_message(message.chat.id, f"Extracting segment {loop_counter}...")

        # Calculate end time for the segment
        end_time = min(start_time + segment_duration, total_duration)

        # Extract segment from the video
        extracted_filename = f"extracted_{file_id}_{loop_counter}.mp4"  # Specify the output format as '.mp4'
        clip_sub.write_videofile(extracted_filename, codec="libx264", fps=24, logger=None, format="mp4")


        # Send extracted segment to user
        with open(extracted_filename, 'rb') as video:
            bot.send_video(message.chat.id, video)

        # Ask user if the segment is acceptable
        response = bot.send_message(message.chat.id, f"Is this segment acceptable? (Yes/No)")

        # Wait for user response
        user_response = bot.wait_for_message(message.chat.id)

        # If user approves, break out of the loop
        if user_response.text.lower() == 'yes':
            bot.send_message(message.chat.id, "Segment accepted.")
            # Ask user for custom caption
            caption_msg = "Please provide a custom caption for the video."
            bot.send_message(message.chat.id, caption_msg)
            user_data[message.chat.id] = {'extracted_video': extracted_filename}
            bot.register_next_step_handler(user_response, handle_caption)
            break
        else:
            # Increment loop counter
            loop_counter += 1

            # Update start time for next segment
            start_time = end_time

            # Remove temporary files
            os.remove(extracted_filename)

    # If end of video reached without user approval, send a message
    if start_time >= total_duration:
        bot.send_message(message.chat.id, "End of video reached without finding an acceptable segment.")

    # Cleanup: Remove local files
    os.remove(video_filename)

# Handler to handle the custom caption provided by the user
def handle_caption(message):
    # Retrieve user data
    user_id = message.chat.id
    if user_id in user_data:
        extracted_filename = user_data[user_id]['extracted_video']
        caption = message.text

        # Add "@NeonGhost_Networks" at the beginning of the caption
        caption_with_tag = "@NeonGhost_Networks\n" + caption

        # Ask user to provide the link
        link_msg = "Please provide a link to add in the caption."
        bot.send_message(message.chat.id, link_msg)
        # Store the custom caption in user_data
        user_data[user_id]['caption'] = caption_with_tag
        # Move to the next step
        bot.register_next_step_handler(message, handle_link)
    else:
        # If user data is not found, ask the user to send a video first.
        bot.send_message(message.chat.id, "Please send a video first.")

# Handler to handle the link provided by the user
def handle_link(message):
    # Retrieve user data
    user_id = message.chat.id
    if user_id in user_data:
        extracted_filename = user_data[user_id]['extracted_video']
        caption = user_data[user_id]['caption']
        link = message.text

        # Format the caption with the link
        caption_with_link = f"{caption}\n\n🔗 Video Link is Given Below:\n{link}"

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
