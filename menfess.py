from pyrogram.types import Message  # <-- Tambahkan ini
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import os
import sqlite3
import zipfile
import json
from dotenv import load_dotenv
import asyncio
from pyrogram.enums import ChatType, ChatMemberStatus
import time
from time import time
from datetime import datetime, timedelta
from pyrogram import Client, filters
from pyrogram.types import CallbackQuery


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
database_file = os.getenv("DATABASE_FILE")
backup_zip = os.getenv("BACKUP_ZIP")

# Initialize bot
app = Client("menfess_bot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

admin_data = {}

def create_database():
    conn = sqlite3.connect(database_file)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS groups (
            chat_id INTEGER PRIMARY KEY,
            admin_id INTEGER,
            title TEXT,
            link TEXT,
            type TEXT
        )
    """)
    conn.commit()
    conn.close())

def add_group_to_db(chat_id: int, admin_id: int, title: str, link: str, chat_type: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        REPLACE INTO groups (chat_id, admin_id, title, link, type) 
        VALUES (?, ?, ?, ?, ?)
    """, (chat_id, admin_id, title, link, chat_type))
    conn.commit()
    conn.close()

    # Setelah grup ditambahkan, buat backup dan kirim ke owner
    create_backup_and_send_to_owner()

def get_db_connection():
    return sqlite3.connect(database_file)

# Fungsi untuk menambahkan grup ke database
def add_group_to_db(chat_id: int, admin_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("REPLACE INTO groups (chat_id, admin_id) VALUES (?, ?)", (chat_id, admin_id))
    conn.commit()
    conn.close()

# Fungsi untuk mendapatkan admin yang menambahkan bot
def get_group_admin(chat_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT admin_id FROM groups WHERE chat_id = ?", (chat_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

def create_backup_and_send_to_owner():
    try:
        # Buat file zip dari database
        with zipfile.ZipFile(backup_zip, 'w') as zipf:
            zipf.write(database_file, os.path.basename(database_file))
        
        # Kirim file backup ke owner
        app.send_document(
            chat_id=owner_id,
            document=backup_zip,
            caption="Database backup terbaru setelah perubahan grup"
        )
        
        print("Backup berhasil dibuat dan dikirim ke owner")
        
    except Exception as e:
        print(f"Error saat membuat/mengirim backup: {e}")

# Panggil fungsi ini ketika bot ditambahkan ke grup baru
def handle_new_chat_member(client, message):
    for member in message.new_chat_members:
        if member.id == client.me.id:
            admin_id = message.from_user.id
            group_id = message.chat.id

            # Simpan admin dan grup ke database
            add_group_to_db(group_id, admin_id)
            
            # Buat backup
            zip_file = create_backup()

            # Kirim file backup ke owner
            send_backup_to_owner(zip_file)

def restore_backup():
    try:
        if os.path.exists(backup_zip):
            with zipfile.ZipFile(backup_zip, 'r') as zipf:
                zipf.extract(os.path.basename(database_file))
            print("Database berhasil di-restore")
            return True
        else:
            print("File backup tidak ditemukan")
            return False
    except Exception as e:
        print(f"Error saat restore: {e}")
        return False

create_database()

def get_all_groups():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM groups")
    groups = cursor.fetchall()
    conn.close()
    return groups

# Fungsi untuk menghapus grup dari database
def remove_group_from_db(chat_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM groups WHERE chat_id = ?", (chat_id,))
    conn.commit()
    conn.close()
    
    # Setelah grup dihapus, buat backup baru
    create_backup_and_send_to_owner()

# Fungsi untuk menghitung durasi waktu dalam format yang lebih mudah dipahami manusia
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

async def is_channel_member(client, user_id, chat_id):
    try:
        member = await client.get_chat_member(chat_id, user_id)
        # Mengizinkan semua member, termasuk administrator, owner, dan member biasa
        return member.status in [
            ChatMemberStatus.OWNER,
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.MEMBER
        ]
    except Exception as e:
        print(f"Error checking channel membership: {e}")
        return False

async def is_channel_member(client, user_id, chat_id):
    try:
        # Pastikan bot menjadi admin di channel
        member = await client.get_chat_member(chat_id, user_id)
        # Mengizinkan semua anggota (owner, admin, dan member biasa)
        return member.status in [
            ChatMemberStatus.OWNER,
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.MEMBER
        ]
    except Exception as e:
        print(f"Error checking channel membership (chat_id: {chat_id}, user_id: {user_id}): {e}")
        return False


from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

@app.on_chat_member_updated()
async def handle_chat_member_updated(client, chat_member_updated):
    chat = chat_member_updated.chat
    new_member = chat_member_updated.new_chat_member
    old_member = chat_member_updated.old_chat_member
    action_by = chat_member_updated.from_user  # Orang yang menambahkan/mengeluarkan bot

    # Jika bot ditambahkan ke grup
    if new_member and new_member.user.id == app.me.id:
        try:
            chat_info = await client.get_chat(chat.id)
            chat_type = str(chat_info.type)

            # Coba buat tautan undangan (jika bot admin)
            invite_link = None
            try:
                invite_link = await chat_info.export_invite_link()
            except:
                invite_link = "🔒 Tidak ada akses untuk membuat tautan."

            # Simpan informasi grup
            menfess_groups[str(chat.id)] = {
                'id': chat.id,
                'title': chat.title,
                'link': invite_link,
                'type': chat_type
            }

            # Simpan ke database grup
            os.makedirs(f"data/{chat.id}", exist_ok=True)
            with open(f"data/{chat.id}/group_info.json", "w") as f:
                json.dump(menfess_groups[str(chat.id)], f)

            # Kirim notifikasi ke owner
            owner_message = f"""
📢 **BOT DITAMBAHKAN KE GRUP** 📢
👥 **Nama Grup:** {chat.title}
🆔 **ID Grup:** `{chat.id}`
🔗 **Tautan:** {invite_link}
📌 **Tipe:** {chat_type}
👤 **Ditambahkan oleh:** [{action_by.first_name}](tg://user?id={action_by.id})
"""

            owner_keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton(f"👤 Profil {action_by.first_name}", url=f"tg://user?id={action_by.id}")],
                [InlineKeyboardButton("🔗 Buka Grup", url=invite_link)] if invite_link != "🔒 Tidak ada akses untuk membuat tautan." else []
            ])

            await client.send_message(owner_id, owner_message, reply_markup=owner_keyboard)

            # Kirim pesan sambutan ke grup dengan button
            welcome_message = f"""
📢 **Halo, Saya Bot Menfes Multi Group !** 📢
🔹 Saya bisa membantu Anda mengirim pesan anonim ke beberapa grup sekaligus.
🔹 **Cara Penggunaan:**
   1️⃣ Tambahkan saya sebagai admin grup.
   2️⃣ Kirim pesan ke bot ini di chat pribadi.
   3️⃣ Pilih grup tujuan dan pesan akan dikirim secara anonim!

🔹Info bot lain silahkan kunjungi Store Kami

🚀 **Tambahkan saya ke lebih banyak grup untuk menikmati fitur multi-group!**
"""
            group_keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("📝 Kirim Pesan Anonim", url="https://t.me/testmenfes_bot")],
                [InlineKeyboardButton("🛒 Store", url="https://t.me/Galerifsyrl")]
            ])

            await client.send_message(chat.id, welcome_message, reply_markup=group_keyboard)

            print(f"Bot berhasil bergabung dengan {chat.title} ({chat.id})")

        except Exception as e:
            print(f"Error saat bot ditambahkan ke grup: {str(e)}")

    # Jika bot dikeluarkan dari grup
    elif old_member and old_member.user.id == app.me.id:
        try:
            # Hapus grup dari database
            if str(chat.id) in menfess_groups:
                del menfess_groups[str(chat.id)]

            # Kirim notifikasi ke owner dengan siapa yang mengeluarkan bot
            owner_message = f"""
⚠️ **BOT DIKELUARKAN DARI GRUP** ⚠️
👥 **Nama Grup:** {chat.title}
🆔 **ID Grup:** `{chat.id}`
📌 **Tipe:** {str(chat.type)}
👤 **Dikeluarkan oleh:** [{action_by.first_name}](tg://user?id={action_by.id})
"""

            owner_keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton(f"👤 Profil {action_by.first_name}", url=f"tg://user?id={action_by.id}")]
            ])

            await client.send_message(owner_id, owner_message, reply_markup=owner_keyboard)

            print(f"Bot dikeluarkan dari {chat.title} ({chat.id}) oleh {action_by.first_name}")

        except Exception as e:
            print(f"Error saat bot dikeluarkan dari grup: {str(e)}")



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

@app.on_message(filters.command("ping", prefixes=["/", "!", "."]) & (filters.private | filters.group))
async def ping_pong(client: Client, message: Message):
    """Menangani perintah /ping untuk mengukur ping dan uptime bot."""

    # Abaikan pesan dari bot sendiri
    if message.from_user and message.from_user.is_bot:
        return  

    # Abaikan pesan jika tidak diawali dengan /, !, atau .
    if message.text and not message.text.startswith(("/", "!", ".")):
        return  

    # Cegah bot merespons /ping saat baru masuk ke grup dalam 30 detik terakhir
    chat_id = str(message.chat.id)
    if chat_id in menfess_groups:
        last_join_time = menfess_groups[chat_id].get("join_time", 0)
        if time() - last_join_time < 30:  # Jika bot baru masuk dalam 30 detik terakhir
            return

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


@app.on_message(filters.private & ~filters.command(["start", "ping", "broadcast", "backup", "muat"]))
async def handle_private_message(client, message):
    user_id = message.from_user.id
    user_ids.add(user_id)

    buttons = []
    for group_id, group_data in menfess_groups.items():
        # Untuk CHANNEL, izinkan SEMUA MEMBER untuk mengirim menfess
        if group_data.get('type') == str(ChatType.CHANNEL):
            is_member = await is_channel_member(client, user_id, group_data['id'])
            if is_member:
                buttons.append([InlineKeyboardButton(
                    f"💌 Kirim Menfess ke {group_data['title']}",
                    callback_data=f"send_menfess_{group_id}"
                )])
        # Untuk GROUP, tetap cek apakah user adalah member
        else:
            if await is_group_member(client, user_id, group_data['id']):
                buttons.append([InlineKeyboardButton(
                    f"💌 Kirim Menfess ke {group_data['title']}",
                    callback_data=f"send_menfess_{group_id}"
                )])

    if not buttons:
        await message.reply_text(
            "Anda tidak mempunyai group atau channel yang sama dengan bot ini.\n"
            "Tambahkan bot ini ke dalam group/channel Anda agar bisa mengirim menfess."
        )
        return

    keyboard = InlineKeyboardMarkup(buttons)

    # Simpan referensi pesan asli
    msg = await message.reply_text("Pilih grup/channel tujuan menfess:", reply_markup=keyboard)
    message_refs[msg.id] = message


async def is_channel_member(client, user_id, chat_id):
    try:
        member = await client.get_chat_member(chat_id, user_id)
        # Mengizinkan semua anggota (owner, admin, dan member biasa)
        return member.status in [
            ChatMemberStatus.OWNER,
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.MEMBER
        ]
    except Exception as e:
        print(f"Error checking channel membership: {e}")
        return False

@app.on_chat_member_updated()
def on_bot_added(client, message: Message):
    if message.new_chat_member and message.new_chat_member.user.id == client.me.id:
        admin_id = message.from_user.id
        chat_id = message.chat.id
        add_group_to_db(chat_id, admin_id)
        create_backup()
        client.send_document(owner_id, backup_zip, caption="Backup database terbaru")

@app.on_message(filters.command("backup") & filters.private)
def backup_database(client: Client, message: Message):
    if message.chat.id == owner_id:
        try:
            # Buat file zip untuk backup
            with zipfile.ZipFile(backup_zip, 'w') as zipf:
                if os.path.exists(database_file):
                    zipf.write(database_file)
                else:
                    client.send_message(
                        chat_id=owner_id,
                        text="File database tidak ditemukan."
                    )
                    return

            # Kirim file zip ke owner
            client.send_document(
                chat_id=owner_id,
                document=backup_zip,
                caption="Berikut adalah file backup dalam format ZIP."
            )

            # Hapus file zip setelah dikirim
            if os.path.exists(backup_zip):
                os.remove(backup_zip)

        except Exception as e:
            client.send_message(
                chat_id=owner_id,
                text=f"Gagal melakukan backup: {str(e)}"
            )
            print(f"Error saat melakukan backup: {str(e)}")
    else:
        # Hanya owner yang bisa melakukan backup
        client.send_message(
            chat_id=message.chat.id,
            text="Perintah /backup hanya bisa dilakukan oleh owner bot."
        )

# Command handler untuk restore database dari zip yang direply
@app.on_message(filters.command("muat") & filters.private)
def restore_database(client: Client, message: Message):
    if message.chat.id == owner_id:
        if message.reply_to_message and message.reply_to_message.document:
            file_id = message.reply_to_message.document.file_id
            file_name = message.reply_to_message.document.file_name

            if file_name.endswith(".zip"):
                try:
                    # Unduh file zip yang di-reply
                    file_path = client.download_media(file_id, file_name=backup_zip)

                    # Ekstrak file zip dan ganti database
                    with zipfile.ZipFile(file_path, 'r') as zipf:
                        zipf.extractall()

                    # Hapus file zip setelah restore selesai
                    if os.path.exists(backup_zip):
                        os.remove(backup_zip)

                    client.send_message(
                        chat_id=owner_id,
                        text="Database berhasil dipulihkan dari file zip."
                    )
                except Exception as e:
                    client.send_message(
                        chat_id=owner_id,
                        text=f"Gagal memulihkan database: {str(e)}"
                    )
                    print(f"Error saat restore: {str(e)}")
            else:
                client.send_message(
                    chat_id=owner_id,
                    text="Harap reply file dengan format .zip untuk restore."
                )
        else:
            client.send_message(
                chat_id=owner_id,
                text="Harap reply file zip yang berisi database untuk melakukan restore."
            )
    else:
        client.send_message(
            chat_id=message.chat.id,
            text="Perintah /restore hanya bisa dilakukan oleh owner bot."
        )

@app.on_callback_query()
async def on_group_selection(client: Client, callback_query: CallbackQuery):
    try:
        user_id = callback_query.from_user.id
        data = callback_query.data

        if not data.startswith("send_menfess_"):
            return

        group_id = data.replace("send_menfess_", "")

        # Cek apakah grup/channel valid
        group_data = menfess_groups.get(group_id)
        if not group_data:
            await callback_query.message.reply_text("Grup/Channel tidak valid. Silakan coba lagi.")
            return

        # Mengizinkan semua member untuk mengirim menfess ke channel tanpa cek admin
        if group_data.get('type') == str(ChatType.CHANNEL):
            await callback_query.message.reply_text(
                f"Menfess Anda akan dikirim ke channel {group_data['title']}."
            )
        else:
            # Cek apakah user adalah anggota grup (untuk grup non-channel)
            is_member = await is_group_member(client, user_id, group_data['id'])
            if not is_member:
                await callback_query.message.reply_text(
                    f"Anda bukan anggota dari grup {group_data['title']} ({group_data['id']}), "
                    "mohon bergabung ke dalam grup yang ingin Anda kirimkan menfess agar bisa memakai bot ini."
                )
                return

        # Cek cooldown pengguna
        if group_id in cooldown_users and user_id in cooldown_users[group_id]:
            await callback_query.message.reply_text(f"Mohon tunggu {delay_time} detik sebelum mengirim menfess lagi.")
            return

        # Ambil pesan asli
        original_message = message_refs.get(callback_query.message.id)
        if not original_message:
            await callback_query.message.reply_text("Pesan tidak ditemukan. Silakan coba lagi.")
            return

        try:
            # Mengirim menfess ke channel atau grup
            if original_message.media:
                # Mengirim media (gambar, video, dll.)
                sent = await original_message.copy(
                    chat_id=group_data['id']
                )
            else:
                # Mengirim pesan teks biasa
                sent = await client.send_message(
                    chat_id=group_data['id'],
                    text=original_message.text if original_message.text else "[Pesan Media]",
                    disable_web_page_preview=True
                )

            # Membuat tautan permanen untuk pesan di channel
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

            # Notifikasi kepada owner dengan isi pesan
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

            # Forward pesan media (jika ada) ke owner
            if original_message.media:
                await original_message.copy(owner_id)

            # Notifikasi ke admin yang menambahkan bot
            admin_who_added_bot_id = admin_data.get(group_data['id'])
            if admin_who_added_bot_id:
                await client.send_message(admin_who_added_bot_id, owner_notification)
                if original_message.media:
                    await original_message.copy(admin_who_added_bot_id)

            # Tambahkan pengguna ke dalam cooldown
            await add_to_cooldown(group_data['id'], user.id)

            # Hapus referensi pesan untuk menghindari kebocoran memori
            del message_refs[callback_query.message.id]

        except Exception as e:
            print(f"Error sending menfess: {str(e)}")
            await callback_query.message.reply_text(
                "Gagal mengirim menfess. Pastikan bot sudah menjadi admin di grup/channel yang dipilih."
            )
        finally:
            print("Proses menfess selesai.")

    except Exception as e:
        print(f"Error in on_group_selection: {str(e)}")

print("\n\nBOT TELAH AKTIF!!!")
app.run()
