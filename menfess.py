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
group1_id = int(os.getenv("GROUP1_ID"))  # Group 1 ID
group2_id = int(os.getenv("GROUP2_ID"))  # Group 2 ID 
group3_id = int(os.getenv("GROUP3_ID"))  # Group 3 ID
group1_link = os.getenv("GROUP1_LINK")  # Group 1 Link
group2_link = os.getenv("GROUP2_LINK")  # Group 2 Link
group3_link = os.getenv("GROUP3_LINK")  # Group 3 Link
admin_list = json.loads(os.getenv("ADMIN"))  # Admin list
delay_time = int(os.getenv("DELAY"))  # Delay time
owner_id = int(os.getenv("OWNER_ID"))  # Owner ID

# Initialize bot
app = Client("menfess_bot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

# Store cooldown users
cooldown_users = []

# Welcome message
start_message = '''
Selamat Datang Di **Ferdi Menfess**

kamu bebas mengirim menfess pada channel support by ferdi, silahkan kirim pesan teks/foto/video/gif/stiker.

Note: Bot menerima pesan teks, foto, video, gif dan stiker.
'''

async def add_to_cooldown(user_id):
    cooldown_users.append(user_id)
    await asyncio.sleep(delay_time)
    cooldown_users.remove(user_id)

@app.on_message(filters.command(["start"]) & filters.private)
async def start_command(client, message):
    user_id = message.from_user.id
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Channel Menfess", url=group1_link)]])
    
    # Store user ID for broadcast
    with open("member.db", "a+") as file:
        file.seek(0)
        if str(user_id) not in file.read().splitlines():
            file.write(f"{user_id}\n")
    
    await message.reply_text(start_message, reply_markup=keyboard)

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

@app.on_message(filters.private & ~filters.command(["broadcast", "start", "ping"]))
async def handle_menfess(client, message):
    user_id = message.from_user.id
    user_mention = message.from_user.mention
    
    caption = message.caption if message.media else None
    text = message.text if message.text else caption
    
    if user_id in cooldown_users:
        await message.reply_text(f"Gagal mengirim!!\n\nKamu baru saja mengirim menfess, beri jarak {delay_time} detik untuk memposting kembali!")
        return
    
    # Kirim notifikasi ke owner
    try:
        await app.send_message(owner_id, f"Ada pesan baru dari: {user_mention}\nUser ID: {user_id}\nIsi pesan: {text}")
    except Exception as e:
        print(f"Gagal mengirim notifikasi ke owner: {str(e)}")
    
    # Pilihan grup untuk menfess
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Group 1", callback_data=f"group1:{message.id}"),
         InlineKeyboardButton("Group 2", callback_data=f"group2:{message.id}"),
         InlineKeyboardButton("Group 3", callback_data=f"group3:{message.id}")]
    ])
    
    await message.reply_text("Pilih grup untuk mengirim menfess:", reply_markup=keyboard)

@app.on_callback_query(filters.regex(r"group[1-3]:\d+"))
async def on_group_selection(client, callback_query):
    try:
        user_id = callback_query.from_user.id
        selected_group, message_id = callback_query.data.split(":")
        message_id = int(message_id)
        
        # Get the original message using message_id
        original_message = await app.get_messages(user_id, message_id)
        
        if not original_message:
            await callback_query.message.reply_text("Pesan tidak ditemukan. Silakan coba lagi.")
            return
            
        group_id = {
            "group1": group1_id,
            "group2": group2_id,
            "group3": group3_id
        }.get(selected_group)
        
        if not group_id:
            await callback_query.message.reply_text("Grup tidak valid. Silakan coba lagi.")
            return
            
        # Make sure bot is member of the group first
        try:
            await app.get_chat(group_id)
        except Exception as e:
            await callback_query.message.reply_text("Bot belum menjadi admin di grup yang dipilih. Silakan hubungi admin.")
            print(f"Error accessing group {group_id}: {str(e)}")
            return
            
        # Copy message with media if exists
        sent = await original_message.copy(group_id)
        
        group_links = {
            "group1": group1_link,
            "group2": group2_link,
            "group3": group3_link
        }
        post_link = f"{group_links[selected_group]}/{sent.id}"
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Cek Postingan", url=post_link)]
        ])
        
        await callback_query.message.reply_text("**Menfess Berhasil Diposting!!**",
                                              reply_markup=keyboard)
        await add_to_cooldown(user_id)
        
    except Exception as e:
        print(f"Error in on_group_selection: {str(e)}")
        await callback_query.message.reply_text("Gagal mengirim menfess. Pastikan bot sudah menjadi admin di grup yang dipilih.")

print("\n\nBOT TELAH AKTIF!!! @GARZPROJECT")
app.run()
