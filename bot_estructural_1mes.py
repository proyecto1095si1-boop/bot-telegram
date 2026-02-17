import yfinance as yf
import pandas as pd
import numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import requests
import io
import warnings
import time
import random
import gc
from datetime import datetime, timedelta

warnings.filterwarnings('ignore')

# --- CONFIGURACIÓN ---
TOKEN = '8173318113:AAFK_OM25CfTAmrmhR1pzwpvcQJWmWzbZg0'
CHAT_ID = '6550986355'

def enviar_telegram(mensaje, fig=None):
    try:
        url_texto = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.post(url_texto, data={'chat_id': CHAT_ID, 'text': mensaje, 'parse_mode': 'Markdown'})
        if fig is not None:
            buf = io.BytesIO()
            fig.savefig(buf, format='png', bbox_inches='tight', dpi=130, facecolor='#0b0f19')
            buf.seek(0)
            url_foto = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
            requests.post(url_foto, data={'chat_id': CHAT_ID}, files={'photo': buf})
            buf.close()
            plt.close('all') 
            gc.collect()     
    except Exception as e:
        print(f"Error Telegram: {e}")

# --- UNIVERSO MAESTRO 45 ---
mercados = {
    '🇦🇷 ARG': ['YPF', 'GGAL', 'BMA', 'PAM', 'VIST', 'TGS', 'CEPU', 'ALUA.BA', 'TXAR.BA', 'EDN', 'LOMA', 'BBAR', 'SUPV', 'CRESY', 'TGNO4.BA'],
    '🇺🇸 USA': ['AAPL', 'MSFT', 'NVDA', 'AMZN', 'GOOGL', 'META', 'TSLA', 'JPM', 'V', 'XOM', 'WMT', 'LLY', 'AVGO', 'PYPL', 'MELI'],
    '🇬🇧 UK': ['SHEL.L', 'BP.L', 'HSBA.L', 'AZN.L', 'GSK.L', 'ULVR.L', 'RIO.L', 'BARC.L', 'VOD.L', 'REL.L', 'RR.L', 'LLOY.L', 'AAL.L', 'DGE.L', 'BA.L']
}

def motor_institucional(ticker):
    for intento in range(3):
        try:
            t = yf.Ticker(ticker)
            df = t.history(period="3y", interval="1d", timeout=10)
            if not df.empty and len(df) > 200: break
        except: time.sleep(2)
    
    if df.empty or len(df) < 200: return None
    
    df['SMA_50'] = df['Close'].rolling(50).mean()
    df['SMA_200'] = df['Close'].rolling(200).mean()
    
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    df['RSI'] = 100 - (100 / (1 + (gain/loss)))
    
    ema12 = df['Close'].ewm(span=12, adjust=False).mean()
    ema26 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = ema12 - ema26
    
    df['STD'] = df['Close'].rolling(20).std()
    df['BB_Upper'] = df['SMA_50'] + (df['STD'] * 2)
    df['BB_Lower'] = df['SMA_50'] - (df['STD'] * 2)
    df['Volatilidad'] = df['Close'].pct_change().rolling(20).std()
    df['ATR'] = df['High'] - df['Low']
    df['ATR'] = df['ATR'].rolling(14).mean()
    
    dias_proy = 60
    df['Target'] = df['Close'].shift(-dias_proy)
    train = df.dropna()
    features = ['Close', 'RSI', 'MACD', 'Volatilidad']
    
    model = HistGradientBoostingRegressor(max_iter=150, learning_rate=0.05, max_depth=5, random_state=42)
    model.fit(train[features].iloc[:-dias_proy], train['Target'].iloc[:-dias_proy])
    
    pred_ia_cruda = model.predict(df[features].iloc[-1:])[0]
    precio_act = df['Close'].iloc[-1]
    
    limite_movimiento = df['ATR'].iloc[-1] * 40
    if pred_ia_cruda > precio_act + limite_movimiento: pred_ia = precio_act + limite_movimiento
    elif pred_ia_cruda < precio_act - limite_movimiento: pred_ia = precio_act - limite_movimiento
    else: pred_ia = pred_ia_cruda
    
    try:
        info = t.info
        rec = str(info.get('recommendationKey', 'HOLD')).upper()
        pe = info.get('forwardPE', 'N/A')
    except:
        rec, pe = "N/A", "N/A"

    return df, {'pred': pred_ia, 'rec': rec, 'pe': pe, 'precio': precio_act, 'std': df['STD'].iloc[-1]}

hoy_str = datetime.now().strftime('%d/%m/%Y')
enviar_telegram(f"🏛️ *TERMINAL INSTITUCIONAL V27.1*\nIniciando Escaneo Avanzado | {hoy_str}\n_Corrección de sintaxis aplicada..._")

for region, activos in mercados.items():
    bandera = region.split()[0]
    for ticker in activos:
        try:
            time.sleep(random.uniform(1.5, 3.5)) 
            res = motor_institucional(ticker)
            if not res: continue
            df, data = res
            
            p = data['precio']
            diff = ((data['pred'] / p) - 1) * 100
            emoji = "🟢" if diff > 0 else "🔴"
            
            # --- SOLUCIÓN DEL ERROR AQUÍ ---
            pe_formateado = data['pe'] if isinstance(data['pe'], str) else f"{data['pe']:.1f}"
            
            msj = (f"{bandera} *{ticker}* | `{data['rec']}`\n"
                   f"💰 Spot: *${p:.2f}* | P/E: `{pe_formateado}`\n"
                   f"🧠 IA Target Q2: *${data['pred']:.2f}* ({diff:+.2f}% {emoji})\n"
                   f"📊 RSI: `{df['RSI'].iloc[-1]:.1f}` | MACD: `{df['MACD'].iloc[-1]:.2f}`")

            # GRÁFICO INSTITUCIONAL
            plt.style.use('dark_background')
            fig = plt.figure(figsize=(11, 7))
            fig.patch.set_facecolor('#0b0f19')
            gs = gridspec.GridSpec(2, 1, height_ratios=[3, 1], hspace=0.1)
            
            ax1 = fig.add_subplot(gs[0])
            ax1.set_facecolor('#0b0f19')
            df_plot = df.iloc[-150:]
            
            ax1.plot(df_plot.index, df_plot['Close'], color='#22d3ee', linewidth=2, label='Cotización')
            ax1.fill_between(df_plot.index, df_plot['BB_Lower'], df_plot['BB_Upper'], color='#38bdf8', alpha=0.05, label='Canal Volatilidad')
            ax1.plot(df_plot.index, df_plot['SMA_200'], color='#f472b6', linestyle='--', alpha=0.6, label='SMA 200 (Tendencia)')
            
            fecha_futura = df.index[-1] + timedelta(days=60)
            ax1.plot([df.index[-1], fecha_futura], [p, data['pred']], color='#4ade80', linestyle='--', linewidth=2.5, marker='o', markersize=6, label='Ruta IA')
            
            margen_error = data['std'] * 1.5
            ax1.fill_between([df.index[-1], fecha_futura], [p, data['pred'] + margen_error], [p, data['pred'] - margen_error], color='#4ade80', alpha=0.15)
            
            ax1.set_title(f"Quantum Analysis: {ticker} (Proyección a 60 días)", color='white', loc='left', fontsize=12, fontweight='bold')
            ax1.legend(loc='upper left', fontsize='small', framealpha=0.2)
            ax1.grid(color='#1e293b', alpha=0.4, linestyle=':')
            ax1.tick_params(labelbottom=False) 
            
            ax2 = fig.add_subplot(gs[1])
            ax2.set_facecolor('#0b0f19')
            ax2.plot(df_plot.index, df_plot['RSI'], color='#c084fc', linewidth=1.5)
            ax2.axhline(70, color='#ef4444', linestyle='--', alpha=0.5) 
            ax2.axhline(30, color='#22c55e', linestyle='--', alpha=0.5) 
            ax2.fill_between(df_plot.index, df_plot['RSI'], 70, where=(df_plot['RSI'] >= 70), color='#ef4444', alpha=0.3)
            ax2.fill_between(df_plot.index, df_plot['RSI'], 30, where=(df_plot['RSI'] <= 30), color='#22c55e', alpha=0.3)
            
            ax2.set_ylabel('RSI (14)', color='gray', fontsize=9)
            ax2.grid(color='#1e293b', alpha=0.4, linestyle=':')
            ax2.tick_params(axis='x', rotation=45, colors='gray')
            ax2.tick_params(axis='y', colors='gray')
            
            ax1.spines['top'].set_visible(False); ax1.spines['right'].set_visible(False)
            ax2.spines['top'].set_visible(False); ax2.spines['right'].set_visible(False)
            
            enviar_telegram(msj, fig)
            
        except Exception as e:
            print(f"Fallo en {ticker}: {e}")
            continue

enviar_telegram("✅ *AUDITORÍA INSTITUCIONAL 2026 FINALIZADA*")
