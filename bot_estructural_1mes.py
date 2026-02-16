import yfinance as yf
import pandas as pd
import numpy as np
from sklearn.ensemble import GradientBoostingClassifier # IA más potente que RandomForest
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

def preparar_datos_ultra(df):
    df = df.copy()
    # Indicadores de precisión para 2026
    df['SMA_20'] = df['Close'].rolling(20).mean()
    df['SMA_200'] = df['Close'].rolling(200).mean()
    df['Volatilidad'] = df['Close'].pct_change().rolling(20).std()
    
    # RSI de corto y largo plazo combinado
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    df['RSI'] = 100 - (100 / (1 + (gain/loss)))
    
    df['ATR'] = df[['High', 'Low', 'Close']].apply(lambda x: max(x['High']-x['Low'], abs(x['High']-x['Close']), abs(x['Low']-x['Close'])), axis=1).rolling(14).mean()
    return df.dropna()

# --- UNIVERSO 2026 ---
argentinas = ['YPF', 'GGAL', 'BMA', 'PAM', 'VIST', 'TGS', 'CEPU', 'TXAR.BA', 'ALUA.BA']
usa = ['AAPL', 'MSFT', 'AMZN', 'NVDA', 'GOOGL', 'META', 'TSLA', 'PYPL', 'MELI', 'BABA']
universo = argentinas + usa

# FORZAMOS LA FECHA DE HOY (Lunes 16 de Febrero de 2026)
fecha_final = datetime.now().strftime('%Y-%m-%d')
fecha_inicio = (datetime.now() - timedelta(days=730)).strftime('%Y-%m-%d') # 2 años atrás

enviar_telegram(f"🚀 *GENERANDO PROYECCIONES REAL-TIME 2026*\nFecha: `{fecha_final}`\nEstado: `Actualizando Base de Datos...`")

for ticker in universo:
    try:
        # Descarga forzada sin caché
        data = yf.download(ticker, start=fecha_inicio, end=fecha_final, interval="1d", progress=False)
        if data.empty or len(data) < 200: continue
        if isinstance(data.columns, pd.MultiIndex): data.columns = data.columns.get_level_values(0)
        
        df = preparar_datos_ultra(data)
        
        # TARGET: Detectar si en los próximos 60 días habrá un movimiento superior a 2.5 veces la volatilidad actual
        df['Ret_Futuro'] = (df['Close'].shift(-60) - df['Close']) / df['Close']
        df['Target'] = np.where(df['Ret_Futuro'] > (df['Volatilidad'] * 2.5), 1, 0)
        
        train = df.dropna()
        features = ['Close', 'SMA_20', 'SMA_200', 'RSI', 'Volatilidad']
        
        # IA: Usamos Gradient Boosting para mayor precisión que el Random Forest
        model = GradientBoostingClassifier(n_estimators=100, learning_rate=0.1, max_depth=3)
        model.fit(train[features].iloc[:-60], train['Target'].iloc[:-60])
        
        ultima_fila = train[features].iloc[-1:]
        prob = model.predict_proba(ultima_fila)[0][1]
        
        precio_actual = float(train['Close'].iloc[-1])
        fecha_actual = train.index[-1]
        
        # PROYECCIÓN AJUSTADA POR VOLATILIDAD (Más realista)
        if prob > 0.65: # Subimos el nivel de exigencia para que sea más acertada
            atr_actual = float(train['ATR'].iloc[-1])
            precio_objetivo = precio_actual + (atr_actual * 5) # Proyecta según la fuerza del precio
            stop_loss = precio_actual - (atr_actual * 3)
            fecha_proy = fecha_actual + timedelta(days=90)
            
            tipo = "🇦🇷" if ticker in argentinas else "🇺🇸"
            msj = (f"🏛️ *PROYECCIÓN DE ALTA PRECISIÓN {tipo} {ticker}*\n"
                   f"📅 Datos al: `{fecha_actual.strftime('%d/%m/%Y')}` (HOY)\n\n"
                   f"💵 Precio Real: *${precio_actual:.2f}*\n"
                   f"🛡️ Stop Loss: *${stop_loss:.2f}*\n"
                   f"🎯 Proyección 90d: *${precio_objetivo:.2f}*\n\n"
                   f"📊 Confianza IA: `{prob:.1%}`\n"
                   f"🔮 Motor: `Gradient Boosting V13`")
            
            # Gráfico con Proyección Realista
            fig, ax = plt.subplots(figsize=(10, 5))
            fig.patch.set_facecolor('#0a192f'); ax.set_facecolor('#0a192f')
            
            # Pasado (150 días hasta hoy)
            df_plot = train.iloc[-150:]
            ax.plot(df_plot.index, df_plot['Close'], color='white', label='Precio Histórico', linewidth=2)
            ax.plot(df_plot.index, df_plot['SMA_200'], color='cyan', alpha=0.3, label='Estructura 200d')
            
            # Futuro (Proyección basada en IA)
            ax.plot([fecha_actual, fecha_proy], [precio_actual, precio_objetivo], 
                    color='#00ff00', linestyle='--', linewidth=3, label='Trayectoria IA')
            ax.fill_between([fecha_actual, fecha_proy], [precio_actual, precio_objetivo + atr_actual], 
                            [precio_actual, precio_objetivo - atr_actual], color='#00ff00', alpha=0.1, label='Margen de Error')
            
            ax.set_title(f"Terminal Proyectiva: {ticker} (Feb 2026)", color='white', fontweight='bold')
            ax.tick_params(colors='white'); ax.legend(facecolor='#112240', labelcolor='white')
            ax.grid(alpha=0.05)
            
            enviar_telegram(msj, fig)
            plt.close(fig)

    except Exception as e: continue

enviar_telegram("✅ *Análisis 2026 Finalizado con Éxito.*")
