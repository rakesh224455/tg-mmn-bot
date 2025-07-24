import os
import json
from datetime import datetime
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from pymongo import MongoClient
import asyncio

# Environment setup
PORT = int(os.environ.get('PORT', 8080))
TG_TOKEN = os.environ.get('TG_TOKEN')
MONGO_URI = os.environ.get('MONGO_URI')
WEBHOOK_PATH = "/webhook"
RENDER_HOSTNAME = os.getenv("RENDER_EXTERNAL_HOSTNAME")
WEBHOOK_URL = f"https://{RENDER_HOSTNAME}{WEBHOOK_PATH}"

# MongoDB setup
client = MongoClient(MONGO_URI)
db = client.telegram_bot
users = db.users
orders = db.orders

# Flask setup
flask_app = Flask(__name__)

# Telegram Bot App
application = Application.builder().token(TG_TOKEN).build()

# Pricing
prices = {
    'Hotstar Super 1 year': 699,
    'Amazon Prime 1 year': 999,
}

# Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🌟 Welcome! Send the service name you want (e.g., 'Hotstar Super 1 year')")

async def process_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    service = update.message.text.strip()
    user_id = str(update.effective_user.id)
    username = update.effective_user.username or update.effective_user.first_name
    price = prices.get(service, 0)

    users.update_one(
        {'telegram_id': user_id},
        {'$set': {'username': username, 'last_seen': datetime.utcnow()}},
        upsert=True
    )

    keyboard = [
        [InlineKeyboardButton("Pay via UPI", callback_data=f'payment_upi_{service}')],
        [InlineKeyboardButton("Pay via Paytm", callback_data=f'payment_paytm_{service}')],
    ]
    await update.message.reply_text("🔹 Select your payment method:", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    _, method, service = query.data.split('_', 2)
    user_id = str(query.from_user.id)
    price = prices.get(service, 0)

    orders.insert_one({
        'user_id': user_id,
        'service': service,
        'amount': price,
        'payment_method': method,
        'status': 'pending',
        'created_at': datetime.utcnow()
    })

    if method == 'upi':
        await query.message.reply_photo(
            photo="YOUR_UPI_IMAGE_LINK",
            caption="🟢 UPI Payment Instructions\n1. Open your UPI app\n2. Scan the QR code above\n3. Send payment screenshot here."
        )
    elif method == 'paytm':
        await query.message.reply_photo(
            photo="YOUR_PAYTM_IMAGE_LINK",
            caption="🔵 Paytm Payment Instructions\n1. Open Paytm app\n2. Scan the QR code above\n3. Send payment screenshot here."
        )

# Add handlers
application.add_handler(CommandHandler('start', start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_order))
application.add_handler(CallbackQueryHandler(handle_payment))

# Flask routes
@flask_app.route('/')
def health_check():
    return "OK", 200

@flask_app.route(WEBHOOK_PATH, methods=['POST'])
async def telegram_webhook():
    if request.headers.get('content-type') == 'application/json':
        json_str = request.get_data(as_text=True)
        update = Update.de_json(json.loads(json_str), application.bot)
        await application.process_update(update)
    return '', 200

# Setup webhook on start
async def init_bot():
    await application.initialize()
    await application.bot.set_webhook(WEBHOOK_URL)
    print(f"✅ Webhook set to {WEBHOOK_URL}")

if __name__ == '__main__':
    asyncio.run(init_bot())
    flask_app.run(host="0.0.0.0", port=PORT)
