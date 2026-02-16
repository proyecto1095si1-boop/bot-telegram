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

# --- CONFIGURACIÓN DE ACCESO ---
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
    df['SMA_50'] = df['Close'].rolling(50).mean()
    df['SMA_200'] = df['Close'].rolling(200).mean()
    
    # RSI de 30 días para ver la tendencia real, no el ruido
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(30).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(30).mean()
    df['RSI_Largo'] = 100 - (100 / (1 + (gain/loss)))
    
    # Indicador de "Barato/Caro": Distancia porcentual a la media de 200
    df['Distancia_SMA200'] = (df['Close'] - df['SMA_200']) / df['SMA_200']
    
    # Volatilidad para Stop Loss de largo plazo
    df['ATR'] = df[['High', 'Low', 'Close']].apply(lambda x: max(x['High']-x['Low'], abs(x['High']-x['Close']), abs(x['Low']-x['Close'])), axis=1).rolling(21).mean()
    
    return df.dropna()

# --- UNIVERSO AMPLIADO ---
argentinas = ['YPF', 'GGAL', 'BMA', 'PAM', 'VIST', 'TGS', 'CEPU', 'CRESY', 'TXAR.BA', 'ALUA.BA', 'COME.BA', 'BYMA.BA']
usa = ['AAPL', 'MSFT', 'AMZN', 'NVDA', 'GOOGL', 'META', 'TSLA', 'JPM', 'XOM', 'KO', 'DIS', 'NFLX', 'PYPL', 'BABA']
universo = argentinas + usa

enviar_telegram("🏦 *INICIANDO ESTRATEGA DE CICLO (2-3 MESES)*\nAnalizando activos con potencial de recuperación...")

for ticker in universo:
    try:
        data = yf.download(ticker, period="3y", progress=False)
        if isinstance(data.columns, pd.MultiIndex): data.columns = data.columns.get_level_values(0)
        
        data = preparar_datos_inversion(data)
        
        # ENTRENAMIENTO: Buscamos 12% de ganancia en 3 meses (63 días hábiles)
        data['Retorno_3M'] = (data['Close'].shift(-63) - data['Close']) / data['Close']
        data['Target'] = np.where(data['Retorno_3M'] > 0.12, 1, 0)
        
        features = ['Close', 'SMA_50', 'SMA_200', 'RSI_Largo', 'Distancia_SMA200']
        train_data = data.dropna()
        
        if len(train_data) < 200: continue
            
        model = RandomForestClassifier(n_estimators=100, random_state=42)
        model.fit(train_data[features].iloc[:-63], train_data['Target'].iloc[:-63])
        
        ultima_fila = train_data[features].iloc[-1:]
        prob = model.predict_proba(ultima_fila)[0][1]
        actual = train_data.iloc[-1]
        
        # NUEVA LÓGICA DE FILTRADO (Más inteligente, menos rígida)
        # 1. Confianza IA superior al 60%
        # 2. No compramos si está en el techo (RSI < 65)
        # 3. Que el precio esté "viva" (RSI > 40) o cerca de recuperar medias
        
        if prob > 0.60 and actual['RSI_Largo'] < 65:
            # Stop Loss de Inversionista (no de trader)
            stop_loss = actual['Close'] - (actual['ATR'] * 4) 
            take_profit = actual['Close'] * 1.25 # Objetivo +25%
            
            mensaje = (
                f"🏛️ *OPORTUNIDAD ESTRUCTURAL: {ticker}*\n"
                f"Horizonte: `2 a 3 Meses`\n\n"
                f"💰 Precio Entrada: *${actual['Close']:.2f}*\n"
                f"🛡️ Stop Loss (Largo): *${stop_loss:.2f}*\n"
                f"🚀 Objetivo 3M: *${take_profit:.2f}*\n\n"
                f"📊 Probabilidad de éxito: `{prob:.1%}`\n"
                f"💡 Nota: `Captura de valor por ciclo de mediano plazo.`"
            )
            
            # Gráfico de 1 año para ver el contexto
            df_plot = train_data.iloc[-250:]
            fig, ax = plt.subplots(figsize=(10, 5))
            fig.patch.set_facecolor('#0a192f'); ax.set_facecolor('#0a192f')
            ax.plot(df_plot.index, df_plot['Close'], color='white', label='Precio', linewidth=1.5)
            ax.plot(df_plot.index, df_plot['SMA_200'], color='magenta', label='SMA 200', linewidth=2)
            ax.fill_between(df_plot.index, actual['Close'], stop_loss, color='red', alpha=0.1)
            ax.set_title(f"Análisis de Ciclo: {ticker}", color='white')
            ax.tick_params(colors='white'); ax.legend()
            
            enviar_telegram(mensaje, fig)
            plt.close(fig)

    except Exception as e: print(f"Error en {ticker}: {e}")

enviar_telegram("✅ *Escaneo de Ciclo Finalizado.*")
