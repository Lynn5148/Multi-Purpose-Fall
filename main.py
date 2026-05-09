import os
import json
import asyncio
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

# ─────────────────────────────────────────
# IMAGE URLS
# ─────────────────────────────────────────
IMAGE_URLS = {
    "start":    "https://plain-apac-prod-public.komododecks.com/202605/06/XUaMU1y29VBWnGl3SjeP/image.jpg",
    "rename":   "https://plain-apac-prod-public.komododecks.com/202605/06/QmxtOBa2q9EIum9HNdZQ/image.jpg",
    "font":     "https://plain-apac-prod-public.komododecks.com/202605/06/alQ822mcjFA0h3mE2NW8/image.jpg",
    "premium":  "https://plain-apac-prod-public.komododecks.com/202605/06/OeNb54pavQiCP3azq9Z4/image.jpg",
    "channels": "https://plain-apac-prod-public.komododecks.com/202605/06/mOEaW5Vv5syrRuKbessY/image.jpg",
}

IMG_CACHE = {}

def load_img_cache():
    global IMG_CACHE
    if os.path.exists(IMG_CACHE_FILE):
        try:
            with open(IMG_CACHE_FILE, "r") as f:
                IMG_CACHE = json.load(f)
        except:
            IMG_CACHE = {}

def save_img_cache():
    with open(IMG_CACHE_FILE, "w") as f:
        json.dump(IMG_CACHE, f)

async def get_img(key, client, fallback_chat_id):
    """Lazy load — cache on first use, reuse file_id forever after."""
    if key in IMG_CACHE:
        return IMG_CACHE[key]

    url = IMAGE_URLS.get(key)
    if not url:
        return None

    try:
        path = f"/tmp/img_{key}.jpg"
        urllib.request.urlretrieve(url, path)
        msg = await client.send_photo(
            chat_id=fallback_chat_id,
            photo=path,
            caption=f"[IMG CACHE: {key}]"
        )
        file_id = msg.photo.file_id
        IMG_CACHE[key] = file_id
        save_img_cache()
        os.remove(path)
        return file_id
    except Exception as e:
        print(f"❌ Image cache failed for {key}: {e}")
        return None

async def send_img(message, key, caption, reply_markup=None):
    """Send cached photo or fallback to text only."""
    file_id = await get_img(key, message._client, message.from_user.id)
    if file_id:
        try:
            await message.reply_photo(
                photo=file_id,
                caption=caption,
                reply_markup=reply_markup
            )
            return
        except Exception as e:
            print(f"❌ send_img failed: {e}")
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
        db[uid] = {"premium": False, "premium_expiry": None, "thumbnail_file_id": None}
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
        expiry = datetime.fromisoformat(user["premium_expiry"])
        if datetime.now() > expiry:
            user["premium"] = False
            user["premium_expiry"] = None
            save_user(user_id, user)
            return False
    return True

def get_stats():
    db = load_db()
    total = len(db)
    premium = sum(1 for u in db.values() if u.get("premium"))
    return total, premium

# ─────────────────────────────────────────
# FAKE PROGRESS
# ─────────────────────────────────────────
async def fake_progress(status_msg, action, stop_event):
    steps = [0, 8, 18, 28, 40, 52, 63, 72, 80, 87, 92, 96]
    emoji = "⬇️" if action == "dl" else "⬆️"
    label = "Downloading" if action == "dl" else "Uploading"
    for pct in steps:
        if stop_event.is_set():
            break
        filled = int(pct / 5)
        bar = "▓" * filled + "░" * (20 - filled)
        try:
            await status_msg.edit_text(
                f"{emoji} **{label}...**\n\n"
                f"`{bar}`\n\n"
                f"**{pct}%** complete"
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
            [KeyboardButton("📁 Rename File"), KeyboardButton("🔤 Font Changer")],
            [KeyboardButton("🖼️ Set Thumbnail"), KeyboardButton("👁️ View Thumbnail")],
            [KeyboardButton("❌ Clear Thumbnail"), KeyboardButton("ℹ️ My Status")],
            [KeyboardButton("👑 Premium"), KeyboardButton("🌐 HeavenFall Channels")]
        ],
        resize_keyboard=True
    )

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
        [InlineKeyboardButton("💎 Purchase Premium — @fangheaven", url="https://t.me/fangheaven")],
    ])

def admin_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Stats", callback_data="adm_stats"),
         InlineKeyboardButton("📢 Broadcast", callback_data="adm_broadcast")],
        [InlineKeyboardButton("👑 Add Premium", callback_data="adm_addprem"),
         InlineKeyboardButton("🗑️ Remove Premium", callback_data="adm_remprem")],
        [InlineKeyboardButton("🔍 User Lookup", callback_data="adm_lookup"),
         InlineKeyboardButton("💥 Reset User", callback_data="adm_reset")],
        [InlineKeyboardButton("🔒 Close Panel", callback_data="adm_close")]
    ])

# ─────────────────────────────────────────
# /start
# ─────────────────────────────────────────
@app.on_message(filters.command("start") & filters.private)
async def start(client, message):
    uid = message.from_user.id
    name = message.from_user.first_name or "there"
    badge = "👑 Premium Member" if is_premium(uid) else "🆓 Free Plan"
    await send_img(
        message, "start",
        caption=(
            f"✦ **HeavenFall Utility Bot** ✦\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"Welcome, **{name}**. 👋\n\n"
            f"Your precision toolkit for Telegram —\n"
            f"built for speed, style, and simplicity.\n\n"
            f"🏷️ **Account Plan:** {badge}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"**What I can do:**\n\n"
            f"📁 **Rename** files with a custom name & thumbnail\n"
            f"🔤 **Convert** text into premium font styles\n"
            f"🖼️ **Store** a permanent thumbnail for all files\n"
            f"🌐 **Explore** all HeavenFall channels\n"
            f"👑 **Upgrade** for unlimited access\n\n"
            f"_Select a feature from the menu below_ 👇"
        ),
        reply_markup=main_reply_kb()
    )

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
            "Compose your message below.\n"
            "It will be delivered to **all users** instantly.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="adm_back")]])
        )

    elif data == "adm_addprem":
        user_state[uid] = {"step": "adm_addprem"}
        await callback_query.message.edit_text(
            "👑 **Grant Premium Access**\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "Send: `<user_id> <days>`\n\n"
            "📌 Examples:\n"
            "`123456789 30` → 30 days\n"
            "`123456789 0` → Lifetime",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="adm_back")]])
        )

    elif data == "adm_remprem":
        user_state[uid] = {"step": "adm_remprem"}
        await callback_query.message.edit_text(
            "🗑️ **Revoke Premium Access**\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "Send the `user_id` to revoke their premium:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="adm_back")]])
        )

    elif data == "adm_lookup":
        user_state[uid] = {"step": "adm_lookup"}
        await callback_query.message.edit_text(
            "🔍 **User Lookup**\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "Send the `user_id` to inspect their account:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="adm_back")]])
        )

    elif data == "adm_reset":
        user_state[uid] = {"step": "adm_reset"}
        await callback_query.message.edit_text(
            "💥 **Reset User Account**\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "⚠️ This **permanently wipes** all data for the user.\n\n"
            "Send the `user_id` to proceed:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="adm_back")]])
        )

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
# MAIN REPLY KEYBOARD HANDLER
# ─────────────────────────────────────────
RESERVED = [
    "📁 Rename File", "🔤 Font Changer", "🖼️ Set Thumbnail",
    "👁️ View Thumbnail", "❌ Clear Thumbnail", "ℹ️ My Status",
    "👑 Premium", "🌐 HeavenFall Channels"
]

@app.on_message(filters.text & filters.private & filters.regex(
    "^(📁 Rename File|🔤 Font Changer|🖼️ Set Thumbnail|👁️ View Thumbnail"
    "|❌ Clear Thumbnail|ℹ️ My Status|👑 Premium|🌐 HeavenFall Channels)$"
))
async def main_kb_handler(client, message):
    uid = message.from_user.id
    text = message.text

    if text == "📁 Rename File":
        user_state[uid] = {"step": "wait_file"}
        await send_img(
            message, "rename",
            caption=(
                "📁 **File Renamer**\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                "Send your file and I'll rename it with precision.\n\n"
                "📦 **Free Plan:** Up to **100 MB**\n"
                "👑 **Premium:** Unlimited file size\n\n"
                "_Drop your file below to begin_ 👇"
            )
        )

    elif text == "🔤 Font Changer":
        user_state[uid] = {"step": "wait_text_font"}
        await send_img(
            message, "font",
            caption=(
                "🔤 **Font Changer**\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                "Elevate your text with **premium Unicode font styles**.\n\n"
                "✍️ Type anything — titles, names, captions —\n"
                "and transform them instantly.\n\n"
                "_Send your text to continue_ 👇"
            )
        )

    elif text == "🖼️ Set Thumbnail":
        user_state[uid] = {"step": "wait_thumbnail"}
        await send_img(
            message, "rename",
            caption=(
                "🖼️ **Set Thumbnail**\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                "Upload a photo to set as your **permanent default thumbnail**.\n\n"
                "📌 Applied automatically to every file you rename.\n\n"
                "_Send your photo now_ 👇"
            )
        )

    elif text == "👁️ View Thumbnail":
        user = get_user(uid)
        thumb_id = user.get("thumbnail_file_id")
        if not thumb_id:
            await message.reply(
                "🖼️ **No Thumbnail Configured**\n\n"
                "You haven't set a thumbnail yet.\n\n"
                "Tap **🖼️ Set Thumbnail** to upload one."
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
        await send_img(
            message, "font",
            caption=(
                f"📊 **Account Status**\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"🏷️ **Plan:** {badge}\n"
                f"📅 **Expiry:** `{expiry}`\n"
                f"🖼️ **Thumbnail:** {thumb}\n\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"_Tap 👑 Premium to unlock full access_"
            )
        )

    elif text == "👑 Premium":
        if is_premium(uid):
            user = get_user(uid)
            expiry = user.get("premium_expiry") or "Lifetime"
            await send_img(
                message, "premium",
                caption=(
                    f"👑 **Premium Member**\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"You have **full access** to all HeavenFall features.\n\n"
                    f"📅 **Expiry:** `{expiry}`\n\n"
                    f"_Thank you for being a part of HeavenFall._ 💫"
                )
            )
        else:
            await send_img(
                message, "premium",
                caption=(
                    "👑 **HeavenFall Premium**\n"
                    "━━━━━━━━━━━━━━━━━━━━\n\n"
                    "Unlock the full HeavenFall experience:\n\n"
                    "✅ Rename files **above 100 MB**\n"
                    "✅ Unlimited font conversions\n"
                    "✅ Auto-thumbnail on every file\n"
                    "✅ Priority support\n"
                    "✅ Access to all future features\n\n"
                    "━━━━━━━━━━━━━━━━━━━━\n"
                    "💬 Contact **@fangheaven** to get started 👇"
                ),
                reply_markup=premium_kb()
            )

    elif text == "🌐 HeavenFall Channels":
        await send_img(
            message, "channels",
            caption=(
                "🌐 **HeavenFall Network**\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                "🔞 **Premium Adult Content — Free of Charge**\n\n"
                "Join our exclusive channels below.\n"
                "Fresh content dropped daily across all categories.\n\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "👇 **Tap any channel to join instantly**"
            ),
            reply_markup=channels_kb()
        )

# ─────────────────────────────────────────
# THUMBNAIL PHOTO HANDLER
# ─────────────────────────────────────────
@app.on_message(filters.photo & filters.private)
async def photo_handler(client, message):
    uid = message.from_user.id
    state = user_state.get(uid, {})
    if state.get("step") == "wait_thumbnail":
        file_id = message.photo.file_id
        user = get_user(uid)
        user["thumbnail_file_id"] = file_id
        save_user(uid, user)
        user_state.pop(uid, None)
        await message.reply(
            "✅ **Thumbnail Saved**\n\n"
            "Locked in and ready. Your thumbnail will be applied\n"
            "automatically to every file you rename. 🔒"
        )

# ─────────────────────────────────────────
# FILE HANDLER
# ─────────────────────────────────────────
@app.on_message((filters.document | filters.video) & filters.private)
async def file_handler(client, message):
    uid = message.from_user.id
    state = user_state.get(uid, {})
    if state.get("step") != "wait_file":
        return

    file = message.document or message.video
    file_size_mb = file.file_size / (1024 * 1024)

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

    original_name = getattr(file, "file_name", None) or "file"
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
        f"✏️ Send me the **new filename** _(without extension)_:"
    )

# ─────────────────────────────────────────
# TEXT HANDLER
# ─────────────────────────────────────────
@app.on_message(
    filters.text & filters.private &
    ~filters.command(["start", "admin", "addpremium", "rempremium"])
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
        sent = 0
        failed = 0
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
            await message.reply(
                f"✅ **Premium Granted**\n\n"
                f"🆔 User: `{target_id}`\n"
                f"⏳ Duration: **{label}**"
            )
        except Exception as e:
            await message.reply(f"❌ **Error:** `{e}`\n\nFormat: `<user_id> <days>`")

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
            await message.reply(
                f"🔍 **User Report**\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"🆔 **ID:** `{target_id}`\n"
                f"🏷️ **Plan:** {badge}\n"
                f"📅 **Expiry:** `{expiry}`\n"
                f"🖼️ **Thumbnail:** {thumb}"
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
            await message.reply(
                f"💥 **User Reset Complete**\n\n"
                f"All data for `{target_id}` has been permanently wiped."
            )
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

# ─────────────────────────────────────────
# RENAME LOGIC
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
    prog_task = asyncio.create_task(fake_progress(status_msg, "dl", stop_dl))

    try:
        path = await app.download_media(file_id, file_name=temp_download)
        stop_dl.set()
        await prog_task

        if not path or not os.path.exists(path):
            await status_msg.edit_text(
                "❌ **Download Failed**\n\nUnable to retrieve your file. Please try again."
            )
            return

        os.rename(path, temp_final)

        await status_msg.edit_text(
            "⬆️ **Uploading...**\n\n"
            "`░░░░░░░░░░░░░░░░░░░░`\n\n"
            "Please wait..."
        )

        stop_ul = asyncio.Event()
        prog_task2 = asyncio.create_task(fake_progress(status_msg, "ul", stop_ul))

        if is_video:
            await app.send_video(
                chat_id=uid,
                video=temp_final,
                caption=f"🎬 `{final_name}`",
                file_name=final_name,
                thumb=thumb_path
            )
        else:
            await app.send_document(
                chat_id=uid,
                document=temp_final,
                caption=f"📄 `{final_name}`",
                file_name=final_name,
                thumb=thumb_path
            )

        stop_ul.set()
        await prog_task2

        await status_msg.edit_text(
            f"✅ **Rename Complete**\n\n"
            f"📄 `{final_name}` has been delivered.\n\n"
            f"_Send another file to rename it_ 📁"
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

    font_key = callback_query.data
    original = state.get("text", "")
    converted = convert_font(original, font_key)

    try:
        await callback_query.message.edit_text(converted, reply_markup=font_kb())
        await callback_query.answer("✅ Style applied!")
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
        await message.reply(f"❌ Usage: `/addpremium <user_id> <days>`\nError: {e}")

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
        await message.reply(f"❌ Usage: `/rempremium <user_id>`\nError: {e}")

# ─────────────────────────────────────────
# RUN
# ─────────────────────────────────────────
load_img_cache()
print("HeavenFall Utility Bot is Alive...")
app.run()
