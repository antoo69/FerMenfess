from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import os
import json
from dotenv import load_dotenv
import asyncio

load_dotenv()

# Bot configuration
api_id = os.getenv("API_ID")
api_hash = os.getenv("API_HASH")
bot_token = os.getenv("BOT_TOKEN")
owner_id = int(os.getenv("OWNER_ID"))  # Owner ID
delay_time = int(os.getenv("DELAY"))  # Delay time

# Initialize bot
app = Client("menfess_bot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

# Store data
cooldown_users = []
menfess_groups = {}  # Store group IDs and links
admin_list = []  # Store admin IDs
start_message = '''
Selamat Datang Di **Menfess Bot**

Silahkan kirim pesan teks/foto/video/gif/stiker.

Note: Bot menerima pesan teks, foto, video, gif dan stiker.
'''

async def add_to_cooldown(user_id):
    cooldown_users.append(user_id)
    await asyncio.sleep(delay_time)
    cooldown_users.remove(user_id)

def is_owner(user_id):
    return user_id == owner_id

def is_admin(user_id):
    return user_id in admin_list or user_id == owner_id

@app.on_message(filters.command("start") & filters.private)
async def start_command(client, message):
    user_id = message.from_user.id
    
    if not menfess_groups:
        if is_owner(user_id):
            await message.reply_text("Harap tambahkan grup terlebih dahulu dengan perintah /addgroup")
            return
        else:
            await message.reply_text("Bot belum dikonfigurasi. Hubungi owner bot.")
            return
            
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Channel Menfess", url=list(menfess_groups.values())[0]['link'])]])
    
    # Store user ID for broadcast
    with open("member.db", "a+") as file:
        file.seek(0)
        if str(user_id) not in file.read().splitlines():
            file.write(f"{user_id}\n")
    
    await message.reply_text(start_message, reply_markup=keyboard)

@app.on_message(filters.command("setmessage") & filters.private)
async def set_message_command(client, message):
    if not is_owner(message.from_user.id):
        await message.reply_text("Hanya owner yang dapat menggunakan perintah ini!")
        return
        
    if len(message.command) < 2:
        await message.reply_text("Gunakan format: /setmessage [pesan start baru]")
        return
        
    global start_message
    start_message = " ".join(message.command[1:])
    await message.reply_text("Pesan start berhasil diubah!")

@app.on_message(filters.command("addgroup") & filters.private)
async def add_group_command(client, message):
    if not is_owner(message.from_user.id):
        await message.reply_text("Hanya owner yang dapat menggunakan perintah ini!")
        return
        
    try:
        _, group_name, group_username = message.command
        
        # Get chat info
        chat = await app.get_chat(group_username)
        
        if chat.type not in ["group", "supergroup", "channel"]:
            await message.reply_text("Hanya grup, supergroup, atau channel yang dapat ditambahkan!")
            return
            
        # Check if bot is admin
        bot_member = await app.get_chat_member(chat.id, "me")
        if not bot_member.status == "administrator":
            await message.reply_text("Bot harus menjadi admin di grup/channel tersebut!")
            return
            
        group_link = f"https://t.me/{chat.username}" if chat.username else chat.invite_link
        
        menfess_groups[group_name] = {
            "id": chat.id,
            "link": group_link
        }
        
        await message.reply_text(f"Grup {group_name} berhasil ditambahkan!")
    except Exception as e:
        await message.reply_text("Format: /addgroup [nama_grup] [username/link]\n\nPastikan:\n- Bot sudah menjadi admin\n- Username/link valid\n- Tipe chat adalah grup/supergroup/channel")

@app.on_message(filters.command("addadmin") & filters.private)
async def add_admin_command(client, message):
    if not is_owner(message.from_user.id):
        await message.reply_text("Hanya owner yang dapat menggunakan perintah ini!")
        return
        
    try:
        _, user_id = message.command
        user_id = int(user_id)
        
        if user_id not in admin_list:
            admin_list.append(user_id)
            await message.reply_text(f"Admin dengan ID {user_id} berhasil ditambahkan!")
        else:
            await message.reply_text("User sudah menjadi admin!")
    except:
        await message.reply_text("Format: /addadmin [user_id]")

@app.on_message(filters.command("ping") & filters.private)
async def ping_command(client, message):
    if not is_admin(message.from_user.id):
        await message.reply_text("Hanya admin yang dapat menggunakan perintah ini!")
        return
        
    total_users = len(open("member.db", "r").readlines())
    await message.reply_text(f"Bot Aktif!!!!\nTotal Pengguna Bot: {total_users}")

@app.on_message(filters.command("broadcast") & filters.private)
async def broadcast_command(client, message):
    if not is_admin(message.from_user.id):
        await message.reply_text("Hanya admin yang dapat menggunakan perintah ini!")
        return
        
    await message.reply_text("Masukkan pesan broadcast:")
    
    @app.on_message(filters.private & ~filters.command([]))
    async def broadcast_message(client, broadcast_msg):
        if broadcast_msg.from_user.id == message.from_user.id:
            with open("member.db", "r") as file:
                users = file.read().splitlines()
                for user in users:
                    try:
                        await broadcast_msg.copy(int(user))
                        await asyncio.sleep(0.5)
                    except Exception as e:
                        print(f"Gagal mengirim ke {user}: {str(e)}")
            await message.reply_text("Pesan broadcast berhasil dikirim.")

@app.on_message(filters.private & ~filters.command([]))
async def handle_menfess(client, message):
    user_id = message.from_user.id
    user_mention = message.from_user.mention
    
    if not menfess_groups:
        await message.reply_text("Bot belum dikonfigurasi. Hubungi owner bot.")
        return
    
    caption = message.caption if message.media else None
    text = message.text if message.text else caption
    
    if user_id in cooldown_users:
        await message.reply_text(f"Gagal mengirim!!\n\nKamu baru saja mengirim menfess, beri jarak {delay_time} detik untuk memposting kembali!")
        return
    
    # Kirim notifikasi ke owner & admin
    try:
        notification = f"Ada pesan baru dari: {user_mention}\nUser ID: {user_id}\nIsi pesan: {text}"
        await app.send_message(owner_id, notification)
        for admin_id in admin_list:
            try:
                await app.send_message(admin_id, notification)
            except:
                pass
    except Exception as e:
        print(f"Gagal mengirim notifikasi: {str(e)}")
    
    # Pilihan grup untuk menfess
    buttons = []
    for name, data in menfess_groups.items():
        buttons.append([InlineKeyboardButton(name, callback_data=f"group_{name}:{message.id}")])
    
    keyboard = InlineKeyboardMarkup(buttons)
    await message.reply_text("Pilih grup untuk mengirim menfess:", reply_markup=keyboard)

@app.on_callback_query(filters.regex(r"group_.*:\d+"))
async def on_group_selection(client, callback_query):
    try:
        user_id = callback_query.from_user.id
        group_name, message_id = callback_query.data.split("_")[1].split(":")
        message_id = int(message_id)
        
        original_message = await app.get_messages(user_id, message_id)
        
        if not original_message:
            await callback_query.message.reply_text("Pesan tidak ditemukan. Silakan coba lagi.")
            return
            
        group_data = menfess_groups.get(group_name)
        if not group_data:
            await callback_query.message.reply_text("Grup tidak valid. Silakan coba lagi.")
            return
            
        try:
            await app.get_chat(group_data['id'])
        except Exception as e:
            await callback_query.message.reply_text("Bot belum menjadi admin di grup yang dipilih. Silakan hubungi admin.")
            print(f"Error accessing group {group_data['id']}: {str(e)}")
            return
            
        sent = await original_message.copy(group_data['id'])
        post_link = f"{group_data['link']}/{sent.id}"
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Cek Postingan", url=post_link)]
        ])
        
        await callback_query.message.reply_text("**Menfess Berhasil Diposting!!**",
                                              reply_markup=keyboard)
        await add_to_cooldown(user_id)
        
    except Exception as e:
        print(f"Error in on_group_selection: {str(e)}")
        await callback_query.message.reply_text("Gagal mengirim menfess. Pastikan bot sudah menjadi admin di grup yang dipilih.")

print("\n\nBOT TELAH AKTIF!!!")
app.run()
