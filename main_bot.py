import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Cargar las credenciales de tu .env
load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mensaje = (
        "🤖 *Terminal Quant Global en línea.*\n\n"
        "Sistemas operativos. Puedes usar comandos como:\n"
        "/macro - Ver calendario de balances\n"
        "/ping - Verificar estado del servidor"
    )
    await update.message.reply_text(mensaje, parse_mode='Markdown')

async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🟢 Servidor Quant activo y escuchando.")

if __name__ == '__main__':
    print("Iniciando motor de Telegram (Long Polling)...")
    app = ApplicationBuilder().token(TOKEN).build()

    # Registrar los comandos que el bot entenderá
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ping", ping))

    print("✅ Bot escuchando. Escribe /start en Telegram.")
    app.run_polling()

