import yfinance as yf
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
import matplotlib.pyplot as plt
import requests
import io
import warnings
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
            fig.savefig(buf, format='png', bbox_inches='tight', dpi=150, facecolor='#0a192f')
            buf.seek(0)
            url_foto = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
            requests.post(url_foto, data={'chat_id': CHAT_ID}, files={'photo': buf})
            buf.close()
    except: pass

def preparar_datos(df):
    df = df.copy()
    df['SMA_50'] = df['Close'].rolling(50).mean()
    df['SMA_200'] = df['Close'].rolling(200).mean()
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(25).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(25).mean()
    df['RSI'] = 100 - (100 / (1 + (gain/loss)))
    df['ATR'] = df[['High', 'Low', 'Close']].apply(lambda x: max(x['High']-x['Low'], abs(x['High']-x['Close']), abs(x['Low']-x['Close'])), axis=1).rolling(20).mean()
    return df.dropna()

# --- UNIVERSO MASIVO ---
argentinas = ['YPF', 'GGAL', 'BMA', 'PAM', 'VIST', 'TGS', 'CEPU', 'CRESY', 'TXAR.BA', 'ALUA.BA', 'EDN', 'BBAR', 'BYMA.BA', 'COME.BA']
usa = ['AAPL', 'MSFT', 'AMZN', 'NVDA', 'GOOGL', 'META', 'TSLA', 'JPM', 'XOM', 'WMT', 'LLY', 'AVGO', 'MELI', 'BABA', 'PYPL']
universo = argentinas + usa

fecha_hoy = datetime.now().strftime('%Y-%m-%d')
enviar_telegram(f"📡 *ESCÁNER PROYECTIVO 2026*\nFecha: `{fecha_hoy}`\nAnalizando {len(universo)} activos...")

encontrados = 0
for ticker in universo:
    try:
        # Descarga forzada a 2026
        data = yf.download(ticker, start="2024-01-01", end=fecha_hoy, progress=False)
        if data.empty or len(data) < 200: continue
        if isinstance(data.columns, pd.MultiIndex): data.columns = data.columns.get_level_values(0)
        
        df = preparar_datos(data)
        
        # IA entrenada para detectar retornos de +12% en 60 días
        df['Ret_60'] = (df['Close'].shift(-60) - df['Close']) / df['Close']
        df['Target'] = np.where(df['Ret_60'] > 0.12, 1, 0)
        
        train = df.dropna()
        if len(train) < 100: continue
        
        features = ['Close', 'SMA_50', 'SMA_200', 'RSI']
        model = RandomForestClassifier(n_estimators=70, random_state=42)
        model.fit(train[features].iloc[:-60], train['Target'].iloc[:-60])
        
        prob = model.predict_proba(train[features].iloc[-1:]) [0][1]
        precio_actual = float(train['Close'].iloc[-1])
        fecha_actual = train.index[-1]
        
        # FILTRO DE COMPRA PROYECTIVO
        if prob > 0.52:
            encontrados += 1
            stop = precio_actual - (float(train['ATR'].iloc[-1]) * 4)
            objetivo_precio = precio_actual * 1.25 # Proyección +25%
            fecha_objetivo = fecha_actual + timedelta(days=90) # Visualización a 3 meses
            
            tipo = "🇦🇷" if ticker in argentinas else "🇺🇸"
            msj = (f"🏛️ *PROYECCIÓN {tipo} {ticker}*\n"
                   f"📅 Desde: `{fecha_actual.strftime('%d/%m/%Y')}`\n\n"
                   f"💵 Precio Hoy: *${precio_actual:.2f}*\n"
                   f"🛡️ Stop Loss: *${stop:.2f}*\n"
                   f"🎯 Objetivo Proyectado: *${objetivo_precio:.2f}*\n\n"
                   f"📊 Confianza IA: `{prob:.1%}`\n"
                   f"🔮 Tendencia: `Proyección a 90 días`")
            
            # Gráfico con línea de futuro
            fig, ax = plt.subplots(figsize=(10, 5))
            fig.patch.set_facecolor('#0a192f'); ax.set_facecolor('#0a192f')
            
            # Dibujar el pasado (últimos 180 días)
            df_plot = train.iloc[-180:]
            ax.plot(df_plot.index, df_plot['Close'], color='white', label='Precio Histórico', linewidth=1.5)
            ax.plot(df_plot.index, df_plot['SMA_200'], color='#FF00FF', label='Media 200 (Tendencia)', alpha=0.6)
            
            # Dibujar la PROYECCIÓN (Futuro)
            ax.plot([fecha_actual, fecha_objetivo], [precio_actual, objetivo_precio], 
                    color='#00ff00', linestyle='--', linewidth=2, label='Proyección IA')
            ax.scatter([fecha_objetivo], [objetivo_precio], color='#00ff00', s=50) # Punto final
            
            ax.set_title(f"Análisis Estructural y Proyección: {ticker}", color='white', fontweight='bold')
            ax.tick_params(colors='white'); ax.legend(facecolor='#112240', labelcolor='white')
            ax.grid(alpha=0.1)
            
            enviar_telegram(msj, fig)
            plt.close(fig)

    except: continue

if encontrados == 0:
    enviar_telegram("🛡️ *Reporte:* No se detectaron proyecciones alcistas claras para hoy lunes 16 de febrero de 2026.")
else:
    enviar_telegram(f"✅ *Análisis Terminado:* Se proyectaron {encontrados} activos con éxito.")
