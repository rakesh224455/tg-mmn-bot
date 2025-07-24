import os
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from pymongo import MongoClient
from datetime import datetime

app = Flask(__name__)
PORT = int(os.environ.get('PORT', 8080))
TG_TOKEN = os.environ.get('TG_TOKEN')
MONGO_URI = os.environ.get('MONGO_URI')

mongo_client = MongoClient(MONGO_URI)
db = mongo_client.telegram_bot
users = db.users
orders = db.orders

prices = {
    'Hotstar Super 1 year': 699,
    'Amazon Prime 1 year': 999,
    # ... add more
}

# Initialize the Telegram bot application
application = Application.builder().token(TG_TOKEN).build()

async def start(update: Update, context: CallbackContext):
    await update.message.reply_text("🌟 Welcome! Send the name of the service you want (e.g., 'Hotstar Super 1 year').")

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
        [InlineKeyboardButton("Pay via Paytm", callback_data=f'payment_paytm_{service}')]
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
    result = orders.insert_one(order)
    order_id = result.inserted_id
    
    if method == 'upi':
        photo_url = "YOUR_UPI_IMAGE_LINK"
        instructions = '''🟢 **UPI Payment Instructions**
1. Open your UPI app.
2. Scan the QR code above to pay.
3. After payment, send a screenshot of the receipt here.
4. Your login details will be delivered within 15–30 minutes after verification.
'''
    elif method == 'paytm':
        photo_url = "YOUR_PAYTM_IMAGE_LINK"
        instructions = '''🔵 **Paytm Payment Instructions**
1. Open Paytm app.
2. Scan the QR code above to pay.
3. After payment, send a screenshot here.
4. We'll deliver your login details soon.
'''
    else:
        await query.message.reply_text("Invalid payment method. Please try again.")
        return
    
    await query.message.reply_photo(photo_url, caption=instructions)
    await query.message.reply_text(f"📝 Order ID: {order_id}\nService: {service}\nAmount: ₹{price}\nPayment method: {method}\n\n👉 Please send your payment screenshot for verification.")

# Set up handlers
application.add_handler(CommandHandler('start', start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_order))
application.add_handler(CallbackQueryHandler(handle_payment))

@app.route('/')
def health_check():
    return "OK", 200

@app.route('/webhook', methods=['POST'])
async def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_str = request.get_data().decode('UTF-8')
        update = Update.de_json(json_str, application.bot)
        await application.update_queue.put(update)
    return 'ok', 200

if __name__ == '__main__':
    application.run_polling()  # For local testing; use webhook for Render
