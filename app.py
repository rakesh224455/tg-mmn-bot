# app.py
import os
from fastapi import FastAPI, Request, Response
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, ContextTypes, Dispatcher, filters

TG_TOKEN = os.getenv("TG_TOKEN")
if not TG_TOKEN:
    raise ValueError("Set TG_TOKEN environment variable")

bot = Bot(token=TG_TOKEN)
app = FastAPI()

UPI_APPS = {
    "Google Pay": "https://play.google.com/store/apps/details?id=com.google.android.apps.nbu.paisa.user",
    "PhonePe": "https://play.google.com/store/apps/details?id=com.phonepe.app",
    "Paytm": "https://play.google.com/store/apps/details?id=net.one97.paytm",
    "BHIM UPI": "https://play.google.com/store/apps/details?id=in.org.npci.upiapp",
    "Amazon Pay": "https://play.google.com/store/apps/details?id=in.amazon.mShop.android.shopping",
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome! Use /upi to get popular UPI scanner apps.")

async def upi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = "\n".join([f"• {name}: {link}" for name, link in UPI_APPS.items()])
    await update.message.reply_text("Here are some popular UPI scanner apps:\n" + msg)

# Create the Application and Dispatcher manually
application = Application.builder().token(TG_TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("upi", upi))

# FastAPI route to receive webhook updates
@app.post("/webhook")
async def telegram_webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, bot)
    await application.update_queue.put(update)
    # Let the dispatcher process the update asynchronously
    await application.process_update(update)
    return Response(status_code=200)

# Optional: root route
@app.get("/")
async def root():
    return {"message": "Telegram UPI Scanner Bot is running."}
