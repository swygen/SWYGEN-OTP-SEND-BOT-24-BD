import telebot
import requests
import random
import time
import math
import logging
from flask import Flask, request, jsonify
from threading import Thread
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# ━─━─━─━─━─━─━─━─━─━─━─━─━─━
# 🔥 CONFIGURATION
# ━─━─━─━─━─━─━─━─━─━─━─━─━─━
BOT_TOKEN = '8576384091:AAHp1QUK21Hk58I52lVgs6LYfAHeQRqurDE' # আপনার নতুন টোকেন
ADMIN_ID = 6243881362

# 🔑 SMS API (SendMySMS)
SMS_API_URL = "https://sendmysms.net/api.php"
SMS_USER = "swygen"
SMS_KEY = "353f2fdf74fd02928be4330f7efb78b7"

# 🗄️ DATABASE (JSONBin)
JSONBIN_API_KEY = '$2a$10$bXRSqzPAb3ta4IK/7CWN0O3aLAY0gEexojcL2efrYIWYM0m.iOrhu'
BIN_ID = '695e450bd0ea881f405a8edb'
JSON_URL = f"https://api.jsonbin.io/v3/b/{BIN_ID}"

# 🤖 INITIALIZE
bot = telebot.TeleBot(BOT_TOKEN, parse_mode='Markdown')
app = Flask(__name__)

# Logger off to keep console clean
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

# ━─━─━─━─━─━─━─━─━─━─━─━─━─━
# 🗄️ DATABASE & SMS FUNCTIONS
# ━─━─━─━─━─━─━─━─━─━─━─━─━─━
def get_db():
    headers = {'X-Master-Key': JSONBIN_API_KEY}
    try:
        req = requests.get(JSON_URL, headers=headers)
        if req.status_code == 200:
            return req.json().get('record', {}).get('requests', [])
        return []
    except: return []

def update_db(new_entry):
    headers = {'Content-Type': 'application/json', 'X-Master-Key': JSONBIN_API_KEY}
    try:
        current = get_db()
        current.insert(0, new_entry)
        if len(current) > 200: current = current[:200]
        requests.put(JSON_URL, json={'requests': current}, headers=headers)
    except: pass

def send_sms(phone, msg):
    try:
        data = {"user": SMS_USER, "key": SMS_KEY, "to": phone, "msg": msg}
        requests.post(SMS_API_URL, data=data)
        return True
    except: return False

# ━─━─━─━─━─━─━─━─━─━─━─━─━─━
# 🌐 WEB SERVER (24/7 Uptime & API)
# ━─━─━─━─━─━─━─━─━─━─━─━─━─━
@app.route('/')
def home():
    return "✅ Bot is Online & Running 24/7!"

@app.route('/send_otp', methods=['GET'])
def api_otp():
    phone = request.args.get('phone')
    if not phone: return jsonify({"status": "error", "message": "Missing Phone"}), 400

    otp = str(random.randint(100000, 999999))
    timestamp = time.strftime("%d-%b %I:%M %p")
    msg_body = f"BD INVESTMENT Verification Code: {otp}\nValid for 10 minutes.\nDo not share this code with anyone."

    send_sms(phone, msg_body)
    
    # Save & Notify
    Thread(target=update_db, args=({"time": timestamp, "phone": phone, "otp": otp, "status": "Sent"},)).start()
    try: bot.send_message(ADMIN_ID, f"🔔 **OTP Sent**\n📱 `{phone}`\n🔢 `{otp}`")
    except: pass

    return jsonify({"status": "success", "otp": otp}), 200

# ━─━─━─━─━─━─━─━─━─━─━─━─━─━
# 🤖 BOT COMMANDS
# ━─━─━─━─━─━─━─━─━─━─━─━─━─━
def main_menu():
    mk = ReplyKeyboardMarkup(resize_keyboard=True)
    mk.add(KeyboardButton("🟢 System Status"), KeyboardButton("📂 View Requests"))
    return mk

@bot.message_handler(commands=['start'])
def start(m):
    if m.chat.id == ADMIN_ID:
        bot.send_message(m.chat.id, "👋 **Admin Panel Active**", reply_markup=main_menu())
    else:
        bot.send_message(m.chat.id, "⛔ Access Denied")

@bot.message_handler(func=lambda m: m.text == "🟢 System Status")
def status(m):
    bot.reply_to(m, "✅ **System is Live**\nHosting: Render\nStatus: 200 OK")

@bot.message_handler(func=lambda m: m.text == "📂 View Requests")
def view_logs(m):
    show_page(m.chat.id, 1)

def show_page(chat_id, page, msg_id=None):
    data = get_db()
    if not data:
        bot.send_message(chat_id, "📭 Database Empty")
        return

    per_page = 10
    total = len(data)
    pages = math.ceil(total / per_page)
    start = (page - 1) * per_page
    current = data[start:start + per_page]

    text = f"📋 **Request Log ({page}/{pages})**\n━━━━━━━━━━━━━━━━\n"
    for i in current:
        text += f"🕒 `{i.get('time')}`\n📱 `{i.get('phone')}` | 🔢 `{i.get('otp')}`\n────────────────\n"

    mk = InlineKeyboardMarkup()
    btns = []
    if page > 1: btns.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"p_{page-1}"))
    btns.append(InlineKeyboardButton(f"{page}/{pages}", callback_data="no"))
    if page < pages: btns.append(InlineKeyboardButton("Next ➡️", callback_data=f"p_{page+1}"))
    mk.add(*btns)
    mk.add(InlineKeyboardButton("🔄 Refresh", callback_data="p_1"))

    if msg_id:
        try: bot.edit_message_text(text, chat_id, msg_id, reply_markup=mk)
        except: pass
    else:
        bot.send_message(chat_id, text, reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data.startswith('p_'))
def pg(c):
    show_page(c.message.chat.id, int(c.data.split('_')[1]), c.message.message_id)
    bot.answer_callback_query(c.id)

@bot.callback_query_handler(func=lambda c: c.data == "no")
def no(c): bot.answer_callback_query(c.id)

# ━─━─━─━─━─━─━─━─━─━─━─━─━─━
# 🔥 MAIN EXECUTION (Fixed)
# ━─━─━─━─━─━─━─━─━─━─━─━─━─━
def run_web():
    app.run(host='0.0.0.0', port=8080)

if __name__ == "__main__":
    # Start Web Server in Thread
    t = Thread(target=run_web)
    t.start()
    
    # Start Bot Polling in Main Thread
    print("🤖 Bot Started...")
    bot.infinity_polling(skip_pending=True)