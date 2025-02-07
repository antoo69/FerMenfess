###########################################
# Garz Menfess Telegram Bot
# Tegar Prayuda | Hak Cipta
# Tolong Hargai Pembuat Script Ini
# Recode ? Cantumin Source
# join t.me/GarzProject
# contact : t.me/tegarprayuda
# Jual Source  Code Menfess Bot Full Fitur 
# github.com/GarzProject/MenfessTelegramBot
###########################################

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import time
import os
import json
from dotenv import load_dotenv
import asyncio

load_dotenv()

# Bot configuration
api_id = "your_api_id"
api_hash = "your_api_hash" 
bot_token = os.getenv("6785563845:AAH-WSJ_KNEjC3QQECkNdRXvqy1pXejP9Ek")
channel_id = os.getenv("-1002236001760")
channel_link = os.getenv("t.me/BestieVirtual")
admin_list = json.loads(os.getenv("ADMIN"))
trigger_tags = json.loads(os.getenv("TAG"))
delay_time = int(os.getenv("DELAY"))

# Initialize bot
app = Client("menfess_bot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

# Store cooldown users
cooldown_users = []

# Welcome message
start_message = '''
Selamat Datang Di *Ferdi Menfess*

kamu bebas mengirim menfess pada channel support by ferdi, jika ingin memposting menfess silahkan kirim pesan teks beserta tag dibawah ini:

{}
'''

async def add_to_cooldown(user_id):
    cooldown_users.append(user_id)
    await asyncio.sleep(delay_time)
    cooldown_users.remove(user_id)

def check_trigger(text):
    for word in text.split():
        if any(tag in word for tag in trigger_tags):
            return True
    return False

@app.on_message(filters.command(["start", "broadcast", "ping"]) & filters.private)
async def handle_commands(client, message):
    user_id = message.from_user.id
    
    # Store user ID for broadcast
    with open("member.db", "a+") as file:
        file.seek(0)
        if str(user_id) not in file.read().splitlines():
            file.write(f"{user_id}\n")
    
    if message.text.startswith("/start"):
        tags = '\n'.join(trigger_tags)
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("Channel Menfess", url=channel_link)
        ]])
        await message.reply_text(start_message.format(tags), 
                               reply_markup=keyboard,
                               parse_mode="markdown")
    
    elif message.text.startswith("/ping"):
        total_users = len(open("member.db", "r").readlines())
        await message.reply_text(f"Bot Aktif!!!!\nTotal Pengguna Bot: {total_users}")
    
    elif message.text.startswith("/broadcast"):
        if user_id in admin_list:
            await message.reply_text("Masukan Pesan Broadcast:")
            @app.on_message(filters.private & ~filters.command)
            async def broadcast_message(client, broadcast_msg):
                if broadcast_msg.from_user.id == user_id:
                    with open("member.db", "r") as file:
                        users = file.read().splitlines()
                        for user in users:
                            try:
                                await broadcast_msg.copy(int(user))
                                await asyncio.sleep(0.5)
                            except Exception as e:
                                print(f"Failed to send to {user}: {str(e)}")
                    await message.reply_text("Pesan broadcast berhasil dikirim.")

@app.on_message(filters.private & filters.text & ~filters.command)
async def handle_menfess(client, message):
    user_id = message.from_user.id
    text = message.text
    words = len(text.split())
    
    if user_id in cooldown_users:
        await message.reply_text(f"Gagal mengirim!!\n\nKamu baru saja mengirim menfess, beri jarak {delay_time} detik untuk memposting kembali!")
        return
        
    if words < 3:
        await message.reply_text("Gagal mengirim!!\n\nTidak boleh kurang dari 3 kata!!")
        return
        
    if not check_trigger(text):
        tags = '\n'.join(trigger_tags)
        await message.reply_text(f"Gagal mengirim!!\n\nHarap gunakan tag dibawah ini:\n{tags}")
        return
        
    try:
        sent = await app.send_message(channel_id, text)
        post_link = f"{channel_link}/{sent.id}"
        comment_link = f"{post_link}?comment={sent.id}"
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("Cek Postingan", url=post_link),
                InlineKeyboardButton("Cek Komentar", url=comment_link)
            ]
        ])
        
        await message.reply_text("*Menfess Berhasil Diposting!!*",
                               parse_mode="markdown",
                               reply_markup=keyboard)
                               
        await add_to_cooldown(user_id)
        
    except Exception as e:
        await message.reply_text("Gagal mengirim menfess. Silakan coba lagi.")

print("\n\nBOT TELAH AKTIF!!! @GARZPROJECT")
app.run()
