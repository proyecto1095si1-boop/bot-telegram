import yfinance as yf
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
import matplotlib.pyplot as plt
import requests
import io
import warnings
import sys

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

def preparar_datos_inversion(df):
    df = df.copy()
    # Medias Móviles para Tendencia de Fondo
    df['SMA_50'] = df['Close'].rolling(50).mean()
    df['SMA_200'] = df['Close'].rolling(200).mean()
    
    # RSI de largo plazo (más suave)
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(30).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(30).mean()
    df['RSI_Largo'] = 100 - (100 / (1 + (gain/loss)))
    
    # Distancia a la SMA 200 (para ver si está "barata")
    df['Distancia_SMA200'] = (df['Close'] - df['SMA_200']) / df['SMA_200']
    
    # Volatilidad para el Stop Loss de 3 meses
    df['ATR'] = df[['High', 'Low', 'Close']].apply(lambda x: max(x['High']-x['Low'], abs(x['High']-x['Close']), abs(x['Low']-x['Close'])), axis=1).rolling(21).mean()
    
    return df.dropna()

# --- UNIVERSO ---
argentinas = ['YPF', 'GGAL', 'BMA', 'PAM', 'VIST', 'TGS', 'CEPU', 'CRESY', 'TXAR.BA', 'ALUA.BA']
usa = ['AAPL', 'MSFT', 'AMZN', 'NVDA', 'GOOGL', 'META', 'TSLA', 'JPM', 'XOM', 'KO', 'DIS', 'NFLX']
universo = argentinas + usa

enviar_telegram("🏦 *Iniciando Radar de Inversión (2-3 Meses)*\nBuscando valor estructural...")

for ticker in universo:
    try:
        data = yf.download(ticker, period="3y", progress=False)
        if isinstance(data.columns, pd.MultiIndex): data.columns = data.columns.get_level_values(0)
        
        data = preparar_datos_inversion(data)
        
        # Objetivo a 3 meses (63 días hábiles)
        data['Retorno_3M'] = (data['Close'].shift(-63) - data['Close']) / data['Close']
        data['Target'] = np.where(data['Retorno_3M'] > 0.12, 1, 0) # Buscamos +12% en 3 meses
        
        features = ['Close', 'SMA_50', 'SMA_200', 'RSI_Largo', 'Distancia_SMA200']
        train_data = data.dropna()
        
        model = RandomForestClassifier(n_estimators=100, random_state=42)
        model.fit(train_data[features].iloc[:-63], train_data['Target'].iloc[:-63])
        
        ultima_fila = train_data[features].iloc[-1:]
        prob = model.predict_proba(ultima_fila)[0][1]
        
        actual = train_data.iloc[-1]
        
        # CONDICIÓN DE INVERSIÓN (Menos rígida que la anterior)
        # 1. Probabilidad IA > 60%
        # 2. Que no esté extremadamente sobrecomprada (RSI < 70)
        # 3. Que el precio esté cerca o recuperando la SMA 200 (no necesariamente arriba)
        
        if prob > 0.60 and actual['RSI_Largo'] < 70:
            stop_loss = actual['Close'] - (actual['ATR'] * 4) # Stop bien ancho
            take_profit = actual['Close'] * 1.25 # Objetivo +25%
            
            mensaje = (
                f"🏛️ *OPORTUNIDAD DE INVERSIÓN: {ticker}*\n"
                f"Plazo estimado: `2 a 3 meses`\n\n"
                f"💰 Precio actual: *${actual['Close']:.2f}*\n"
                f"🛡️ Piso sugerido: *${stop_loss:.2f}*\n"
                f"🚀 Objetivo: *${take_profit:.2f}*\n\n"
                f"📊 Confianza IA: `{prob:.1%}`\n"
                f"💡 Nota: `Filtro SMA 200 flexibilizado para captura de valor`"
            )
            
            # Generar gráfico
            df_plot = train_data.iloc[-250:]
            fig, ax = plt.subplots(figsize=(10, 5))
            fig.patch.set_facecolor('#0a192f'); ax.set_facecolor('#0a192f')
            ax.plot(df_plot.index, df_plot['Close'], color='white', label='Precio')
            ax.plot(df_plot.index, df_plot['SMA_200'], color='magenta', label='SMA 200 (Tendencia)')
            ax.axhline(actual['Close'], color='orange', linestyle='--')
            ax.tick_params(colors='white'); ax.legend()
            
            enviar_telegram(mensaje, fig)
            plt.close(fig)

    except Exception as e: print(f"Error en {ticker}: {e}")

enviar_telegram("✅ *Escaneo de Inversión Finalizado.*")
