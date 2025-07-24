import os
from flask import Flask, request
import telebot
from pymongo import MongoClient
from datetime import datetime
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

app = Flask(__name__)
PORT = int(os.environ.get('PORT', 8080))
TG_TOKEN = os.environ.get('TG_TOKEN')
MONGO_URI = os.environ.get('MONGO_URI')

bot = telebot.TeleBot(TG_TOKEN)
client = MongoClient(MONGO_URI)
db = client.telegram_bot
users = db.users
orders = db.orders

prices = {
    'Hotstar Super 1 year': 699,
    'Amazon Prime 1 year': 999,
    'Zee5 1 year': 399,
    'SonyLIV 1 year': 499,
    'JioSaavn 3 months': 99,
    'Gaana 1 year': 199,
}

@bot.message_handler(commands=['start'])
def send_welcome(message):
    reply = '''🌟 Welcome to Premium Subscriptions! 🌟
Send me the name of the subscription you want (e.g., "Hotstar Super 1 year").
    '''
    bot.reply_to(message, reply)

@bot.message_handler(func=lambda message: True)
def process_order(message):
    service = message.text.strip()
    user_id = str(message.from_user.id)
    username = message.from_user.username or message.from_user.first_name
    price = prices.get(service, 0)
    
    users.update_one(
        {'telegram_id': user_id},
        {'$set': {'username': username, 'last_seen': datetime.utcnow()}},
        upsert=True
    )
    
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("Pay via UPI", callback_data=f'payment_upi_{service}'),
        InlineKeyboardButton("Pay via Paytm", callback_data=f'payment_paytm_{service}')
    )
    
    bot.reply_to(message, "🔹 Select your payment method:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('payment_'))
def handle_payment(call):
    _, method, service = call.data.split('_', 2)
    user_id = str(call.from_user.id)
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
1. Open your UPI app (GPay, PhonePe, Paytm, etc.)
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
        bot.send_message(call.message.chat.id, "Invalid payment method. Please try again.")
        return
    
    bot.send_photo(call.message.chat.id, photo_url, caption=instructions)
    bot.send_message(call.message.chat.id, f"📝 Order ID: {order_id}\nService: {service}\nAmount: ₹{price}\nPayment method: {method}\n\n👉 Please send your payment screenshot for verification.")

@app.route('/', methods=['GET'])
def health_check():
    return "OK", 200

@app.route('/webhook', methods=['POST'])
def webhook():
    json_data = request.get_json()
    update = telebot.types.Update.de_json(json_data)
    bot.process_new_updates([update])
    return 'ok', 200

if __name__ == '__main__':
    bot.remove_webhook()
    bot.set_webhook(url=os.environ.get('WEBHOOK_URL', 'https://your-app-name.onrender.com/webhook'))
    app.run(host='0.0.0.0', port=PORT)
