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
            plt.close('all') # ANTI-CRASH: Vacía la memoria gráfica
            gc.collect()     # ANTI-CRASH: Vacía la memoria RAM
    except Exception as e:
        print(f"Error Telegram: {e}")

# --- UNIVERSO MACRO 2026 ---
sectores = {
    '💎 MATERIAS PRIMAS': {
        '🥇 ORO': 'GC=F', '🥈 PLATA': 'SI=F', '🏗️ COBRE': 'HG=F', 
        '🛢️ PETRÓLEO WTI': 'CL=F', '🔋 LITIO (ETF)': 'LIT', '⚛️ URANIO': 'URA', '🪙 BITCOIN': 'BTC-USD'
    },
    '🌍 MERCADOS EMERGENTES': {
        '🇧🇷 BRASIL (EWZ)': 'EWZ', '🇨🇳 CHINA (FXI)': 'FXI', '🇮🇳 INDIA (INDA)': 'INDA',
        '🇲🇽 MÉXICO (EWW)': 'EWW', '🇦🇷 ARGENTINA (ARGT)': 'ARGT', '🌐 EMERGENTES (EEM)': 'EEM'
    }
}

def motor_macro_quant(ticker):
    # Descarga Blindada (3 intentos)
    for intento in range(3):
        try:
            t = yf.Ticker(ticker)
            df = t.history(period="3y", interval="1d", timeout=10)
            if not df.empty and len(df) > 200: break
        except: time.sleep(2)
    
    if df.empty or len(df) < 200: return None
    
    # --- INDICADORES TÉCNICOS MACRO ---
    df['SMA_50'] = df['Close'].rolling(50).mean()
    df['SMA_200'] = df['Close'].rolling(200).mean()
    df['STD'] = df['Close'].rolling(20).std()
    df['BB_Upper'] = df['SMA_50'] + (df['STD'] * 2)
    df['BB_Lower'] = df['SMA_50'] - (df['STD'] * 2)
    
    # RSI
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    df['RSI'] = 100 - (100 / (1 + (gain/loss)))
    
    df['Volatilidad'] = df['Close'].pct_change().rolling(20).std()
    df['ATR'] = (df['High'] - df['Low']).rolling(14).mean()
    
    # --- IA: HIST GRADIENT BOOSTING (45 Días) ---
    dias_proy = 45
    df['Target'] = df['Close'].shift(-dias_proy)
    train = df.dropna()
    features = ['Close', 'RSI', 'Volatilidad']
    
    model = HistGradientBoostingRegressor(max_iter=150, learning_rate=0.05, max_depth=5, random_state=42)
    model.fit(train[features].iloc[:-dias_proy], train['Target'].iloc[:-dias_proy])
    
    pred_ia_cruda = model.predict(df[features].iloc[-1:])[0]
    precio_act = df['Close'].iloc[-1]
    
    # Filtro de Realismo MACRO (Materias primas vuelan, pero le ponemos un límite seguro)
    limite_mov = df['ATR'].iloc[-1] * 35
    if pred_ia_cruda > precio_act + limite_mov: pred_ia = precio_act + limite_mov
    elif pred_ia_cruda < precio_act - limite_mov: pred_ia = precio_act - limite_mov
    else: pred_ia = pred_ia_cruda

    return df, {'pred': pred_ia, 'precio': precio_act, 'std': df['STD'].iloc[-1]}

hoy_str = datetime.now().strftime('%d/%m/%Y')
enviar_telegram(f"🌍 *TERMINAL MACRO GLOBAL V28.0*\nSincronizando Commodities y Emergentes | {hoy_str}\n_Filtros Anti-Crash Activados..._")

for sector, activos in sectores.items():
    enviar_telegram(f"📁 *ANALIZANDO: {sector}*")
    
    for nombre, ticker in activos.items():
        try:
            time.sleep(random.uniform(1.5, 3.0)) # Modo Sigilo
            res = motor_macro_quant(ticker)
            if not res: continue
            df, data = res
            
            p = data['precio']
            diff = ((data['pred'] / p) - 1) * 100
            tendencia = "🔥 BULLISH" if p > df['SMA_200'].iloc[-1] else "❄️ BEARISH"
            emoji_proy = "🟢" if diff > 0 else "🔴"
            
            msj = (f"*{nombre}* (`{ticker}`)\n"
                   f"💰 Spot: *${p:.2f}* | RSI: `{df['RSI'].iloc[-1]:.1f}`\n"
                   f"🏛️ Régimen 200d: `{tendencia}`\n"
                   f"🧠 IA Target Q2: *${data['pred']:.2f}* ({diff:+.2f}% {emoji_proy})\n"
                   f"📉 Riesgo Histórico: `±{df['STD'].iloc[-1]:.2f}`")

            # --- GRÁFICO INSTITUCIONAL DUAL ---
            plt.style.use('dark_background')
            fig = plt.figure(figsize=(11, 7))
            fig.patch.set_facecolor('#0b0f19')
            gs = gridspec.GridSpec(2, 1, height_ratios=[3, 1], hspace=0.1)
            
            # Panel Superior: Precio y Proyección IA
            ax1 = fig.add_subplot(gs[0])
            ax1.set_facecolor('#0b0f19')
            df_plot = df.iloc[-180:]
            
            ax1.plot(df_plot.index, df_plot['Close'], color='#eab308', linewidth=2, label='Precio Spot') # Amarillo Oro
            ax1.fill_between(df_plot.index, df_plot['BB_Lower'], df_plot['BB_Upper'], color='#eab308', alpha=0.05, label='Bandas Volatilidad')
            ax1.plot(df_plot.index, df_plot['SMA_200'], color='#ec4899', linestyle='--', alpha=0.6, label='SMA 200')
            
            # Proyección y Cono
            fecha_futura = df.index[-1] + timedelta(days=45)
            ax1.plot([df.index[-1], fecha_futura], [p, data['pred']], color='#10b981', linestyle='--', linewidth=2.5, marker='o', label='Target IA')
            
            margen_error = data['std'] * 1.5
            ax1.fill_between([df.index[-1], fecha_futura], [p, data['pred'] + margen_error], [p, data['pred'] - margen_error], color='#10b981', alpha=0.15)
            
            ax1.set_title(f"Macro Terminal: {nombre} (Proyección 45d)", color='white', loc='left', fontsize=12, fontweight='bold')
            ax1.legend(loc='upper left', fontsize='small', framealpha=0.2)
            ax1.grid(color='#1e293b', alpha=0.4, linestyle=':')
            ax1.tick_params(labelbottom=False)
            
            # Panel Inferior: RSI
            ax2 = fig.add_subplot(gs[1])
            ax2.set_facecolor('#0b0f19')
            ax2.plot(df_plot.index, df_plot['RSI'], color='#8b5cf6', linewidth=1.5)
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

enviar_telegram("✅ *AUDITORÍA MACRO 2026 FINALIZADA*")
