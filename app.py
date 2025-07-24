import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TG_TOKEN = os.getenv("TG_TOKEN")
if not TG_TOKEN:
    raise ValueError("Please set the TG_TOKEN environment variable")

UPI_APPS = {
    "Google Pay": "https://play.google.com/store/apps/details?id=com.google.android.apps.nbu.paisa.user",
    "PhonePe": "https://play.google.com/store/apps/details?id=com.phonepe.app",
    "Paytm": "https://play.google.com/store/apps/details?id=net.one97.paytm",
    "BHIM UPI": "https://play.google.com/store/apps/details?id=in.org.npci.upiapp",
    "Amazon Pay": "https://play.google.com/store/apps/details?id=in.amazon.mShop.android.shopping",
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Welcome! Use /upi to get popular UPI scanner apps."
    )

async def upi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg_lines = ["Here are some popular UPI scanner apps:\n"]
    for app_name, link in UPI_APPS.items():
        msg_lines.append(f"• {app_name}: {link}")
    await update.message.reply_text("\n".join(msg_lines))

def create_app():
    app = ApplicationBuilder().token(TG_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("upi", upi))
    return app

app = create_app()
