import os
import re
import json
import asyncio
import time
import urllib.request
from pyrogram import Client, filters
from pyrogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton
)
from config import *
from fonts import convert_font
from datetime import datetime, timedelta

app = Client("utilbot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

user_state = {}
DB_FILE = "users_db.json"
IMG_CACHE_FILE = "img_cache.json"
IMG_VERSION = "v4"

BULK_LIMIT_FREE = 10
BULK_LIMIT_PREMIUM = 100

IMAGE_URLS = {
    "start":    "https://kommodo.ai/i/CvcKWCkMyVIhfyJBnuGz",
    "rename":   "https://kommodo.ai/i/HmXYEMb2nsGg1svKdGt6",
    "font":     "https://kommodo.ai/i/TuLS5WD04IB9QQ8oCoNe",
    "premium":  "https://kommodo.ai/i/8DTtO57boWXtEaQk1HZO",
    "status":   "https://kommodo.ai/i/0JHYKt67GvLOtdWfCXqq",
    "bulk":     "https://kommodo.ai/i/G7gIWIZqzdiFJdxzV1h8",
    "channels": "https://kommodo.ai/i/OGZBDAAhWOHCQkdE4CvU",
}

IMG_CACHE = {}

# ─────────────────────────────────────────
# IMAGE CACHE
# ─────────────────────────────────────────
def load_img_cache():
    global IMG_CACHE
    if os.path.exists(IMG_CACHE_FILE):
        try:
            with open(IMG_CACHE_FILE, "r") as f:
                data = json.load(f)
            if data.get("version") == IMG_VERSION:
                IMG_CACHE = data.get("cache", {})
                print("Image cache loaded.")
                return
            print("Image cache outdated, clearing...")
        except:
            pass
    IMG_CACHE = {}

def save_img_cache():
    with open(IMG_CACHE_FILE, "w") as f:
        json.dump({"version": IMG_VERSION, "cache": IMG_CACHE}, f)

async def get_img(key, client, chat_id):
    if key in IMG_CACHE:
        return IMG_CACHE[key]
    url = IMAGE_URLS.get(key)
    if not url:
        return None
    path = f"/tmp/img_{key}.jpg"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            with open(path, "wb") as f:
                f.write(resp.read())
        msg = await client.send_photo(chat_id=chat_id, photo=path, caption=f"[CACHE:{key}]")
        IMG_CACHE[key] = msg.photo.file_id
        save_img_cache()
        if os.path.exists(path):
            os.remove(path)
        return IMG_CACHE[key]
    except Exception as e:
        print(f"Image cache error [{key}]: {e}")
        if os.path.exists(path):
            os.remove(path)
        return None

async def send_img(message, key, caption, reply_markup=None):
    fid = await get_img(key, message._client, message.from_user.id)
    if fid:
        try:
            await message.reply_photo(photo=fid, caption=caption, reply_markup=reply_markup)
            return
        except:
            IMG_CACHE.pop(key, None)
            save_img_cache()
    await message.reply(caption, reply_markup=reply_markup)

# ─────────────────────────────────────────
# DATABASE
# ─────────────────────────────────────────
def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_db(db):
    with open(DB_FILE, "w") as f:
        json.dump(db, f, indent=4)

def get_user(user_id):
    db = load_db()
    uid = str(user_id)
    if uid not in db:
        db[uid] = {
            "premium": False,
            "premium_expiry": None,
            "thumbnail_file_id": None,
            "bulk_quota": {"used": 0, "reset_at": None}
        }
        save_db(db)
    return db[uid]

def save_user(user_id, data):
    db = load_db()
    db[str(user_id)] = data
    save_db(db)

def is_premium(user_id):
    user = get_user(user_id)
    if not user["premium"]:
        return False
    if user.get("premium_expiry"):
        if datetime.now() > datetime.fromisoformat(user["premium_expiry"]):
            user["premium"] = False
            user["premium_expiry"] = None
            save_user(user_id, user)
            return False
    return True

def is_admin(user_id):
    return user_id in ADMINS

def get_stats():
    db = load_db()
    total = len(db)
    premium = sum(1 for u in db.values() if u.get("premium"))
    return total, premium

# ─────────────────────────────────────────
# BULK QUOTA
# ─────────────────────────────────────────
def get_bulk_limit(user_id):
    if is_admin(user_id):
        return float("inf")
    return BULK_LIMIT_PREMIUM if is_premium(user_id) else BULK_LIMIT_FREE

def check_bulk_quota(user_id):
    if is_admin(user_id):
        return float("inf"), float("inf")
    user = get_user(user_id)
    quota = user.get("bulk_quota", {"used": 0, "reset_at": None})
    now = datetime.now()
    reset_at = quota.get("reset_at")
    if reset_at and datetime.fromisoformat(reset_at) < now:
        quota = {"used": 0, "reset_at": None}
    used = quota.get("used", 0)
    limit = get_bulk_limit(user_id)
    remaining = max(0, limit - used)
    return limit, remaining

def consume_bulk_quota(user_id, count):
    if is_admin(user_id):
        return
    user = get_user(user_id)
    quota = user.get("bulk_quota", {"used": 0, "reset_at": None})
    now = datetime.now()
    reset_at = quota.get("reset_at")
    if reset_at and datetime.fromisoformat(reset_at) < now:
        quota = {"used": 0, "reset_at": None}
    if not quota.get("reset_at"):
        quota["reset_at"] = (now + timedelta(hours=1)).isoformat()
    quota["used"] = quota.get("used", 0) + count
    user["bulk_quota"] = quota
    save_user(user_id, user)

# ─────────────────────────────────────────
# PROGRESS
# ─────────────────────────────────────────
async def fake_progress(status_msg, action, stop_event, total_mb=0):
    start_time = time.time()
    steps = [2, 8, 15, 24, 35, 47, 58, 68, 77, 84, 90, 95, 98]
    label = "Downloading" if action == "dl" else "Uploading"
    for pct in steps:
        if stop_event.is_set():
            break
        elapsed = max(0.1, time.time() - start_time)
        done_mb = total_mb * pct / 100 if total_mb else 0
        speed = done_mb / elapsed if elapsed > 0 and done_mb > 0 else 0
        remaining_mb = (total_mb - done_mb) if total_mb else 0
        eta = int(remaining_mb / speed) if speed > 0 else 0
        filled = int(pct / 5)
        bar = "█" * filled + "░" * (20 - filled)
        size_str = f"{done_mb:.2f} MB / {total_mb:.2f} MB" if total_mb else "Calculating..."
        speed_str = f"{speed:.2f} MB/s" if speed > 0 else "..."
        eta_str = f"{eta} sec" if eta > 1 else "< 1 sec"
        try:
            await status_msg.edit_text(
                f"**{label}...**\n\n"
                f"`{bar}`\n\n"
                f"📁 **Size**  :  {size_str}\n"
                f"⏳ **Done**  :  {pct:.1f}%\n"
                f"🚀 **Speed** :  {speed_str}\n"
                f"⏰ **ETA**   :  {eta_str}"
            )
        except:
            pass
        await asyncio.sleep(2)
    while not stop_event.is_set():
        await asyncio.sleep(0.5)

# ─────────────────────────────────────────
# KEYBOARDS
# ─────────────────────────────────────────
def main_reply_kb():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("📁 Rename File"), KeyboardButton("📦 Bulk Rename")],
            [KeyboardButton("🔤 Font Changer"), KeyboardButton("🖼️ Set Thumbnail")],
            [KeyboardButton("👁️ View Thumbnail"), KeyboardButton("❌ Clear Thumbnail")],
            [KeyboardButton("ℹ️ My Status"), KeyboardButton("👑 Premium")],
            [KeyboardButton("🌐 HeavenFall Channels")]
        ],
        resize_keyboard=True
    )

def font_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("𝗛𝗲𝗮𝘃𝗲𝗻𝗙𝗮𝗹𝗹", callback_data="font_sans_bold"),
         InlineKeyboardButton("𝙃𝙚𝙖𝙫𝙚𝙣𝙁𝙖𝙡𝙡", callback_data="font_sans_bold_italic"),
         InlineKeyboardButton("𝘏𝘦𝘢𝘷𝘦𝘯𝘍𝘢𝘭𝘭", callback_data="font_sans_italic")],
        [InlineKeyboardButton("𝐇𝐞𝐚𝐯𝐞𝐧𝐅𝐚𝐥𝐥", callback_data="font_serif_bold"),
         InlineKeyboardButton("𝑯𝒆𝒂𝒗𝒆𝒏𝑭𝒂𝒍𝒍", callback_data="font_bold_italic_serif"),
         InlineKeyboardButton("𝙷𝚎𝚊𝚟𝚎𝚗𝙵𝚊𝚕𝚕", callback_data="font_mono")],
        [InlineKeyboardButton("ʜᴇᴀᴠᴇɴꜰᴀʟʟ", callback_data="font_small_caps"),
         InlineKeyboardButton("HᴇᴀᴠᴇɴFᴀʟʟ", callback_data="font_mixed_caps"),
         InlineKeyboardButton("𝘏𝘦𝘢𝘷𝘦𝘯𝘍𝘢𝘭𝘭", callback_data="font_italic_serif")],
        [InlineKeyboardButton("𝓗𝓮𝓪𝓿𝓮𝓷𝓕𝓪𝓵𝓵", callback_data="font_cursive"),
         InlineKeyboardButton("ＨｅａｖｅｎＦａｌｌ", callback_data="font_fullwidth"),
         InlineKeyboardButton("ᴴᵉᵃᵛᵉⁿᶠᵃˡˡ", callback_data="font_superscript")],
        [InlineKeyboardButton("𝔥𝔢𝔞𝔳𝔢𝔫𝔣𝔞𝔩𝔩", callback_data="font_fraktur"),
         InlineKeyboardButton("𝕳𝖊𝖆𝖛𝖊𝖓𝕱𝖆𝖑𝖑", callback_data="font_gothic"),
         InlineKeyboardButton("🅗🅔🅐🅥🅔🅝🅕🅐🅛🅛", callback_data="font_block")],
        [InlineKeyboardButton("🔙 Back", callback_data="back_main")]
    ])

def premium_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💎 Purchase Premium — @fangheaven", url="https://t.me/fangheaven")]
    ])

def channels_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏠 Main Network", url="https://t.me/HeavenFallNetwork")],
        [InlineKeyboardButton("📖 Cornhwa", url="https://t.me/+IHY2h3qLgjtmMzA1"),
         InlineKeyboardButton("🌍 International", url="https://t.me/+VSAoNrs1NBBjOGY1")],
        [InlineKeyboardButton("😈 Adult Videos", url="https://t.me/+K4ap0zrg6IA2MTI1"),
         InlineKeyboardButton("💎 OnlyFans", url="https://t.me/+a0iGoOFSf4syYTQ1")],
        [InlineKeyboardButton("🎭 Cosplay Girls", url="https://t.me/+ekqjAhNgFWJmN2Zl"),
         InlineKeyboardButton("👩 Milf Videos", url="https://t.me/+HEQJRNDQGog5ZGVl")],
        [InlineKeyboardButton("🎌 Hentai / Anime", url="https://t.me/+wb16uJ7ckM83NDJl"),
         InlineKeyboardButton("📚 Doujinshi", url="https://t.me/doujinshi_adultmanga_fall")],
        [InlineKeyboardButton("🎌 Japanese JAV", url="https://t.me/Javcorn_HeavenFall"),
         InlineKeyboardButton("🇮🇳 Indian / Desi", url="https://t.me/+BwFvtFx-WNkwYzFl")],
        [InlineKeyboardButton("👥 G@ngb@ng", url="https://t.me/+QXdo489mELkzOTdl"),
         InlineKeyboardButton("🎭 Stickers NSFW", url="https://t.me/stickernsfwheavenfall")],
    ])

def admin_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Stats", callback_data="adm_stats"),
         InlineKeyboardButton("📢 Broadcast", callback_data="adm_broadcast")],
        [InlineKeyboardButton("👑 Add Premium", callback_data="adm_addprem"),
         InlineKeyboardButton("🗑️ Remove Premium", callback_data="adm_remprem")],
        [InlineKeyboardButton("🔍 User Lookup", callback_data="adm_lookup"),
         InlineKeyboardButton("💥 Reset User", callback_data="adm_reset")],
        [InlineKeyboardButton("🔄 Clear Img Cache", callback_data="adm_imgcache"),
         InlineKeyboardButton("🔒 Close Panel", callback_data="adm_close")]
    ])

def bulk_confirm_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Confirm Rename", callback_data="bulk_confirm"),
         InlineKeyboardButton("❌ Cancel", callback_data="bulk_cancel")]
    ])

# ─────────────────────────────────────────
# /start
# ─────────────────────────────────────────
@app.on_message(filters.command("start") & filters.private)
async def start(client, message):
    uid = message.from_user.id
    name = message.from_user.first_name or "there"
    badge = "👑 Premium Member" if is_premium(uid) else "🆓 Free Plan"
    await send_img(message, "start", caption=(
        f"✦ **HeavenFall Utility Bot** ✦\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Welcome, **{name}**. 👋\n\n"
        f"Your precision toolkit for Telegram,\n"
        f"built for speed, style, and simplicity.\n\n"
        f"🏷️ **Account Plan:** {badge}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"**What I can do:**\n\n"
        f"📁 Rename files with custom name and thumbnail\n"
        f"📦 Bulk rename up to 100 files at once\n"
        f"🔤 Convert text into premium font styles\n"
        f"🖼️ Store a permanent thumbnail for all files\n"
        f"🌐 Explore all HeavenFall channels\n"
        f"👑 Upgrade for unlimited access\n\n"
        f"Select a feature from the menu below 👇"
    ), reply_markup=main_reply_kb())

# ─────────────────────────────────────────
# /admin
# ─────────────────────────────────────────
@app.on_message(filters.command("admin") & filters.user(ADMINS))
async def admin_panel(client, message):
    total, premium = get_stats()
    await message.reply(
        f"🛠️ **HeavenFall — Admin Panel**\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 **Total Users:** `{total}`\n"
        f"👑 **Premium Users:** `{premium}`\n"
        f"🆓 **Free Users:** `{total - premium}`\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Select an action below 👇",
        reply_markup=admin_kb()
    )

@app.on_callback_query(filters.regex("^adm_") & filters.user(ADMINS))
async def admin_callbacks(client, callback_query):
    data = callback_query.data
    uid = callback_query.from_user.id

    if data == "adm_stats":
        total, premium = get_stats()
        await callback_query.message.edit_text(
            f"📊 **Bot Statistics**\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👥 **Total Users:** `{total}`\n"
            f"👑 **Premium Users:** `{premium}`\n"
            f"🆓 **Free Users:** `{total - premium}`",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="adm_back")]])
        )
    elif data == "adm_broadcast":
        user_state[uid] = {"step": "adm_broadcast"}
        await callback_query.message.edit_text(
            "📢 **Broadcast Message**\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "Compose your message. It will be delivered to all users instantly.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="adm_back")]])
        )
    elif data == "adm_addprem":
        user_state[uid] = {"step": "adm_addprem"}
        await callback_query.message.edit_text(
            "👑 **Grant Premium Access**\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "Send: `user_id days`\n\n"
            "123456789 30 — 30 days\n"
            "123456789 0 — Lifetime",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="adm_back")]])
        )
    elif data == "adm_remprem":
        user_state[uid] = {"step": "adm_remprem"}
        await callback_query.message.edit_text(
            "🗑️ **Revoke Premium Access**\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "Send the user_id to revoke premium from:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="adm_back")]])
        )
    elif data == "adm_lookup":
        user_state[uid] = {"step": "adm_lookup"}
        await callback_query.message.edit_text(
            "🔍 **User Lookup**\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "Send the user_id to inspect:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="adm_back")]])
        )
    elif data == "adm_reset":
        user_state[uid] = {"step": "adm_reset"}
        await callback_query.message.edit_text(
            "💥 **Reset User Account**\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "This permanently wipes all data for the user.\n\n"
            "Send the user_id to proceed:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="adm_back")]])
        )
    elif data == "adm_imgcache":
        global IMG_CACHE
        IMG_CACHE = {}
        if os.path.exists(IMG_CACHE_FILE):
            os.remove(IMG_CACHE_FILE)
        await callback_query.answer("Image cache cleared. Will re-download on next use.", show_alert=True)
    elif data == "adm_back":
        user_state.pop(uid, None)
        total, premium = get_stats()
        await callback_query.message.edit_text(
            f"🛠️ **HeavenFall — Admin Panel**\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👥 **Total Users:** `{total}`\n"
            f"👑 **Premium Users:** `{premium}`\n"
            f"🆓 **Free Users:** `{total - premium}`\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"Select an action below 👇",
            reply_markup=admin_kb()
        )
    elif data == "adm_close":
        user_state.pop(uid, None)
        await callback_query.message.delete()

# ─────────────────────────────────────────
# RESERVED KEYBOARD BUTTONS
# ─────────────────────────────────────────
RESERVED = [
    "📁 Rename File", "📦 Bulk Rename", "🔤 Font Changer",
    "🖼️ Set Thumbnail", "👁️ View Thumbnail", "❌ Clear Thumbnail",
    "ℹ️ My Status", "👑 Premium", "🌐 HeavenFall Channels"
]

@app.on_message(filters.text & filters.private & filters.regex(
    "^(📁 Rename File|📦 Bulk Rename|🔤 Font Changer|🖼️ Set Thumbnail"
    "|👁️ View Thumbnail|❌ Clear Thumbnail|ℹ️ My Status|👑 Premium|🌐 HeavenFall Channels)$"
))
async def main_kb_handler(client, message):
    uid = message.from_user.id
    text = message.text

    if text == "📁 Rename File":
        user_state[uid] = {"step": "wait_file"}
        await send_img(message, "rename", caption=(
            "📁 **File Renamer**\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "Send your file and I will rename it with precision.\n\n"
            "📦 **Free Plan:** Up to 100 MB\n"
            "👑 **Premium:** Unlimited file size\n\n"
            "Drop your file below to begin 👇"
        ))

    elif text == "📦 Bulk Rename":
        limit, remaining = check_bulk_quota(uid)
        if remaining == 0:
            cap = BULK_LIMIT_PREMIUM if is_premium(uid) else BULK_LIMIT_FREE
            await message.reply(
                f"⏳ **Hourly Limit Reached**\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"You have used your **{cap} file** bulk rename quota for this hour.\n\n"
                f"Your limit resets within 60 minutes.\n\n"
                f"{'Upgrade to 👑 **Premium** for 100 files/hour — contact **@fangheaven**.' if not is_premium(uid) else 'Contact **@fangheaven** to extend your limit.'}",
                reply_markup=premium_kb() if not is_premium(uid) else None
            )
            return
        limit_txt = "Unlimited" if is_admin(uid) else f"{int(remaining)} files remaining this hour"
        user_state[uid] = {"step": "bulk_collecting", "files": []}
        await send_img(message, "bulk", caption=(
            "📦 **Bulk Rename**\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📊 **Quota:** {limit_txt}\n\n"
            "Send all your files one by one.\n"
            "When you are done, send /done to proceed.\n\n"
            "Files will be renamed in the order they arrive 👇"
        ))

    elif text == "🔤 Font Changer":
        user_state[uid] = {"step": "wait_text_font"}
        await send_img(message, "font", caption=(
            "🔤 **Font Changer**\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "Elevate your text with premium Unicode font styles.\n\n"
            "Type anything — titles, names, captions —\n"
            "and transform them instantly.\n\n"
            "Send your text to continue 👇"
        ))

    elif text == "🖼️ Set Thumbnail":
        user_state[uid] = {"step": "wait_thumbnail"}
        await send_img(message, "rename", caption=(
            "🖼️ **Set Thumbnail**\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "Upload a photo to set as your permanent default thumbnail.\n\n"
            "Applied automatically to every file you rename.\n\n"
            "Send your photo now 👇"
        ))

    elif text == "👁️ View Thumbnail":
        user = get_user(uid)
        thumb_id = user.get("thumbnail_file_id")
        if not thumb_id:
            await message.reply(
                "🖼️ **No Thumbnail Configured**\n\n"
                "You have not set a thumbnail yet.\n\n"
                "Tap Set Thumbnail to upload one."
            )
        else:
            await message.reply_photo(
                photo=thumb_id,
                caption="🖼️ **Your Current Thumbnail**\n\nApplied to all files you rename."
            )

    elif text == "❌ Clear Thumbnail":
        user = get_user(uid)
        user["thumbnail_file_id"] = None
        save_user(uid, user)
        await message.reply(
            "🗑️ **Thumbnail Cleared**\n\n"
            "Your default thumbnail has been removed.\n"
            "Files will be sent without a custom thumbnail."
        )

    elif text == "ℹ️ My Status":
        user = get_user(uid)
        badge = "👑 Premium Member" if is_premium(uid) else "🆓 Free Plan"
        thumb = "✅ Configured" if user.get("thumbnail_file_id") else "❌ Not set"
        expiry = user.get("premium_expiry") or "—"
        limit, remaining = check_bulk_quota(uid)
        rem_txt = "Unlimited" if is_admin(uid) else f"{int(remaining)} of {int(limit)}"
        await send_img(message, "status", caption=(
            f"📊 **Account Status**\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🏷️ **Plan:** {badge}\n"
            f"📅 **Expiry:** `{expiry}`\n"
            f"🖼️ **Thumbnail:** {thumb}\n"
            f"📦 **Bulk Quota:** {rem_txt} remaining this hour\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"Tap 👑 Premium to unlock full access"
        ))

    elif text == "👑 Premium":
        if is_premium(uid):
            user = get_user(uid)
            expiry = user.get("premium_expiry") or "Lifetime"
            await send_img(message, "premium", caption=(
                f"👑 **Premium Member**\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"You have full access to all HeavenFall features.\n\n"
                f"📅 **Expiry:** `{expiry}`\n\n"
                f"Thank you for being a part of HeavenFall. 💫"
            ))
        else:
            await send_img(message, "premium", caption=(
                "👑 **HeavenFall Premium**\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                "Unlock the full HeavenFall experience:\n\n"
                "✅ Rename files above 100 MB\n"
                "✅ Bulk rename up to 100 files per hour\n"
                "✅ Unlimited font conversions\n"
                "✅ Auto-thumbnail on every file\n"
                "✅ Priority support\n"
                "✅ Access to all future features\n\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "Contact **@fangheaven** to get started 👇"
            ), reply_markup=premium_kb())

    elif text == "🌐 HeavenFall Channels":
        await send_img(message, "channels", caption=(
            "🌐 **HeavenFall Network**\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "🔞 Premium Adult Content — Free of Charge\n\n"
            "Join our exclusive channels below.\n"
            "Fresh content dropped daily across all categories.\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "Tap any channel to join instantly 👇"
        ), reply_markup=channels_kb())

# ─────────────────────────────────────────
# /bulkrename COMMAND
# ─────────────────────────────────────────
@app.on_message(filters.command("bulkrename") & filters.private)
async def cmd_bulk_rename(client, message):
    uid = message.from_user.id
    limit, remaining = check_bulk_quota(uid)
    if remaining == 0:
        cap = BULK_LIMIT_PREMIUM if is_premium(uid) else BULK_LIMIT_FREE
        await message.reply(
            f"⏳ **Hourly Limit Reached**\n\n"
            f"You have used all {cap} bulk rename slots for this hour.\n"
            f"Quota resets within 60 minutes.\n\n"
            f"Contact **@fangheaven** to extend or upgrade.",
            reply_markup=premium_kb() if not is_premium(uid) else None
        )
        return
    limit_txt = "Unlimited" if is_admin(uid) else f"{int(remaining)} files remaining this hour"
    user_state[uid] = {"step": "bulk_collecting", "files": []}
    await message.reply(
        f"📦 **Bulk Rename Started**\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📊 **Quota:** {limit_txt}\n\n"
        f"Send all your files one by one.\n"
        f"Send /done when finished.\n\n"
        f"Files will be renamed in the order received 👇"
    )

def extract_num(filename):
    """Extract last number from filename — handles ch12, [12], 12, Chapter 12, Vol.2 Ch.15 etc."""
    name = os.path.splitext(filename)[0]
    numbers = re.findall(r'\d+', name)
    return int(numbers[-1]) if numbers else float('inf')

# ─────────────────────────────────────────
# /done COMMAND
# ─────────────────────────────────────────
@app.on_message(filters.command("done") & filters.private)
async def cmd_done(client, message):
    uid = message.from_user.id
    state = user_state.get(uid, {})
    if state.get("step") != "bulk_collecting":
        return
    files = state.get("files", [])
    if not files:
        await message.reply("No files received yet. Send your files first, then /done.")
        return

    # Auto-sort by number extracted from filename
    try:
        files_sorted = sorted(files, key=lambda f: extract_num(f["name"]))
        was_sorted = [f["name"] for f in files_sorted] != [f["name"] for f in files]
    except:
        files_sorted = files
        was_sorted = False

    state["files"] = files_sorted
    state["step"] = "bulk_wait_name"
    user_state[uid] = state

    sort_note = "\n\n🔢 **Auto-sorted by chapter number.**" if was_sorted else ""
    # Show first 5 in order for confirmation
    preview_lines = "\n".join(
        f"`{i+1}. {f['name']}`" for i, f in enumerate(files_sorted[:5])
    )
    if len(files_sorted) > 5:
        preview_lines += f"\n... and {len(files_sorted) - 5} more"

    await message.reply(
        f"✅ **{len(files_sorted)} file(s) collected.**{sort_note}\n\n"
        f"**Order they will be renamed:**\n{preview_lines}\n\n"
        f"Now send the **base name** for all files.\n\n"
        f"Example: `Tower of God`"
    )

# ─────────────────────────────────────────
# PHOTO HANDLER
# ─────────────────────────────────────────
@app.on_message(filters.photo & filters.private)
async def photo_handler(client, message):
    uid = message.from_user.id
    state = user_state.get(uid, {})
    if state.get("step") == "wait_thumbnail":
        user = get_user(uid)
        user["thumbnail_file_id"] = message.photo.file_id
        save_user(uid, user)
        user_state.pop(uid, None)
        await message.reply(
            "✅ **Thumbnail Saved**\n\n"
            "Locked in and ready. Your thumbnail will be applied\n"
            "automatically to every file you rename."
        )

# ─────────────────────────────────────────
# FILE HANDLER
# ─────────────────────────────────────────
@app.on_message((filters.document | filters.video) & filters.private)
async def file_handler(client, message):
    uid = message.from_user.id
    state = user_state.get(uid, {})
    step = state.get("step")
    file = message.document or message.video
    file_size_mb = file.file_size / (1024 * 1024)
    original_name = getattr(file, "file_name", None) or "file"

    if step == "bulk_collecting":
        _, remaining = check_bulk_quota(uid)
        files = state.get("files", [])
        if not is_admin(uid) and len(files) >= int(remaining):
            cap = BULK_LIMIT_PREMIUM if is_premium(uid) else BULK_LIMIT_FREE
            await message.reply(
                f"⚠️ **Quota Limit Reached**\n\n"
                f"Maximum **{cap} files per hour** on your plan.\n"
                f"This file was not added.\n\n"
                f"Send /done to process the {len(files)} files already received."
            )
            return
        files.append({
            "file_id": file.file_id,
            "name": original_name,
            "mime": getattr(file, "mime_type", "") or "",
            "size": file_size_mb
        })
        state["files"] = files
        user_state[uid] = state
        await message.reply(f"📥 **File {len(files)} added:** `{original_name}`\n\nSend more files or /done to continue.")
        return

    if step != "wait_file":
        return

    if file_size_mb > 100 and not is_premium(uid):
        await message.reply(
            f"⚠️ **File Size Exceeded**\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📦 Your file: **{file_size_mb:.1f} MB**\n"
            f"🚫 Free plan limit: **100 MB**\n\n"
            f"Upgrade to 👑 **Premium** for unlimited file size."
        )
        user_state.pop(uid, None)
        return

    user_state[uid] = {
        "step": "wait_newname",
        "file_id": file.file_id,
        "file_size": file_size_mb,
        "original_name": original_name,
        "mime_type": getattr(file, "mime_type", "") or "",
        "msg_id": message.id
    }
    await message.reply(
        f"✅ **File Received**\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📋 **Name:** `{original_name}`\n"
        f"📦 **Size:** `{file_size_mb:.2f} MB`\n\n"
        f"Send the **new filename** (without extension):"
    )

# ─────────────────────────────────────────
# TEXT HANDLER
# ─────────────────────────────────────────
@app.on_message(
    filters.text & filters.private &
    ~filters.command(["start", "admin", "addpremium", "rempremium", "bulkrename", "done"])
)
async def text_handler(client, message):
    uid = message.from_user.id
    text = message.text
    if text in RESERVED:
        return
    state = user_state.get(uid, {})
    step = state.get("step")

    if step == "adm_broadcast":
        db = load_db()
        user_state.pop(uid, None)
        sent = failed = 0
        prog = await message.reply("📢 **Broadcasting...** Please wait.")
        for user_id in db.keys():
            try:
                await app.send_message(int(user_id), text)
                sent += 1
                await asyncio.sleep(0.05)
            except:
                failed += 1
        await prog.edit_text(
            f"✅ **Broadcast Complete**\n\n"
            f"✔️ Delivered: `{sent}`\n"
            f"❌ Failed: `{failed}`"
        )

    elif step == "adm_addprem":
        user_state.pop(uid, None)
        try:
            parts = text.strip().split()
            target_id = int(parts[0])
            days = int(parts[1]) if len(parts) > 1 else 0
            user = get_user(target_id)
            user["premium"] = True
            user["premium_expiry"] = (datetime.now() + timedelta(days=days)).isoformat() if days > 0 else None
            save_user(target_id, user)
            label = f"{days} days" if days > 0 else "Lifetime"
            await message.reply(f"✅ **Premium Granted**\n\n🆔 User: `{target_id}`\n⏳ Duration: **{label}**")
        except Exception as e:
            await message.reply(f"❌ **Error:** `{e}`\n\nFormat: user_id days")

    elif step == "adm_remprem":
        user_state.pop(uid, None)
        try:
            target_id = int(text.strip())
            user = get_user(target_id)
            user["premium"] = False
            user["premium_expiry"] = None
            save_user(target_id, user)
            await message.reply(f"✅ **Premium Revoked** from `{target_id}`")
        except Exception as e:
            await message.reply(f"❌ **Error:** `{e}`")

    elif step == "adm_lookup":
        user_state.pop(uid, None)
        try:
            target_id = int(text.strip())
            user = get_user(target_id)
            badge = "👑 Premium" if user.get("premium") else "🆓 Free"
            expiry = user.get("premium_expiry") or "—"
            thumb = "✅ Set" if user.get("thumbnail_file_id") else "❌ Not set"
            quota = user.get("bulk_quota", {})
            await message.reply(
                f"🔍 **User Report**\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"🆔 **ID:** `{target_id}`\n"
                f"🏷️ **Plan:** {badge}\n"
                f"📅 **Expiry:** `{expiry}`\n"
                f"🖼️ **Thumbnail:** {thumb}\n"
                f"📦 **Bulk Used:** `{quota.get('used', 0)}`"
            )
        except Exception as e:
            await message.reply(f"❌ **Error:** `{e}`")

    elif step == "adm_reset":
        user_state.pop(uid, None)
        try:
            target_id = int(text.strip())
            db = load_db()
            if str(target_id) in db:
                del db[str(target_id)]
                save_db(db)
            await message.reply(f"💥 **User Reset Complete**\n\nAll data for `{target_id}` permanently wiped.")
        except Exception as e:
            await message.reply(f"❌ **Error:** `{e}`")

    elif step == "wait_text_font":
        user_state[uid] = {"step": "wait_font_choice", "text": text}
        await message.reply(text, reply_markup=font_kb())

    elif step == "wait_newname":
        state["new_name"] = text.strip()
        state["step"] = "wait_rename_go"
        user_state[uid] = state
        await do_rename(message, uid)

    elif step == "bulk_wait_name":
        state["base_name"] = text.strip()
        state["step"] = "bulk_wait_numbering"
        user_state[uid] = state
        await message.reply(
            f"✅ **Base name set:** `{text.strip()}`\n\n"
            f"Now send the **numbering range.**\n\n"
            f"Example: `1-100` starts numbering from 1\n"
            f"Example: `51-100` starts numbering from 51\n\n"
            f"Total files collected: **{len(state['files'])}**"
        )

    elif step == "bulk_wait_numbering":
        raw = text.strip()
        try:
            start = int(raw.split("-")[0].strip()) if "-" in raw else int(raw)
            state["start_num"] = start
            state["step"] = "bulk_preview"
            user_state[uid] = state
            await show_bulk_preview(message, uid)
        except:
            await message.reply("❌ Invalid format. Send like `1-100` or just `1`")

# ─────────────────────────────────────────
# BULK PREVIEW
# ─────────────────────────────────────────
async def show_bulk_preview(message, uid):
    state = user_state.get(uid, {})
    files = state["files"]
    base_name = state["base_name"]
    start = state["start_num"]
    total = len(files)
    _, orig_ext = os.path.splitext(files[0]["name"] if files else "file.pdf")
    ext = orig_ext if orig_ext else ".pdf"
    state["ext"] = ext
    user_state[uid] = state

    def line(i):
        return f"`[{start + i}] {base_name}{ext}`"

    lines = []
    if total <= 6:
        for i in range(total):
            lines.append(line(i))
    else:
        for i in range(3):
            lines.append(line(i))
        lines.append(f"... {total - 5} more files ...")
        for i in range(total - 2, total):
            lines.append(line(i))

    await message.reply(
        f"📋 **Rename Preview**\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📁 **Files:** {total}\n"
        f"🏷️ **Base Name:** `{base_name}`\n"
        f"🔢 **Numbering:** [{start}] to [{start + total - 1}]\n\n"
        f"{chr(10).join(lines)}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Confirm to start renaming 👇",
        reply_markup=bulk_confirm_kb()
    )

# ─────────────────────────────────────────
# BULK CONFIRM / CANCEL
# ─────────────────────────────────────────
@app.on_callback_query(filters.regex("^bulk_"))
async def bulk_callbacks(client, callback_query):
    uid = callback_query.from_user.id
    state = user_state.get(uid, {})
    data = callback_query.data

    if data == "bulk_cancel":
        user_state.pop(uid, None)
        await callback_query.message.edit_text("❌ **Bulk Rename Cancelled.**\n\nNo files were renamed.")
        return

    if data == "bulk_confirm":
        if state.get("step") != "bulk_preview":
            await callback_query.answer("Session expired. Start again.", show_alert=True)
            return

        files = state["files"]
        base_name = state["base_name"]
        start = state["start_num"]
        ext = state.get("ext", ".pdf")
        total = len(files)
        _, remaining = check_bulk_quota(uid)
        allowed = total if is_admin(uid) else min(total, int(remaining))

        user = get_user(uid)
        thumb_file_id = user.get("thumbnail_file_id")
        thumb_path = None
        if thumb_file_id:
            thumb_path = f"/tmp/thumb_{uid}.jpg"
            try:
                await client.download_media(thumb_file_id, file_name=thumb_path)
            except:
                thumb_path = None

        status_msg = callback_query.message
        await status_msg.edit_text(
            f"⚙️ **Bulk Renaming...**\n\n"
            f"`░░░░░░░░░░░░░░░░░░░░`\n\n"
            f"0 of {allowed} files done"
        )

        done = failed = 0

        for i, file_data in enumerate(files[:allowed]):
            final_name = f"[{start + i}] {base_name}{ext}"
            temp_dl = f"/tmp/bulk_dl_{uid}_{i}{ext}"
            temp_out = f"/tmp/bulk_out_{uid}_{i}{ext}"
            is_video = file_data.get("mime", "").startswith("video/")

            try:
                path = await client.download_media(file_data["file_id"], file_name=temp_dl)
                if not path or not os.path.exists(path):
                    failed += 1
                    continue
                os.rename(path, temp_out)
                if is_video:
                    await client.send_video(
                        chat_id=uid, video=temp_out,
                        caption=f"🎬 `{final_name}`",
                        file_name=final_name, thumb=thumb_path
                    )
                else:
                    await client.send_document(
                        chat_id=uid, document=temp_out,
                        caption=f"📄 `{final_name}`",
                        file_name=final_name, thumb=thumb_path
                    )
                done += 1
                pct = int(done / allowed * 100)
                filled = int(pct / 5)
                bar = "█" * filled + "░" * (20 - filled)
                try:
                    await status_msg.edit_text(
                        f"⚙️ **Bulk Renaming...**\n\n"
                        f"`{bar}`\n\n"
                        f"✅ {done} of {allowed} files done"
                    )
                except:
                    pass
            except Exception as e:
                failed += 1
                print(f"Bulk error file {i}: {e}")
            finally:
                for f in [temp_dl, temp_out]:
                    if os.path.exists(f):
                        try:
                            os.remove(f)
                        except:
                            pass

        consume_bulk_quota(uid, done)
        if thumb_path and os.path.exists(thumb_path):
            try:
                os.remove(thumb_path)
            except:
                pass

        user_state.pop(uid, None)
        skipped_msg = ""
        if allowed < total:
            skipped = total - allowed
            cap = BULK_LIMIT_FREE if not is_premium(uid) else BULK_LIMIT_PREMIUM
            skipped_msg = (
                f"\n\n⚠️ **{skipped} file(s) skipped** — hourly quota reached.\n"
                f"{'Upgrade to 👑 Premium for 100 files/hour — contact **@fangheaven**.' if not is_premium(uid) else 'Contact **@fangheaven** to extend your limit.'}"
            )

        await status_msg.edit_text(
            f"✅ **Bulk Rename Complete**\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"✔️ Renamed: **{done}** files\n"
            f"❌ Failed: **{failed}** files"
            f"{skipped_msg}",
            reply_markup=premium_kb() if allowed < total and not is_premium(uid) else None
        )

# ─────────────────────────────────────────
# SINGLE RENAME LOGIC
# ─────────────────────────────────────────
async def do_rename(message, uid):
    state = user_state.get(uid, {})
    new_name = state["new_name"]
    file_id = state["file_id"]
    original_name = state.get("original_name", "file")
    mime = state.get("mime_type", "")
    _, orig_ext = os.path.splitext(original_name)
    ext = orig_ext if orig_ext else ".pdf"
    final_name = new_name + ext
    is_video = mime.startswith("video/")

    user = get_user(uid)
    thumb_file_id = user.get("thumbnail_file_id")
    thumb_path = None
    if thumb_file_id:
        thumb_path = f"/tmp/thumb_{uid}.jpg"
        try:
            await app.download_media(thumb_file_id, file_name=thumb_path)
        except:
            thumb_path = None

    temp_download = f"/tmp/dl_{uid}_{state.get('msg_id', 0)}{ext}"
    temp_final = f"/tmp/out_{uid}_{state.get('msg_id', 0)}{ext}"

    status_msg = await message.reply(
        "⬇️ **Downloading...**\n\n"
        "`░░░░░░░░░░░░░░░░░░░░`\n\n"
        "Please wait..."
    )

    stop_dl = asyncio.Event()
    prog_task = asyncio.create_task(fake_progress(status_msg, "dl", stop_dl, file_size_mb))

    try:
        path = await app.download_media(file_id, file_name=temp_download)
        stop_dl.set()
        await prog_task

        if not path or not os.path.exists(path):
            await status_msg.edit_text("❌ **Download Failed.** Please try again.")
            return

        os.rename(path, temp_final)
        await status_msg.edit_text(
            "⬆️ **Uploading...**\n\n"
            "`░░░░░░░░░░░░░░░░░░░░`\n\n"
            "Please wait..."
        )

        stop_ul = asyncio.Event()
        prog_task2 = asyncio.create_task(fake_progress(status_msg, "ul", stop_ul, file_size_mb))

        if is_video:
            await app.send_video(chat_id=uid, video=temp_final,
                caption=f"🎬 `{final_name}`", file_name=final_name, thumb=thumb_path)
        else:
            await app.send_document(chat_id=uid, document=temp_final,
                caption=f"📄 `{final_name}`", file_name=final_name, thumb=thumb_path)

        stop_ul.set()
        await prog_task2

        await status_msg.edit_text(
            f"✅ **Rename Complete**\n\n"
            f"📄 `{final_name}` has been delivered.\n\n"
            f"Send another file to rename it 📁"
        )
        user_state[uid] = {"step": "wait_file"}

    except Exception as e:
        stop_dl.set()
        await status_msg.edit_text(f"❌ **Error:** `{e}`")
        user_state.pop(uid, None)
    finally:
        for f in [temp_download, temp_final, thumb_path]:
            if f and os.path.exists(f):
                try:
                    os.remove(f)
                except:
                    pass

# ─────────────────────────────────────────
# FONT CALLBACK
# ─────────────────────────────────────────
@app.on_callback_query(filters.regex("^font_"))
async def font_callback(client, callback_query):
    uid = callback_query.from_user.id
    state = user_state.get(uid, {})
    if state.get("step") != "wait_font_choice":
        await callback_query.answer("Please send your text first.", show_alert=True)
        return
    converted = convert_font(state.get("text", ""), callback_query.data)
    try:
        await callback_query.message.edit_text(converted, reply_markup=font_kb())
        await callback_query.answer("Style applied!")
    except Exception as e:
        await callback_query.answer(f"Error: {e}", show_alert=True)

@app.on_callback_query(filters.regex("^back_main$"))
async def cb_back(client, callback_query):
    user_state.pop(callback_query.from_user.id, None)
    await callback_query.message.delete()

# ─────────────────────────────────────────
# LEGACY ADMIN COMMANDS
# ─────────────────────────────────────────
@app.on_message(filters.command("addpremium") & filters.user(ADMINS))
async def add_premium(client, message):
    try:
        parts = message.command
        target_id = int(parts[1])
        days = int(parts[2]) if len(parts) > 2 else 0
        user = get_user(target_id)
        user["premium"] = True
        user["premium_expiry"] = (datetime.now() + timedelta(days=days)).isoformat() if days > 0 else None
        save_user(target_id, user)
        label = f"{days} days" if days > 0 else "Lifetime"
        await message.reply(f"✅ Premium granted to `{target_id}` — **{label}**")
    except Exception as e:
        await message.reply(f"❌ Error: {e}")

@app.on_message(filters.command("rempremium") & filters.user(ADMINS))
async def rem_premium(client, message):
    try:
        target_id = int(message.command[1])
        user = get_user(target_id)
        user["premium"] = False
        user["premium_expiry"] = None
        save_user(target_id, user)
        await message.reply(f"✅ Premium removed from `{target_id}`")
    except Exception as e:
        await message.reply(f"❌ Error: {e}")

# ─────────────────────────────────────────
# RUN
# ─────────────────────────────────────────
load_img_cache()
print("HeavenFall Utility Bot is Alive...")
app.run()
