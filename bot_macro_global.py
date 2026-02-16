import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import requests
import io
import warnings

warnings.filterwarnings('ignore')

# --- CONFIGURACIÓN DE TELEGRAM ---
TOKEN = '8173318113:AAFK_OM25CfTAmrmhR1pzwpvcQJWmWzbZg0'
CHAT_ID = '6550986355'

def enviar_telegram(mensaje, fig=None):
    try:
        url_texto = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.post(url_texto, data={'chat_id': CHAT_ID, 'text': mensaje, 'parse_mode': 'Markdown'})
        if fig is not None:
            buf = io.BytesIO()
            fig.savefig(buf, format='png', bbox_inches='tight', dpi=120, facecolor='#0d0d0d')
            buf.seek(0)
            url_foto = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
            requests.post(url_foto, data={'chat_id': CHAT_ID}, files={'photo': buf})
            buf.close()
    except: pass

# --- DICCIONARIOS DE ACTIVOS ---
# MATERIAS PRIMAS (Futuros y ETFs clave)
commodities = {
    'ORO (Refugio)': 'GC=F',
    'PETROLEO WTI': 'CL=F',
    'PLATA': 'SI=F',
    'COBRE (Doctor Cobre)': 'HG=F',
    'SOJA': 'ZS=F',
    'GAS NATURAL': 'NG=F',
    'URANIO (ETF)': 'URA'
}

# MERCADOS EMERGENTES (ETFs de países)
emergentes = {
    'BRASIL (EWZ)': 'EWZ',
    'CHINA (MCHI)': 'MCHI',
    'MÉXICO (EWW)': 'EWW',
    'INDIA (INDA)': 'INDA',
    'CHILE (ECH)': 'ECH',
    'EMERGENTES GLOBAL (EEM)': 'EEM'
}

def analizar_activo(ticker, nombre, categoria):
    try:
        # Descargamos 2 años para tener perspectiva estructural
        data = yf.download(ticker, period="2y", progress=False)
        if data.empty: return
        if isinstance(data.columns, pd.MultiIndex): data.columns = data.columns.get_level_values(0)

        # Calculos Técnicos
        data['SMA_50'] = data['Close'].rolling(50).mean()
        data['SMA_200'] = data['Close'].rolling(200).mean()
        
        actual = float(data['Close'].iloc[-1])
        sma200 = float(data['SMA_200'].iloc[-1])
        var_diaria = ((actual / float(data['Close'].iloc[-2])) - 1) * 100
        dist_200 = ((actual / sma200) - 1) * 100

        # Determinamos "Sentimiento"
        estado = "📈 BULLISH" if actual > sma200 else "📉 BEARISH"
        if dist_200 < -15: estado = "🆘 SOBREVENTA (Oportunidad)"
        if dist_200 > 15: estado = "🔥 SOBRECOMPRA (Riesgo)"

        # Formateo de Mensaje
        emoji_cat = "⛏️" if categoria == "COMMO" else "🚩"
        msj = (f"{emoji_cat} *{nombre}*\n"
               f"Precio: `${actual:.2f}` ({var_diaria:+.2f}%)\n"
               f"Estado: `{estado}`\n"
               f"Dist. a Media 200: `{dist_200:+.2f}%`\n")

        # Gráfico Estructural
        df_plot = data.iloc[-250:]
        fig, ax = plt.subplots(figsize=(10, 4))
        fig.patch.set_facecolor('#0d0d0d'); ax.set_facecolor('#0d0d0d')
        ax.plot(df_plot.index, df_plot['Close'], color='#00ff00' if actual > sma200 else '#ff3333', linewidth=2)
        ax.plot(df_plot.index, df_plot['SMA_200'], color='white', linestyle='--', alpha=0.6, label='Tendencia 200d')
        ax.set_title(f"{nombre} - Visión de Fondo", color='white', fontsize=12)
        ax.tick_params(colors='white'); ax.grid(alpha=0.1)
        
        enviar_telegram(msj, fig)
        plt.close(fig)
        
    except Exception as e:
        print(f"Error analizando {ticker}: {e}")

# --- EJECUCIÓN ---
enviar_telegram("🧭 *INICIANDO RADAR MACRO GLOBAL*\nAnalizando Materias Primas y Mercados Emergentes...")

# 1. Analizar Commodities
enviar_telegram("📦 *SECTOR MATERIAS PRIMAS*")
for nombre, ticker in commodities.items():
    analizar_activo(ticker, nombre, "COMMO")

# 2. Analizar Emergentes
enviar_telegram("🌍 *SECTOR MERCADOS EMERGENTES*")
for nombre, ticker in emergentes.items():
    analizar_activo(ticker, nombre, "EMER")

enviar_telegram("🏁 *FIN DEL REPORTE GLOBAL*")
