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

# --- UNIVERSO INTRADÍA (Solo Activos de Alta Liquidez) ---
# Para Day Trading, necesitamos activos que se muevan rápido y tengan mucho volumen.
activos_sniper = {
    '🚀 TECH USA': ['AAPL', 'NVDA', 'TSLA', 'AMD', 'META'],
    '🇦🇷 ADRs ARG': ['GGAL', 'YPF', 'PAM', 'BMA'],
    '🪙 CRIPTO & MACRO': ['BTC-USD', 'SPY', 'QQQ', 'GC=F']
}

def motor_sniper_15m(ticker):
    df = pd.DataFrame()
    for intento in range(3):
        try:
            t = yf.Ticker(ticker)
            # Descargamos velas de 15 minutos de los últimos 5 días
            df = t.history(period="5d", interval="15m", timeout=10)
            if not df.empty and len(df) > 50: break
        except: time.sleep(2)
    
    if df.empty or len(df) < 50: return None
    
    # --- INDICADORES DE ALTA FRECUENCIA ---
    # 1. EMAs Rápidas (El Gatillo)
    df['EMA_9'] = df['Close'].ewm(span=9, adjust=False).mean()
    df['EMA_21'] = df['Close'].ewm(span=21, adjust=False).mean()
    
    # 2. VWAP Intradía (Precio Promedio Ponderado por Volumen)
    # El VWAP se reinicia cada día al abrir el mercado
    df['Date'] = df.index.date
    df['Typical_Price'] = (df['High'] + df['Low'] + df['Close']) / 3
    df['VWAP'] = (df['Typical_Price'] * df['Volume']).groupby(df['Date']).cumsum() / df['Volume'].groupby(df['Date']).cumsum()
    
    # 3. ATR (Para calcular Stop Loss y Take Profit milimétricos)
    df['TR'] = np.maximum(df['High'] - df['Low'], 
               np.maximum(abs(df['High'] - df['Close'].shift(1)), abs(df['Low'] - df['Close'].shift(1))))
    df['ATR'] = df['TR'].rolling(14).mean()
    
    # 4. RSI Rápido (Periodo 9 en lugar de 14 para day trading)
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(9).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(9).mean()
    df['RSI'] = 100 - (100 / (1 + (gain/loss)))
    
    # --- IA PROYECTIVA CORTA (Próximas 8 velas = 2 Horas) ---
    velas_proy = 8 
    df['Target_Ret'] = (df['Close'].shift(-velas_proy) / df['Close']) - 1.0
    train = df.dropna(subset=['Close', 'EMA_9', 'EMA_21', 'RSI', 'Target_Ret'])
    
    features = ['Close', 'EMA_9', 'EMA_21', 'RSI']
    scaler = StandardScaler()
    
    if len(train) > 20:
        X_train = scaler.fit_transform(train[features].iloc[:-velas_proy])
        y_train = train['Target_Ret'].iloc[:-velas_proy]
        
        model = Ridge(alpha=0.1) # Alta sensibilidad
        model.fit(X_train, y_train)
        
        X_ultima = scaler.transform(df[features].iloc[-1:])
        pred_retorno = model.predict(X_ultima)[0]
    else:
        pred_retorno = 0.0
        
    precio_act = float(df['Close'].iloc[-1])
    pred_ia_cruda = precio_act * (1 + pred_retorno)
    
    # Determinar Tendencia Inmediata
    ema9_act = df['EMA_9'].iloc[-1]
    ema21_act = df['EMA_21'].iloc[-1]
    vwap_act = df['VWAP'].iloc[-1]
    atr_act = df['ATR'].iloc[-1]
    
    estado_tendencia = "NEUTRAL ⚪"
    accion = "ESPERAR ⏳"
    
    if ema9_act > ema21_act and precio_act > vwap_act:
        estado_tendencia = "ALCISTA 🟢"
        accion = "LONG (COMPRAR) 🚀"
        stop_loss = precio_act - (atr_act * 1.5) # Stop ajustado
        take_profit = precio_act + (atr_act * 3.0) # TP al doble de riesgo
    elif ema9_act < ema21_act and precio_act < vwap_act:
        estado_tendencia = "BAJISTA 🔴"
        accion = "SHORT (VENDER) 🩸"
        stop_loss = precio_act + (atr_act * 1.5)
        take_profit = precio_act - (atr_act * 3.0)
    else:
        # En consolidación
        stop_loss = precio_act - (atr_act * 1.5)
        take_profit = precio_act + (atr_act * 1.5)

    return df, {
        'precio': precio_act, 'pred': float(pred_ia_cruda), 
        'vwap': vwap_act, 'accion': accion, 'estado': estado_tendencia,
        'sl': float(stop_loss), 'tp': float(take_profit), 'rsi': float(df['RSI'].iloc[-1])
    }

hoy_str = datetime.now().strftime('%d/%m/%Y %H:%M')
enviar_telegram(f"⚡ *SNIPER INTRADÍA V1.0*\nActivando radares de 15 minutos | {hoy_str}\n_Buscando liquidez institucional..._")

for sector, activos in activos_sniper.items():
    for ticker in activos:
        try:
            time.sleep(random.uniform(1.0, 2.5)) 
            res = motor_sniper_15m(ticker)
            if not res: continue
            df, data = res
            
            p = data['precio']
            rsi_formateado = f"{data['rsi']:.1f}"
            
            msj = (f"🎯 *{ticker}* | 15 MINUTOS\n"
                   f"💰 Spot: *${p:.2f}* | VWAP: `${data['vwap']:.2f}`\n"
                   f"🚦 Señal: *{data['accion']}*\n\n"
                   f"🛡️ *PLAN DE TRADING:*\n"
                   f"• Take Profit: `${data['tp']:.2f}`\n"
                   f"• Stop Loss: `${data['sl']:.2f}`\n\n"
                   f"🧠 IA 2 Horas: `${data['pred']:.2f}` | RSI: `{rsi_formateado}`")

            # --- GRÁFICO INTRADÍA TIPO SCALPING ---
            plt.style.use('dark_background')
            fig = plt.figure(figsize=(11, 7))
            fig.patch.set_facecolor('#0b0f19')
            gs = gridspec.GridSpec(2, 1, height_ratios=[3, 1], hspace=0.1)
            
            ax1 = fig.add_subplot(gs[0])
            ax1.set_facecolor('#0b0f19')
            
            # Mostrar solo las últimas 60 velas (unas 15 horas de mercado)
            df_plot = df.iloc[-60:] 
            
            # Línea de precio
            ax1.plot(df_plot.index, df_plot['Close'], color='#e2e8f0', linewidth=2, label='Precio')
            
            # VWAP (Línea Institucional)
            ax1.plot(df_plot.index, df_plot['VWAP'], color='#eab308', linestyle='-.', linewidth=2, alpha=0.8, label='VWAP (Institucional)')
            
            # EMAs rápidas
            ax1.plot(df_plot.index, df_plot['EMA_9'], color='#4ade80', linewidth=1.2, alpha=0.9, label='EMA 9 (Rápida)')
            ax1.plot(df_plot.index, df_plot['EMA_21'], color='#f43f5e', linewidth=1.2, alpha=0.9, label='EMA 21 (Lenta)')
            
            # Zonas de Stop y Profit (Líneas horizontales en la última vela)
            ax1.axhline(data['tp'], color='#4ade80', linestyle=':', alpha=0.8, label='Take Profit')
            ax1.axhline(data['sl'], color='#ef4444', linestyle=':', alpha=0.8, label='Stop Loss')
            
            ax1.set_title(f"Sniper Intradía: {ticker} | {data['estado']}", color='white', loc='left', fontsize=12, fontweight='bold')
            ax1.legend(loc='upper left', fontsize='x-small', framealpha=0.2)
            ax1.grid(color='#1e293b', alpha=0.4, linestyle=':')
            ax1.tick_params(labelbottom=False) 
            
            # Panel de Volumen (Para el scalping el volumen es más importante que el RSI solo)
            ax2 = fig.add_subplot(gs[1])
            ax2.set_facecolor('#0b0f19')
            
            # Colores de volumen (verde si cerró al alza, rojo a la baja)
            colores_vol = ['#4ade80' if c >= o else '#ef4444' for c, o in zip(df_plot['Close'], df_plot['Open'])]
            ax2.bar(df_plot.index, df_plot['Volume'], color=colores_vol, alpha=0.6, width=0.01)
            
            ax2.set_ylabel('Volumen', color='gray', fontsize=9)
            ax2.grid(color='#1e293b', alpha=0.4, linestyle=':')
            ax2.tick_params(axis='x', rotation=45, colors='gray')
            ax2.tick_params(axis='y', colors='gray')
            
            ax1.spines['top'].set_visible(False); ax1.spines['right'].set_visible(False)
            ax2.spines['top'].set_visible(False); ax2.spines['right'].set_visible(False)
            
            enviar_telegram(msj, fig)
            
        except Exception as e:
            print(f"Fallo en {ticker}: {e}")
            continue

enviar_telegram("🛑 *RADAR INTRADÍA FINALIZADO*")
