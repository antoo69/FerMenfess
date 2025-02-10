from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import os
import json
from dotenv import load_dotenv
import asyncio
from pyrogram.enums import ChatType, ChatMemberStatus
import time

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
cooldown_users = {}  # Dict to store cooldown users per group
menfess_groups = {}  # Store group IDs and links
start_message = '''
Selamat Datang Di **Menfess Bot**

Silahkan kirim pesan teks/foto/video/gif/stiker.

Note: Bot menerima pesan teks, foto, video, gif dan stiker.
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
                    'link': invite_link
                }
                
                # Save to group-specific database
                os.makedirs(f"data/{chat.id}", exist_ok=True)
                with open(f"data/{chat.id}/group_info.json", "w") as f:
                    json.dump(menfess_groups[str(chat.id)], f)
                    
                print(f"Bot added to {chat.title} ({chat.id})")
                
        except Exception as e:
            print(f"Error handling new chat member: {str(e)}")

@app.on_message(filters.command("ping") & filters.private)
async def ping_command(client, message):
    start = time.time()
    reply = await message.reply_text("Pong!")
    end = time.time()
    await reply.edit_text(f"Pong! `{round((end-start)*1000)}ms`")

@app.on_message(filters.command("start") & filters.private)
async def start_command(client, message):
    await message.reply_text(start_message)

@app.on_message(filters.private & ~filters.command(["start", "ping"]))
async def handle_private_message(client, message):
    user_id = message.from_user.id
    
    # Create buttons for groups where user is a member
    buttons = []
    for group_id, group_data in menfess_groups.items():
        # Check if user is member of the group
        if await is_group_member(client, user_id, group_data['id']):
            buttons.append([InlineKeyboardButton(
                f"💌 Kirim Menfess ke {group_data['title']}", 
                callback_data=f"send_menfess_{group_id}"
            )])
    
    if not buttons:
        await message.reply_text("Anda harus menjadi anggota grup untuk mengirim menfess. Silakan bergabung dengan grup terlebih dahulu.")
        return
        
    keyboard = InlineKeyboardMarkup(buttons)
    
    # Store the original message reference
    msg = await message.reply_text("Pilih grup tujuan menfess:", reply_markup=keyboard)
    message_refs[msg.id] = message

@app.on_callback_query()
async def on_group_selection(client, callback_query):
    try:
        user_id = callback_query.from_user.id
        data = callback_query.data
        
        if not data.startswith("send_menfess_"):
            return
            
        group_id = data.replace("send_menfess_", "")
        
        # Check if user is member of the group
        group_data = menfess_groups.get(group_id)
        if not group_data:
            await callback_query.message.reply_text("Grup tidak valid. Silakan coba lagi.")
            return
            
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
            # Send message to group
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
Group: {group_data['title']}
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
                "Gagal mengirim menfess. Pastikan bot sudah menjadi admin di grup yang dipilih."
            )
            
    except Exception as e:
        print(f"Error in callback: {str(e)}")
        await callback_query.message.reply_text("Terjadi kesalahan. Silakan coba lagi.")

print("\n\nBOT TELAH AKTIF!!!")
app.run()
