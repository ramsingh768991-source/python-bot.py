import os
import json
import time
import io
import random
import secrets
import threading
import requests
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import urllib3

# SSL warning hide karne ke liye
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ========== CONFIG ==========
BOT_TOKEN = "8963206324:AAHCZmYlGxFp2l4aj7OcxjoFaQcmLJS7pCY"
ADMIN_ID = 8954250383
API_PORT = 5000

# STRICT ALLOWED CHANNEL
ALLOWED_CHANNEL = "@yadavmods1"
ALLOWED_CHANNEL_LINK = "https://t.me/yadavmods1"

if ":" not in BOT_TOKEN:
    raise ValueError("BOT_TOKEN galat hai! Kripya BotFather se pura token copy karke dalein.")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

# ========== ANTI-SPAM ==========
user_last_click = {}

def is_flooding(user_id):
    now = time.time()
    uid = str(user_id)
    if uid in user_last_click:
        if now - user_last_click[uid] < 0.3:
            return True
    user_last_click[uid] = now
    return False

# ========== FILES & STORAGE ==========
FILES = [
    "balances.json", "orders.json", "users.json", "settings.json", 
    "categories.json", "products.json", "temp.json", "payments.json", 
    "utr_history.json", "resellers.json", "spins.json", "referrals.json",
    "coupons.json"
]
for filename in FILES:
    if not os.path.exists(filename) or os.path.getsize(filename) == 0:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump({}, f, ensure_ascii=False)

def load_json(filename):
    try:
        if not os.path.exists(filename) or os.path.getsize(filename) == 0:
            return {}
        with open(filename, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}

def save_json(filename, data):
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving {filename}: {e}")

def load_coupons():
    return load_json("coupons.json")

def save_coupons(data):
    save_json("coupons.json", data)

settings = load_json("settings.json")
default_settings = {
    "proof_link": ALLOWED_CHANNEL_LINK,
    "howto_link": ALLOWED_CHANNEL_LINK,
    "support_user": "@valimods34",
    "admin_telegram": ALLOWED_CHANNEL_LINK,
    "fampay_upi": "abhishekryadv@fam",
    "fampay_api": "FAM_9D5789E1790D3F127382DB4187F8708C40F845A2",
    "reseller_api_key": "8a36b04b2b5244ded2b47c7e338c783b",
    "reseller_master_key": "a7f3e8b2c9d1f4a6b8c2d5e9f1a3b6c8",
    "referral_bonus": 1.5,
    "log_channel_id": ALLOWED_CHANNEL,
    "server_public_ip": "YOUR_SERVER_IP",
    "maintenance_mode": False
}
for key, val in default_settings.items():
    if key not in settings:
        settings[key] = val
settings["log_channel_id"] = ALLOWED_CHANNEL
settings["proof_link"] = ALLOWED_CHANNEL_LINK
save_json("settings.json", settings)

categories = load_json("categories.json")
if not categories:
    categories = {
        "c1": {"name": "Non-Root Mobile", "position": 1},
        "c2": {"name": "Root Mobile", "position": 2},
        "c3": {"name": "PC / Computer", "position": 3},
        "c4": {"name": "iOS / iPhone", "position": 4}
    }
    save_json("categories.json", categories)

products = load_json("products.json")
if not products:
    products = {
        "p1": {
            "name": "VIP Mod Non-Root",
            "cat": "c1",
            "position": 1,
            "is_api": 0,
            "plans": [
                {"days": "1 Day", "price": 50, "reseller_price": 40, "keys": ["DEMO-KEY-1DAY-9988"]},
                {"days": "7 Days", "price": 200, "reseller_price": 160, "keys": ["DEMO-KEY-7DAYS-4411"]}
            ]
        }
    }
    save_json("products.json", products)

def set_temp(user_id, key, val):
    temp = load_json("temp.json")
    uid = str(user_id)
    if uid not in temp:
        temp[uid] = {}
    temp[uid][key] = val
    save_json("temp.json", temp)

def get_temp(user_id, key):
    temp = load_json("temp.json")
    return temp.get(str(user_id), {}).get(key, "")

def is_reseller(user_id):
    resellers = load_json("resellers.json")
    return str(user_id) in resellers

def is_maintenance():
    st = load_json("settings.json")
    return st.get("maintenance_mode", False)

def generate_unique_reseller_keys(user_id):
    resellers = load_json("resellers.json")
    uid_str = str(user_id)
    if uid_str not in resellers:
        resellers[uid_str] = {
            "added_date": datetime.now().strftime("%d %b %Y"),
            "reseller_key": f"res_{secrets.token_hex(10)}",
            "master_key": f"mst_{secrets.token_hex(14)}"
        }
        save_json("resellers.json", resellers)
    elif "reseller_key" not in resellers[uid_str] or "master_key" not in resellers[uid_str]:
        resellers[uid_str]["reseller_key"] = f"res_{secrets.token_hex(10)}"
        resellers[uid_str]["master_key"] = f"mst_{secrets.token_hex(14)}"
        save_json("resellers.json", resellers)
    return resellers[uid_str]

def mask_utr(utr_val):
    u = str(utr_val).strip()
    if len(u) <= 4:
        return "••••••••"
    return f"••••••••{u[-4:]} (VERIFIED)"

def mask_license_key(key):
    if not key or len(key) <= 6:
        return "████████ (HIDDEN)"
    return f"{key[:4]}••••••••{key[-2:]} (PROTECTED)"

def show_page(chat_id, message_id, text, reply_markup=None):
    try:
        bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, reply_markup=reply_markup)
    except Exception:
        try:
            bot.delete_message(chat_id=chat_id, message_id=message_id)
        except Exception:
            pass
        bot.send_message(chat_id, text, reply_markup=reply_markup)

def send_channel_log(msg_text):
    try:
        bot_info = bot.get_me()
        bot_username = f"@{bot_info.username}" if bot_info.username else "@AbhishekStoreBot"
    except Exception:
        bot_username = "@AbhishekStoreBot"

    full_msg = f"{msg_text}\n\n🤖 <b>Store Bot:</b> {bot_username}"
    kb = InlineKeyboardMarkup().add(InlineKeyboardButton("🤖 Open Store Bot", url=f"https://t.me/{bot_username.replace('@', '')}"))

    try:
        bot.send_message(ALLOWED_CHANNEL, full_msg, reply_markup=kb)
    except Exception as e:
        print(f"Log Channel Broadcast Error: {e}")

@bot.my_chat_member_handler()
def block_unauthorized_channels(update):
    chat = update.chat
    if chat.type in ["channel", "group", "supergroup"]:
        chat_user = f"@{chat.username}" if chat.username else str(chat.id)
        if chat_user.lower() != ALLOWED_CHANNEL.lower():
            try:
                bot.leave_chat(chat.id)
            except Exception:
                pass

# ========== RESELLER API CALL ==========
def call_reseller_api(post_data, master_key):
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "x-master-key": master_key,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
    urls = [
        "https://bantibhaiya.com/api/reseller_v1.php",
        "https://bantibhaiya.to/api/reseller_v1.php"
    ]
    for url in urls:
        try:
            r = requests.post(url, data=post_data, headers=headers, timeout=20, verify=False)
            return r.json()
        except Exception:
            continue
    return {"status": "error", "message": "Server Connection Failed"}

# ========== BUILT-IN REST API SERVER ==========
class ResellerAPIHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == "/api/reseller/generate_key":
            content_length = int(self.headers.get('Content-Length', 0))
            post_data_raw = self.rfile.read(content_length).decode('utf-8')
            
            req = {}
            try:
                req = json.loads(post_data_raw)
            except Exception:
                parsed = parse_qs(post_data_raw)
                req = {k: v[0] for k, v in parsed.items()}

            reseller_key = req.get("reseller_key", "").strip()
            master_key = req.get("master_key", "").strip()
            product_id = req.get("product_id", "").strip()
            duration = req.get("duration", "").strip().replace("_", " ")
            android_id = req.get("android_id", "").strip()

            resellers = load_json("resellers.json")
            user_id = None
            for r_uid, r_data in resellers.items():
                if r_data.get("reseller_key") == reseller_key and r_data.get("master_key") == master_key:
                    user_id = str(r_uid)
                    break

            if not user_id:
                self.send_response(401)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": "Unauthorized! You are not an active Reseller."}).encode())
                return

            products_data = load_json("products.json")
            if product_id not in products_data:
                self.send_response(404)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": "Invalid Product ID"}).encode())
                return

            prod = products_data[product_id]
            plan = None
            for p in prod.get("plans", []):
                if p["days"].lower() == duration.lower():
                    plan = p
                    break

            if not plan:
                self.send_response(404)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": f"Plan '{duration}' not found"}).encode())
                return

            price = float(plan.get("reseller_price", plan["price"]))
            balances = load_json("balances.json")
            current_bal = float(balances.get(user_id, 0))

            if current_bal < price:
                self.send_response(402)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": "Insufficient Balance"}).encode())
                return

            assigned_key = ""
            if prod.get("is_api"):
                st = load_json("settings.json")
                api_post_data = {
                    "api_key": st.get("reseller_api_key", ""),
                    "action": "buy",
                    "product_id": prod.get("api_pid", ""),
                    "duration": plan["days"],
                    "android_id": android_id
                }
                api_res = call_reseller_api(api_post_data, st.get("reseller_master_key", ""))

                if api_res.get("status") in ["success", 1, "1"] or "key" in api_res or "license" in api_res:
                    assigned_key = api_res.get("key") or api_res.get("license") or "KEY_SUCCESS"
                else:
                    self.send_response(502)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({"status": "error", "message": "API Error"}).encode())
                    return
            else:
                if not plan.get("keys"):
                    self.send_response(503)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({"status": "error", "message": "Out of Stock"}).encode())
                    return
                assigned_key = plan["keys"].pop(0)
                save_json("products.json", products_data)

            balances[user_id] = current_bal - price
            save_json("balances.json", balances)

            order_id = f"ORD{int(time.time())}"
            orders = load_json("orders.json")
            orders[order_id] = {
                "user_id": user_id,
                "product": prod["name"],
                "days": plan["days"],
                "price": price,
                "type": "OTHER_BOT_API",
                "key": assigned_key,
                "date": datetime.now().strftime("%d %b %Y %H:%M")
            }
            save_json("orders.json", orders)

            users_data = load_json("users.json")
            u_info = users_data.get(user_id, {})
            u_name = u_info.get("name", "User")
            u_uname = f"@{u_info.get('username')}" if u_info.get("username") else "N/A"

            send_channel_log(
                f"⚡ <b>OTHER BOT AUTO KEY GENERATED!</b>\n\n"
                f"👤 <b>Customer:</b> {u_name} ({u_uname})\n"
                f"📦 <b>Product:</b> {prod['name']}\n"
                f"⏳ <b>Duration:</b> {plan['days']}\n"
                f"💵 <b>Price Paid:</b> ₹{price}\n"
                f"🔐 <b>License Key:</b> <code>{mask_license_key(assigned_key)}</code>\n"
                f"✅ <b>Status:</b> Auto Synced & Delivered"
            )

            resp_data = {
                "status": "success",
                "order_id": order_id,
                "product": prod["name"],
                "duration": plan["days"],
                "license_key": assigned_key,
                "deducted_price": price,
                "remaining_balance": balances[user_id]
            }

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(resp_data).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        return

def run_api_server():
    try:
        server = HTTPServer(('0.0.0.0', API_PORT), ResellerAPIHandler)
        server.serve_forever()
    except Exception as e:
        print(f"API Server Port Error: {e}")

# ========== FAMPAY GATEWAY INTEGRATION ==========
def create_fampay_order(chat_id, message_id, user_id, amount):
    st = load_json("settings.json")
    api_key = st.get("fampay_api", "").strip()
    
    if amount < 1 or amount > 5000:
        try:
            bot.edit_message_text(chat_id=chat_id, message_id=message_id, text="❌ Amount ₹1 se ₹5000 ke beech me hona chahiye", reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("⬅️ Back", callback_data="addbal")))
        except Exception:
            bot.send_message(chat_id, "❌ Amount ₹1 se ₹5000 ke beech me hona chahiye", reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("⬅️ Back", callback_data="addbal")))
        return
        
    url = f"https://fampaygateway.site/api/create_order.php?amount={amount}&api_key={api_key}"
    try:
        res = requests.get(url, timeout=15, verify=False).json()
    except Exception as e:
        res = {"status": "error", "message": str(e)}
        
    if res.get("status") == "success":
        data = res.get("data", {})
        order_id = data.get("order_id")
        expire_time = int(time.time()) + (5 * 60)
        
        orders = load_json("orders.json")
        orders[order_id] = {
            "user": user_id,
            "amount": amount,
            "status": "pending",
            "created": int(time.time()),
            "expire": expire_time
        }
        save_json("orders.json", orders)
        
        expire_display = datetime.fromtimestamp(expire_time).strftime("%H:%M:%S")
        msg = (f"💸 <b>Payment Request</b>\n\n"
               f"Amount: ₹{data.get('amount')}\n"
               f"Order ID: <code>{data.get('order_id')}</code>\n"
               f"UPI ID: <code>{data.get('upi_id')}</code>\n"
               f"⏰ Expire: {expire_display}\n\n"
               f"QR scan karke turant payment karo")
               
        kb = InlineKeyboardMarkup(row_width=1).add(
            InlineKeyboardButton("🔄 Check Payment", callback_data=f"check_{order_id}"),
            InlineKeyboardButton("❌ Cancel Order", callback_data=f"cancel_{order_id}"),
            InlineKeyboardButton("⬅️ Back", callback_data="addbal")
        )
        
        try:
            bot.delete_message(chat_id, message_id)
        except Exception:
            pass
        bot.send_photo(chat_id, photo=data.get('qr_url'), caption=msg, reply_markup=kb)
    else:
        err_msg = res.get("message", "Unknown error")
        try:
            bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=f"❌ Order create nahi hua. Dubara try karo\n\nError: {err_msg}", reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("⬅️ Back", callback_data="addbal")))
        except Exception:
            bot.send_message(chat_id, f"❌ Order create nahi hua. Dubara try karo\n\nError: {err_msg}", reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("⬅️ Back", callback_data="addbal")))

def check_fampay_payment(chat_id, message_id, order_id):
    st = load_json("settings.json")
    api_key = st.get("fampay_api", "").strip()
    orders = load_json("orders.json")
    
    if order_id not in orders:
        bot.answer_callback_query(chat_id, "Order nahi mila ya expire ho gaya", show_alert=True)
        return
        
    ord_info = orders[order_id]
    if int(time.time()) > ord_info.get("expire", 0):
        ord_info["status"] = "expired"
        save_json("orders.json", orders)
        try:
            bot.edit_message_text(chat_id=chat_id, message_id=message_id, text="❌ <b>Order Expired!</b>\n\n5 Minute ho gaye. Naya order banao", reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("➕ New Payment", callback_data="addbal")))
        except Exception:
            bot.send_message(chat_id, "❌ <b>Order Expired!</b>", reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("➕ New Payment", callback_data="addbal")))
        return
        
    if ord_info.get("status") == "paid":
        bot.answer_callback_query(chat_id, "Payment already ho chuki hai", show_alert=True)
        return
        
    url = f"https://fampaygateway.site/api/verify.php?order_id={order_id}&api_key={api_key}"
    try:
        res = requests.get(url, timeout=15, verify=False).json()
    except Exception:
        res = {}
        
    if res.get("status") == "success" and "data" in res and "utr" in res["data"]:
        amount = float(res["data"]["amount"])
        user_id = str(ord_info["user"])
        raw_utr = res["data"]["utr"]
        hidden_utr = mask_utr(raw_utr)
        
        balances = load_json("balances.json")
        balances[user_id] = balances.get(user_id, 0) + amount
        save_json("balances.json", balances)
        
        became_reseller = False
        if amount >= 300:
            generate_unique_reseller_keys(user_id)
            became_reseller = True

        ord_info["status"] = "paid"
        save_json("orders.json", orders)
        
        users_data = load_json("users.json")
        user_info = users_data.get(user_id, {})
        u_name = user_info.get("name", "User")
        u_uname = f"@{user_info.get('username')}" if user_info.get("username") else "N/A"
        
        try:
            admin_msg = (
                f"💰 <b>New Balance Added!</b>\n\n"
                f"👤 Name: {u_name}\n"
                f"🔗 Username: {u_uname}\n"
                f"🆔 User ID: <code>{user_id}</code>\n"
                f"💵 Amount: ₹{amount}\n"
                f"🔖 UTR: <code>{raw_utr}</code>"
            )
            bot.send_message(ADMIN_ID, admin_msg)
        except Exception as e:
            print(f"Admin notification error: {e}")

        channel_pay_msg = (
            f"💰 <b>NEW PAYMENT RECEIVED!</b>\n\n"
            f"👤 <b>User:</b> {u_name} ({u_uname})\n"
            f"🆔 <b>User ID:</b> <code>{user_id}</code>\n"
            f"💵 <b>Amount Added:</b> ₹{amount}\n"
            f"🔖 <b>UTR:</b> <code>{hidden_utr}</code>\n"
            f"⏰ <b>Time:</b> {res['data'].get('payment_time', datetime.now().strftime('%H:%M:%S'))}\n"
        )
        if became_reseller:
            channel_pay_msg += "👑 <b>Status:</b> Upgraded to Reseller ⭐\n"
        channel_pay_msg += "✅ <b>Wallet Balance Updated Successfully!</b>"
        send_channel_log(channel_pay_msg)
        
        msg = (f"✅ <b>Payment Successful!</b>\n\n"
               f"₹{amount} Balance me add ho gaya\n")
        if became_reseller:
            msg += "👑 <b>Badhai ho! Aapko Reseller status mil gaya hai!</b>\n"
        
        msg += f"UTR: <code>{hidden_utr}</code>\nTime: {res['data'].get('payment_time', datetime.now().strftime('%H:%M:%S'))}"
        kb = InlineKeyboardMarkup().add(InlineKeyboardButton("⬅️ Menu", callback_data="back"))
        try:
            bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=msg, reply_markup=kb)
        except Exception:
            bot.send_message(chat_id, msg, reply_markup=kb)
    else:
        remaining = ord_info.get("expire", 0) - int(time.time())
        if remaining < 0:
            remaining = 0
        min_rem = remaining // 60
        sec_rem = remaining % 60
        bot.answer_callback_query(chat_id, f"Payment abhi pending hai! ({min_rem}m {sec_rem}s bache hain)", show_alert=True)

def cancel_fampay_order(chat_id, message_id, order_id):
    orders = load_json("orders.json")
    if order_id in orders:
        orders[order_id]["status"] = "cancelled"
        save_json("orders.json", orders)
        try:
            bot.edit_message_text(chat_id=chat_id, message_id=message_id, text="❌ <b>Order Cancelled</b>\n\nNaya payment kar sakte ho", reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("➕ New Payment", callback_data="addbal")))
        except Exception:
            bot.send_message(chat_id, "❌ <b>Order Cancelled</b>", reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("➕ New Payment", callback_data="addbal")))

# ========== MAIN MENU ==========
def get_main_menu(user_id=None):
    st = load_json("settings.json")
    check_update_url = st.get("proof_link", ALLOWED_CHANNEL_LINK)
    
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("🛒 Shop / Store Product", callback_data="shop"),
        InlineKeyboardButton("📢 Official Channel", url=check_update_url),
        InlineKeyboardButton("Add Balance", callback_data="addbal"),
        InlineKeyboardButton("👑 Reseller", callback_data="become_reseller")
    )
    kb.add(InlineKeyboardButton("👤 My Profile + Key History", callback_data="profile"))
    kb.add(
        InlineKeyboardButton("Referral", callback_data="referral"),
        InlineKeyboardButton("How To Use", callback_data="howto"),
        InlineKeyboardButton("Support", callback_data="support"),
        InlineKeyboardButton("Lucky Spin", callback_data="lucky_spin")
    )
    return kb

def get_admin_panel():
    st = load_json("settings.json")
    m_status = "ON 🔴" if st.get("maintenance_mode", False) else "OFF 🟢"
    
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton(f"🛠️ Maintenance: {m_status}", callback_data="toggle_maintenance"),
        InlineKeyboardButton("📁 Add/Order Category", callback_data="addcat"),
        InlineKeyboardButton("📦 Add/Order Product", callback_data="addprod"),
        InlineKeyboardButton("➕ Add Plan", callback_data="addplan"),
        InlineKeyboardButton("✏️ Edit Plan Price/Details", callback_data="editplan"),
        InlineKeyboardButton("🔑 Add Manual Keys", callback_data="addplankeys"),
        InlineKeyboardButton("🗑️ Delete Product", callback_data="delprod"),
        InlineKeyboardButton("👥 User List", callback_data="userlist"),
        InlineKeyboardButton("📢 Broadcast", callback_data="broadcast"),
        InlineKeyboardButton("👑 Manage Resellers", callback_data="manageresellers"),
        InlineKeyboardButton("❌ Remove Reseller", callback_data="removereseller"),
        InlineKeyboardButton("💰 Manual Add Bal", callback_data="adduserbal"),
        InlineKeyboardButton("🌐 All API", callback_data="all_api"),
        InlineKeyboardButton("📱 Set FamPay UPI ID", callback_data="setupiapi"),
        InlineKeyboardButton("🔑 Set UPI API Key", callback_data="setapikey"),
        InlineKeyboardButton("🔗 Set Telegram/Social Links", callback_data="settelegramlinks"),
        InlineKeyboardButton("📹 Set Tutorial Link", callback_data="settutoriallink")
    )
    return kb

# ========== COMMAND HANDLERS ==========
@bot.message_handler(commands=["start"])
def cmd_start(message):
    try:
        uid = str(message.from_user.id)
        chat_id = message.chat.id
        
        # Check Maintenance
        if is_maintenance() and int(uid) != ADMIN_ID:
            return bot.send_message(
                chat_id,
                "🚧 <b>Bot Under Maintenance!</b>\n\n"
                "Kripya dhyan dein: Bot par abhi maintenance chal raha hai.\n"
                "Kuch samay baad dobara try karein. असुविधा के लिए खेद है!"
            )
            
        set_temp(uid, "waiting", "")
        
        args = message.text.split()
        referrer_id = args[1] if len(args) > 1 else None
        
        balances = load_json("balances.json")
        users = load_json("users.json")
        referrals = load_json("referrals.json")
        
        if uid not in balances:
            balances[uid] = 0
            save_json("balances.json", balances)
            
        if uid not in users:
            users[uid] = {
                "name": message.from_user.first_name or "User",
                "username": message.from_user.username or "",
                "join": datetime.now().strftime("%d %b %Y")
            }
            save_json("users.json", users)
            
            if referrer_id and referrer_id != uid and referrer_id in users:
                if uid not in referrals:
                    referrals[uid] = referrer_id
                    save_json("referrals.json", referrals)
            
        bal = balances.get(uid, 0)
        
        msg = (
            "🏢 <b>ABHISHEK STORE</b>\n\n"
            f"🎉 Hello, <b>{message.from_user.first_name}</b>!\n\n"
            "🔑 Powered by Abhishek Store\n\n"
            "— 🏢 Direct deals with every supplier\n"
            "— 💧 Instant delivery after payment\n"
            "— 📤 Guaranteed discounted prices\n"
            "— 📞 24/7 admin support\n\n"
            "<i>Tap any button below to begin.</i>\n\n"
            f"💲 <b>Your Balance: ₹{bal}.00</b>"
        )
        bot.send_message(chat_id, msg, reply_markup=get_main_menu(uid))
    except Exception as e:
        print(f"Error in /start: {e}")

@bot.message_handler(commands=["admin"])
def cmd_admin(message):
    uid = message.from_user.id
    if uid != ADMIN_ID:
        return
    set_temp(str(uid), "waiting", "")
    bot.send_message(message.chat.id, "⚙️ <b>Admin Panel</b>", reply_markup=get_admin_panel())

@bot.message_handler(commands=["gen", "generate"])
def cmd_reseller_gen(message):
    uid = str(message.from_user.id)
    chat_id = message.chat.id
    
    if is_maintenance() and int(uid) != ADMIN_ID:
        return bot.send_message(chat_id, "🚧 <b>Bot Under Maintenance!</b> Kuch samay baad try karein.")
        
    args = message.text.split()
    
    if not is_reseller(uid):
        return bot.send_message(chat_id, "❌ <b>Access Denied!</b> Sirf active Resellers hi key generate kar sakte hain. Pehle ₹300 add karke Reseller banein.")

    if len(args) < 5:
        return bot.send_message(
            chat_id,
            "⚠️ <b>Requirement Command Format:</b>\n\n"
            "<code>/gen &lt;reseller_key&gt; &lt;master_key&gt; &lt;product_id&gt; &lt;duration&gt; [android_id]</code>\n\n"
            "<b>Example:</b>\n"
            "<code>/gen res_xxxx mst_xxxx p1 1_Day</code>"
        )

    r_key, m_key, pid, dur = args[1].strip(), args[2].strip(), args[3].strip(), args[4].replace("_", " ").strip()
    a_id = args[5].strip() if len(args) > 5 else ""

    resellers = load_json("resellers.json")
    user_keys = resellers.get(uid, {})
    if r_key != user_keys.get("reseller_key") or m_key != user_keys.get("master_key"):
        return bot.send_message(chat_id, "❌ Aapki Reseller Key ya Master Key galat hai!")

    prods = load_json("products.json")
    if pid not in prods:
        return bot.send_message(chat_id, "❌ Product nahi mila.")

    plan_idx = None
    for idx, pl in enumerate(prods[pid].get("plans", [])):
        if pl["days"].lower() == dur.lower():
            plan_idx = idx
            break

    if plan_idx is None:
        return bot.send_message(chat_id, "❌ Plan duration galat hai.")

    execute_purchase(chat_id, uid, pid, plan_idx, a_id)

# ========== CALLBACK ROUTER ==========
@bot.callback_query_handler(func=lambda call: True)
def callback_router(call):
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    user_id = str(call.from_user.id)
    
    # Check Maintenance for callbacks
    if is_maintenance() and int(user_id) != ADMIN_ID:
        try:
            bot.answer_callback_query(call.id, "🚧 Bot maintenance mode par hai! Kripya intezar karein.", show_alert=True)
        except Exception:
            pass
        return
        
    if is_flooding(user_id):
        try:
            bot.answer_callback_query(call.id, "⚠️️ Bahut tezi se click kar rahe ho!", show_alert=True)
        except Exception:
            pass
        return

    data = call.data

    # TOGGLE MAINTENANCE (Admin Only)
    if data == "toggle_maintenance" and int(user_id) == ADMIN_ID:
        st = load_json("settings.json")
        curr = st.get("maintenance_mode", False)
        st["maintenance_mode"] = not curr
        save_json("settings.json", st)
        status_txt = "ON 🔴" if st["maintenance_mode"] else "OFF 🟢"
        bot.answer_callback_query(call.id, f"Maintenance Mode is now {status_txt}")
        try:
            bot.edit_message_reply_markup(chat_id=chat_id, message_id=message_id, reply_markup=get_admin_panel())
        except Exception:
            bot.send_message(chat_id, "⚙️️ <b>Admin Panel</b>", reply_markup=get_admin_panel())
        return

    if data == "back":
        bot.answer_callback_query(call.id)
        set_temp(user_id, "waiting", "")
        balances = load_json("balances.json")
        bal = balances.get(user_id, 0)
        
        msg = (
            "🏢 <b>ABHISHEK STORE</b>\n\n"
            f"🎉 Hello, <b>{call.from_user.first_name}</b>!\n\n"
            "🔑 Powered by Abhishek Store\n\n"
            "— 🏢 Direct deals with every supplier\n"
            "— 💧 Instant delivery after payment\n"
            "— 📤 Guaranteed discounted prices\n"
            "— 📞 24/7 admin support\n\n"
            "<i>Tap any button below to begin.</i>\n\n"
            f"💲 <b>Your Balance: ₹{bal}.00</b>"
        )
        try:
            bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=msg, reply_markup=get_main_menu(user_id))
        except Exception:
            bot.send_message(chat_id, msg, reply_markup=get_main_menu(user_id))

    elif data == "become_reseller":
        bot.answer_callback_query(call.id)
        if is_reseller(user_id):
            res_info = generate_unique_reseller_keys(user_id)
            st = load_json("settings.json")
            server_ip = st.get("server_public_ip", "YOUR_SERVER_IP")
            r_key = res_info.get("reseller_key")
            m_key = res_info.get("master_key")

            other_bot_sample_code = (
                f"# ===== OTHER BOT INTEGRATION CODE =====\n"
                f"import requests\n\n"
                f"API_URL = \"http://{server_ip}:{API_PORT}/api/reseller/generate_key\"\n\n"
                f"def auto_generate_key(product_id, duration, android_id=\"\"):\n"
                f"    payload = {{\n"
                f"        \"reseller_key\": \"{r_key}\",\n"
                f"        \"master_key\": \"{m_key}\",\n"
                f"        \"product_id\": product_id,\n"
                f"        \"duration\": duration,\n"
                f"        \"android_id\": android_id\n"
                f"    }}\n"
                f"    res = requests.post(API_URL, json=payload).json()\n"
                f"    if res.get(\"status\") == \"success\":\n"
                f"        return res[\"license_key\"]\n"
                f"    return f\"Error: {{res.get('message')}}\"\n"
            )

            msg = (
                "👑 <b>RESELLER API & OTHER BOT PANEL</b>\n\n"
                "Aap active <b>Reseller</b> hain aur aapko discounted prices mil rahe hain!\n\n"
                "Aapki personal unique keys:\n"
                f"🔑 <b>Your Reseller API Key:</b>\n<code>{r_key}</code>\n\n"
                f"🔒 <b>Your Master Key:</b>\n<code>{m_key}</code>\n\n"
                f"🌐 <b>API Endpoint:</b>\n"
                f"<code>http://{server_ip}:{API_PORT}/api/reseller/generate_key</code>\n\n"
                "📜 <b>Other Bot Python Code:</b>\n"
                f"<code>{other_bot_sample_code}</code>\n\n"
                "💬 <b>Telegram Direct Command:</b>\n"
                f"<code>/gen {r_key} {m_key} &lt;product_id&gt; &lt;duration&gt;</code>"
            )
            kb = InlineKeyboardMarkup().add(InlineKeyboardButton("⬅️ Back", callback_data="back"))
        else:
            kb = InlineKeyboardMarkup(row_width=1).add(
                InlineKeyboardButton("💳 Add ₹300 for Reseller Status", callback_data="reseller_pay_300"),
                InlineKeyboardButton("⬅️ Back", callback_data="back")
            )
            msg = (
                "👑 <b>Become a Reseller</b>\n\n"
                "Reseller banne ke liye aapko ek baar me minimum <b>₹300</b> add karne honge.\n\n"
                "<b>Reseller Features:</b>\n"
                "— Sabhi items Reseller Discount rate par milenge\n"
                "— Unique <b>Reseller Key & Master Key</b> milegi\n"
                "— Apna khud ka alag <b>Other Bot</b> chalane ka pura code milega\n\n"
                "<i>₹300 add hote hi automatic aapka Reseller account activate ho jayega!</i>\n\n"
                "Neeche click karke payment karein:"
            )
        try:
            bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=msg, reply_markup=kb)
        except Exception:
            bot.send_message(chat_id, msg, reply_markup=kb)

    elif data == "reseller_pay_300":
        bot.answer_callback_query(call.id)
        set_temp(user_id, "waiting", "reseller_custom_amt")
        create_fampay_order(chat_id, message_id, user_id, 300.0)

    elif data in ["shop", "backcat"]:
        bot.answer_callback_query(call.id)
        set_temp(user_id, "waiting", "")
        cats = load_json("categories.json")
        
        sorted_cats = sorted(cats.items(), key=lambda x: x[1].get("position", 999))
        kb = InlineKeyboardMarkup(row_width=1)
        for cid, c in sorted_cats:
            kb.add(InlineKeyboardButton(f"📁 {c['name']}", callback_data=f"cat_{cid}"))
        kb.add(InlineKeyboardButton("⬅️ Back to Menu", callback_data="back"))
        
        shop_text = "<b>ABHISHEK PANEL — SHOP</b>\n\n📁 <b>Select Category:</b>"
        
        try:
            bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=shop_text, reply_markup=kb)
        except Exception:
            bot.send_message(chat_id, shop_text, reply_markup=kb)

    elif data.startswith("cat_"):
        bot.answer_callback_query(call.id)
        cid = data.replace("cat_", "")
        prods = load_json("products.json")
        
        cat_prods = [(pid, p) for pid, p in prods.items() if p.get("cat") == cid]
        sorted_prods = sorted(cat_prods, key=lambda x: x[1].get("position", 999))
        
        kb = InlineKeyboardMarkup(row_width=1)
        found = False
        for pid, p in sorted_prods:
            kb.add(InlineKeyboardButton(f"📦 {p['name']}", callback_data=f"buy_{pid}"))
            found = True
        if not found:
            kb.add(InlineKeyboardButton("⚠️ Is Category me koi Product nahi hai", callback_data="backcat"))
        kb.add(InlineKeyboardButton("⬅️ Back to Categories", callback_data="backcat"))
        
        prod_text = "<b>ABHISHEK PANEL — SHOP</b>\n\n📦 <b>Select Product:</b>"
        
        try:
            bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=prod_text, reply_markup=kb)
        except Exception:
            bot.send_message(chat_id, prod_text, reply_markup=kb)

    elif data.startswith("buy_"):
        bot.answer_callback_query(call.id)
        pid = data.replace("buy_", "")
        prods = load_json("products.json")
        p = prods.get(pid)
        if not p:
            return bot.send_message(chat_id, "❌ Product nahi mila.", reply_markup=get_main_menu(user_id))
        
        user_is_reseller = is_reseller(user_id)
        kb = InlineKeyboardMarkup(row_width=1)
        for idx, plan in enumerate(p.get("plans", [])):
            price = plan.get("reseller_price" if user_is_reseller else "price", plan["price"])
            stock = "⚡ Auto API" if p.get("is_api") else f"Stock: {len(plan.get('keys', []))}"
            kb.add(InlineKeyboardButton(f"⏳ {plan['days']} - ₹{price} ({stock})", callback_data=f"plan_{pid}_{idx}"))
        
        if int(user_id) == ADMIN_ID:
            kb.add(InlineKeyboardButton("➕ Add Plan (Admin)", callback_data=f"adminaddplan_{pid}"))
            
        kb.add(InlineKeyboardButton("⬅️ Back", callback_data=f"cat_{p['cat']}"))
        try:
            bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=f"🛒 <b>Select Plan for {p['name']}:</b>", reply_markup=kb)
        except Exception:
            bot.send_message(chat_id, f"🛒 <b>Select Plan for {p['name']}:</b>", reply_markup=kb)

    elif data.startswith("adminaddplan_") and int(user_id) == ADMIN_ID:
        bot.answer_callback_query(call.id)
        pid = data.replace("adminaddplan_", "")
        set_temp(user_id, "addplan_pid", pid)
        set_temp(user_id, "waiting", "plan_days")
        bot.send_message(chat_id, "📅 <b>Duration Bhejo:</b> (e.g. <code>1 Day</code>, <code>3 Days</code>, <code>7 Days</code>)")

    elif data.startswith("plan_"):
        bot.answer_callback_query(call.id)
        _, pid, plan_idx = data.split("_")
        plan_idx = int(plan_idx)
        prods = load_json("products.json")
        p = prods.get(pid, {})
        if p.get("is_api") and p.get("need_android_id"):
            set_temp(user_id, "pending_pid", pid)
            set_temp(user_id, "pending_plan_idx", plan_idx)
            set_temp(user_id, "waiting", "android_id")
            kb = InlineKeyboardMarkup().add(InlineKeyboardButton("⬅️ Cancel", callback_data="shop"))
            bot.send_message(chat_id, "📱 <b>Enter Your Android ID:</b>\n\nExample: <code>0b9b969bc2e7997b</code>", reply_markup=kb)
        else:
            execute_purchase(chat_id, user_id, pid, plan_idx, "")

    elif data == "profile":
        bot.answer_callback_query(call.id)
        users = load_json("users.json")
        balances = load_json("balances.json")
        orders = load_json("orders.json")
        u = users.get(user_id, {"name": call.from_user.first_name, "join": "N/A"})
        bal = balances.get(user_id, 0)
        reseller_status = "👑 Yes (Reseller Price Active)" if is_reseller(user_id) else "❌ No"
        
        user_orders = [o for o in orders.values() if str(o.get("user_id")) == user_id]
        
        msg = (f"👤 <b>User Profile & Key History</b>\n\n"
               f"🆔 <b>ID:</b> <code>{user_id}</code>\n"
               f"👤 <b>Name:</b> {u.get('name')}\n"
               f"💰 <b>Balance:</b> ₹{bal}\n"
               f"👑 <b>Reseller Status:</b> {reseller_status}\n"
               f"📅 <b>Joined:</b> {u.get('join')}\n"
               f"📦 <b>Total Keys Purchased:</b> {len(user_orders)}\n\n")
        
        if user_orders:
            msg += "🔑 <b>Recent Purchased Keys History:</b>\n"
            for o in user_orders[-5:]:
                msg += f"• <b>{o.get('product')}</b> ({o.get('days')})\n  Key: <code>{o.get('key')}</code>\n  Date: {o.get('date')}\n\n"
        else:
            msg += "<i>Aapne abhi tak koi key nahi kharidi hai.</i>"

        kb = InlineKeyboardMarkup().add(
            InlineKeyboardButton("📦 View All Orders", callback_data="orders"),
            InlineKeyboardButton("⬅️ Back", callback_data="back")
        )
        try:
            bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=msg, reply_markup=kb)
        except Exception:
            bot.send_message(chat_id, msg, reply_markup=kb)

    elif data == "orders":
        bot.answer_callback_query(call.id)
        orders = load_json("orders.json")
        user_orders = [o for o in orders.values() if str(o.get("user_id")) == user_id]
        if not user_orders:
            msg = "📦 Aapne abhi tak koi order / key nahi kharida hai."
        else:
            msg = "📦 <b>Your Purchase & Key History:</b>\n\n"
            for o in user_orders:
                msg += f"• <b>{o.get('product')}</b> ({o.get('days')}) - ₹{o.get('price', 0)}\n  Key: <code>{o.get('key')}</code>\n  Date: {o.get('date')}\n\n"
        kb = InlineKeyboardMarkup().add(InlineKeyboardButton("⬅️ Back", callback_data="profile"))
        try:
            bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=msg, reply_markup=kb)
        except Exception:
            bot.send_message(chat_id, msg, reply_markup=kb)

    elif data == "lucky_spin":
        bot.answer_callback_query(call.id)
        spins = load_json("spins.json")
        today = datetime.now().strftime("%d %m %Y")
        
        if user_id in spins and spins[user_id] == today:
            msg = "🍀 <b>Lucky Spin:</b>\n\n❌ Aapne aaj ka spin pehle hi use kar liya hai! Kal dobara koshish karein."
            kb = InlineKeyboardMarkup().add(InlineKeyboardButton("⬅️ Back", callback_data="back"))
            try:
                bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=msg, reply_markup=kb)
            except Exception:
                bot.send_message(chat_id, msg, reply_markup=kb)
        else:
            kb = InlineKeyboardMarkup().add(
                InlineKeyboardButton("🎰 Spin Now!", callback_data="dospin"),
                InlineKeyboardButton("⬅️ Back", callback_data="back")
            )
            try:
                bot.edit_message_text(chat_id=chat_id, message_id=message_id, text="🍀 <b>Welcome to Lucky Spin!</b>\n\nHar 24 ghante me 1 spin free milega. Paise jeetne ke liye neeche click karein:", reply_markup=kb)
            except Exception:
                bot.send_message(chat_id, "🍀 <b>Welcome to Lucky Spin!</b>", reply_markup=kb)

    elif data == "dospin":
        bot.answer_callback_query(call.id)
        spins = load_json("spins.json")
        today = datetime.now().strftime("%d %m %Y")
        
        if user_id in spins and spins[user_id] == today:
            return bot.answer_callback_query(call.id, "Aap aaj spin kar chuke hain!", show_alert=True)
            
        spins[user_id] = today
        save_json("spins.json", spins)
        
        won_amounts = [0.50, 0.60, 0.70, 0.75, 0.80, 0.90, 1.00]
        won = random.choice(won_amounts)
        
        balances = load_json("balances.json")
        balances[user_id] = balances.get(user_id, 0) + won
        save_json("balances.json", balances)
        
        msg = f"🎉 <b>Congratulation!</b>\n\nLucky Spin me aapne jeete hain: <b>₹{won}</b>\nAapke wallet me add kar diye gaye hain!"
        kb = InlineKeyboardMarkup().add(InlineKeyboardButton("⬅️ Back to Menu", callback_data="back"))
        try:
            bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=msg, reply_markup=kb)
        except Exception:
            bot.send_message(chat_id, msg, reply_markup=kb)

    elif data == "referral":
        bot.answer_callback_query(call.id)
        st = load_json("settings.json")
        bonus = st.get("referral_bonus", 2.0)
        bot_username = bot.get_me().username
        ref_link = f"https://t.me/{bot_username}?start={user_id}"
        
        msg = (f"🟨 <b>Refer & Earn Program</b>\n\n"
               f"Apne dosto ko ye link share karein.\n"
               f"Jab koi aapke link se bot join karega aur purchase karega, tab aapko <b>₹{bonus}</b> ka referral bonus milega!\n\n"
               f"🔗 <b>Aapka Referral Link:</b>\n<code>{ref_link}</code>")
        kb = InlineKeyboardMarkup().add(InlineKeyboardButton("⬅️ Back", callback_data="back"))
        try:
            bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=msg, reply_markup=kb)
        except Exception:
            bot.send_message(chat_id, msg, reply_markup=kb)

    elif data == "addbal":
        bot.answer_callback_query(call.id)
        set_temp(user_id, "waiting", "custom_amount")
        kb = InlineKeyboardMarkup().add(InlineKeyboardButton("⬅️ Cancel", callback_data="back"))
        msg = (
            "💸 <b>Add Balance</b>\n\n"
            "Kitna balance add karna hai? Amount type karein (₹):\n"
            "Min: ₹1 • Max: ₹5,000"
        )
        try:
            bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=msg, reply_markup=kb)
        except Exception:
            bot.send_message(chat_id, msg, reply_markup=kb)

    elif data == "custom_pay":
        bot.answer_callback_query(call.id)
        set_temp(user_id, "waiting", "custom_amount")
        kb = InlineKeyboardMarkup().add(InlineKeyboardButton("⬅️ Cancel", callback_data="back"))
        bot.send_message(chat_id, "💰 <b>Kitna Balance Add Karna Hai?</b>\n\nAmount type karein (₹):", reply_markup=kb)

    elif data.startswith("pay_"):
        bot.answer_callback_query(call.id)
        amt = float(data.replace("pay_", ""))
        create_fampay_order(chat_id, message_id, user_id, amt)

    elif data.startswith("check_"):
        order_id = data.replace("check_", "")
        check_fampay_payment(chat_id, message_id, order_id)

    elif data.startswith("cancel_"):
        order_id = data.replace("cancel_", "")
        cancel_fampay_order(chat_id, message_id, order_id)

    elif data == "broadcast" and int(user_id) == ADMIN_ID:
        bot.answer_callback_query(call.id)
        set_temp(user_id, "waiting", "broadcast_msg")
        kb = InlineKeyboardMarkup().add(InlineKeyboardButton("⬅️ Cancel", callback_data="backadmin"))
        bot.send_message(chat_id, "📢 <b>Broadcast Message Bhejo:</b>\n\nJo bhi message ya photo aap yahan bhejenge, woh sabhi registered users ko chala jayega:", reply_markup=kb)

    elif data == "howto":
        bot.answer_callback_query(call.id)
        st = load_json("settings.json")
        tutorial_link = st.get("howto_link", ALLOWED_CHANNEL_LINK)
        kb = InlineKeyboardMarkup(row_width=1).add(
            InlineKeyboardButton("📹 Watch Tutorial Video", url=tutorial_link),
            InlineKeyboardButton("⬅️ Back", callback_data="back")
        )
        try:
            bot.edit_message_text(chat_id=chat_id, message_id=message_id, text="📖 <b>Tutorial & How To Use:</b>", reply_markup=kb)
        except Exception:
            bot.send_message(chat_id, "📖 <b>Tutorial & How To Use:</b>", reply_markup=kb)

    elif data == "support":
        bot.answer_callback_query(call.id)
        kb = InlineKeyboardMarkup(row_width=1).add(
            InlineKeyboardButton("👨‍💻 Contact Admin", url="https://t.me/valimods34"),
            InlineKeyboardButton("⬅️ Back", callback_data="back")
        )
        msg = "💬 <b>Contact Admin</b>\n\nFor any support or help, contact our admin below:"
        try:
            bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=msg, reply_markup=kb)
        except Exception:
            bot.send_message(chat_id, msg, reply_markup=kb)

    elif data == "backadmin":
        if int(user_id) != ADMIN_ID:
            return
        bot.answer_callback_query(call.id)
        set_temp(user_id, "waiting", "")
        bot.send_message(chat_id, "⚙️ <b>Admin Panel</b>", reply_markup=get_admin_panel())

    elif data == "all_api" and int(user_id) == ADMIN_ID:
        bot.answer_callback_query(call.id)
        st = load_json("settings.json")
        kb = InlineKeyboardMarkup(row_width=1).add(
            InlineKeyboardButton("🔑 Reseller API Key", callback_data="edit_reseller_api"),
            InlineKeyboardButton("🔒 Master API Key", callback_data="edit_master_api"),
            InlineKeyboardButton("💳 FamPay API Key", callback_data="edit_fampay_api_key"),
            InlineKeyboardButton("📱 FamPay UPI ID", callback_data="edit_fampay_upi_id"),
            InlineKeyboardButton("📹 Set Tutorial Link", callback_data="edit_tutorial_link"),
            InlineKeyboardButton("⬅️️ Back to Admin Panel", callback_data="backadmin")
        )
        msg = (
            "🌐 <b>All API & Settings</b>\n\n"
            f"• Reseller API Key: <code>{st.get('reseller_api_key', 'Not Set')}</code>\n"
            f"• Master API Key: <code>{st.get('reseller_master_key', 'Not Set')}</code>\n"
            f"• FamPay API Key: <code>{st.get('fampay_api', 'Not Set')}</code>\n"
            f"• FamPay UPI ID: <code>{st.get('fampay_upi', 'Not Set')}</code>\n"
            f"• Tutorial Link: <code>{st.get('howto_link', 'Not Set')}</code>\n"
            f"• Authorized Channel: <code>{ALLOWED_CHANNEL}</code>\n\n"
            "Kis setting ko update karna hai, select karein:"
        )
        try:
            bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=msg, reply_markup=kb)
        except Exception:
            bot.send_message(chat_id, msg, reply_markup=kb)

    elif data == "edit_tutorial_link" and int(user_id) == ADMIN_ID:
        bot.answer_callback_query(call.id)
        set_temp(user_id, "waiting", "set_tutorial_link")
        kb = InlineKeyboardMarkup().add(InlineKeyboardButton("⬅️ Cancel", callback_data="all_api"))
        bot.send_message(chat_id, "📹 <b>Naya Tutorial (YouTube/Video) Link Bhejo:</b>", reply_markup=kb)

    elif data == "edit_reseller_api" and int(user_id) == ADMIN_ID:
        bot.answer_callback_query(call.id)
        set_temp(user_id, "waiting", "set_reseller_api")
        kb = InlineKeyboardMarkup().add(InlineKeyboardButton("⬅️ Cancel", callback_data="all_api"))
        bot.send_message(chat_id, "🔑 <b>Nayi Reseller API Key Bhejo:</b>", reply_markup=kb)

    elif data == "edit_master_api" and int(user_id) == ADMIN_ID:
        bot.answer_callback_query(call.id)
        set_temp(user_id, "waiting", "set_master_api")
        kb = InlineKeyboardMarkup().add(InlineKeyboardButton("⬅️ Cancel", callback_data="all_api"))
        bot.send_message(chat_id, "🔒 <b>Nayi Master API Key Bhejo:</b>", reply_markup=kb)

    elif data == "edit_fampay_api_key" and int(user_id) == ADMIN_ID:
        bot.answer_callback_query(call.id)
        set_temp(user_id, "waiting", "set_fampay_api")
        kb = InlineKeyboardMarkup().add(InlineKeyboardButton("⬅️ Cancel", callback_data="all_api"))
        bot.send_message(chat_id, "💳 <b>Nayi FamPay API Key Bhejo:</b>", reply_markup=kb)

    elif data == "edit_fampay_upi_id" and int(user_id) == ADMIN_ID:
        bot.answer_callback_query(call.id)
        set_temp(user_id, "waiting", "set_fampay_upi")
        kb = InlineKeyboardMarkup().add(InlineKeyboardButton("⬅️ Cancel", callback_data="all_api"))
        bot.send_message(chat_id, "📱 <b>Nayi FamPay UPI ID Bhejo:</b>", reply_markup=kb)

    elif data == "settutoriallink" and int(user_id) == ADMIN_ID:
        bot.answer_callback_query(call.id)
        set_temp(user_id, "waiting", "set_tutorial_link")
        st = load_json("settings.json")
        kb = InlineKeyboardMarkup().add(InlineKeyboardButton("⬅️ Cancel", callback_data="backadmin"))
        bot.send_message(chat_id, f"📹 <b>How To Use (YouTube/Video) Link Bhejo:</b>\n\nCurrent Link: <code>{st.get('howto_link')}</code>", reply_markup=kb)

    elif data == "setapikey" and int(user_id) == ADMIN_ID:
        bot.answer_callback_query(call.id)
        set_temp(user_id, "waiting", "set_fampay_api")
        st = load_json("settings.json")
        current_api = st.get("fampay_api", "Not Set")
        kb = InlineKeyboardMarkup().add(InlineKeyboardButton("⬅️ Cancel", callback_data="backadmin"))
        bot.send_message(chat_id, f"🔑 <b>UPI Verification API Key Bhejo:</b>\n\nCurrent: <code>{current_api}</code>", reply_markup=kb)

    elif data == "setupiapi" and int(user_id) == ADMIN_ID:
        bot.answer_callback_query(call.id)
        set_temp(user_id, "waiting", "set_fampay_upi")
        kb = InlineKeyboardMarkup().add(InlineKeyboardButton("⬅️ Cancel", callback_data="backadmin"))
        bot.send_message(chat_id, "📱 <b>FamPay UPI ID Bhejo:</b>\n\nExample: <code>yourupi@fam</code>", reply_markup=kb)

    elif data == "settelegramlinks" and int(user_id) == ADMIN_ID:
        bot.answer_callback_query(call.id)
        set_temp(user_id, "waiting", "set_tg_link")
        st = load_json("settings.json")
        kb = InlineKeyboardMarkup().add(InlineKeyboardButton("⬅️ Cancel", callback_data="backadmin"))
        bot.send_message(chat_id, f"🔗 <b>Check Update Link Bhejo:</b>\n\nCurrent Link: <code>{st.get('proof_link')}</code>", reply_markup=kb)

    elif data == "manageresellers" and int(user_id) == ADMIN_ID:
        bot.answer_callback_query(call.id)
        set_temp(user_id, "waiting", "add_reseller_id")
        kb = InlineKeyboardMarkup().add(InlineKeyboardButton("⬅️ Cancel", callback_data="backadmin"))
        bot.send_message(chat_id, "👑 <b>Reseller Banana Hai?</b>\n\nUs user ki <b>Telegram User ID</b> bhejo:", reply_markup=kb)

    elif data == "removereseller" and int(user_id) == ADMIN_ID:
        bot.answer_callback_query(call.id)
        set_temp(user_id, "waiting", "remove_reseller_id")
        kb = InlineKeyboardMarkup().add(InlineKeyboardButton("⬅️ Cancel", callback_data="backadmin"))
        bot.send_message(chat_id, "❌ <b>Reseller Hatana Hai?</b>\n\nUs user ki <b>Telegram User ID</b> bhejo jise reseller se hatana hai:", reply_markup=kb)

    elif data == "addcat" and int(user_id) == ADMIN_ID:
        bot.answer_callback_query(call.id)
        set_temp(user_id, "waiting", "newcat_name")
        kb = InlineKeyboardMarkup().add(InlineKeyboardButton("⬅️ Cancel", callback_data="backadmin"))
        bot.send_message(chat_id, "📁 <b>Category Ka Naam Bhejo:</b>", reply_markup=kb)

    elif data == "addprod" and int(user_id) == ADMIN_ID:
        bot.answer_callback_query(call.id)
        cats = load_json("categories.json")
        kb = InlineKeyboardMarkup(row_width=1)
        for cid, c in cats.items():
            kb.add(InlineKeyboardButton(c["name"], callback_data=f"selcat_{cid}"))
        kb.add(InlineKeyboardButton("⬅️ Cancel", callback_data="backadmin"))
        bot.send_message(chat_id, "📁 <b>Select Category:</b>", reply_markup=kb)

    elif data.startswith("selcat_") and int(user_id) == ADMIN_ID:
        bot.answer_callback_query(call.id)
        cid = data.replace("selcat_", "")
        set_temp(user_id, "addprod_cat", cid)
        kb = InlineKeyboardMarkup(row_width=1).add(
            InlineKeyboardButton("⚡ Reseller API Auto-Key", callback_data="type_api"),
            InlineKeyboardButton("📦 Manual Stock Keys", callback_data="type_manual"),
            InlineKeyboardButton("⬅️ Cancel", callback_data="backadmin")
        )
        bot.send_message(chat_id, "⚙️ <b>Product Type Chunein:</b>", reply_markup=kb)

    elif data in ["type_api", "type_manual"] and int(user_id) == ADMIN_ID:
        bot.answer_callback_query(call.id)
        is_api = 1 if data == "type_api" else 0
        set_temp(user_id, "addprod_is_api", is_api)
        set_temp(user_id, "waiting", "prod_name")
        bot.send_message(chat_id, "📦 <b>Product Ka Naam Bhejo:</b>")

    elif data in ["bound_yes", "bound_no"] and int(user_id) == ADMIN_ID:
        bot.answer_callback_query(call.id)
        need_id = 1 if data == "bound_yes" else 0
        set_temp(user_id, "temp_need_id", need_id)
        set_temp(user_id, "waiting", "prod_position")
        bot.send_message(chat_id, "🔢 <b>Product ka Number (Position) Bhejo</b> (जैसे 1, 2, 3):")

    elif data == "addplan" and int(user_id) == ADMIN_ID:
        bot.answer_callback_query(call.id)
        prods = load_json("products.json")
        kb = InlineKeyboardMarkup(row_width=1)
        for pid, p in prods.items():
            kb.add(InlineKeyboardButton(p["name"], callback_data=f"planprod_{pid}"))
        kb.add(InlineKeyboardButton("⬅️ Cancel", callback_data="backadmin"))
        bot.send_message(chat_id, "📦 <b>Select Product:</b>", reply_markup=kb)

    elif data.startswith("planprod_") and int(user_id) == ADMIN_ID:
        bot.answer_callback_query(call.id)
        pid = data.replace("planprod_", "")
        set_temp(user_id, "addplan_pid", pid)
        set_temp(user_id, "waiting", "plan_days")
        bot.send_message(chat_id, "📅 <b>Duration Bhejo:</b> (e.g. <code>1 Day</code>, <code>7 Days</code>)")

    elif data == "editplan" and int(user_id) == ADMIN_ID:
        bot.answer_callback_query(call.id)
        prods = load_json("products.json")
        kb = InlineKeyboardMarkup(row_width=1)
        for pid, p in prods.items():
            kb.add(InlineKeyboardButton(p["name"], callback_data=f"editprodplan_{pid}"))
        kb.add(InlineKeyboardButton("⬅️ Cancel", callback_data="backadmin"))
        bot.send_message(chat_id, "✏️ <b>Kis Product ka Plan Edit karna hai? Product Chunein:</b>", reply_markup=kb)

    elif data.startswith("editprodplan_") and int(user_id) == ADMIN_ID:
        bot.answer_callback_query(call.id)
        pid = data.replace("editprodplan_", "")
        prods = load_json("products.json")
        p = prods.get(pid, {})
        kb = InlineKeyboardMarkup(row_width=1)
        for idx, plan in enumerate(p.get("plans", [])):
            kb.add(InlineKeyboardButton(f"{plan['days']} - Normal: ₹{plan['price']} | Reseller: ₹{plan.get('reseller_price', plan['price'])}", callback_data=f"doeditplan_{pid}_{idx}"))
        kb.add(InlineKeyboardButton("⬅️ Cancel", callback_data="backadmin"))
        bot.send_message(chat_id, "📋 <b>Konsa Plan Edit karna hai?</b>", reply_markup=kb)

    elif data.startswith("doeditplan_") and int(user_id) == ADMIN_ID:
        bot.answer_callback_query(call.id)
        _, pid, idx = data.split("_")
        set_temp(user_id, "edit_pid", pid)
        set_temp(user_id, "edit_idx", int(idx))
        set_temp(user_id, "waiting", "edit_plan_days")
        bot.send_message(chat_id, "📅 <b>Naya Duration Bhejo (jaise 3 Days):</b>\n(Agar duration nahi badalna hai toh <b>No</b> bhejein)")

    elif data == "addplankeys" and int(user_id) == ADMIN_ID:
        bot.answer_callback_query(call.id)
        prods = load_json("products.json")
        kb = InlineKeyboardMarkup(row_width=1)
        for pid, p in prods.items():
            if not p.get("is_api"):
                kb.add(InlineKeyboardButton(p["name"], callback_data=f"selkeysprod_{pid}"))
        kb.add(InlineKeyboardButton("⬅️ Cancel", callback_data="backadmin"))
        bot.send_message(chat_id, "📦 <b>Select Manual Product:</b>", reply_markup=kb)

    elif data.startswith("selkeysprod_") and int(user_id) == ADMIN_ID:
        bot.answer_callback_query(call.id)
        pid = data.replace("selkeysprod_", "")
        prods = load_json("products.json")
        kb = InlineKeyboardMarkup(row_width=1)
        for idx, plan in enumerate(prods.get(pid, {}).get("plans", [])):
            kb.add(InlineKeyboardButton(f"{plan['days']} - ₹{plan['price']}", callback_data=f"addkplan_{pid}_{idx}"))
        kb.add(InlineKeyboardButton("⬅️ Cancel", callback_data="backadmin"))
        bot.send_message(chat_id, "📅 <b>Select Plan:</b>", reply_markup=kb)

    elif data.startswith("addkplan_") and int(user_id) == ADMIN_ID:
        bot.answer_callback_query(call.id)
        _, pid, idx = data.split("_")
        set_temp(user_id, "k_pid", pid)
        set_temp(user_id, "k_idx", int(idx))
        set_temp(user_id, "waiting", "add_keys")
        bot.send_message(chat_id, "🔑 <b>Keys Bhejo (Ek line me ek key):</b>")

    elif data == "delprod" and int(user_id) == ADMIN_ID:
        bot.answer_callback_query(call.id)
        prods = load_json("products.json")
        kb = InlineKeyboardMarkup(row_width=1)
        for pid, p in prods.items():
            kb.add(InlineKeyboardButton(p["name"], callback_data=f"confirmdel_{pid}"))
        kb.add(InlineKeyboardButton("⬅️ Cancel", callback_data="backadmin"))
        bot.send_message(chat_id, "🗑️ <b>Select Product to Delete:</b>", reply_markup=kb)

    elif data.startswith("confirmdel_") and int(user_id) == ADMIN_ID:
        bot.answer_callback_query(call.id)
        pid = data.replace("confirmdel_", "")
        prods = load_json("products.json")
        if pid in prods:
            del prods[pid]
            save_json("products.json", prods)
        bot.send_message(chat_id, "🗑️ <b>Product Deleted Successfully!</b>", reply_markup=get_admin_panel())

    elif data == "adduserbal" and int(user_id) == ADMIN_ID:
        bot.answer_callback_query(call.id)
        set_temp(user_id, "waiting", "user_id")
        bot.send_message(chat_id, "💰 <b>User ID Bhejo:</b>")

    elif data == "userlist" and int(user_id) == ADMIN_ID:
        bot.answer_callback_query(call.id)
        users = load_json("users.json")
        msg = f"👥 <b>Total Users:</b> {len(users)}\n\n"
        for idx, (uid_key, u) in enumerate(list(users.items())[:20], 1):
            un = f"(@{u.get('username')})" if u.get('username') else ""
            msg += f"{idx}. {u.get('name')} {un}\n   🆔 <code>{uid_key}</code>\n\n"
        kb = InlineKeyboardMarkup().add(InlineKeyboardButton("⬅️ Back", callback_data="backadmin"))
        bot.send_message(chat_id, msg, reply_markup=kb)

# ========== TEXT MESSAGES HANDLER ==========
@bot.message_handler(content_types=["text", "photo", "video", "document"])
def text_messages(message):
    uid = str(message.from_user.id)
    chat_id = message.chat.id

    if is_maintenance() and int(uid) != ADMIN_ID:
        return bot.send_message(
            chat_id,
            "🚧 <b>Bot Under Maintenance!</b>\n\n"
            "Kripya dhyan dein: Bot par abhi maintenance chal raha hai.\n"
            "Kuch samay baad dobara try karein. असुविधा के लिए खेद है!"
        )

    waiting = get_temp(uid, "waiting")

    if waiting == "broadcast_msg" and int(uid) == ADMIN_ID:
        set_temp(uid, "waiting", "")
        users = load_json("users.json")
        success = 0
        failed = 0
        
        status_msg = bot.send_message(message.chat.id, f"📢 <b>Broadcast shuru ho gaya hai...</b>\nTotal users: {len(users)}")
        
        for u_id in users.keys():
            try:
                bot.copy_message(chat_id=int(u_id), from_chat_id=message.chat.id, message_id=message.message_id)
                success += 1
                time.sleep(0.02)
            except Exception:
                failed += 1
                
        bot.edit_message_text(chat_id=message.chat.id, message_id=status_msg.message_id, text=f"✅ <b>Broadcast Complete!</b>\n\nSuccessful: {success}\nFailed: {failed}", reply_markup=get_admin_panel())
        return

    if not message.text:
        return

    text = message.text.strip()

    if waiting == "set_tutorial_link" and int(uid) == ADMIN_ID:
        settings = load_json("settings.json")
        settings["howto_link"] = text
        save_json("settings.json", settings)
        set_temp(uid, "waiting", "")
        bot.send_message(message.chat.id, f"✅ <b>Tutorial Link Updated Successfully!</b>\n\nNew Link: <code>{text}</code>", reply_markup=get_admin_panel())

    elif waiting == "set_reseller_api" and int(uid) == ADMIN_ID:
        settings = load_json("settings.json")
        settings["reseller_api_key"] = text
        save_json("settings.json", settings)
        set_temp(uid, "waiting", "")
        bot.send_message(message.chat.id, f"✅ <b>Reseller API Key Updated!</b>\n\nKey: <code>{text}</code>", reply_markup=get_admin_panel())

    elif waiting == "set_master_api" and int(uid) == ADMIN_ID:
        settings = load_json("settings.json")
        settings["reseller_master_key"] = text
        save_json("settings.json", settings)
        set_temp(uid, "waiting", "")
        bot.send_message(message.chat.id, f"✅ <b>Master API Key Updated!</b>\n\nKey: <code>{text}</code>", reply_markup=get_admin_panel())

    elif waiting == "set_fampay_api" and int(uid) == ADMIN_ID:
        settings = load_json("settings.json")
        settings["fampay_api"] = text
        save_json("settings.json", settings)
        set_temp(uid, "waiting", "")
        bot.send_message(message.chat.id, f"✅ <b>FamPay API Key Updated!</b>\n\nKey: <code>{text}</code>", reply_markup=get_admin_panel())

    elif waiting == "set_fampay_upi" and int(uid) == ADMIN_ID:
        settings = load_json("settings.json")
        settings["fampay_upi"] = text
        save_json("settings.json", settings)
        set_temp(uid, "waiting", "")
        bot.send_message(message.chat.id, f"✅ <b>UPI ID Updated!</b>\n\nUPI: <code>{text}</code>", reply_markup=get_admin_panel())

    elif waiting == "set_tg_link" and int(uid) == ADMIN_ID:
        settings = load_json("settings.json")
        settings["proof_link"] = text
        save_json("settings.json", settings)
        set_temp(uid, "waiting", "")
        bot.send_message(message.chat.id, f"✅ <b>Check Update Link Updated Successfully!</b>\n\nNew Link: <code>{text}</code>", reply_markup=get_admin_panel())

    elif waiting == "add_reseller_id" and int(uid) == ADMIN_ID:
        generate_unique_reseller_keys(text)
        set_temp(uid, "waiting", "")
        bot.send_message(message.chat.id, f"✅ User <code>{text}</code> ko successful <b>Reseller</b> bana diya gaya hai!", reply_markup=get_admin_panel())

    elif waiting == "remove_reseller_id" and int(uid) == ADMIN_ID:
        resellers = load_json("resellers.json")
        if text in resellers:
            del resellers[text]
            save_json("resellers.json", resellers)
            set_temp(uid, "waiting", "")
            bot.send_message(message.chat.id, f"✅ User <code>{text}</code> ko successful <b>Reseller</b> se hata diya gaya hai!", reply_markup=get_admin_panel())
        else:
            set_temp(uid, "waiting", "")
            bot.send_message(message.chat.id, f"❌ User <code>{text}</code> reseller list me nahi mila!", reply_markup=get_admin_panel())

    elif waiting == "custom_amount":
        try:
            amt = float(text)
            if amt < 1 or amt > 5000:
                return bot.send_message(message.chat.id, "❌ Amount ₹1 se ₹5000 ke beech me hona chahiye:")
            set_temp(uid, "waiting", "")
            create_fampay_order(message.chat.id, message.message_id, uid, amt)
        except ValueError:
            bot.send_message(message.chat.id, "❌ Sahi number (amount) bhejo:")

    elif waiting == "reseller_custom_amt":
        try:
            amt = float(text)
            if amt < 300:
                return bot.send_message(message.chat.id, "❌ Reseller banne ke liye kam se kam ₹300 add karna zaroori hai. Dobara amount bhejo:")
            set_temp(uid, "waiting", "")
            create_fampay_order(message.chat.id, message.message_id, uid, amt)
        except ValueError:
            bot.send_message(message.chat.id, "❌ Sahi number (amount) bhejo:")

    elif waiting == "edit_plan_days" and int(uid) == ADMIN_ID:
        set_temp(uid, "edit_new_days", text)
        set_temp(uid, "waiting", "edit_plan_normal")
        bot.send_message(message.chat.id, "💰 <b>Naya Normal Price Bhejo (₹):</b>\n(Agar price nahi badalna hai toh <b>No</b> bhejein)")

    elif waiting == "edit_plan_normal" and int(uid) == ADMIN_ID:
        set_temp(uid, "edit_new_normal", text)
        set_temp(uid, "waiting", "edit_plan_reseller")
        bot.send_message(message.chat.id, "👑 <b>Naya Reseller Price Bhejo (₹):</b>\n(Agar reseller price nahi badalna hai toh <b>No</b> bhejein)")

    elif waiting == "edit_plan_reseller" and int(uid) == ADMIN_ID:
        pid = get_temp(uid, "edit_pid")
        idx = int(get_temp(uid, "edit_idx"))
        new_days = get_temp(uid, "edit_new_days")
        new_normal = get_temp(uid, "edit_new_normal")
        new_reseller = text
        
        prods = load_json("products.json")
        if pid in prods and len(prods[pid]["plans"]) > idx:
            plan = prods[pid]["plans"][idx]
            if new_days.lower() != "no":
                plan["days"] = new_days
            if new_normal.lower() != "no":
                try:
                    plan["price"] = float(new_normal)
                except ValueError:
                    pass
            if new_reseller.lower() != "no":
                try:
                    plan["reseller_price"] = float(new_reseller)
                except ValueError:
                    pass
            save_json("products.json", prods)
            
        set_temp(uid, "waiting", "")
        bot.send_message(message.chat.id, "✅ Plan Successfully Updated!", reply_markup=get_admin_panel())

    elif waiting == "android_id":
        pid = get_temp(uid, "pending_pid")
        plan_idx = int(get_temp(uid, "pending_plan_idx"))
        set_temp(uid, "waiting", "")
        execute_purchase(message.chat.id, uid, pid, plan_idx, text)

    elif waiting == "newcat_name" and int(uid) == ADMIN_ID:
        set_temp(uid, "temp_cat_name", text)
        set_temp(uid, "waiting", "newcat_pos")
        bot.send_message(message.chat.id, "🔢 <b>Category ki Position (Number) Bhejo:</b> (जैसे 1, 2, 3)")

    elif waiting == "newcat_pos" and int(uid) == ADMIN_ID:
        try:
            pos = int(text)
        except ValueError:
            return bot.send_message(message.chat.id, "❌ Sahi number (position) daalein:")
        cats = load_json("categories.json")
        cid = f"c{int(time.time())}"
        cats[cid] = {"name": get_temp(uid, "temp_cat_name"), "position": pos}
        save_json("categories.json", cats)
        set_temp(uid, "waiting", "")
        bot.send_message(message.chat.id, f"✅ Category Added with position {pos}!", reply_markup=get_admin_panel())

    elif waiting == "prod_name" and int(uid) == ADMIN_ID:
        is_api = get_temp(uid, "addprod_is_api")
        if is_api:
            set_temp(uid, "temp_name", text)
            set_temp(uid, "waiting", "api_pid")
            bot.send_message(message.chat.id, "🔗 <b>Reseller API Product PID Bhejo:</b>\nExample: <code>PRODUCT ID </code>")
        else:
            set_temp(uid, "temp_name", text)
            set_temp(uid, "waiting", "prod_position")
            bot.send_message(message.chat.id, "🔢 <b>Product ka Number (Position) Bhejo</b> (जैसे 1, 2, 3):")

    elif waiting == "prod_position" and int(uid) == ADMIN_ID:
        try:
            pos = int(text)
        except ValueError:
            return bot.send_message(message.chat.id, "❌ Sahi number daalein:")
        
        is_api = get_temp(uid, "addprod_is_api")
        prods = load_json("products.json")
        pid = f"p{int(time.time())}"
        
        if is_api:
            prods[pid] = {
                "name": get_temp(uid, "temp_name"),
                "cat": get_temp(uid, "addprod_cat"),
                "is_api": 1,
                "api_pid": get_temp(uid, "temp_api_pid"),
                "need_android_id": get_temp(uid, "temp_need_id"),
                "position": pos,
                "plans": []
            }
        else:
            prods[pid] = {
                "name": get_temp(uid, "temp_name"),
                "cat": get_temp(uid, "addprod_cat"),
                "is_api": 0,
                "position": pos,
                "plans": []
            }
        save_json("products.json", prods)
        set_temp(uid, "waiting", "")
        bot.send_message(message.chat.id, "✅ Product Successfully Created with position!", reply_markup=get_admin_panel())

    elif waiting == "api_pid" and int(uid) == ADMIN_ID:
        set_temp(uid, "temp_api_pid", text)
        set_temp(uid, "waiting", "")
        kb = InlineKeyboardMarkup().add(
            InlineKeyboardButton("✅ Yes (Device Bound)", callback_data="bound_yes"),
            InlineKeyboardButton("❌ No", callback_data="bound_no")
        )
        bot.send_message(message.chat.id, "📱 <b>Kya is product ke liye Android ID zaroori hai?</b>", reply_markup=kb)

    elif waiting == "plan_days" and int(uid) == ADMIN_ID:
        set_temp(uid, "temp_days", text)
        set_temp(uid, "waiting", "plan_price")
        bot.send_message(message.chat.id, "💰 <b>Normal Price Bhejo (₹):</b>")

    elif waiting == "plan_price" and int(uid) == ADMIN_ID:
        try:
            price = float(text)
        except ValueError:
            return bot.send_message(message.chat.id, "❌ Invalid Price. Sahi number daalein:")
        set_temp(uid, "temp_price", price)
        set_temp(uid, "waiting", "plan_reseller_price")
        bot.send_message(message.chat.id, "👑 <b>Reseller Price Bhejo (₹):</b>")

    elif waiting == "plan_reseller_price" and int(uid) == ADMIN_ID:
        try:
            res_price = float(text)
        except ValueError:
            return bot.send_message(message.chat.id, "❌ Invalid Price. Sahi number daalein:")
        
        pid = get_temp(uid, "addplan_pid")
        days = get_temp(uid, "temp_days")
        normal_price = get_temp(uid, "temp_price")
        
        prods = load_json("products.json")
        if pid in prods:
            prods[pid]["plans"].append({
                "days": days, 
                "price": normal_price, 
                "reseller_price": res_price, 
                "keys": []
            })
            save_json("products.json", prods)
        
        set_temp(uid, "waiting", "")
        bot.send_message(message.chat.id, "✅ Plan with Reseller Price Added Successfully!", reply_markup=get_admin_panel())

    elif waiting == "add_keys" and int(uid) == ADMIN_ID:
        keys = [k.strip() for k in text.split("\n") if k.strip()]
        if not keys:
            return bot.send_message(message.chat.id, "❌ Dobara keys bhejo:")
        pid = get_temp(uid, "k_pid")
        idx = int(get_temp(uid, "k_idx"))
        prods = load_json("products.json")
        if pid in prods and len(prods[pid].get("plans", [])) > idx:
            if "keys" not in prods[pid]["plans"][idx]:
                prods[pid]["plans"][idx]["keys"] = []
            prods[pid]["plans"][idx]["keys"].extend(keys)
            save_json("products.json", prods)
        set_temp(uid, "waiting", "")
        bot.send_message(message.chat.id, f"✅ {len(keys)} Keys Added!", reply_markup=get_admin_panel())

    elif waiting == "user_id" and int(uid) == ADMIN_ID:
        set_temp(uid, "target_user", text)
        set_temp(uid, "waiting", "amount")
        bot.send_message(message.chat.id, "💰 <b>Kitna Balance Add Karna Hai?</b>")

    elif waiting == "amount" and int(uid) == ADMIN_ID:
        try:
            amt = float(text)
        except ValueError:
            return bot.send_message(message.chat.id, "❌ Invalid Amount. Sahi number daalein:")
        target = get_temp(uid, "target_user")
        balances = load_json("balances.json")
        balances[target] = balances.get(target, 0) + amt
        save_json("balances.json", balances)
        
        if amt >= 300:
            generate_unique_reseller_keys(target)

        send_channel_log(f"💰 <b>ADMIN BALANCE TOP-UP!</b>\n\n🆔 User: <code>{target}</code>\n💵 Amount: ₹{amt}")

        set_temp(uid, "waiting", "")
        bot.send_message(message.chat.id, f"✅ ₹{amt} added to {target}!", reply_markup=get_admin_panel())
        try:
            if amt >= 300:
                bot.send_message(int(target), f"🎉 <b>Admin credited ₹{amt} to your wallet! Aapko Reseller status bhi mil gaya hai!</b>")
            else:
                bot.send_message(int(target), f"🎉 <b>Admin credited ₹{amt} to your wallet!</b>")
        except Exception:
            pass

# ========== PURCHASE CORE ==========
def execute_purchase(chat_id, user_id, pid, plan_index, android_id):
    uid_str = str(user_id)
    products = load_json("products.json")
    balances = load_json("balances.json")
    orders = load_json("orders.json")
    st = load_json("settings.json")
    
    product = products.get(pid)
    plan = product["plans"][plan_index] if product and len(product.get("plans", [])) > plan_index else None
    if not plan:
        return bot.send_message(chat_id, "❌ Plan nahi mila.")
        
    user_is_reseller = is_reseller(user_id)
    price = plan.get("reseller_price" if user_is_reseller else "price", plan["price"])
    
    user_bal = balances.get(uid_str, 0)
    
    if user_bal < price:
        kb = InlineKeyboardMarkup().add(
            InlineKeyboardButton("💳 Add Balance", callback_data="addbal"),
            InlineKeyboardButton("⬅️ Back", callback_data="shop")
        )
        return bot.send_message(chat_id, f"❌ <b>Insufficient Balance!</b>\n\nPrice: ₹{price}\nYour Balance: ₹{user_bal}", reply_markup=kb)
        
    assigned_key = ""
    if product.get("is_api"):
        res = call_reseller_api({
            "api_key": st.get("reseller_api_key", ""),
            "action": "buy",
            "product_id": product.get("api_pid", ""),
            "duration": plan["days"],
            "android_id": android_id
        }, st.get("reseller_master_key", ""))
        
        if res.get("status") in ["success", 1, "1"] or "key" in res or "license" in res:
            assigned_key = res.get("key") or res.get("license") or "SUCCESS_KEY"
        else:
            err = res.get("message") or res.get("msg") or "API Error"
            return bot.send_message(chat_id, f"❌ <b>API Error:</b> {err}\nBalance deduct nahi hua.")
    else:
        if not plan.get("keys"):
            return bot.send_message(chat_id, "⚠️ <b>Out of Stock!</b>")
        assigned_key = plan["keys"].pop(0)
        save_json("products.json", products)
        
    balances[uid_str] = user_bal - price
    
    referrals = load_json("referrals.json")
    if uid_str in referrals:
        referrer_id = referrals[uid_str]
        bonus = float(st.get("referral_bonus", 2.0))
        balances[referrer_id] = balances.get(referrer_id, 0) + bonus
        save_json("balances.json", balances)
        try:
            bot.send_message(int(referrer_id), f"🎉 <b>Aapke referral ne purchase kiya hai!</b>\n\nAapko <b>₹{bonus}</b> referral bonus mila hai!")
        except Exception:
            pass
        del referrals[uid_str]
        save_json("referrals.json", referrals)

    order_id = f"ORD{int(time.time())}"
    orders[order_id] = {
        "user_id": uid_str,
        "product": product["name"],
        "days": plan["days"],
        "price": price,
        "key": assigned_key,
        "date": datetime.now().strftime("%d %b %Y %H:%M")
    }
    save_json("balances.json", balances)
    save_json("orders.json", orders)
    
    users_data = load_json("users.json")
    user_info = users_data.get(uid_str, {})
    u_name = user_info.get("name", "User")
    u_uname = f"@{user_info.get('username')}" if user_info.get("username") else "N/A"
    
    # LIVE CHANNEL BROADCAST - NEW KEY PURCHASED (KEY IS HIDDEN)
    send_channel_log(
        f"🛍️ <b>NEW LIVE KEY PURCHASED!</b>\n\n"
        f"👤 <b>Customer:</b> {u_name} ({u_uname})\n"
        f"📦 <b>Product:</b> {product['name']}\n"
        f"⏳ <b>Plan:</b> {plan['days']}\n"
        f"💵 <b>Price:</b> ₹{price}\n"
        f"🔐 <b>License Key:</b> <code>{mask_license_key(assigned_key)}</code>\n"
        f"⚡ <b>Delivery:</b> Instant Auto API ✅"
    )

    try:
        admin_purchase_msg = (
            f"🛒 <b>New Product Purchased!</b>\n\n"
            f"👤 Name: {u_name}\n"
            f"🔗 Username: {u_uname}\n"
            f"🆔 User ID: <code>{uid_str}</code>\n"
            f"📦 Product: {product['name']}\n"
            f"📅 Plan: {plan['days']}\n"
            f"💰 Paid: ₹{price}\n"
            f"🔑 Key: <code>{assigned_key}</code>"
        )
        bot.send_message(ADMIN_ID, admin_purchase_msg)
    except Exception as e:
        print(f"Admin purchase notification error: {e}")
    
    msg = (f"🎉 <b>Purchase Successful!</b>\n\n"
           f"📦 <b>Product:</b> {product['name']}\n"
           f"📅 <b>Duration:</b> {plan['days']}\n"
           f"💰 <b>Paid:</b> ₹{price}\n\n"
           f"🔑 <b>Your License Key:</b>\n<code>{assigned_key}</code>\n\n"
           f"Remaining Balance: ₹{balances[uid_str]}")
    kb = InlineKeyboardMarkup().add(
        InlineKeyboardButton("📦 View Orders", callback_data="orders"),
        InlineKeyboardButton("⬅️ Back to Shop", callback_data="shop")
    )
    bot.send_message(chat_id, msg, reply_markup=kb)

# ========== SAFE RUNNING (IN-BUILT SERVER + BOT) ==========
if __name__ == "__main__":
    print(f"🌐 Starting Built-in API Server on port {API_PORT}...")
    api_thread = threading.Thread(target=run_api_server, daemon=True)
    api_thread.start()

    print("🤖 Abhishek Store Bot is Running successfully on Pydroid 3!")
    while True:
        try:
            bot.polling(none_stop=True, interval=0.2, timeout=20)
        except Exception as e:
            print(f"Polling error: {e}")
            time.sleep(1)