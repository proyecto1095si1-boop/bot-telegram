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

# Asegúrate de importar la función arriba
from bot_calendario_macro import obtener_reporte_balances

# Esta es la función que se ejecuta cuando escribes /macro
async def comando_macro(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Avisamos al usuario que estamos calculando
    await update.message.reply_text("⏳ Procesando datos de Yahoo Finance...")
    
    # Llamamos a tu código quant
    datos = obtener_reporte_balances()
    
    # 1. Enviamos el encabezado inicial
    await update.message.reply_text(datos["encabezado"], parse_mode='Markdown')
    
    # 2. Si no hay eventos, mandamos el mensaje vacío
    if not datos["hay_eventos"]:
        await update.message.reply_text(datos["mensaje_vacio"], parse_mode='Markdown')
    
    # 3. Si hay eventos, enviamos cada tarjeta (imagen + texto)
    else:
        for tarjeta in datos["tarjetas"]:
            await update.message.reply_photo(
                photo=tarjeta["imagen"], 
                caption=tarjeta["texto"], 
                parse_mode='Markdown'
            )
        
        # Mensaje de cierre
        await update.message.reply_text("🏁 *ESCANEO DE CALENDARIO FINALIZADO*", parse_mode='Markdown')
