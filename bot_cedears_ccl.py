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

# --- UNIVERSO CEDEARs (Máxima Liquidez en ByMA) ---
cedears_pesos = [
    'SPY.BA', 'QQQ.BA', 'DIA.BA', 'AAPL.BA', 'MSFT.BA', 
    'NVDA.BA', 'AMZN.BA', 'MELI.BA', 'KO.BA', 'V.BA'
]

def motor_cedears(ticker):
    df = pd.DataFrame()
    for intento in range(3):
        try:
            t = yf.Ticker(ticker)
            df = t.history(period="2y", interval="1d", timeout=10)
            if not df.empty and len(df) > 150: break
        except: time.sleep(2)
    
    if df.empty or len(df) < 150: return None
    
    # Indicadores
    df['SMA_20'] = df['Close'].rolling(20).mean()
    df['SMA_50'] = df['Close'].rolling(50).mean()
    
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    df['RSI'] = 100 - (100 / (1 + (gain/loss)))
    
    df['STD'] = df['Close'].rolling(20).std()
    df['BB_Upper'] = df['SMA_20'] + (df['STD'] * 2)
    df['BB_Lower'] = df['SMA_20'] - (df['STD'] * 2)
    
    # --- IA: PREDICCIÓN A 30 DÍAS (COBERTURA) ---
    dias_proy = 30
    df['Target_Ret'] = (df['Close'].shift(-dias_proy) / df['Close']) - 1.0
    train = df.dropna()
    
    features = ['Close', 'SMA_20', 'SMA_50', 'RSI']
    scaler = StandardScaler()
    
    if len(train) <= dias_proy:
        return None
        
    X_train = scaler.fit_transform(train[features].iloc[:-dias_proy])
    y_train = train['Target_Ret'].iloc[:-dias_proy]
    
    model = Ridge(alpha=0.5) 
    model.fit(X_train, y_train)
    
    X_ultima = scaler.transform(df[features].iloc[-1:])
    pred_retorno = model.predict(X_ultima)[0]
    precio_act = float(df['Close'].iloc[-1])
    
    pred_ia_cruda = precio_act * (1 + pred_retorno)
    
    # Filtro Anti-Pesimismo para CEDEARs (El CCL tiende al alza a la larga)
    soporte_50 = float(df['SMA_50'].iloc[-1])
    if pred_ia_cruda < precio_act and precio_act > soporte_50:
        pred_ia = max(pred_ia_cruda, soporte_50 * 0.95)
    else:
        pred_ia = pred_ia_cruda

    return df, {'pred': float(pred_ia), 'precio': precio_act, 'std': float(df['STD'].iloc[-1])}

hoy_str = datetime.now().strftime('%d/%m/%Y')
enviar_telegram(f"🛡️ *ESCUDO CEDEARs V1.0*\nMonitor Anti-Devaluación Activado | {hoy_str}\n_Analizando flujo de pesos hacia Wall Street..._")

for ticker in cedears_pesos:
    try:
        time.sleep(random.uniform(1.5, 3.0)) 
        res = motor_cedears(ticker)
        if not res: continue
        df, data = res
        
        p = data['precio']
        diff = ((data['pred'] / p) - 1) * 100
        emoji = "🟢" if diff > 0 else "🔴"
        
        # Etiqueta de cobertura
        if diff > 5.0:
            estado_cobertura = "🔥 FUERTE SEÑAL DE COBERTURA"
        elif diff > 0:
            estado_cobertura = "🛡️ COBERTURA ESTABLE"
        else:
            estado_cobertura = "⚠️ RIESGO DE CORRECCIÓN CCL/USA"
            
        valor_rsi = float(df['RSI'].iloc[-1])
        rsi_formateado = str(round(valor_rsi, 1))
        
        msj = (f"🇦🇷 *{ticker}* | (Cotización en ARS)\n"
               f"{estado_cobertura}\n\n"
               f"💰 Spot Actual: *${p:,.2f} ARS*\n"
               f"🧠 IA Target 30d: *${data['pred']:,.2f} ARS* ({diff:+.2f}% {emoji})\n"
               f"📊 RSI: `{rsi_formateado}` | Volatilidad: `±{data['std']:,.2f}`")

        # GRÁFICO CEDEAR
        plt.style.use('dark_background')
        fig = plt.figure(figsize=(11, 7))
        fig.patch.set_facecolor('#0b0f19')
        gs = gridspec.GridSpec(2, 1, height_ratios=[3, 1], hspace=0.1)
        
        ax1 = fig.add_subplot(gs[0])
        ax1.set_facecolor('#0b0f19')
        df_plot = df.iloc[-120:] # Ver los últimos 6 meses aprox
        
        ax1.plot(df_plot.index, df_plot['Close'], color='#eab308', linewidth=2, label='Cotización CEDEAR (ARS)') # Dorado por el dólar
        ax1.fill_between(df_plot.index, df_plot['BB_Lower'], df_plot['BB_Upper'], color='#fef08a', alpha=0.05)
        ax1.plot(df_plot.index, df_plot['SMA_50'], color='#38bdf8', linestyle='--', alpha=0.8, label='SMA 50 (Soporte CCL)')
        
        fecha_futura = df.index[-1] + timedelta(days=30)
        color_cono = '#4ade80' if diff > 0 else '#ef4444'
        ax1.plot([df.index[-1], fecha_futura], [p, data['pred']], color=color_cono, linestyle='--', linewidth=2.5, marker='o', markersize=6, label='Proyección IA')
        
        margen_error = data['std'] * 1.5
        ax1.fill_between([df.index[-1], fecha_futura], [p, data['pred'] + margen_error], [p, data['pred'] - margen_error], color=color_cono, alpha=0.15)
        
        ax1.set_title(f"Monitor CEDEAR: {ticker} | Perspectiva 30 Días", color='white', loc='left', fontsize=12, fontweight='bold')
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

enviar_telegram("✅ *AUDITORÍA DE CEDEARs FINALIZADA*")
