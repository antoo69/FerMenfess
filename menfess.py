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
cooldown_users = {}  # Changed to dict to support multiple instances
menfess_groups = {}  # Store group IDs and links per bot token
admin_list = {}  # Store admin IDs per bot token
start_message = '''
Selamat Datang Di **Menfess Bot**

Silahkan kirim pesan teks/foto/video/gif/stiker.

Note: Bot menerima pesan teks, foto, video, gif dan stiker.
'''

# Store message references
message_refs = {}

# Store bot instances
bot_instances = {}

async def add_to_cooldown(bot_token, user_id):
    if bot_token not in cooldown_users:
        cooldown_users[bot_token] = []
    cooldown_users[bot_token].append(user_id)
    await asyncio.sleep(delay_time)
    cooldown_users[bot_token].remove(user_id)

def is_owner(user_id):
    return user_id == owner_id

def is_admin(bot_token, user_id):
    if bot_token not in admin_list:
        admin_list[bot_token] = []
    return user_id in admin_list[bot_token] or user_id == owner_id

def create_bot_instance(bot_token):
    if bot_token not in bot_instances:
        bot = Client(f"menfess_bot_{bot_token[-6:]}", 
                    api_id=api_id,
                    api_hash=api_hash,
                    bot_token=bot_token)
        bot_instances[bot_token] = bot
        
        # Initialize data structures for this bot
        menfess_groups[bot_token] = {}
        admin_list[bot_token] = []
        cooldown_users[bot_token] = []
        
        # Create bot-specific database files
        os.makedirs(f"data/{bot_token}", exist_ok=True)
        with open(f"data/{bot_token}/groups.json", "w") as f:
            json.dump({}, f)
        with open(f"data/{bot_token}/member.db", "w") as f:
            f.write("")
            
        return bot

@app.on_message(filters.command("clone") & filters.private)
async def clone_bot(client, message):
    if not is_owner(message.from_user.id):
        await message.reply_text("Hanya owner yang dapat menggunakan perintah ini!")
        return
        
    try:
        # Get bot token from command or forwarded message
        if len(message.command) > 1:
            new_bot_token = message.command[1]
        elif message.forward_from is not None and message.forward_from.username == "BotFather":
            token_line = [line for line in message.text.split('\n') if ':' in line]
            if token_line:
                new_bot_token = token_line[0].split(':')[1].strip()
            else:
                await message.reply_text("Bot token tidak ditemukan dalam pesan yang diteruskan")
                return
        else:
            await message.reply_text("Silakan masukkan bot token atau teruskan pesan dari BotFather")
            return
            
        # Create new bot instance
        new_bot = create_bot_instance(new_bot_token)
        if new_bot:
            await new_bot.start()
            await message.reply_text("Bot berhasil di-clone! Silakan tambahkan grup dengan /addgroup")
        else:
            await message.reply_text("Gagal membuat instance bot baru")
            
    except Exception as e:
        await message.reply_text(f"Gagal melakukan clone bot: {str(e)}")

@app.on_message(filters.command("start") & filters.private)
async def start_command(client, message):
    bot_token = client.bot_token
    user_id = message.from_user.id
    
    if bot_token not in menfess_groups or not menfess_groups[bot_token]:
        if is_owner(user_id):
            await message.reply_text("Harap tambahkan grup terlebih dahulu dengan perintah /addgroup")
            return
        else:
            await message.reply_text("Bot belum dikonfigurasi. Hubungi owner bot.")
            return
            
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Channel Menfess", url=list(menfess_groups[bot_token].values())[0]['link'])]])
    
    # Store user ID for broadcast
    with open(f"data/{bot_token}/member.db", "a+") as file:
        file.seek(0)
        if str(user_id) not in file.read().splitlines():
            file.write(f"{user_id}\n")
    
    await message.reply_text(start_message, reply_markup=keyboard)

# ... (remaining handlers follow same pattern of using bot_token for data access)
# Update all other command handlers to use bot_token for accessing data structures

print("\n\nBOT TELAH AKTIF!!!")
app.run()
