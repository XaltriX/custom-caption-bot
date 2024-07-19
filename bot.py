import os
import cv2
import asyncio
import re
import aiohttp
import numpy as np
from PIL import Image
from moviepy.editor import VideoFileClip
from telethon import TelegramClient, events, Button
from telethon.tl.types import InputMediaUploadedPhoto
from telethon.tl.functions.messages import UploadMediaRequest

API_ID = 28192191
API_HASH = '663164abd732848a90e76e25cb9cf54a'
BOT_TOKEN = '7147998933:AAGxVDx1pxyM8MVYvrbm3Nb8zK6DgI1H8RU'
THUMBNAIL_URL = 'https://telegra.ph/file/cab0b607ce8c4986e083c.jpg'

client = TelegramClient('bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)
user_data = {}

@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    buttons = [
        [Button.inline("Custom Caption", data="custom_caption"),
         Button.inline("TeraBox Editor", data="terabox_editor")],
        [Button.inline("Cancel", data="cancel")]
    ]
    await event.reply("Welcome! Please choose a feature:", buttons=buttons)

@client.on(events.CallbackQuery())
async def handle_callback(event):
    data = event.data.decode('utf-8')
    chat_id = event.chat_id

    if data == "cancel":
        if chat_id in user_data:
            del user_data[chat_id]
        await event.edit("Process cancelled. Send /start to begin again.")
        return

    if data == "custom_caption":
        buttons = [
            [Button.inline("Manual Preview", data="manual_preview"),
             Button.inline("Auto Preview", data="auto_preview")],
            [Button.inline("Cancel", data="cancel")]
        ]
        await event.edit("Please choose preview type:", buttons=buttons)

    elif data == "terabox_editor":
        user_data[chat_id] = {"state": "terabox_editor"}
        await event.edit("Please send one or more images, videos, or GIFs with TeraBox links in the captions.")

    elif data == "manual_preview":
        user_data[chat_id] = {"state": "manual_preview"}
        await event.edit("Please provide the manual preview link:")

    elif data == "auto_preview":
        user_data[chat_id] = {"state": "auto_preview"}
        await event.edit("Please send a video to generate the preview.")

@client.on(events.NewMessage(func=lambda e: e.message.video))
async def handle_video(event):
    chat_id = event.chat_id
    if chat_id not in user_data or user_data[chat_id].get("state") != "auto_preview":
        return

    progress_message = await event.reply("Processing your video...")
    try:
        video = event.message.video
        file = await client.download_media(video, file="temp_video", progress_callback=lambda d, t: asyncio.ensure_future(update_progress(d, t, progress_message)))
        await progress_message.edit("Generating screenshots...")
        screenshots = await generate_screenshots(file, progress_message)
        collage = create_collage(screenshots)
        collage_path = f"{file}_collage.jpg"
        collage.save(collage_path, optimize=True, quality=95)
        await progress_message.edit("Uploading to graph.org...")
        graph_url = await upload_to_graph(collage_path, progress_message)
        user_data[chat_id]["preview_link"] = graph_url
        user_data[chat_id]["state"] = "waiting_caption"
        await progress_message.edit("Preview generated. Please provide a custom caption for the video.")
    except Exception as e:
        await event.reply(f"An error occurred: {str(e)}")
    finally:
        if os.path.exists(file):
            os.unlink(file)
        if os.path.exists(collage_path):
            os.unlink(collage_path)

async def update_progress(current, total, message):
    percent = round(current / total * 100, 1)
    await message.edit(f"Downloading video: {percent}%")

async def generate_screenshots(video_file, message):
    clip = VideoFileClip(video_file)
    duration = clip.duration
    num_screenshots = 5 if duration < 60 else 10
    time_points = np.linspace(0, duration, num_screenshots, endpoint=False)
    screenshots = []
    for i, time_point in enumerate(time_points):
        frame = clip.get_frame(time_point)
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        screenshot = Image.fromarray(frame)
        screenshots.append(screenshot)
        progress = int((i + 1) / num_screenshots * 100)
        await message.edit(f"Generating screenshots: {progress}%")
    clip.close()
    return screenshots

def create_collage(screenshots):
    cols = 2
    rows = (len(screenshots) + 1) // 2
    collage_width = 640 * cols
    collage_height = 360 * rows
    collage = Image.new('RGB', (collage_width, collage_height))
    for i, screenshot in enumerate(screenshots):
        x = (i % cols) * 640
        y = (i // cols) * 360
        collage.paste(screenshot.resize((640, 360)), (x, y))
    return collage

async def upload_to_graph(image_path, message):
    url = "https://graph.org/upload"
    async with aiohttp.ClientSession() as session:
        with open(image_path, "rb") as file:
            data = aiohttp.FormData()
            data.add_field('file', file)
            async with session.post(url, data=data) as response:
                if response.status == 200:
                    data = await response.json()
                    if data[0].get("src"):
                        return f"https://graph.org{data[0]['src']}"
                    else:
                        raise Exception("Unable to retrieve image link from response")
                else:
                    raise Exception(f"Upload failed with status code {response.status}")

@client.on(events.NewMessage(func=lambda e: e.text and not e.text.startswith('/')))
async def handle_text(event):
    chat_id = event.chat_id
    if chat_id in user_data:
        state = user_data[chat_id].get("state")
        if state == "manual_preview":
            user_data[chat_id]["preview_link"] = event.text
            user_data[chat_id]["state"] = "waiting_caption"
            await event.reply("Please provide a custom caption for the video.")
        elif state == "waiting_caption":
            user_data[chat_id]["caption"] = event.text
            user_data[chat_id]["state"] = "waiting_link"
            await event.reply("Please provide a link to add in the caption.")
        elif state == "waiting_link":
            await create_final_post(event, chat_id, event.text)
        else:
            await event.reply("Please start the process by sending /start.")

async def create_final_post(event, chat_id, link):
    preview_link = user_data[chat_id]["preview_link"]
    caption = user_data[chat_id]["caption"]
    formatted_caption = (
        f"◇──◆──◇──◆ ◇──◆──◇──◆\n"
        f" @NeonGhost_Networks\n"
        f"◇──◆──◇──◆ ◇──◆──◇──◆\n\n"
        f"╰┈┈➤ 🚨 {caption} 🚨\n\n"
        f"╰┈┈┈┈┈➤ 🔗 Preview Link: {preview_link}\n\n"
        f"╰┈┈┈┈┈┈┈┈➤ 💋 🔗🤞 Full Video Link: {link} 🔞🤤\n"
    )

    # Download the thumbnail
    async with aiohttp.ClientSession() as session:
        async with session.get(THUMBNAIL_URL) as response:
            if response.status == 200:
                thumbnail_data = await response.read()
                thumbnail_file = await client.upload_file(thumbnail_data, file_name="thumbnail.jpg")
            else:
                await event.reply("Failed to download thumbnail. Using default image.")
                thumbnail_file = None

    # Upload the thumbnail
    if thumbnail_file:
        uploaded_thumb = await client(UploadMediaRequest(
            peer=chat_id,
            media=InputMediaUploadedPhoto(thumbnail_file)
        ))
    else:
        uploaded_thumb = None

    # Send the message with the uploaded thumbnail
    buttons = [
        [Button.url("How To Watch & Download 🔞", "https://t.me/HTDTeraBox/5")],
        [Button.url("Movie Group🔞🎥", "https://t.me/RequestGroupNG")],
        [Button.url("BackUp Channel🎯", "https://t.me/+ZgpjbYx8dGZjODI9")]
    ]

    if uploaded_thumb:
        await client.send_message(chat_id, formatted_caption, file=uploaded_thumb.photo, buttons=buttons)
    else:
        await client.send_message(chat_id, formatted_caption, buttons=buttons)

    # Reset user data
    del user_data[chat_id]
    await event.reply("Your post has been created. Send /start to begin again.")

@client.on(events.NewMessage(func=lambda e: e.photo or e.video or (e.document and e.document.mime_type == 'image/gif')))
async def handle_media(event):
    chat_id = event.chat_id
    if chat_id not in user_data or user_data[chat_id].get("state") != "terabox_editor":
        return

    if event.photo:
        media_type = 'photo'
        file_attr = event.photo
    elif event.video:
        media_type = 'video'
        file_attr = event.video
    else:  # GIF
        media_type = 'gif'
        file_attr = event.document

    caption = event.message.caption
    if not caption:
        await event.reply("No caption provided. Please try again with a caption containing TeraBox links.")
        return

    terabox_links = re.findall(r'https?://\S*terabox\S*', caption, re.IGNORECASE)
    if not terabox_links:
        await event.reply("No valid TeraBox link found in the caption. Please try again.")
        return

    formatted_caption = (
        f"⚝─────⭒─⭑─⭒──────⚝\n"
        " 👉 🇼🇪🇱🇨🇴🇲🇪❗ 👈\n"
        " ⚝─────⭒─⭑─⭒──────⚝\n\n"
        "≿━━━━━━━༺❀༻━━━━━━≾\n"
        f"📥 𝐉𝐎𝐈𝐍 𝐔𝐒 :– @NeonGhost_Networks\n"
        "≿━━━━━━━༺❀༻━━━━━━≾\n\n"
    )

    if len(terabox_links) == 1:
        formatted_caption += f"➽───❥🔗𝐅𝐮𝐥𝐥 𝐕𝐢𝐝𝐞𝐨 𝐋𝐢𝐧𝐤:🔗 {terabox_links[0]}\n\n"
    else:
        for idx, link in enumerate(terabox_links, start=1):
            formatted_caption += f"➽───❥🔗𝐕𝐢𝐝𝐞𝐨 𝐋𝐢𝐧𝐤 {idx}:🔗 {link}\n\n"

    formatted_caption += "─❚█═𝑩𝒚 𝑵𝒆𝒐𝒏𝑮𝒉𝒐𝒔𝒕 𝑵𝒆𝒕𝒘𝒐𝒓𝒌𝒔═█❚─"

    buttons = [
        [Button.url("How To Watch & Download 🔞", "https://t.me/HTDTeraBox/5")],
        [Button.url("Movie Group🔞🎥", "https://t.me/RequestGroupNG")],
        [Button.url("BackUp Channel🎯", "https://t.me/+ZgpjbYx8dGZjODI9")]
    ]

    await client.send_file(
        chat_id,
        file=file_attr,
        caption=formatted_caption,
        buttons=buttons,
        link_preview=False
    )

    del user_data[chat_id]
    await event.reply("Your post has been created. Send /start to begin again.")

print("Bot is running...")
client.run_until_disconnected()
