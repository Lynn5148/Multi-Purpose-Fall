import os
import json
import asyncio
from pyrogram import Client, filters
from pyrogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
)
from config import *
from fonts import convert_font
from datetime import datetime, timedelta

app = Client("utilbot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

user_state = {}
DB_FILE = "users_db.json"

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

# ─────────────────────────────────────────
# PROGRESS — manual update every 3 seconds
# ─────────────────────────────────────────
async def progress(current, total, status_msg, action):
    percent = (current / total) * 100
    filled = int(percent / 5)
    bar = "▓" * filled + "░" * (20 - filled)
    emoji = "⬇️" if action == "dl" else "⬆️"
    label = "Downloading" if action == "dl" else "Uploading"
    size_done = current / (1024 * 1024)
    size_total = total / (1024 * 1024)
    try:
        await status_msg.edit_text(
            f"{emoji} **{label}...**\n\n"
            f"`{bar}`\n\n"
            f"**{percent:.1f}%** — {size_done:.2f} MB / {size_total:.2f} MB"
        )
    except:
        pass

# ─────────────────────────────────────────
# KEYBOARDS
# ─────────────────────────────────────────
def main_reply_kb():
    """Permanent bottom keyboard — always visible"""
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("📁 Rename File"), KeyboardButton("🔤 Font Changer")],
            [KeyboardButton("🖼️ Set Thumbnail"), KeyboardButton("👁️ View Thumbnail")],
            [KeyboardButton("❌ Clear Thumbnail"), KeyboardButton("ℹ️ My Status")],
            [KeyboardButton("👑 Premium")]
        ],
        resize_keyboard=True
    )

def format_reply_kb():
    """Bottom keyboard for format selection"""
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("📄 Document"), KeyboardButton("🎬 Video")],
            [KeyboardButton("❌ Cancel")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
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
        [InlineKeyboardButton("🔙 Back to Menu", callback_data="back_main")]
    ])

def premium_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💎 Buy Premium — Contact @fangheaven", url="https://t.me/fangheaven")],
        [InlineKeyboardButton("🔙 Back", callback_data="back_main")]
    ])

# ─────────────────────────────────────────
# /start
# ─────────────────────────────────────────
@app.on_message(filters.command("start") & filters.private)
async def start(client, message):
    badge = "👑 **PREMIUM**" if is_premium(message.from_user.id) else "🆓 **FREE**"
    await message.reply(
        f"✨ **Welcome to HeavenFall Utility Bot** ✨\n\n"
        f"Your all-in-one tool for file renaming,\nfont conversion & more.\n\n"
        f"Status: {badge}\n\n"
        f"Use the buttons below 👇",
        reply_markup=main_reply_kb()
    )

# ─────────────────────────────────────────
# MAIN REPLY KEYBOARD HANDLER
# ─────────────────────────────────────────
MAIN_KB_BUTTONS = [
    "📁 Rename File", "🔤 Font Changer",
    "🖼️ Set Thumbnail", "👁️ View Thumbnail",
    "❌ Clear Thumbnail", "ℹ️ My Status", "👑 Premium"
]

@app.on_message(filters.text & filters.private & filters.regex(
    "^(📁 Rename File|🔤 Font Changer|🖼️ Set Thumbnail|👁️ View Thumbnail|❌ Clear Thumbnail|ℹ️ My Status|👑 Premium)$"
))
async def main_kb_handler(client, message):
    uid = message.from_user.id
    text = message.text

    if text == "📁 Rename File":
        user_state[uid] = {"step": "wait_file"}
        await message.reply(
            "📁 **File Renamer**\n\n"
            "Send me the file you want to rename.\n\n"
            "⚠️ Free limit: **100MB max**\n"
            "👑 Premium: **Unlimited size**"
        )

    elif text == "🔤 Font Changer":
        user_state[uid] = {"step": "wait_text_font"}
        await message.reply("🔤 **Font Changer**\n\nSend me the text you want to convert:")

    elif text == "🖼️ Set Thumbnail":
        user_state[uid] = {"step": "wait_thumbnail"}
        await message.reply(
            "🖼️ **Set Thumbnail**\n\n"
            "Send me a photo to use as your default thumbnail.\n"
            "It will be applied to all your renamed files."
        )

    elif text == "👁️ View Thumbnail":
        user = get_user(uid)
        thumb_id = user.get("thumbnail_file_id")
        if not thumb_id:
            await message.reply("❌ No thumbnail set yet.")
        else:
            await message.reply_photo(photo=thumb_id, caption="🖼️ **Your current thumbnail**")

    elif text == "❌ Clear Thumbnail":
        user = get_user(uid)
        user["thumbnail_file_id"] = None
        save_user(uid, user)
        await message.reply("✅ Thumbnail cleared.")

    elif text == "ℹ️ My Status":
        user = get_user(uid)
        badge = "👑 PREMIUM" if is_premium(uid) else "🆓 FREE"
        thumb = "✅ Set" if user.get("thumbnail_file_id") else "❌ Not set"
        expiry = user.get("premium_expiry") or "—"
        await message.reply(
            f"📊 **Your Status**\n\n"
            f"🏷️ Plan: **{badge}**\n"
            f"📅 Premium expiry: `{expiry}`\n"
            f"🖼️ Thumbnail: {thumb}"
        )

    elif text == "👑 Premium":
        if is_premium(uid):
            user = get_user(uid)
            expiry = user.get("premium_expiry") or "Lifetime"
            await message.reply(f"👑 **You are already PREMIUM!**\n\nExpiry: `{expiry}`")
        else:
            await message.reply(
                "👑 **HeavenFall Premium**\n\n"
                "━━━━━━━━━━━━━━━━━━\n"
                "✅ Rename files **above 100MB**\n"
                "✅ Unlimited font conversions\n"
                "✅ Priority support\n"
                "✅ Exclusive future features\n"
                "━━━━━━━━━━━━━━━━━━\n\n"
                "To purchase, contact **@fangheaven** 👇",
                reply_markup=premium_kb()
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
        await message.reply("✅ **Thumbnail saved!** It will be applied to your renamed files.")

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
            f"⚠️ **File too large!**\n\n"
            f"Size: **{file_size_mb:.1f}MB** — Free limit is **100MB**.\n\n"
            f"Tap 👑 Premium to unlock unlimited size.",
        )
        user_state.pop(uid, None)
        return

    original_name = getattr(file, "file_name", None) or "file"
    user_state[uid] = {
        "step": "wait_newname",
        "file_id": file.file_id,
        "file_size": file_size_mb,
        "original_name": original_name,
        "mime_type": getattr(file, "mime_type", "") or ""
    }
    await message.reply(
        f"📁 **File received!**\n\n"
        f"📋 Name: `{original_name}`\n"
        f"📦 Size: `{file_size_mb:.2f} MB`\n\n"
        f"Send me the **new name** (without extension):"
    )

# ─────────────────────────────────────────
# TEXT HANDLER — general
# ─────────────────────────────────────────
@app.on_message(
    filters.text & filters.private &
    ~filters.command(["start", "addpremium", "rempremium"]) &
    ~filters.regex("^(📁 Rename File|🔤 Font Changer|🖼️ Set Thumbnail|👁️ View Thumbnail|❌ Clear Thumbnail|ℹ️ My Status|👑 Premium|📄 Document|🎬 Video|❌ Cancel)$")
)
async def text_handler(client, message):
    uid = message.from_user.id
    state = user_state.get(uid, {})
    step = state.get("step")

    if step == "wait_text_font":
        user_state[uid] = {"step": "wait_font_choice", "text": message.text}
        await message.reply(message.text, reply_markup=font_kb())

    elif step == "wait_newname":
        state["new_name"] = message.text.strip()
        state["step"] = "wait_format"
        user_state[uid] = state
        await message.reply(
            f"✅ New name: **{message.text.strip()}**\n\nChoose output format:",
            reply_markup=format_reply_kb()
        )

# ─────────────────────────────────────────
# FORMAT CHOICE — reply keyboard
# ─────────────────────────────────────────
@app.on_message(
    filters.text & filters.private &
    filters.regex("^(📄 Document|🎬 Video|❌ Cancel)$")
)
async def format_choice_handler(client, message):
    uid = message.from_user.id
    state = user_state.get(uid, {})

    if state.get("step") != "wait_format":
        return

    if message.text == "❌ Cancel":
        user_state.pop(uid, None)
        await message.reply("❌ Cancelled.", reply_markup=main_reply_kb())
        return

    fmt = "document" if message.text == "📄 Document" else "video"
    new_name = state["new_name"]
    file_id = state["file_id"]
    original_name = state.get("original_name", "file")

    _, orig_ext = os.path.splitext(original_name)
    ext = ".mp4" if fmt == "video" else (orig_ext if orig_ext else ".pdf")
    final_name = new_name + ext

    # Thumbnail — download from file_id to /tmp
    user = get_user(uid)
    thumb_file_id = user.get("thumbnail_file_id")
    thumb_path = None
    if thumb_file_id:
        thumb_path = f"/tmp/thumb_{uid}.jpg"
        try:
            await client.download_media(thumb_file_id, file_name=thumb_path)
        except:
            thumb_path = None

    # Unique temp paths per user+file
    temp_download = f"/tmp/dl_{uid}_{message.id}{orig_ext or '.bin'}"
    temp_final = f"/tmp/out_{uid}_{message.id}{ext}"

    status_msg = await message.reply(
        "⬇️ **Downloading...**\n\n"
        "`░░░░░░░░░░░░░░░░░░░░`\n\n"
        "**0.0%** — 0.00 MB / 0.00 MB",
        reply_markup=main_reply_kb()
    )

    try:
        path = await client.download_media(
            file_id,
            file_name=temp_download,
            progress=progress,
            progress_args=(status_msg, "dl")
        )

        if not path or not os.path.exists(path):
            await status_msg.edit_text("❌ Download failed. Please try again.")
            return

        # Rename the file
        os.rename(path, temp_final)

        await status_msg.edit_text(
            "⬆️ **Uploading...**\n\n"
            "`░░░░░░░░░░░░░░░░░░░░`\n\n"
            "**0.0%** — 0.00 MB / 0.00 MB"
        )

        if fmt == "video":
            await client.send_video(
                chat_id=uid,
                video=temp_final,
                caption=f"🎬 `{final_name}`",
                file_name=final_name,
                thumb=thumb_path,
                progress=progress,
                progress_args=(status_msg, "ul")
            )
        else:
            await client.send_document(
                chat_id=uid,
                document=temp_final,
                caption=f"📄 `{final_name}`",
                file_name=final_name,
                thumb=thumb_path,
                progress=progress,
                progress_args=(status_msg, "ul")
            )

        await status_msg.edit_text(
            f"✅ **Done!**\n\n`{final_name}` sent successfully."
        )

    except Exception as e:
        await status_msg.edit_text(f"❌ Error: `{e}`")

    finally:
        for f in [temp_download, temp_final, thumb_path]:
            if f and os.path.exists(f):
                try:
                    os.remove(f)
                except:
                    pass
        user_state.pop(uid, None)

# ─────────────────────────────────────────
# FONT CALLBACK
# ─────────────────────────────────────────
@app.on_callback_query(filters.regex("^font_"))
async def font_callback(client, callback_query):
    uid = callback_query.from_user.id
    state = user_state.get(uid, {})

    if state.get("step") != "wait_font_choice":
        await callback_query.answer("Send text first.", show_alert=True)
        return

    font_key = callback_query.data
    original = state.get("text", "")
    converted = convert_font(original, font_key)

    try:
        await callback_query.message.edit_text(converted, reply_markup=font_kb())
        await callback_query.answer("✅ Font applied!")
    except Exception as e:
        await callback_query.answer(f"Error: {e}", show_alert=True)

@app.on_callback_query(filters.regex("^back_main$"))
async def cb_back(client, callback_query):
    user_state.pop(callback_query.from_user.id, None)
    await callback_query.message.delete()

# ─────────────────────────────────────────
# ADMIN: ADD / REMOVE PREMIUM
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

print("HeavenFall Utility Bot is Alive...")
app.run()