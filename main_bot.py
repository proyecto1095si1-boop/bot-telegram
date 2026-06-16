import os
import asyncio
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Importamos tu lógica de negocios (debe estar en el mismo directorio)
from bot_calendario_macro import obtener_reporte_balances

# 1. Cargar las credenciales del archivo .env
load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")

# 2. Definición de comandos
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mensaje = (
        "🤖 *Terminal Quant Global en línea.*\n\n"
        "Comandos disponibles:\n"
        "/macro - Ver calendario de balances (próximos 15 días)\n"
        "/ping - Verificar estado del servidor"
    )
    await update.message.reply_text(mensaje, parse_mode='Markdown')

async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🟢 Servidor Quant activo y escuchando.")

async def comando_macro(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Avisamos al usuario que estamos trabajando
    await update.message.reply_text("⏳ Procesando datos de mercado...")
    
    # Llamamos a tu lógica quant refactorizada
    datos = obtener_reporte_balances()
    
    # Enviamos el encabezado
    await update.message.reply_text(datos["encabezado"], parse_mode='Markdown')
    
    # Lógica de respuesta según si hay o no eventos
    if not datos["hay_eventos"]:
        await update.message.reply_text(datos["mensaje_vacio"], parse_mode='Markdown')
    else:
        # Enviamos cada tarjeta visual
        for tarjeta in datos["tarjetas"]:
            await update.message.reply_photo(
                photo=tarjeta["imagen"], 
                caption=tarjeta["texto"], 
                parse_mode='Markdown'
            )
        await update.message.reply_text("🏁 *ESCANEO DE CALENDARIO FINALIZADO*", parse_mode='Markdown')

# 3. Bloque principal de ejecución
if __name__ == '__main__':
    if not TOKEN:
        print("❌ Error: No se encontró el TOKEN en el archivo .env")
        exit()

    print("🚀 Iniciando motor de Telegram (Long Polling)...")
    app = ApplicationBuilder().token(TOKEN).build()

    # Registro de handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ping", ping))
    app.add_handler(CommandHandler("macro", comando_macro)) # <-- Registro vital

    print("✅ Bot activo. Ve a Telegram y escribe /start o /macro")
    app.run_polling()
