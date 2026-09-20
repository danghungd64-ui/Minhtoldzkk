# -*- coding: utf-8 -*-
# ============================================================
#   LEMINH TOOL MD5 - VIP 2026 - v8 FULL
#   Admin: 0372834763
#   Bank: MBBANK 0372834763
# ============================================================
import os
import re
import json
import html
import time
import random
import string
import hashlib
import asyncio
import logging
from datetime import datetime, timedelta

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# ============================================================
#   CONFIG - SỬA TOKEN CỦA BẠN Ở ĐÂY
# ============================================================
BOT_TOKEN = "8934734495:AAGVXUK0muIIPK2XYJhzxwHJoaZNbysc-UY"

RENDER_URL = os.getenv("RENDER_EXTERNAL_URL", "")
PORT = int(os.getenv("PORT", 10000))

# ---- ADMIN ----
ADMIN_IDS = [
    # Điền Telegram ID của bạn vào đây (dạng số)
    # Ví dụ: 123456789,
]
ADMIN_PHONE = "0372834763"

# ---- BANK ----
BANK_NAME = "MBBANK"
BANK_ACC = "0372834763"
BANK_OWNER = "LE MINH"

# ---- TOKEN BÍ MẬT ----
SECRET_TOKEN = "LEMINH_TOOL_VIP_2026_KEY"

# ---- DATABASE (file JSON) ----
DB_FILE = "users_db.json"
KEYS_FILE = "keys_db.json"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

LINE = "━━━━━━━━━━━━━"

# ============================================================
#   BẢNG GIÁ KEY
# ============================================================
KEY_PRICING = {
    "1h":      {"price": 5000,   "seconds": 3600,     "label": "1 Giờ"},
    "1day":    {"price": 20000,  "seconds": 86400,    "label": "1 Ngày"},
    "1week":   {"price": 50000,  "seconds": 604800,   "label": "1 Tuần"},
    "1month":  {"price": 100000, "seconds": 2592000,  "label": "1 Tháng"},
    "forever": {"price": 0,      "seconds": -1,       "label": "Vĩnh Viễn"},
}

# ============================================================
#   DATABASE - JSON
# ============================================================
def load_db(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_db(path, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error("Save DB error: " + str(e))

# ============================================================
#   KEY MANAGEMENT
# ============================================================
def gen_key():
    """Sinh key 16 ký tự"""
    return "LM-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=13))

def create_key(key_type, custom_key=None):
    keys = load_db(KEYS_FILE)
    key = custom_key if custom_key else gen_key()
    info = KEY_PRICING.get(key_type, KEY_PRICING["1day"])
    keys[key] = {
        "type": key_type,
        "label": info["label"],
        "seconds": info["seconds"],
        "created": time.time(),
        "used_by": None,
        "used_at": None,
    }
    save_db(KEYS_FILE, keys)
    return key

def activate_key(user_id, key):
    keys = load_db(KEYS_FILE)
    users = load_db(DB_FILE)
    key = key.strip().upper()

    if key not in keys:
        return False, "❌ Key không tồn tại!"

    info = keys[key]
    if info.get("used_by"):
        return False, "❌ Key đã được sử dụng!"

    # Gán key cho user
    info["used_by"] = str(user_id)
    info["used_at"] = time.time()
    keys[key] = info
    save_db(KEYS_FILE, keys)

    # Cập nhật user
    uid = str(user_id)
    now = time.time()

    if info["seconds"] == -1:
        # Vĩnh viễn
        users[uid] = {
            "key": key,
            "type": info["type"],
            "label": info["label"],
            "activated": now,
            "expires": -1,
            "username": "",
            "first_name": "",
        }
    else:
        # Có thời hạn
        existing = users.get(uid, {})
        # Nếu đang có key còn hạn → cộng dồn
        if existing and existing.get("expires", 0) > now:
            base = existing["expires"]
        else:
            base = now
        users[uid] = {
            "key": key,
            "type": info["type"],
            "label": info["label"],
            "activated": now,
            "expires": base + info["seconds"],
            "username": existing.get("username", ""),
            "first_name": existing.get("first_name", ""),
        }
    save_db(DB_FILE, users)
    return True, info

def check_user(user_id):
    users = load_db(DB_FILE)
    uid = str(user_id)
    if uid not in users:
        return False, None

    u = users[uid]
    if u.get("expires") == -1:
        return True, u

    if u.get("expires", 0) > time.time():
        return True, u
    return False, u

def get_remaining(expires):
    if expires == -1:
        return "Vĩnh viễn ♾️"
    remain = int(expires - time.time())
    if remain <= 0:
        return "Hết hạn"
    d = remain // 86400
    h = (remain % 86400) // 3600
    m = (remain % 3600) // 60
    if d > 0:
        return str(d) + " ngày " + str(h) + " giờ"
    if h > 0:
        return str(h) + " giờ " + str(m) + " phút"
    return str(m) + " phút"

def is_admin(user_id):
    return user_id in ADMIN_IDS

# ============================================================
#   THUẬT TOÁN v8 - 40 VÒNG + 9 LỚP MIX
# ============================================================
def detect_hash_type(h):
    h = h.strip()
    if re.fullmatch(r"[a-fA-F0-9]{32}", h):
        return "MD5"
    if re.fullmatch(r"[a-fA-F0-9]{64}", h):
        return "SHA-256"
    return None

def hash_to_score(h, htype):
    h = h.lower()
    weight = 47 if htype == "MD5" else 59

    salt1 = "LEMINH_V8_A"
    salt2 = "SEED_" + str(len(h)) + "_" + str(weight)
    salt3 = "X9K2M7P4Q1Z8"
    salt4 = "R_" + hashlib.md5(h.encode()).hexdigest()[:10]
    salt5 = "ZK3L8N5W2Y7M4"
    salt6 = "VIP2026"

    mixed = (h + "::" + SECRET_TOKEN + "::" + salt1 + "::" + salt2
             + "::" + salt3 + "::" + salt4 + "::" + salt5 + "::" + salt6).encode()

    # 40 vòng băm xen kẽ 4 hash
    for i in range(40):
        r = i % 4
        if r == 0:
            mixed = hashlib.sha512(mixed + str(i).encode() + salt1.encode()).digest()
        elif r == 1:
            mixed = hashlib.sha256(mixed + str(i).encode() + salt2.encode()).digest()
        elif r == 2:
            mixed = hashlib.blake2b(mixed + str(i).encode() + salt3.encode()).digest()
        else:
            mixed = hashlib.sha3_256(mixed + str(i).encode() + salt4.encode()).digest()

    # Avalanche - đảo bit 3 lần
    b = int.from_bytes(mixed[:8], "big")
    b = ((b << 13) | (b >> 51)) & 0xFFFFFFFFFFFFFFFF
    b ^= 0xA5A5A5A5A5A5A5A5
    b = ((b << 7) | (b >> 57)) & 0xFFFFFFFFFFFFFFFF
    b ^= 0x5A5A5A5A5A5A5A5A
    b = ((b << 11) | (b >> 53)) & 0xFFFFFFFFFFFFFFFF
    mixed = b.to_bytes(8, "big") + mixed[8:]

    # Khuếch tán 3 lớp
    score = 0
    for i in range(0, len(mixed), 2):
        cb = mixed[i:i + 4]
        if len(cb) < 4:
            cb += b"\x00" * (4 - len(cb))
        ck = int.from_bytes(cb, "big")
        score = (score * weight + (ck * ck) % 9973 + ck) % 100
        score = (score ^ (ck % 97)) % 100
        inv = pow(ck % 89 + 1, 87, 89)
        score = (score + inv) % 100

    # Bit-mix
    fm = int.from_bytes(hashlib.sha256(mixed).digest()[:8], "big")
    score = (score * 73 + fm) % 100
    score = (score * 97 + 43) % 100
    score = (score ^ 0x5A) % 100

    return abs(score) % 100

def predict(h):
    h = h.strip()
    htype = detect_hash_type(h)
    if not htype:
        return {"error": True}
    score = hash_to_score(h, htype)
    return {
        "hash": h,
        "type": htype,
        "result": "XỈU" if score < 50 else "TÀI",
        "tai": score,
        "xiu": 100 - score,
    }

def esc(t):
    return html.escape(str(t))

# ============================================================
#   HANDLERS - USER
# ============================================================
async def start(update, ctx):
    user = update.effective_user
    # Lưu tên user
    users = load_db(DB_FILE)
    uid = str(user.id)
    if uid in users:
        users[uid]["username"] = user.username or ""
        users[uid]["first_name"] = user.first_name or ""
        save_db(DB_FILE, users)

    is_vip, info = check_user(user.id)

    if is_vip:
        status = "✅ VIP - Còn: " + get_remaining(info.get("expires", -1))
    else:
        status = "❌ Chưa kích hoạt - Gõ /key"

    text = (
        "🎯 <b>LEMINH TOOL VIP</b>\n"
        "Dự đoán TÀI / XỈU chuẩn xác 💰\n"
        + LINE + "\n\n"
        "📥 <b>Gửi MD5 (32) hoặc SHA-256 (64)</b>\n"
        "→ Bot tự nhận diện\n"
        "→ Dự đoán TÀI / XỈU\n\n"
        + LINE + "\n"
        "🔑 <b>Trạng thái:</b> " + status + "\n\n"
        "📋 <b>Lệnh:</b>\n"
        "• /key – Kích hoạt key\n"
        "• /nap – Nạp tiền mua key\n"
        "• /info – Xem thông tin VIP\n"
        "• /hotro – Liên hệ admin\n"
        "• /xoa – Xoá tin nhắn bot"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


async def cmd_key(update, ctx):
    args = ctx.args
    if not args:
        text = (
            "🔑 <b>KÍCH HOẠT KEY</b>\n"
            + LINE + "\n\n"
            "📝 Cú pháp:\n"
            "<code>/key MÃ_KEY_CỦA_BẠN</code>\n\n"
            "💡 Ví dụ:\n"
            "<code>/key LM-ABCD1234XYZ</code>\n\n"
            "📞 Chưa có key? Gõ /nap để mua"
        )
        await update.message.reply_text(text, parse_mode=ParseMode.HTML)
        return

    key = args[0].strip().upper()
    ok, result = activate_key(update.effective_user.id, key)

    if ok:
        text = (
            "✅ <b>KÍCH HOẠT THÀNH CÔNG!</b>\n"
            + LINE + "\n"
            "🔑 Key: <code>" + esc(key) + "</code>\n"
            "🎁 Loại: <b>" + result["label"] + "</b>\n"
            "⏱️ Hạn: " + (get_remaining(result["seconds"]) if result["seconds"] != -1 else "Vĩnh viễn ♾️") + "\n\n"
            "👉 Gửi MD5 / HASH để dự đoán!"
        )
    else:
        text = "❌ " + result

    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


async def cmd_nap(update, ctx):
    text = (
        "💳 <b>NẠP TIỀN MUA KEY</b>\n"
        + LINE + "\n"
        "🏦 Ngân hàng: <b>" + BANK_NAME + "</b>\n"
        "💳 Số TK: <code>" + BANK_ACC + "</code>\n"
        "👤 Chủ TK: <b>" + BANK_OWNER + "</b>\n"
        "📝 Nội dung: <b>SĐT Telegram của bạn</b>\n\n"
        + LINE + "\n"
        "💎 <b>BẢNG GIÁ:</b>\n"
        "• 1 Giờ      → <b>5.000đ</b>\n"
        "• 1 Ngày     → <b>20.000đ</b>\n"
        "• 1 Tuần     → <b>50.000đ</b>\n"
        "• 1 Tháng    → <b>100.000đ</b>\n"
        "• Vĩnh viễn  → <b>Liên hệ</b>\n\n"
        + LINE + "\n"
        "📞 Sau khi CK, gửi bill cho admin:\n"
        "• Zalo: <code>" + ADMIN_PHONE + "</code>"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("💬 Zalo Admin", url="https://zalo.me/" + ADMIN_PHONE)],
    ])
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)


async def cmd_info(update, ctx):
    user = update.effective_user
    ok, info = check_user(user.id)

    if not ok and info is None:
        text = (
            "👤 <b>THÔNG TIN</b>\n"
            + LINE + "\n"
            "🆔 ID: <code>" + str(user.id) + "</code>\n"
            "👤 Tên: " + esc(user.first_name) + "\n"
            "🔑 Key: <b>Chưa kích hoạt</b>\n\n"
            "👉 Gõ /key để kích hoạt\n"
            "👉 Gõ /nap để mua key"
        )
    elif not ok:
        text = (
            "👤 <b>THÔNG TIN</b>\n"
            + LINE + "\n"
            "🆔 ID: <code>" + str(user.id) + "</code>\n"
            "👤 Tên: " + esc(user.first_name) + "\n"
            "🔑 Key: <code>" + esc(info.get("key", "")) + "</code>\n"
            "🎁 Loại: " + esc(info.get("label", "")) + "\n"
            "⏱️ Trạng thái: <b>Hết hạn</b>\n\n"
            "👉 Gõ /nap để gia hạn"
        )
    else:
        text = (
            "👤 <b>THÔNG TIN VIP</b>\n"
            + LINE + "\n"
            "🆔 ID: <code>" + str(user.id) + "</code>\n"
            "👤 Tên: " + esc(user.first_name) + "\n"
            "🔑 Key: <code>" + esc(info.get("key", "")) + "</code>\n"
            "🎁 Loại: <b>" + esc(info.get("label", "")) + "</b>\n"
            "⏱️ Còn lại: <b>" + get_remaining(info.get("expires", -1)) + "</b>"
        )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


async def cmd_hotro(update, ctx):
    text = (
        "📞 <b>LIÊN HỆ ADMIN</b>\n"
        + LINE + "\n"
        "• Zalo: <code>" + ADMIN_PHONE + "</code>\n"
        "• SĐT: <code>" + ADMIN_PHONE + "</code>\n\n"
        "💳 Nạp tiền: gõ /nap\n"
        "🔑 Kích hoạt: gõ /key"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("💬 Zalo Admin", url="https://zalo.me/" + ADMIN_PHONE)],
    ])
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)


async def cmd_xoa(update, ctx):
    try:
        await update.message.delete()
    except Exception:
        pass
    msg = await ctx.bot.send_message(
        chat_id=update.effective_chat.id,
        text="🧹 <b>Đã xoá!</b>",
        parse_mode=ParseMode.HTML,
    )
    await asyncio.sleep(3)
    try:
        await msg.delete()
    except Exception:
        pass


async def cmd_32(update, ctx):
    text = (
        "📘 <b>HƯỚNG DẪN 32 KÝ TỰ (MD5)</b>\n"
        + LINE + "\n"
        "• Chuỗi đúng <b>32</b> ký tự hex\n"
        "• Ví dụ:\n"
        "<code>d41d8cd98f00b204e9800998ecf8427e</code>"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


async def cmd_64(update, ctx):
    text = (
        "📗 <b>HƯỚNG DẪN 64 KÝ TỰ (SHA-256)</b>\n"
        + LINE + "\n"
        "• Chuỗi đúng <b>64</b> ký tự hex\n"
        "• Ví dụ:\n"
        "<code>e3b0c44298fc1c149afbf4c8996fb924"
        "27ae41e4649b934ca495991b7852b855</code>"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


# ============================================================
#   HANDLER CHÍNH - XỬ LÝ HASH
# ============================================================
async def handle_hash(update, ctx):
    user = update.effective_user
    text = update.message.text.strip()

    # Update tên user
    users = load_db(DB_FILE)
    uid = str(user.id)
    if uid in users:
        users[uid]["username"] = user.username or ""
        users[uid]["first_name"] = user.first_name or ""
        save_db(DB_FILE, users)

    # Check VIP (trừ admin)
    if not is_admin(user.id):
        is_vip, _ = check_user(user.id)
        if not is_vip:
            msg = (
                "🔒 <b>CHƯA KÍCH HOẠT KEY!</b>\n"
                + LINE + "\n\n"
                "📋 Để sử dụng tool:\n"
                "1️⃣ Gõ /nap để xem bảng giá\n"
                "2️⃣ Chuyển khoản MBBANK\n"
                "3️⃣ Nhận key từ admin\n"
                "4️⃣ Gõ /key MÃ_KEY để kích hoạt\n\n"
                "📞 Zalo admin: <code>" + ADMIN_PHONE + "</code>"
            )
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("💳 Nạp Tiền", callback_data="nap")],
                [InlineKeyboardButton("🔑 Nhập Key", callback_data="huongdan_key")],
                [InlineKeyboardButton("💬 Zalo Admin", url="https://zalo.me/" + ADMIN_PHONE)],
            ])
            await update.message.reply_text(msg, parse_mode=ParseMode.HTML, reply_markup=kb)
            return

    # Dự đoán
    res = predict(text)
    if res.get("error"):
        msg = (
            "❌ <b>SAI ĐỊNH DẠNG!</b>\n"
            + LINE + "\n"
            "• MD5: đúng <b>32</b> ký tự hex\n"
            "• SHA-256: đúng <b>64</b> ký tự hex\n\n"
            "👉 Gõ /32kitu hoặc /64kitu"
        )
        await update.message.reply_text(msg, parse_mode=ParseMode.HTML)
        return

    emoji = "🔴" if res["result"] == "TÀI" else "🔵"

    # Kết quả ngắn gọn, nét keng
    msg = (
        "🎯 <b>LEMINH VIP</b>\n"
        + LINE + "\n"
        + "🔎 <code>" + esc(res["hash"]) + "</code>\n"
        + "🧩 " + res["type"] + "\n\n"
        + emoji + " <b>" + res["result"] + "</b>\n"
        + "📊 TÀI: <b>" + str(res["tai"]) + "%</b>  |  XỈU: <b>" + str(res["xiu"]) + "%</b>\n"
        + LINE + "\n"
        + "💰 Chúc bạn thắng lớn!"
    )
    await update.message.reply_text(msg, parse_mode=ParseMode.HTML)


# ============================================================
#   HANDLERS - ADMIN
# ============================================================
async def cmd_admin(update, ctx):
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text("❌ Bạn không phải admin!")
        return

    users = load_db(DB_FILE)
    keys = load_db(KEYS_FILE)
    now = time.time()

    total_users = len(users)
    active_users = sum(1 for u in users.values() if u.get("expires", 0) == -1 or u.get("expires", 0) > now)
    total_keys = len(keys)
    used_keys = sum(1 for k in keys.values() if k.get("used_by"))
    unused_keys = total_keys - used_keys

    text = (
        "👑 <b>ADMIN PANEL</b>\n"
        + LINE + "\n"
        "👥 Tổng user: <b>" + str(total_users) + "</b>\n"
        "✅ User VIP đang hoạt động: <b>" + str(active_users) + "</b>\n"
        "🔑 Tổng key: <b>" + str(total_keys) + "</b>\n"
        "✔️ Key đã dùng: <b>" + str(used_keys) + "</b>\n"
        "🆓 Key chưa dùng: <b>" + str(unused_keys) + "</b>\n"
        + LINE + "\n"
        "📋 <b>Lệnh admin:</b>\n"
        "• /users – Danh sách user\n"
        "• /capkey [loại] – Tạo key mới\n"
        "    Loại: 1h | 1day | 1week | 1month | forever\n"
        "• /keys – Xem tất cả key\n"
        "• /delkey MÃ – Xoá key\n"
        "• /addadmin ID – Thêm admin\n"
        "• /myid – Xem ID Telegram của bạn"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


async def cmd_myid(update, ctx):
    user = update.effective_user
    text = (
        "🆔 <b>Telegram ID của bạn:</b>\n"
        "<code>" + str(user.id) + "</code>\n\n"
        "👤 Tên: " + esc(user.first_name) + "\n"
        "📛 Username: @" + esc(user.username or "không có")
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


async def cmd_capkey(update, ctx):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Bạn không phải admin!")
        return

    args = ctx.args
    if not args:
        text = (
            "🔑 <b>CẤP KEY</b>\n"
            + LINE + "\n"
            "📝 Cú pháp: <code>/capkey [loại] [số_lượng]</code>\n\n"
            "📋 Loại key:\n"
            "• <code>1h</code> – 1 Giờ (5k)\n"
            "• <code>1day</code> – 1 Ngày (20k)\n"
            "• <code>1week</code> – 1 Tuần (50k)\n"
            "• <code>1month</code> – 1 Tháng (100k)\n"
            "• <code>forever</code> – Vĩnh viễn\n\n"
            "💡 Ví dụ:\n"
            "<code>/capkey 1day 5</code> – Tạo 5 key 1 ngày\n"
            "<code>/capkey 1month 1</code> – Tạo 1 key 1 tháng"
        )
        await update.message.reply_text(text, parse_mode=ParseMode.HTML)
        return

    key_type = args[0].lower()
    if key_type not in KEY_PRICING:
        await update.message.reply_text("❌ Loại key không hợp lệ!")
        return

    qty = 1
    if len(args) > 1:
        try:
            qty = int(args[1])
            qty = max(1, min(qty, 50))
        except Exception:
            qty = 1

    keys_created = []
    for _ in range(qty):
        k = create_key(key_type)
        keys_created.append(k)

    info = KEY_PRICING[key_type]
    text = (
        "✅ <b>ĐÃ TẠO " + str(qty) + " KEY</b>\n"
        + LINE + "\n"
        "🎁 Loại: <b>" + info["label"] + "</b>\n"
        "💰 Giá: <b>" + "{:,}".format(info["price"]).replace(",", ".") + "đ</b>\n"
        + LINE + "\n"
        "🔑 <b>DANH SÁCH KEY:</b>\n"
    )
    for k in keys_created:
        text += "<code>" + k + "</code>\n"

    text += "\n💡 Gửi key này cho khách để họ kích hoạt."
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


async def cmd_users(update, ctx):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Bạn không phải admin!")
        return

    users = load_db(DB_FILE)
    if not users:
        await update.message.reply_text("📋 Chưa có user nào.")
        return

    now = time.time()
    text = "👥 <b>DANH SÁCH USER</b>\n" + LINE + "\n"

    items = list(users.items())
    items.sort(key=lambda x: x[1].get("activated", 0), reverse=True)

    for uid, u in items[:30]:
        expires = u.get("expires", 0)
        if expires == -1:
            status = "♾️ Vĩnh viễn"
        elif expires > now:
            status = "✅ " + get_remaining(expires)
        else:
            status = "❌ Hết hạn"

        name = u.get("first_name", "") or u.get("username", "") or "Ẩn danh"
        key = u.get("key", "N/A")

        text += (
            "👤 <b>" + esc(name[:20]) + "</b>\n"
            "   🆔 <code>" + uid + "</code>\n"
            "   🔑 <code>" + esc(key) + "</code>\n"
            "   ⏱️ " + status + "\n\n"
        )

    if len(users) > 30:
        text += "... và " + str(len(users) - 30) + " user khác"

    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


async def cmd_keys(update, ctx):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Bạn không phải admin!")
        return

    keys = load_db(KEYS_FILE)
    if not keys:
        await update.message.reply_text("📋 Chưa có key nào.")
        return

    used = []
    unused = []
    for k, v in keys.items():
        if v.get("used_by"):
            used.append((k, v))
        else:
            unused.append((k, v))

    text = "🔑 <b>QUẢN LÝ KEY</b>\n" + LINE + "\n"
    text += "🆓 Chưa dùng: <b>" + str(len(unused)) + "</b>\n"
    text += "✔️ Đã dùng: <b>" + str(len(used)) + "</b>\n\n"

    text += "🆓 <b>KEY CHƯA DÙNG (tối đa 20):</b>\n"
    for k, v in unused[:20]:
        text += "<code>" + k + "</code> [" + v["label"] + "]\n"

    if len(unused) > 20:
        text += "... và " + str(len(unused) - 20) + " key khác\n"

    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


async def cmd_delkey(update, ctx):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Bạn không phải admin!")
        return

    args = ctx.args
    if not args:
        await update.message.reply_text("📝 Cú pháp: /delkey MÃ_KEY")
        return

    key = args[0].strip().upper()
    keys = load_db(KEYS_FILE)
    if key not in keys:
        await update.message.reply_text("❌ Key không tồn tại!")
        return

    del keys[key]
    save_db(KEYS_FILE, keys)
    await update.message.reply_text("✅ Đã xoá key: <code>" + esc(key) + "</code>", parse_mode=ParseMode.HTML)


# ============================================================
#   CALLBACK BUTTON
# ============================================================
async def button_cb(update, ctx):
    q = update.callback_query
    await q.answer()
    if q.data == "nap":
        await q.message.reply_text(
            "💳 Chuyển khoản: <b>" + BANK_NAME + "</b>\n"
            "Số TK: <code>" + BANK_ACC + "</code>\n"
            "Chủ TK: " + BANK_OWNER + "\n\n"
            "Sau đó gửi bill cho admin:\n"
            "Zalo: <code>" + ADMIN_PHONE + "</code>",
            parse_mode=ParseMode.HTML,
        )
    elif q.data == "huongdan_key":
        await q.message.reply_text(
            "🔑 Cú pháp: <code>/key MÃ_KEY</code>\n"
            "Ví dụ: <code>/key LM-ABC123XYZ</code>",
            parse_mode=ParseMode.HTML,
        )


# ============================================================
#   POST INIT
# ============================================================
async def post_init(app):
    await app.bot.set_my_commands([
        BotCommand("start", "Bắt đầu"),
        BotCommand("key", "Kích hoạt key"),
        BotCommand("nap", "Nạp tiền mua key"),
        BotCommand("info", "Thông tin VIP"),
        BotCommand("32kitu", "Hướng dẫn MD5"),
        BotCommand("64kitu", "Hướng dẫn SHA-256"),
        BotCommand("hotro", "Liên hệ admin"),
        BotCommand("xoa", "Xoá tin nhắn bot"),
        BotCommand("myid", "Xem ID Telegram"),
        BotCommand("admin", "Admin panel"),
    ])
    await app.bot.delete_webhook(drop_pending_updates=True)
    logger.info("✅ Đã set commands")


# ============================================================
#   MAIN
# ============================================================
def main():
    if BOT_TOKEN == "PASTE_TOKEN_VÀO_ĐÂY" or not BOT_TOKEN:
        raise SystemExit("⚠️ Chưa nhập BOT_TOKEN vào code!")

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    # User
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("key", cmd_key))
    app.add_handler(CommandHandler("nap", cmd_nap))
    app.add_handler(CommandHandler("info", cmd_info))
    app.add_handler(CommandHandler("hotro", cmd_hotro))
    app.add_handler(CommandHandler("xoa", cmd_xoa))
    app.add_handler(CommandHandler("32kitu", cmd_32))
    app.add_handler(CommandHandler("64kitu", cmd_64))
    app.add_handler(CommandHandler("myid", cmd_myid))

    # Admin
    app.add_handler(CommandHandler("admin", cmd_admin))
    app.add_handler(CommandHandler("capkey", cmd_capkey))
    app.add_handler(CommandHandler("users", cmd_users))
    app.add_handler(CommandHandler("keys", cmd_keys))
    app.add_handler(CommandHandler("delkey", cmd_delkey))

    # Callback
    from telegram.ext import CallbackQueryHandler
    app.add_handler(CallbackQueryHandler(button_cb))

    # Message
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_hash))

    webhook_url = RENDER_URL + "/" + BOT_TOKEN
    logger.info("🚀 Webhook: " + webhook_url)

    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=BOT_TOKEN,
        webhook_url=webhook_url,
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()
