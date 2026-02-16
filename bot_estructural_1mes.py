import yfinance as yf
import pandas as pd
import numpy as np
from sklearn.ensemble import GradientBoostingClassifier
import matplotlib.pyplot as plt
import requests
import io
import time
from datetime import datetime, timedelta

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

# --- FUERZA BRUTA 2026 ---
# Definimos la fecha de hoy EXACTA
AHORA = datetime.now()
FECHA_HOY = AHORA.strftime('%Y-%m-%d')
if AHORA.year < 2026:
    enviar_telegram("⚠️ *ERROR DE SISTEMA:* El servidor detecta un año anterior a 2026. Revisando sincronización...")

def preparar_datos_precision(df):
    df = df.copy()
    df['SMA_20'] = df['Close'].rolling(20).mean()
    df['SMA_200'] = df['Close'].rolling(200).mean()
    df['RSI'] = 100 - (100 / (1 + (df['Close'].diff().where(df['Close'].diff() > 0, 0).rolling(14).mean() / 
                                  -df['Close'].diff().where(df['Close'].diff() < 0, 0).rolling(14).mean())))
    df['ATR'] = df[['High', 'Low', 'Close']].apply(lambda x: max(x['High']-x['Low'], abs(x['High']-x['Close']), abs(x['Low']-x['Close'])), axis=1).rolling(14).mean()
    return df.dropna()

universo = ['YPF', 'GGAL', 'BMA', 'VIST', 'AAPL', 'MSFT', 'AMZN', 'NVDA', 'PYPL', 'BABA', 'MELI']

enviar_telegram(f"⚡ *SISTEMA PROYECTIVO V14 (ANTI-CACHÉ)*\nIniciando auditoría de datos para el `{FECHA_HOY}`...")

for ticker in universo:
    try:
        # PARÁMETRO MÁGICO: Agregamos una descarga de 1d con intervalo pequeño para "despertar" el servidor
        # y luego descargamos el historial completo hasta HOY.
        ticker_obj = yf.Ticker(ticker)
        data = ticker_obj.history(start="2024-01-01", end=FECHA_HOY, interval="1d")
        
        if data.empty or len(data) < 200: continue
        
        # Limpieza de columnas
        data.columns = [c.capitalize() for c in data.columns]
        
        df = preparar_datos_precision(data)
        precio_actual = float(df['Close'].iloc[-1])
        fecha_data = df.index[-1].strftime('%d/%m/%Y')
        
        # VALIDACIÓN CRUCIAL
        if "2026" not in fecha_data and "2025" in fecha_data:
            print(f"Saltando {ticker}: Datos obsoletos detectados ({fecha_data})")
            continue

        # IA de Alta Precisión
        df['Ret_Futuro'] = (df['Close'].shift(-60) - df['Close']) / df['Close']
        df['Target'] = np.where(df['Ret_Futuro'] > 0.12, 1, 0)
        
        train = df.dropna()
        features = ['Close', 'SMA_20', 'SMA_200', 'RSI']
        model = GradientBoostingClassifier(n_estimators=100, learning_rate=0.05)
        model.fit(train[features].iloc[:-60], train['Target'].iloc[:-60])
        
        prob = model.predict_proba(train[features].iloc[-1:])[0][1]
        
        if prob > 0.60:
            atr = float(df['ATR'].iloc[-1])
            proy_precio = precio_actual + (atr * 6)
            stop_loss = precio_actual - (atr * 3)
            fecha_proy = df.index[-1] + timedelta(days=90)
            
            msj = (f"🏛️ *PROYECCIÓN REAL 2026: {ticker}*\n"
                   f"📅 Fecha de la data: `{fecha_data}`\n\n"
                   f"💵 Precio Actual: *${precio_actual:.2f}*\n"
                   f"🛡️ Stop Loss: *${stop_loss:.2f}*\n"
                   f"🎯 Proyección (3 Meses): *${proy_precio:.2f}*\n\n"
                   f"📊 Confianza IA: `{prob:.1%}`\n"
                   f"🔥 *ESTADO: DATOS ACTUALIZADOS*")

            plt.style.use('dark_background')
            fig, ax = plt.subplots(figsize=(10, 5))
            fig.patch.set_facecolor('#0a192f'); ax.set_facecolor('#0a192f')
            
            # Gráfico con área de confianza
            df_p = df.iloc[-150:]
            ax.plot(df_p.index, df_p['Close'], color='white', linewidth=2, label='Precio')
            ax.plot([df_p.index[-1], fecha_proy], [precio_actual, proy_precio], color='#00ff00', linestyle='--', linewidth=3, label='Proyección')
            ax.fill_between([df_p.index[-1], fecha_proy], [precio_actual, proy_precio + atr], [precio_actual, proy_precio - atr], color='#00ff00', alpha=0.1)
            
            ax.set_title(f"Terminal Proyectiva 2026 - {ticker}", color='cyan')
            ax.legend(); ax.grid(alpha=0.1)
            
            enviar_telegram(msj, fig)
            plt.close(fig)
            
    except Exception as e:
        print(f"Error en {ticker}: {e}")

enviar_telegram("🏁 *Auditoría de Mercado 2026 Finalizada.*")
