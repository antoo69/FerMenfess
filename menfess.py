from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import os
import json
from dotenv import load_dotenv
import asyncio

load_dotenv()

# Bot configuration (semua diambil dari file .env)
api_id = os.getenv("API_ID")
api_hash = os.getenv("API_HASH")
bot_token = os.getenv("BOT_TOKEN")
group1_id = os.getenv("GROUP1_ID")  # Group 1 ID
group2_id = os.getenv("GROUP2_ID")  # Group 2 ID
group3_id = os.getenv("GROUP3_ID")  # Group 3 ID
group1_link = os.getenv("GROUP1_LINK")  # Group 1 Link
group2_link = os.getenv("GROUP2_LINK")  # Group 2 Link
group3_link = os.getenv("GROUP3_LINK")  # Group 3 Link
admin_list = json.loads(os.getenv("ADMIN"))  # Admin list
trigger_tags = json.loads(os.getenv("TAG"))  # Trigger tags
delay_time = int(os.getenv("DELAY"))  # Delay time
owner_id = int(os.getenv("OWNER_ID"))  # Owner ID

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

@app.on_message(filters.command(["start"]) & filters.private)
async def start_command(client, message):
    user_id = message.from_user.id
    tags = '\n'.join(trigger_tags)
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Channel Menfess", url=group1_link)]])
    
    # Store user ID for broadcast
    with open("member.db", "a+") as file:
        file.seek(0)
        if str(user_id) not in file.read().splitlines():
            file.write(f"{user_id}\n")
    
    await message.reply_text(start_message.format(tags), 
                             reply_markup=keyboard,
                             parse_mode="markdown")

# Perintah Ping - hanya untuk owner
@app.on_message(filters.command(["ping"]) & filters.private)
async def ping_command(client, message):
    user_id = message.from_user.id
    if user_id == owner_id:  # Hanya owner yang bisa menggunakan
        total_users = len(open("member.db", "r").readlines())
        await message.reply_text(f"Bot Aktif!!!!\nTotal Pengguna Bot: {total_users}")
    else:
        await message.reply_text("Kamu tidak memiliki izin untuk menggunakan perintah ini.")

# Perintah Broadcast - hanya untuk owner
@app.on_message(filters.command(["broadcast"]) & filters.private)
async def broadcast_command(client, message):
    user_id = message.from_user.id
    if user_id == owner_id:  # Hanya owner yang bisa menggunakan
        await message.reply_text("Masukkan pesan broadcast:")
        
        @app.on_message(filters.private & ~filters.command(["broadcast", "start", "ping"]))
        async def broadcast_message(client, broadcast_msg):
            if broadcast_msg.from_user.id == owner_id:  # Verifikasi ulang jika owner
                with open("member.db", "r") as file:
                    users = file.read().splitlines()
                    for user in users:
                        try:
                            await broadcast_msg.copy(int(user))
                            await asyncio.sleep(0.5)
                        except Exception as e:
                            print(f"Gagal mengirim ke {user}: {str(e)}")
                await message.reply_text("Pesan broadcast berhasil dikirim.")
    else:
        await message.reply_text("Kamu tidak memiliki izin untuk menggunakan perintah ini.")

@app.on_message(filters.private & filters.text & ~filters.command(["broadcast", "start", "ping"]))
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
    
    # Pilihan grup untuk menfess
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Group 1", callback_data="group1"),
         InlineKeyboardButton("Group 2", callback_data="group2"),
         InlineKeyboardButton("Group 3", callback_data="group3")]
    ])
    
    await message.reply_text("Pilih grup untuk mengirim menfess:", reply_markup=keyboard)

@app.on_callback_query(filters.regex(r"group[1-3]"))
async def on_group_selection(client, callback_query):
    user_id = callback_query.from_user.id
    selected_group = callback_query.data
    message = callback_query.message
    
    group_id = {
        "group1": group1_id,
        "group2": group2_id,
        "group3": group3_id
    }[selected_group]
    
    try:
        sent = await app.send_message(group_id, message.reply_to_message.text)
        group_links = {
            "group1": group1_link,
            "group2": group2_link,
            "group3": group3_link
        }
        post_link = f"{group_links[selected_group]}/{sent.id}"
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Cek Postingan", url=post_link)]
        ])
        
        await callback_query.message.reply_text("*Menfess Berhasil Diposting!!*",
                                                parse_mode="markdown",
                                                reply_markup=keyboard)
        await add_to_cooldown(user_id)
        
    except Exception as e:
        await callback_query.message.reply_text("Gagal mengirim menfess. Silakan coba lagi.")

print("\n\nBOT TELAH AKTIF!!! @GARZPROJECT")
app.run()
