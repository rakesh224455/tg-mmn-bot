import json
import os
from datetime import datetime
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    CallbackContext,
)
from pymongo import MongoClient

app = Flask(__name__)
PORT = int(os.environ.get('PORT', 8080))
TG_TOKEN = os.environ.get('TG_TOKEN')
MONGO_URI = os.environ.get('MONGO_URI')

client = MongoClient(MONGO_URI)
db = client.telegram_bot
users = db.users
orders = db.orders

prices = {
    'Hotstar Super 1 year': 699,
    'Amazon Prime 1 year': 999,
}

application = Application.builder().token(TG_TOKEN).build()

async def start(update: Update, context: CallbackContext):
    await update.message.reply_text("🌟 Welcome! Send the service name you want (e.g., 'Hotstar Super 1 year')")

async def process_order(update: Update, context: CallbackContext):
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
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🔹 Select your payment method:", reply_markup=reply_markup)

async def handle_payment(update: Update, context: CallbackContext):
    query = update.callback_query
    _, method, service = query.data.split('_', 2)
    user_id = str(query.from_user.id)
    price = prices.get(service, 0)
    
    order = {
        'user_id': user_id,
        'service': service,
        'amount': price,
        'payment_method': method,
        'status': 'pending',
        'created_at': datetime.utcnow()
    }
    orders.insert_one(order)
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

application.add_handler(CommandHandler('start', start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_order))
application.add_handler(CallbackQueryHandler(handle_payment))

@app.route('/')
def health_check():
    return "OK", 200

@app.route('/webhook', methods=['POST'])
async def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_str = request.get_data(as_text=True)
        json_dict = json.loads(json_str)
        update = Update.de_json(json_dict, application.bot)
        await application.update_queue.put(update)
    return '', 200
