import os
import json
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
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
        db[uid] = {"premium": False, "premium_expiry": None, "thumbnail": None, "usage": {"rename": 0, "font": 0}}
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
    if user["premium_expiry"]:
        expiry = datetime.fromisoformat(user["premium_expiry"])
        if datetime.now() > expiry:
            user["premium"] = False
            user["premium_expiry"] = None
            save_user(user_id, user)
            return False
    return True

# ─────────────────────────────────────────
# KEYBOARDS
# ─────────────────────────────────────────
def main_menu_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📁 Rename File", callback_data="menu_rename"),
         InlineKeyboardButton("🔤 Font Changer", callback_data="menu_font")],
        [InlineKeyboardButton("🖼️ Set Thumbnail", callback_data="menu_thumbnail"),
         InlineKeyboardButton("❌ Clear Thumbnail", callback_data="clear_thumb")],
        [InlineKeyboardButton("👑 Premium", callback_data="menu_premium"),
         InlineKeyboardButton("ℹ️ My Status", callback_data="menu_status")]
    ])

def font_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("𝗦𝗮𝗻𝘀 𝗕𝗼𝗹𝗱", callback_data="font_sans_bold"),
         InlineKeyboardButton("𝙎𝙖𝙣𝙨 𝘽𝙄", callback_data="font_sans_bold_italic"),
         InlineKeyboardButton("𝘚𝘢𝘯𝘀 𝘐𝘵𝘢𝘭𝘪𝘤", callback_data="font_sans_italic")],
        [InlineKeyboardButton("𝐒𝐞𝐫𝐢𝐟 𝐁𝐨𝐥𝐝", callback_data="font_serif_bold"),
         InlineKeyboardButton("𝑩𝒐𝒍𝒅 𝑰𝒕𝒂𝒍𝒊𝒄", callback_data="font_bold_italic_serif"),
         InlineKeyboardButton("𝙼𝚘𝚗𝚘𝚜𝚙𝚊𝚌𝚎", callback_data="font_mono")],
        [InlineKeyboardButton("ꜱᴍᴀʟʟ ᴄᴀᴘꜱ", callback_data="font_small_caps"),
         InlineKeyboardButton("Mɪxed Cᴀps", callback_data="font_mixed_caps"),
         InlineKeyboardButton("𝘐𝘵𝘢𝘭𝘪𝘤 𝘚𝘦𝘳𝘪𝘧", callback_data="font_italic_serif")],
        [InlineKeyboardButton("𝓒𝓾𝓻𝓼𝓲𝓿𝓮", callback_data="font_cursive"),
         InlineKeyboardButton("Ｆｕｌｌｗｉｄｔｈ", callback_data="font_fullwidth"),
         InlineKeyboardButton("ᴮᵘᵇᵇˡᵉ", callback_data="font_superscript")],
        [InlineKeyboardButton("𝔉𝔯𝔞𝔨𝔱𝔲𝔯", callback_data="font_fraktur"),
         InlineKeyboardButton("𝕺𝖑𝖉 𝕰𝖓𝖌𝖑𝖎𝖘𝖍", callback_data="font_gothic"),
         InlineKeyboardButton("🅑🅛🅞🅒🅚", callback_data="font_block")],
        [InlineKeyboardButton("🔙 Back", callback_data="back_main")]
    ])

def rename_format_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📄 Document", callback_data="fmt_document"),
         InlineKeyboardButton("🎬 Video", callback_data="fmt_video")],
        [InlineKeyboardButton("🔙 Cancel", callback_data="back_main")]
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
    user = get_user(message.from_user.id)
    badge = "👑 **PREMIUM**" if is_premium(message.from_user.id) else "🆓 **FREE**"
    await message.reply(
        f"✨ **Welcome to HeavenFall Utility Bot** ✨\n\n"
        f"Your all-in-one tool for file renaming,\nfont conversion & more.\n\n"
        f"Status: {badge}\n\n"
        f"Select an option below 👇",
        reply_markup=main_menu_kb()
    )

# ─────────────────────────────────────────
# MENU CALLBACKS
# ─────────────────────────────────────────
@app.on_callback_query(filters.regex("^menu_rename$"))
async def cb_rename(client, callback_query):
    user_state[callback_query.from_user.id] = {"step": "wait_file"}
    await callback_query.message.edit_text(
        "📁 **File Renamer**\n\n"
        "Send me the file you want to rename.\n\n"
        "⚠️ Free limit: **100MB max**\n"
        "👑 Premium: **Unlimited size**",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Cancel", callback_data="back_main")]])
    )

@app.on_callback_query(filters.regex("^menu_font$"))
async def cb_font(client, callback_query):
    user_state[callback_query.from_user.id] = {"step": "wait_text_font"}
    await callback_query.message.edit_text(
        "🔤 **Font Changer**\n\nSend me the text you want to convert:",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Cancel", callback_data="back_main")]])
    )

@app.on_callback_query(filters.regex("^menu_thumbnail$"))
async def cb_thumbnail(client, callback_query):
    user_state[callback_query.from_user.id] = {"step": "wait_thumbnail"}
    await callback_query.message.edit_text(
        "🖼️ **Set Thumbnail**\n\n"
        "Send me a photo to use as your default thumbnail.\n"
        "It will be applied to all your renamed PDFs automatically.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Cancel", callback_data="back_main")]])
    )

@app.on_callback_query(filters.regex("^clear_thumb$"))
async def cb_clear_thumb(client, callback_query):
    user = get_user(callback_query.from_user.id)
    user["thumbnail"] = None
    save_user(callback_query.from_user.id, user)
    await callback_query.answer("✅ Thumbnail cleared!", show_alert=True)
    await callback_query.message.edit_text(
        "✅ Thumbnail removed.\n\nYour files will be sent without a custom thumbnail.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back_main")]])
    )

@app.on_callback_query(filters.regex("^menu_premium$"))
async def cb_premium(client, callback_query):
    uid = callback_query.from_user.id
    if is_premium(uid):
        user = get_user(uid)
        expiry = user.get("premium_expiry", "Lifetime")
        await callback_query.message.edit_text(
            f"👑 **You are already PREMIUM!**\n\n"
            f"Expiry: `{expiry}`\n\n"
            f"Enjoy unlimited access to all features.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back_main")]])
        )
    else:
        await callback_query.message.edit_text(
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

@app.on_callback_query(filters.regex("^menu_status$"))
async def cb_status(client, callback_query):
    uid = callback_query.from_user.id
    user = get_user(uid)
    badge = "👑 PREMIUM" if is_premium(uid) else "🆓 FREE"
    thumb = "✅ Set" if user.get("thumbnail") else "❌ Not set"
    expiry = user.get("premium_expiry", "—") if is_premium(uid) else "—"
    await callback_query.message.edit_text(
        f"📊 **Your Status**\n\n"
        f"🏷️ Plan: **{badge}**\n"
        f"📅 Premium expiry: `{expiry}`\n"
        f"🖼️ Thumbnail: {thumb}\n",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back_main")]])
    )

@app.on_callback_query(filters.regex("^back_main$"))
async def cb_back(client, callback_query):
    user_state.pop(callback_query.from_user.id, None)
    badge = "👑 **PREMIUM**" if is_premium(callback_query.from_user.id) else "🆓 **FREE**"
    await callback_query.message.edit_text(
        f"✨ **HeavenFall Utility Bot** ✨\n\nStatus: {badge}\n\nSelect an option below 👇",
        reply_markup=main_menu_kb()
    )

# ─────────────────────────────────────────
# THUMBNAIL PHOTO HANDLER
# ─────────────────────────────────────────
@app.on_message(filters.photo & filters.private)
async def photo_handler(client, message):
    uid = message.from_user.id
    state = user_state.get(uid, {})

    if state.get("step") == "wait_thumbnail":
        user = get_user(uid)
        user["thumbnail"] = message.photo.file_id
        save_user(uid, user)
        user_state.pop(uid, None)
        await message.reply(
            "✅ **Thumbnail saved!**\n\nIt will be applied automatically to your renamed PDFs.",
            reply_markup=main_menu_kb()
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
            f"⚠️ **File too large!**\n\n"
            f"Your file is **{file_size_mb:.1f}MB**.\n"
            f"Free users can only rename files up to **100MB**.\n\n"
            f"Upgrade to 👑 **Premium** for unlimited size.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("👑 Get Premium", callback_data="menu_premium")],
                [InlineKeyboardButton("🔙 Back", callback_data="back_main")]
            ])
        )
        user_state.pop(uid, None)
        return

    user_state[uid] = {
        "step": "wait_newname",
        "file_id": file.file_id,
        "file_size": file_size_mb,
        "original_name": file.file_name or "file",
        "mime_type": file.mime_type or ""
    }
    await message.reply(
        f"📁 **File received!**\n\n"
        f"Name: `{file.file_name}`\n"
        f"Size: `{file_size_mb:.2f}MB`\n\n"
        f"Now send me the **new name** (without extension):",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Cancel", callback_data="back_main")]])
    )

# ─────────────────────────────────────────
# TEXT HANDLER
# ─────────────────────────────────────────
@app.on_message(filters.text & filters.private & ~filters.command(["start", "addpremium", "rempremium"]))
async def text_handler(client, message):
    uid = message.from_user.id
    state = user_state.get(uid, {})
    step = state.get("step")

    if step == "wait_text_font":
        user_state[uid] = {"step": "wait_font_choice", "text": message.text}
        await message.reply(
            f"✏️ Text received:\n`{message.text}`\n\nChoose a font style 👇",
            reply_markup=font_kb()
        )

    elif step == "wait_newname":
        state["new_name"] = message.text.strip()
        state["step"] = "wait_format"
        user_state[uid] = state
        await message.reply(
            f"✅ New name set: **{message.text.strip()}**\n\nChoose output format:",
            reply_markup=rename_format_kb()
        )

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

    user_state.pop(uid, None)
    await callback_query.message.edit_text(
        f"✅ **Converted Text:**\n\n{converted}\n\n"
        f"_(Tap to copy)_",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Convert Again", callback_data="menu_font")],
            [InlineKeyboardButton("🔙 Main Menu", callback_data="back_main")]
        ])
    )

# ─────────────────────────────────────────
# FORMAT CALLBACK (Document / Video)
# ─────────────────────────────────────────
@app.on_callback_query(filters.regex("^fmt_"))
async def format_callback(client, callback_query):
    uid = callback_query.from_user.id
    state = user_state.get(uid, {})
    if state.get("step") != "wait_format":
        await callback_query.answer("Please start over.", show_alert=True)
        return

    fmt = callback_query.data.split("_")[1]
    new_name = state["new_name"]
    file_id = state["file_id"]
    mime = state.get("mime_type", "")

    # Determine extension
    if fmt == "document":
        if "pdf" in mime:
            ext = ".pdf"
        elif "word" in mime or "document" in mime:
            ext = ".docx"
        elif "zip" in mime:
            ext = ".zip"
        else:
            orig = state.get("original_name", "file")
            ext = os.path.splitext(orig)[1] or ".file"
    else:
        ext = ".mp4"

    final_name = new_name + ext
    user = get_user(uid)
    thumb = user.get("thumbnail")

    await callback_query.message.edit_text(f"⏳ Sending **{final_name}**...")

    try:
        if fmt == "video":
            await callback_query.message._client.send_video(
                chat_id=uid,
                video=file_id,
                caption=f"🎬 `{final_name}`\n\n@HeavenFallNetwork",
                file_name=final_name,
                thumb=thumb
            )
        else:
            await callback_query.message._client.send_document(
                chat_id=uid,
                document=file_id,
                caption=f"📄 `{final_name}`\n\n@HeavenFallNetwork",
                file_name=final_name,
                thumb=thumb
            )
        user_state.pop(uid, None)
        await callback_query.message.edit_text(
            f"✅ **Done!** `{final_name}` sent.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📁 Rename Another", callback_data="menu_rename")],
                [InlineKeyboardButton("🔙 Main Menu", callback_data="back_main")]
            ])
        )
    except Exception as e:
        await callback_query.message.edit_text(
            f"❌ Error: `{e}`",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back_main")]])
        )

# ─────────────────────────────────────────
# ADMIN: ADD / REMOVE PREMIUM
# ─────────────────────────────────────────
@app.on_message(filters.command("addpremium") & filters.user(ADMINS))
async def add_premium(client, message):
    # Usage: /addpremium <user_id> <days>  (0 days = lifetime)
    try:
        parts = message.command
        target_id = int(parts[1])
        days = int(parts[2]) if len(parts) > 2 else 0
        user = get_user(target_id)
        user["premium"] = True
        if days > 0:
            user["premium_expiry"] = (datetime.now() + timedelta(days=days)).isoformat()
        else:
            user["premium_expiry"] = None
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
