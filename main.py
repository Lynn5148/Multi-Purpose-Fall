import os
import json
import asyncio
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
# FAKE PROGRESS BAR (runs in background)
# ─────────────────────────────────────────
async def fake_progress(status_msg, action, stop_event):
    """Animates progress bar while download/upload runs in background"""
    steps = [0, 5, 12, 20, 30, 42, 55, 65, 74, 82, 88, 93, 97]
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
    # Hold at 97% until done
    while not stop_event.is_set():
        await asyncio.sleep(1)

# ─────────────────────────────────────────
# KEYBOARDS
# ─────────────────────────────────────────
def main_reply_kb():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("📁 Rename File"), KeyboardButton("🔤 Font Changer")],
            [KeyboardButton("🖼️ Set Thumbnail"), KeyboardButton("👁️ View Thumbnail")],
            [KeyboardButton("❌ Clear Thumbnail"), KeyboardButton("ℹ️ My Status")],
            [KeyboardButton("👑 Premium")]
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
        [InlineKeyboardButton("💎 Buy Premium — @fangheaven", url="https://t.me/fangheaven")],
    ])

def admin_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Stats", callback_data="adm_stats"),
         InlineKeyboardButton("📢 Broadcast", callback_data="adm_broadcast")],
        [InlineKeyboardButton("👑 Add Premium", callback_data="adm_addprem"),
         InlineKeyboardButton("🗑️ Remove Premium", callback_data="adm_remprem")],
        [InlineKeyboardButton("🔍 User Lookup", callback_data="adm_lookup"),
         InlineKeyboardButton("💥 Reset User", callback_data="adm_reset")],
        [InlineKeyboardButton("🔒 Close", callback_data="adm_close")]
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
# /admin
# ─────────────────────────────────────────
@app.on_message(filters.command("admin") & filters.user(ADMINS))
async def admin_panel(client, message):
    total, premium = get_stats()
    await message.reply(
        f"🛠️ **HeavenFall Admin Panel**\n\n"
        f"👥 Total Users: `{total}`\n"
        f"👑 Premium Users: `{premium}`\n"
        f"🆓 Free Users: `{total - premium}`\n\n"
        f"Select an action below:",
        reply_markup=admin_kb()
    )

@app.on_callback_query(filters.regex("^adm_") & filters.user(ADMINS))
async def admin_callbacks(client, callback_query):
    data = callback_query.data
    uid = callback_query.from_user.id

    if data == "adm_stats":
        total, premium = get_stats()
        await callback_query.message.edit_text(
            f"📊 **Bot Statistics**\n\n"
            f"👥 Total Users: `{total}`\n"
            f"👑 Premium Users: `{premium}`\n"
            f"🆓 Free Users: `{total - premium}`",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="adm_back")]])
        )

    elif data == "adm_broadcast":
        user_state[uid] = {"step": "adm_broadcast"}
        await callback_query.message.edit_text(
            "📢 **Broadcast**\n\nSend the message you want to broadcast to all users:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="adm_back")]])
        )

    elif data == "adm_addprem":
        user_state[uid] = {"step": "adm_addprem"}
        await callback_query.message.edit_text(
            "👑 **Add Premium**\n\nSend:\n`<user_id> <days>`\n\n_(0 days = Lifetime)_",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="adm_back")]])
        )

    elif data == "adm_remprem":
        user_state[uid] = {"step": "adm_remprem"}
        await callback_query.message.edit_text(
            "🗑️ **Remove Premium**\n\nSend the `user_id` to remove premium from:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="adm_back")]])
        )

    elif data == "adm_lookup":
        user_state[uid] = {"step": "adm_lookup"}
        await callback_query.message.edit_text(
            "🔍 **User Lookup**\n\nSend the `user_id` to look up:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="adm_back")]])
        )

    elif data == "adm_reset":
        user_state[uid] = {"step": "adm_reset"}
        await callback_query.message.edit_text(
            "💥 **Reset User**\n\nSend the `user_id` to fully reset their data:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="adm_back")]])
        )

    elif data == "adm_back":
        user_state.pop(uid, None)
        total, premium = get_stats()
        await callback_query.message.edit_text(
            f"🛠️ **HeavenFall Admin Panel**\n\n"
            f"👥 Total Users: `{total}`\n"
            f"👑 Premium Users: `{premium}`\n"
            f"🆓 Free Users: `{total - premium}`\n\n"
            f"Select an action below:",
            reply_markup=admin_kb()
        )

    elif data == "adm_close":
        user_state.pop(uid, None)
        await callback_query.message.delete()

# ─────────────────────────────────────────
# MAIN REPLY KEYBOARD HANDLER
# ─────────────────────────────────────────
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
            "Send me a photo to set as your default thumbnail.\n"
            "It will be applied to all renamed files."
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
            f"📅 Expiry: `{expiry}`\n"
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
                "Contact **@fangheaven** to purchase 👇",
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
            f"Tap 👑 **Premium** to unlock unlimited size."
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
        f"📁 **File received!**\n\n"
        f"📋 Name: `{original_name}`\n"
        f"📦 Size: `{file_size_mb:.2f} MB`\n\n"
        f"Send me the **new name** (without extension):"
    )

# ─────────────────────────────────────────
# TEXT HANDLER
# ─────────────────────────────────────────
RESERVED = [
    "📁 Rename File", "🔤 Font Changer", "🖼️ Set Thumbnail",
    "👁️ View Thumbnail", "❌ Clear Thumbnail", "ℹ️ My Status", "👑 Premium"
]

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

    # ── Admin flows ──
    if step == "adm_broadcast":
        db = load_db()
        user_state.pop(uid, None)
        sent = 0
        failed = 0
        await message.reply("📢 Broadcasting...")
        for user_id in db.keys():
            try:
                await app.send_message(int(user_id), text)
                sent += 1
                await asyncio.sleep(0.05)
            except:
                failed += 1
        await message.reply(f"✅ Broadcast done.\n\n✔️ Sent: {sent}\n❌ Failed: {failed}")

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
            await message.reply(f"✅ Premium granted to `{target_id}` — **{label}**")
        except Exception as e:
            await message.reply(f"❌ Error: {e}\n\nFormat: `<user_id> <days>`")

    elif step == "adm_remprem":
        user_state.pop(uid, None)
        try:
            target_id = int(text.strip())
            user = get_user(target_id)
            user["premium"] = False
            user["premium_expiry"] = None
            save_user(target_id, user)
            await message.reply(f"✅ Premium removed from `{target_id}`")
        except Exception as e:
            await message.reply(f"❌ Error: {e}")

    elif step == "adm_lookup":
        user_state.pop(uid, None)
        try:
            target_id = int(text.strip())
            user = get_user(target_id)
            badge = "👑 PREMIUM" if user.get("premium") else "🆓 FREE"
            expiry = user.get("premium_expiry") or "—"
            thumb = "✅ Set" if user.get("thumbnail_file_id") else "❌ Not set"
            await message.reply(
                f"🔍 **User: `{target_id}`**\n\n"
                f"Plan: {badge}\n"
                f"Expiry: `{expiry}`\n"
                f"Thumbnail: {thumb}"
            )
        except Exception as e:
            await message.reply(f"❌ Error: {e}")

    elif step == "adm_reset":
        user_state.pop(uid, None)
        try:
            target_id = int(text.strip())
            db = load_db()
            if str(target_id) in db:
                del db[str(target_id)]
                save_db(db)
            await message.reply(f"💥 User `{target_id}` fully reset.")
        except Exception as e:
            await message.reply(f"❌ Error: {e}")

    # ── Font flow ──
    elif step == "wait_text_font":
        user_state[uid] = {"step": "wait_font_choice", "text": text}
        await message.reply(text, reply_markup=font_kb())

    # ── Rename flow ──
    elif step == "wait_newname":
        state["new_name"] = text.strip()
        state["step"] = "wait_rename_go"
        user_state[uid] = state
        await do_rename(message, uid)

# ─────────────────────────────────────────
# RENAME LOGIC — no format selection, auto detect
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

    # Auto detect: video mime = send as video, else document
    is_video = mime.startswith("video/")

    # Thumbnail
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

    stop_event = asyncio.Event()
    progress_task = asyncio.create_task(
        fake_progress(status_msg, "dl", stop_event)
    )

    try:
        path = await app.download_media(file_id, file_name=temp_download)
        stop_event.set()
        await progress_task

        if not path or not os.path.exists(path):
            await status_msg.edit_text("❌ Download failed. Please try again.")
            return

        os.rename(path, temp_final)
        stop_event.clear()

        await status_msg.edit_text(
            "⬆️ **Uploading...**\n\n"
            "`░░░░░░░░░░░░░░░░░░░░`\n\n"
            "Please wait..."
        )

        stop_event2 = asyncio.Event()
        progress_task2 = asyncio.create_task(
            fake_progress(status_msg, "ul", stop_event2)
        )

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

        stop_event2.set()
        await progress_task2

        await status_msg.edit_text(f"✅ **Done!**\n\n`{final_name}` sent successfully.")

    except Exception as e:
        stop_event.set()
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
# LEGACY ADMIN COMMANDS (still work)
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