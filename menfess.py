from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import os
import json
from dotenv import load_dotenv
import asyncio
from pyrogram.enums import ChatType, ChatMemberStatus

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

async def add_to_cooldown(group_id, user_id):
    if group_id not in cooldown_users:
        cooldown_users[group_id] = []
    cooldown_users[group_id].append(user_id)
    await asyncio.sleep(delay_time)
    cooldown_users[group_id].remove(user_id)

def is_owner(user_id):
    return user_id == owner_id

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
                    
                # Create member database for this group
                open(f"data/{chat.id}/members.db", "a").close()
                
                print(f"Bot added to {chat.title} ({chat.id})")
                
        except Exception as e:
            print(f"Error handling new chat member: {str(e)}")

@app.on_message(filters.command("start") & filters.private)
async def start_command(client, message):
    user_id = message.from_user.id
    
    # Create buttons for all groups bot is in
    buttons = []
    for group_id, group_data in menfess_groups.items():
        buttons.append([InlineKeyboardButton(
            f"💌 Kirim Menfess ke {group_data['title']}", 
            callback_data=f"send_menfess_{group_id}"
        )])
    
    if not buttons:
        await message.reply_text("Bot belum ditambahkan ke grup manapun. Silakan tambahkan bot ke grup terlebih dahulu.")
        return
        
    keyboard = InlineKeyboardMarkup(buttons)
    
    # Store user ID in all group member databases
    for group_id in menfess_groups:
        with open(f"data/{group_id}/members.db", "a+") as file:
            file.seek(0)
            if str(user_id) not in file.read().splitlines():
                file.write(f"{user_id}\n")
    
    await message.reply_text(start_message, reply_markup=keyboard)

print("\n\nBOT TELAH AKTIF!!!")
app.run()
