import yfinance as yf
import pandas as pd
import numpy as np
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
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

# --- UNIVERSO MACRO 2026 ---
sectores = {
    '💎 MATERIAS PRIMAS': {
        '🥇 ORO': 'GC=F', '🥈 PLATA': 'SI=F', '🏗️ COBRE': 'HG=F', 
        '🛢️ PETRÓLEO WTI': 'CL=F', '🔋 LITIO': 'LIT', '⚛️ URANIO': 'URA', '🪙 BITCOIN': 'BTC-USD'
    },
    '🌍 EMERGENTES': {
        '🇧🇷 BRASIL (EWZ)': 'EWZ', '🇨🇳 CHINA (FXI)': 'FXI', '🇮🇳 INDIA (INDA)': 'INDA',
        '🇲🇽 MÉXICO (EWW)': 'EWW', '🇦🇷 ARGENTINA (ARGT)': 'ARGT', '🌐 GLOBAL EM': 'EEM'
    }
}

def motor_macro_equilibrado(ticker):
    df = pd.DataFrame()
    for intento in range(3):
        try:
            t = yf.Ticker(ticker)
            df = t.history(period="3y", interval="1d", timeout=10)
            if not df.empty and len(df) > 200: break
        except: time.sleep(2)
    
    if df.empty or len(df) < 200: return None
    
    # Indicadores Clave
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
    
    # --- IA: RIDGE REGRESSION MACRO ---
    dias_proy = 45 # En macro miramos a mes y medio
    df['Target'] = df['Close'].shift(-dias_proy).rolling(5).mean() 
    train = df.dropna()
    
    features = ['Close', 'SMA_50', 'SMA_200', 'RSI', 'MACD']
    scaler = StandardScaler()
    X_train = scaler.fit_transform(train[features].iloc[:-dias_proy])
    y_train = train['Target'].iloc[:-dias_proy]
    
    model = Ridge(alpha=1.0)
    model.fit(X_train, y_train)
    
    X_ultima = scaler.transform(df[features].iloc[-1:])
    pred_ia_cruda = model.predict(X_ultima)[0]
    precio_act = float(df['Close'].iloc[-1])
    
    # Filtro Anti-Pesimismo Estructural (Evita pronósticos apocalípticos falsos)
    soporte_200 = df['SMA_200'].iloc[-1]
    if pred_ia_cruda < precio_act and precio_act > soporte_200:
        pred_ia = max(pred_ia_cruda, soporte_200 * 0.90) # Suaviza la caída si está en mercado alcista
    else:
        pred_ia = pred_ia_cruda

    return df, {'pred': float(pred_ia), 'precio': precio_act, 'std': float(df['STD'].iloc[-1])}

hoy_str = datetime.now().strftime('%d/%m/%Y')
enviar_telegram(f"🌍 *MACRO TERMINAL EQUILIBRADA V29.0*\nSincronizando Commodities y Emergentes | {hoy_str}\n_Motor Ridge Regression Activado..._")

for sector, activos in sectores.items():
    enviar_telegram(f"📁 *ANALIZANDO: {sector}*")
    
    for nombre, ticker in activos.items():
        try:
            time.sleep(random.uniform(1.5, 3.0)) # Evitar bloqueos de Yahoo
            res = motor_macro_equilibrado(ticker)
            if not res: continue
            df, data = res
            
            p = data['precio']
            diff = ((data['pred'] / p) - 1) * 100
            
            # Formateo seguro de variables
            valor_rsi = float(df['RSI'].iloc[-1])
            rsi_formateado = str(round(valor_rsi, 1))
            tendencia_fondo = "🔥 BULLISH" if p > float(df['SMA_200'].iloc[-1]) else "❄️ BEARISH"
            emoji = "🟢" if diff > 0 else "🔴"
            
            msj = (f"*{nombre}* (`{ticker}`)\n"
                   f"💰 Spot: *${p:.2f}* | RSI: `{rsi_formateado}`\n"
                   f"🏛️ Régimen 200d: `{tendencia_fondo}`\n"
                   f"🧠 IA Target 45d: *${data['pred']:.2f}* ({diff:+.2f}% {emoji})")

            # --- GRÁFICO DUAL CON COLORES DINÁMICOS ---
            plt.style.use('dark_background')
            fig = plt.figure(figsize=(11, 7))
            fig.patch.set_facecolor('#0b0f19')
            gs = gridspec.GridSpec(2, 1, height_ratios=[3, 1], hspace=0.1)
            
            ax1 = fig.add_subplot(gs[0])
            ax1.set_facecolor('#0b0f19')
            df_plot = df.iloc[-180:] 
            
            # Color del precio (Dorado para dar toque Macro)
            ax1.plot(df_plot.index, df_plot['Close'], color='#eab308', linewidth=2, label='Cotización Spot')
            ax1.fill_between(df_plot.index, df_plot['BB_Lower'], df_plot['BB_Upper'], color='#eab308', alpha=0.05, label='Canal Volatilidad')
            ax1.plot(df_plot.index, df_plot['SMA_200'], color='#ec4899', linestyle='--', alpha=0.6, label='SMA 200 (Tendencia)')
            
            # Color dinámico de proyección (Verde si sube, Rojo si baja)
            color_proy = '#4ade80' if diff > 0 else '#ef4444'
            fecha_futura = df.index[-1] + timedelta(days=45)
            
            ax1.plot([df.index[-1], fecha_futura], [p, data['pred']], color=color_proy, linestyle='--', linewidth=2.5, marker='o', markersize=6, label='Ruta IA')
            
            margen_error = data['std'] * 1.5
            ax1.fill_between([df.index[-1], fecha_futura], [p, data['pred'] + margen_error], [p, data['pred'] - margen_error], color=color_proy, alpha=0.15)
            
            ax1.set_title(f"Macro Equilibrium: {nombre} (Proyección 45d)", color='white', loc='left', fontsize=12, fontweight='bold')
            ax1.legend(loc='upper left', fontsize='small', framealpha=0.2)
            ax1.grid(color='#1e293b', alpha=0.4, linestyle=':')
            ax1.tick_params(labelbottom=False) 
            
            # Panel RSI Inferior
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

enviar_telegram("✅ *AUDITORÍA MACRO EQUILIBRADA FINALIZADA*")
