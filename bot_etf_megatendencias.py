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

# --- UNIVERSO MEGA-TENDENCIAS (ETFs Globales) ---
etfs_tematicos = {
    '🤖 Semiconductores (IA)': 'SMH',
    '🦾 Robótica & IA': 'BOTZ',
    '☢️ Uranio & Nuclear': 'URA',
    '🛡️ Ciberseguridad': 'CIBR',
    '🧬 Biotecnología': 'IBB',
    '🚀 Defensa Aeroespacial': 'ITA',
    '💧 Recursos Hídricos': 'PHO'
}

def motor_tendencias(ticker):
    df = pd.DataFrame()
    for intento in range(3):
        try:
            t = yf.Ticker(ticker)
            df = t.history(period="2y", interval="1d", timeout=10)
            if not df.empty and len(df) > 150: break
        except: time.sleep(2)
    
    if df.empty or len(df) < 150: return None
    
    df['SMA_50'] = df['Close'].rolling(50).mean()
    df['SMA_200'] = df['Close'].rolling(200).mean()
    
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    df['RSI'] = 100 - (100 / (1 + (gain/loss)))
    
    df['STD'] = df['Close'].rolling(20).std()
    
    # --- IA: PROYECCIÓN DEL FLUJO (30 DÍAS) ---
    dias_proy = 30
    df['Target_Ret'] = (df['Close'].shift(-dias_proy) / df['Close']) - 1.0
    train = df.dropna()
    
    features = ['Close', 'SMA_50', 'SMA_200', 'RSI']
    scaler = StandardScaler()
    
    if len(train) <= dias_proy:
        return None
        
    X_train = scaler.fit_transform(train[features].iloc[:-dias_proy])
    y_train = train['Target_Ret'].iloc[:-dias_proy]
    
    model = Ridge(alpha=1.0) 
    model.fit(X_train, y_train)
    
    X_ultima = scaler.transform(df[features].iloc[-1:])
    pred_retorno = model.predict(X_ultima)[0]
    precio_act = float(df['Close'].iloc[-1])
    
    pred_ia = precio_act * (1 + pred_retorno)

    return df, {'pred': float(pred_ia), 'precio': precio_act, 'std': float(df['STD'].iloc[-1])}

hoy_str = datetime.now().strftime('%d/%m/%Y')
enviar_telegram(f"🌐 *CAZADOR DE MEGA-TENDENCIAS V1.0*\nEscaneando ETFs Globales | {hoy_str}\n_Rastreando flujo de dinero inteligente..._")

for nombre, ticker in etfs_tematicos.items():
    try:
        time.sleep(random.uniform(1.5, 3.0)) 
        res = motor_tendencias(ticker)
        if not res: continue
        df, data = res
        
        p = data['precio']
        diff = ((data['pred'] / p) - 1) * 100
        
        # Termómetro de Flujo
        if diff > 3.0 and p > float(df['SMA_50'].iloc[-1]):
            estado = "🔥 SECTOR ON FIRE (Alta Demanda)"
            color_tema = '#f97316' # Naranja fuego
            emoji = "🟢"
        elif diff < 0:
            estado = "❄️ SECTOR ENFRIÁNDOSE (Toma de Ganancias)"
            color_tema = '#38bdf8' # Azul hielo
            emoji = "🔴"
        else:
            estado = "⚖️ SECTOR ESTABLE (Acumulación Silenciosa)"
            color_tema = '#a855f7' # Violeta
            emoji = "⚪"
            
        msj = (f"*{nombre}* | ETF: `{ticker}`\n"
               f"{estado}\n\n"
               f"💰 Spot Actual: *${p:.2f} USD*\n"
               f"🧠 Proyección 30d: *${data['pred']:.2f} USD* ({diff:+.2f}% {emoji})\n"
               f"📊 RSI: `{df['RSI'].iloc[-1]:.1f}` | Desviación: `±{data['std']:.2f}`")

        # --- GRÁFICO FUTURISTA ---
        plt.style.use('dark_background')
        fig = plt.figure(figsize=(11, 7))
        fig.patch.set_facecolor('#0b0f19')
        gs = gridspec.GridSpec(2, 1, height_ratios=[3, 1], hspace=0.1)
        
        ax1 = fig.add_subplot(gs[0])
        ax1.set_facecolor('#0b0f19')
        df_plot = df.iloc[-120:] 
        
        ax1.plot(df_plot.index, df_plot['Close'], color=color_tema, linewidth=2.5, label='Cotización ETF')
        ax1.fill_between(df_plot.index, df_plot['Close'].rolling(10).mean() - data['std'], df_plot['Close'].rolling(10).mean() + data['std'], color=color_tema, alpha=0.1)
        ax1.plot(df_plot.index, df_plot['SMA_200'], color='#f472b6', linestyle='--', alpha=0.8, label='SMA 200 (Estructural)')
        
        fecha_futura = df.index[-1] + timedelta(days=30)
        color_cono = '#4ade80' if diff > 0 else '#ef4444'
        ax1.plot([df.index[-1], fecha_futura], [p, data['pred']], color=color_cono, linestyle='--', linewidth=2.5, marker='o', markersize=6, label='IA Target')
        
        margen_error = data['std'] * 1.5
        ax1.fill_between([df.index[-1], fecha_futura], [p, data['pred'] + margen_error], [p, data['pred'] - margen_error], color=color_cono, alpha=0.15)
        
        ax1.set_title(f"Mega-Tendencia: {nombre} | Flujo 30 Días", color='white', loc='left', fontsize=12, fontweight='bold')
        ax1.legend(loc='upper left', fontsize='small', framealpha=0.2)
        ax1.grid(color='#1e293b', alpha=0.4, linestyle=':')
        ax1.tick_params(labelbottom=False) 
        
        ax2 = fig.add_subplot(gs[1])
        ax2.set_facecolor('#0b0f19')
        ax2.plot(df_plot.index, df_plot['RSI'], color=color_tema, linewidth=1.5, alpha=0.8)
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

enviar_telegram("✅ *AUDITORÍA DE MEGA-TENDENCIAS FINALIZADA*")
