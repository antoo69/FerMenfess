from pyrogram.types import Message  # <-- Tambahkan ini
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import os
import json
from dotenv import load_dotenv
import asyncio
from pyrogram.enums import ChatType, ChatMemberStatus
import time
from time import time
from datetime import datetime, timedelta

load_dotenv()
# Waktu mulai bot dalam UTC dan WIB
START_TIME_UTC = datetime.utcnow()
START_TIME_WIB = START_TIME_UTC + timedelta(hours=7)
START_TIME_WIB_ISO = START_TIME_WIB.replace(microsecond=0).isoformat()

# Konstanta durasi waktu
TIME_DURATION_UNITS = (
    ("week", 60 * 60 * 24 * 7),
    ("day", 60**2 * 24),
    ("hour", 60**2),
    ("min", 60),
    ("sec", 1),
)

# Bot configuration
api_id = os.getenv("API_ID")
api_hash = os.getenv("API_HASH")
bot_token = os.getenv("BOT_TOKEN")
owner_id = int(os.getenv("OWNER_ID"))  # Owner ID
delay_time = int(os.getenv("DELAY"))  # Delay time

# Initialize bot
app = Client("menfess_bot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

async def _human_time_duration(seconds):
    """Mengonversi detik ke format durasi waktu yang lebih mudah dibaca."""
    if seconds == 0:
        return "inf"
    parts = []
    for unit, div in TIME_DURATION_UNITS:
        amount, seconds = divmod(int(seconds), div)
        if amount > 0:
            parts.append(f'{amount} {unit}{"" if amount == 1 else "s"}')
    return ", ".join(parts)

# Store data
cooldown_users = {}  # Dict to store cooldown users per group
menfess_groups = {}  # Store group IDs and links
user_ids = set()  # Store user IDs for broadcast
start_message = start_message = '''
Selamat Datang Di **Ferdi Menfes Bot**

🔰 Cara Penggunaan Bot:
• Tambahkan bot ini ke grup/channel Anda
• Bot akan otomatis aktif setelah ditambahkan
• Anda dapat mengirim menfess ke grup/channel yang sama dengan bot

📝 Jenis Pesan yang Didukung:
• Teks
• Foto 
• Video
• GIF
• Stiker
• Pesan Suara (Tanpa Limit)

ℹ️ Informasi Tambahan:
• Bot dapat digunakan di grup dan channel
• Untuk channel, hanya admin yang dapat mengirim menfess
• Bot ini GRATIS tanpa biaya apapun

• Info bot lain bisa kunjungi @Galerifsyrl

Silakan mulai mengirim pesan menfess Anda!
'''


# Store message references
message_refs = {}

# Create data directory if not exists
os.makedirs("data", exist_ok=True)

# Load existing groups from data directory
def load_existing_groups():
    for item in os.listdir("data"):
        group_path = os.path.join("data", item)
        if os.path.isdir(group_path):
            group_info_path = os.path.join(group_path, "group_info.json")
            if os.path.exists(group_info_path):
                try:
                    with open(group_info_path, "r") as f:
                        group_data = json.load(f)
                        menfess_groups[str(group_data['id'])] = group_data
                except Exception as e:
                    print(f"Error loading group data from {group_info_path}: {str(e)}")

# Load existing groups on startup
load_existing_groups()

async def add_to_cooldown(group_id, user_id):
    if group_id not in cooldown_users:
        cooldown_users[group_id] = []
    cooldown_users[group_id].append(user_id)
    await asyncio.sleep(delay_time)
    cooldown_users[group_id].remove(user_id)

def is_owner(user_id):
    return user_id == owner_id

async def is_group_member(client, user_id, chat_id):
    try:
        member = await client.get_chat_member(chat_id, user_id)
        return member.status not in [ChatMemberStatus.LEFT, ChatMemberStatus.BANNED]
    except:
        return False

async def is_channel_admin(client, user_id, chat_id):
    try:
        member = await client.get_chat_member(chat_id, user_id)
        return member.status in [ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR]
    except:
        return False

@app.on_chat_member_updated()
async def handle_chat_member_updated(client, chat_member_updated):
    chat = chat_member_updated.chat
    new_member = chat_member_updated.new_chat_member
    
    if new_member and new_member.user.id == app.me.id:
        # Bot was added to a group/channel
        try:
            chat_info = await client.get_chat(chat.id)
            if chat_info.type in [ChatType.GROUP, ChatType.SUPERGROUP, ChatType.CHANNEL]:
                # Get invite link
                invite_link = await chat_info.export_invite_link()
                
                # Store group info
                menfess_groups[str(chat.id)] = {
                    'id': chat.id,
                    'title': chat.title,
                    'link': invite_link,
                    'type': str(chat_info.type)  # Store chat type
                }
                
                # Save to group-specific database
                os.makedirs(f"data/{chat.id}", exist_ok=True)
                with open(f"data/{chat.id}/group_info.json", "w") as f:
                    json.dump(menfess_groups[str(chat.id)], f)
                    
                print(f"Bot added to {chat.title} ({chat.id})")
                
        except Exception as e:
            print(f"Error handling new chat member: {str(e)}")

@app.on_message(filters.command("broadcast") & filters.private)
async def broadcast_command(client, message):
    if not is_owner(message.from_user.id):
        await message.reply_text("Maaf, hanya owner bot yang dapat menggunakan perintah ini.")
        return
        
    if len(message.command) < 2 and not message.reply_to_message:
        await message.reply_text("Silakan balas ke pesan yang ingin disiarkan atau ketik pesan setelah /broadcast")
        return
        
    broadcast_message = message.reply_to_message if message.reply_to_message else message
    
    if len(message.command) >= 2:
        broadcast_text = " ".join(message.command[1:])
    else:
        broadcast_text = broadcast_message.text or broadcast_message.caption or ""
    
    success_count = 0
    fail_count = 0
    
    progress_msg = await message.reply_text("Memulai broadcast...")
    
    for user_id in user_ids:
        try:
            if broadcast_message.media:
                await broadcast_message.copy(user_id)
            else:
                await client.send_message(user_id, broadcast_text)
            success_count += 1
        except Exception as e:
            print(f"Failed to send broadcast to {user_id}: {str(e)}")
            fail_count += 1
            
        # Update progress every 5 users
        if (success_count + fail_count) % 5 == 0:
            await progress_msg.edit_text(
                f"Progress: {success_count + fail_count}/{len(user_ids)}\n"
                f"Berhasil: {success_count}\n"
                f"Gagal: {fail_count}"
            )
    
    await progress_msg.edit_text(
        f"Broadcast selesai!\n"
        f"Total: {len(user_ids)}\n"
        f"Berhasil: {success_count}\n"
        f"Gagal: {fail_count}"
    )

@app.on_message(filters.command("start") & filters.private)
async def start_command(client, message):
    user_ids.add(message.from_user.id)
    await message.reply_text(start_message)

@app.on_message(filters.command("ping") & (filters.private | filters.group))
async def ping_pong(client: Client, message: Message):
    if message.from_user and message.from_user.is_bot:
        return  # Abaikan jika pesan dikirim oleh bot sendiri

    start = time()
    current_time = datetime.utcnow()
    uptime_sec = (current_time - START_TIME_UTC).total_seconds()
    uptime = await _human_time_duration(int(uptime_sec))
    
    m_reply = await message.reply_text("Pinging...")
    delta_ping = time() - start
    
    await m_reply.edit(
        "**PONG!!** 🏓\n"
        f"**• Pinger -** `{delta_ping * 1000:.3f} ms`\n"
        f"**• Uptime -** `{uptime}`"
    )

@app.on_message(filters.command("time") & filters.private | filters.group  )
async def get_uptime(client: Client, message: Message):
    """Menangani perintah /time untuk menampilkan uptime dan waktu mulai bot."""
    current_time_utc = datetime.utcnow()
    current_time_wib = current_time_utc + timedelta(hours=7)
    uptime_sec = (current_time_utc - START_TIME_UTC).total_seconds()
    uptime = await _human_time_duration(int(uptime_sec))
    
    await message.reply_text(
        "🤖 **Bot Status:**\n"
        f"• **Uptime:** `{uptime}`\n"
        f"• **Start Time:** `{START_TIME_WIB_ISO}` (WIB)\n"
        f"• **Current UTC Time:** `{current_time_utc.replace(microsecond=0)}`\n"
        f"• **Current WIB Time:** `{current_time_wib.replace(microsecond=0)}`\n"
    )

@app.on_message(filters.private & ~filters.command(["start", "ping", "broadcast"]))
async def handle_private_message(client, message):
    user_id = message.from_user.id
    user_ids.add(user_id)
    
    # Create buttons for groups where user is a member
    buttons = []
    for group_id, group_data in menfess_groups.items():
        # For channels, check if user is admin
        if group_data.get('type') == str(ChatType.CHANNEL):
            if await is_channel_admin(client, user_id, group_data['id']):
                buttons.append([InlineKeyboardButton(
                    f"💌 Kirim Menfess ke {group_data['title']}", 
                    callback_data=f"send_menfess_{group_id}"
                )])
        # For groups, check if user is member
        else:
            if await is_group_member(client, user_id, group_data['id']):
                buttons.append([InlineKeyboardButton(
                    f"💌 Kirim Menfess ke {group_data['title']}", 
                    callback_data=f"send_menfess_{group_id}"
                )])
    
    if not buttons:
        await message.reply_text("Anda tidak mempunyai group yang sama dengan bot ini\ntolong tambahkan bot ini kedalam group anda\nagar anda bisa mengirim menfess")
        return
        
    keyboard = InlineKeyboardMarkup(buttons)
    
    # Store the original message reference
    msg = await message.reply_text("Pilih grup/channel tujuan menfess:", reply_markup=keyboard)
    message_refs[msg.id] = message

@app.on_callback_query()
async def on_group_selection(client, callback_query):
    try:
        user_id = callback_query.from_user.id
        data = callback_query.data
        
        if not data.startswith("send_menfess_"):
            return
            
        group_id = data.replace("send_menfess_", "")
        
        # Check if group/channel exists
        group_data = menfess_groups.get(group_id)
        if not group_data:
            await callback_query.message.reply_text("Grup/Channel tidak valid. Silakan coba lagi.")
            return
            
        # Check permissions based on chat type
        if group_data.get('type') == str(ChatType.CHANNEL):
            is_authorized = await is_channel_admin(client, user_id, group_data['id'])
            if not is_authorized:
                await callback_query.message.reply_text(
                    f"Anda bukan admin dari channel {group_data['title']}. "
                    "Hanya admin yang dapat mengirim menfess ke channel."
                )
                return
        else:
            is_member = await is_group_member(client, user_id, group_data['id'])
            if not is_member:
                await callback_query.message.reply_text(
                    f"Anda bukan anggota dari group {group_data['title']} ({group_data['id']}), "
                    "mohon bergabung ke dalam group yang ingin anda kirimkan menfes agar bisa memakai bot ini"
                )
                return
        
        # Check if user is in cooldown
        if group_id in cooldown_users and user_id in cooldown_users[group_id]:
            await callback_query.message.reply_text(f"Mohon tunggu {delay_time} detik sebelum mengirim menfess lagi.")
            return
            
        # Get the original message
        original_message = message_refs.get(callback_query.message.id)
        if not original_message:
            await callback_query.message.reply_text("Pesan tidak ditemukan. Silakan coba lagi.")
            return
            
        try:
            # Send message to group/channel
            sent = await original_message.copy(group_data['id'])
            
            # Create permanent message link
            chat = await client.get_chat(group_data['id'])
            if chat.username:
                post_link = f"https://t.me/{chat.username}/{sent.id}"
            else:
                post_link = f"https://t.me/c/{str(group_data['id'])[4:]}/{sent.id}"
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("Cek Postingan", url=post_link)]
            ])
            
            await callback_query.message.reply_text(
                "**Menfess Berhasil Diposting!!**",
                reply_markup=keyboard
            )
            
            # Send notification to owner with message content
            user = callback_query.from_user
            message_text = original_message.text if original_message.text else "[Media Message]"
            owner_notification = f"""
New Menfess Sent!
Username: @{user.username if user.username else 'None'}
Name: {user.first_name} {user.last_name if user.last_name else ''}
User ID: {user.id}
Group/Channel: {group_data['title']}
Message: {message_text}
"""
            await client.send_message(owner_id, owner_notification)
            
            # If original message contains media, forward it to owner
            if original_message.media:
                await original_message.copy(owner_id)
            
            # Add user to cooldown
            await add_to_cooldown(group_id, user_id)
            
            # Clean up message reference
            del message_refs[callback_query.message.id]
            
        except Exception as e:
            print(f"Error sending menfess: {str(e)}")
            await callback_query.message.reply_text(
                "Gagal mengirim menfess. Pastikan bot sudah menjadi admin di grup/channel yang dipilih."
            )
            
    except Exception as e:
        print(f"Error in callback: {str(e)}")
        await callback_query.message.reply_text("Terjadi kesalahan. Silakan coba lagi.")

print("\n\nBOT TELAH AKTIF!!!")
app.run()
