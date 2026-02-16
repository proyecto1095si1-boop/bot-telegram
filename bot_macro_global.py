import yfinance as yf
import pandas as pd
import numpy as np
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.preprocessing import MinMaxScaler
import matplotlib.pyplot as plt
import requests
import io
import warnings
from datetime import datetime, timedelta

warnings.filterwarnings('ignore')

# --- CONFIGURACIÓN DE ACCESO ---
TOKEN = '8173318113:AAFK_OM25CfTAmrmhR1pzwpvcQJWmWzbZg0'
CHAT_ID = '6550986355'

def enviar_telegram(mensaje, fig=None):
    try:
        url_texto = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.post(url_texto, data={'chat_id': CHAT_ID, 'text': mensaje, 'parse_mode': 'Markdown'})
        if fig is not None:
            buf = io.BytesIO()
            fig.savefig(buf, format='png', bbox_inches='tight', dpi=180, facecolor='#020617')
            buf.seek(0)
            url_foto = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
            requests.post(url_foto, data={'chat_id': CHAT_ID}, files={'photo': buf})
            buf.close()
    except: pass

# --- UNIVERSO MAESTRO 2026 ---
sectores = {
    '💎 MINERÍA & COMMODITIES': {
        '🥇 ORO': 'GC=F', '🥈 PLATA': 'SI=F', '🏗️ COBRE': 'HG=F', 
        '🔋 LITIO': 'LIT', '⚛️ URANIO': 'URA', '🛢️ PETRÓLEO': 'CL=F', '🌽 SOJA': 'ZS=F'
    },
    '🇦🇷 ARGENTINA (MERVAL)': {
        'YPF': 'YPF', 'GALICIA': 'GGAL', 'MACRO': 'BMA', 'PAMPA': 'PAM', 
        'VISTA': 'VIST', 'TGS': 'TGS', 'ALUAR': 'ALUA.BA', 'TERNIUM': 'TXAR.BA'
    },
    '🇺🇸 USA & LONDRES': {
        'APPLE': 'AAPL', 'NVIDIA': 'NVDA', 'TESLA': 'TSLA', 'MELI': 'MELI',
        'SHELL': 'SHEL.L', 'BP': 'BP.L', 'HSBC': 'HSBA.L', 'RIO TINTO': 'RIO.L'
    }
}

def procesar_terminal_full(ticker, nombre):
    t = yf.Ticker(ticker)
    df = t.history(period="3y", interval="1d")
    if df.empty or len(df) < 200: return None

    # --- INGENIERÍA DE INDICADORES QUANT ---
    df['SMA_20'] = df['Close'].rolling(20).mean()
    df['SMA_200'] = df['Close'].rolling(200).mean()
    df['STD'] = df['Close'].rolling(20).std()
    df['Upper'] = df['SMA_20'] + (df['STD'] * 2)
    df['Lower'] = df['SMA_20'] - (df['STD'] * 2)
    
    # RSI & Momentum
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    df['RSI'] = 100 - (100 / (1 + (gain/loss)))
    df['Momentum'] = df['Close'] / df['Close'].shift(10) - 1

    # --- ENTRENAMIENTO IA V23 (1000 ESTIMADORES) ---
    df['Target'] = df['Close'].shift(-45)
    train = df.dropna()
    features = ['Close', 'SMA_20', 'SMA_200', 'RSI', 'Momentum']
    
    model = GradientBoostingRegressor(n_estimators=1000, learning_rate=0.03, max_depth=6, random_state=42)
    model.fit(train[features].iloc[:-45], train['Target'].iloc[:-45])
    
    pred_45d = model.predict(df[features].iloc[-1:])[0]
    precio_act = df['Close'].iloc[-1]
    
    # --- ANÁLISIS DE SENTIMIENTO & FUNDAMENTOS ---
    info = t.info
    per = info.get('trailingPE', 'N/A')
    mkt_cap = info.get('marketCap', 0) / 1e9
    noticias = t.news[:2]
    titulares = " | ".join([n['title'] for n in noticias]) if noticias else "Sin noticias relevantes."

    return df, {'pred': pred_45d, 'per': per, 'cap': mkt_cap, 'news': titulares, 'precio': precio_act}

enviar_telegram("🏛️ *TERMINAL QUANT OMNISCIENTE V23.0*\nSincronizado: `Lunes 16 de Febrero, 2026`\n_Ejecutando Modelos de Alta Intensidad..._")

for cat_nombre, activos in sectores.items():
    enviar_telegram(f"📁 *SECTOR:* {cat_nombre}")
    
    for nombre, ticker in activos.items():
        try:
            res = procesar_terminal_full(ticker, nombre)
            if not res: continue
            df, data = res
            
            p = data['precio']
            diff_proy = ((data['pred'] / p) - 1) * 100
            fecha_proy = df.index[-1] + timedelta(days=45)
            
            # Formateo de Mensaje Institucional
            msj = (f"💎 *{nombre}* (`{ticker}`)\n"
                   f"💰 Precio: *${p:.2f}* | RSI: `{df['RSI'].iloc[-1]:.1f}`\n"
                   f"🏛️ Cap. Mercado: `${data['cap']:.1f}B` | P/E: `{data['per']}`\n\n"
                   f"🧠 *PROYECCIÓN IA (ABRIL 2026):*\n"
                   f"🎯 Tentativa: *${data['pred']:.2f}* ({diff_proy:+.2f}%)\n"
                   f"📉 Riesgo (STD): `±{df['STD'].iloc[-1]:.2f}`\n\n"
                   f"📰 *SENTIMIENTO:* \n_{data['news']}_")

            # --- GRÁFICO NIVEL PROFESIONAL ---
            plt.style.use('dark_background')
            fig, ax = plt.subplots(figsize=(12, 6))
            fig.patch.set_facecolor('#020617'); ax.set_facecolor('#020617')
            
            # Eje Histórico (Velas/Línea)
            df_p = df.iloc[-180:]
            ax.plot(df_p.index, df_p['Close'], color='#38bdf8', linewidth=2, label='Precio 2026')
            ax.fill_between(df_p.index, df_p['Lower'], df_p['Upper'], color='#38bdf8', alpha=0.05, label='Bandas Volatilidad')
            ax.plot(df_p.index, df_p['SMA_200'], color='#f43f5e', alpha=0.4, label='Estructura de Fondo')
            
            # Eje Proyección IA
            fechas_fut = [df_p.index[-1], fecha_proy]
            precios_fut = [p, data['pred']]
            ax.plot(fechas_fut, precios_fut, color='#10b981', linestyle='--', marker='o', markersize=8, linewidth=2.5, label='Proyección IA')
            
            # Etiquetas y Estética
            ax.set_title(f"Quantum Analysis: {nombre}", color='white', loc='left', fontsize=14, fontweight='bold')
            ax.grid(color='#1e293b', alpha=0.3)
            ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
            ax.legend(frameon=False, loc='upper left', fontsize='small')
            
            enviar_telegram(msj, fig)
            plt.close(fig)
            
        except Exception as e: print(f"Error en {ticker}: {e}")

enviar_telegram("✅ *TERMINAL 2026: ESCANEO TOTAL COMPLETADO*")
