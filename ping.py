import asyncio
from datetime import datetime, timedelta
from time import time
from pyrogram import filters
from pyrogram.types import Message
import app

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

@app.on_message(filters.command("ping") & filters.group, group=28)
async def ping_pong(client, message: Message):
    """Menangani perintah /pung untuk mengukur ping dan uptime bot."""
    start = time()
    current_time = datetime.utcnow()
    uptime_sec = (current_time - START_TIME_UTC).total_seconds()
    uptime = await _human_time_duration(int(uptime_sec))
    m_reply = await message.reply("Pinging...")
    delta_ping = time() - start
    await m_reply.edit(
        "**PONG!!**🏓\n"
        f"**• Pinger -** `{delta_ping * 1000:.3f} ms`\n"
        f"**• Uptime -** `{uptime}`"
    )

@app.on_message(filters.command("time") & filters.group, group=27)
async def get_uptime(client, message: Message):
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
