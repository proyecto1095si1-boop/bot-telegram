import yfinance as yf
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
import matplotlib.pyplot as plt
import requests
import io
import warnings

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

# --- UNIVERSO MASIVO (ARG + USA) ---
argentinas = [
    'YPF', 'GGAL', 'BMA', 'PAM', 'VIST', 'TGS', 'CEPU', 'CRESY', 'LOMA', 'TEO', 
    'EDN', 'BBAR', 'SUPV', 'TXAR.BA', 'ALUA.BA', 'TGNO4.BA', 'TRAN.BA', 'COME.BA', 
    'BYMA.BA', 'VALO.BA', 'MIRG.BA', 'AGRO.BA', 'LEDE.BA', 'MORI.BA', 'CGPA2.BA'
]

# Top 80 del S&P 500 (Tecnología, Bancos, Consumo, Energía)
usa = [
    'AAPL', 'MSFT', 'AMZN', 'NVDA', 'GOOGL', 'META', 'TSLA', 'BRK-B', 'JPM', 'UNH',
    'V', 'JNJ', 'XOM', 'WMT', 'MA', 'AVGO', 'PG', 'ORCL', 'ADBE', 'ASML', 'COST',
    'CVX', 'HD', 'LLY', 'BAC', 'PEP', 'KO', 'ABBV', 'MRK', 'AVGO', 'CRM', 'ACN',
    'AMD', 'NFLX', 'LIN', 'TMO', 'DIS', 'WFC', 'INTU', 'DHR', 'INTC', 'VZ', 'CAT',
    'AMAT', 'PFE', 'CMCSA', 'IBM', 'NOW', 'UNP', 'TXN', 'GE', 'QCOM', 'PM', 'LOW',
    'ISRG', 'HON', 'AMGN', 'COP', 'SPGI', 'AXP', 'NKE', 'GS', 'PLTR', 'BABA', 'PYPL',
    'SQ', 'UBER', 'SNOW', 'SHOP', 'MELI', 'T', 'X', 'F', 'GM', 'XLF', 'XLK', 'GDX'
]

universo = argentinas + usa

enviar_telegram(f"🏦 *TERMINAL DE INVERSIÓN GLOBAL*\nEscaneando {len(universo)} activos en Argentina y USA...")

encontrados = 0
for ticker in universo:
    try:
        data = yf.download(ticker, period="3y", progress=False)
        if data.empty or len(data) < 250: continue
        if isinstance(data.columns, pd.MultiIndex): data.columns = data.columns.get_level_values(0)
        
        df = preparar_datos(data)
        
        # IA entrenada para detectar retornos de +10% en 3 meses (60 días hábiles)
        df['Ret_60'] = (df['Close'].shift(-60) - df['Close']) / df['Close']
        df['Target'] = np.where(df['Ret_60'] > 0.10, 1, 0)
        
        train = df.dropna()
        if len(train) < 100: continue
        
        features = ['Close', 'SMA_50', 'SMA_200', 'RSI']
        model = RandomForestClassifier(n_estimators=70, random_state=42)
        model.fit(train[features].iloc[:-60], train['Target'].iloc[:-60])
        
        prob = model.predict_proba(train[features].iloc[-1:]) [0][1]
        actual = train.iloc[-1]
        
        # FILTRO DE COMPRA (IA > 55% y sin sobrecompra extrema)
        if prob > 0.55 and actual['RSI'] < 70:
            encontrados += 1
            stop = actual['Close'] - (actual['ATR'] * 4) # Stop amplio para inversión
            target = actual['Close'] * 1.25 # Objetivo 25% de suba
            
            tipo = "🇦🇷 ARG" if ticker in argentinas else "🇺🇸 USA/INT"
            msj = (f"🏛️ *SEÑAL ESTRUCTURAL ({tipo}): {ticker}*\n"
                   f"Horizonte: `2 a 3 Meses`\n\n"
                   f"💵 Entrada: *${actual['Close']:.2f}*\n"
                   f"🛡️ Stop Sugerido: *${stop:.2f}*\n"
                   f"🎯 Objetivo Largo: *${target:.2f}*\n\n"
                   f"📊 Confianza Motor IA: `{prob:.1%}`\n"
                   f"📌 Estado: `Tendencia de Fondo en Desarrollo`")
            
            fig, ax = plt.subplots(figsize=(10, 5))
            fig.patch.set_facecolor('#0a192f'); ax.set_facecolor('#0a192f')
            ax.plot(train.index[-250:], train['Close'].iloc[-250:], color='white', label='Precio', linewidth=1.5)
            ax.plot(train.index[-250:], train['SMA_200'].iloc[-250:], color='#FF00FF', label='SMA 200', linewidth=2)
            ax.set_title(f"Planificación 90 días: {ticker}", color='white', fontweight='bold')
            ax.tick_params(colors='white'); ax.legend(facecolor='#112240', labelcolor='white')
            ax.grid(alpha=0.2)
            
            enviar_telegram(msj, fig)
            plt.close(fig)

    except: continue

if encontrados == 0:
    enviar_telegram("🛡️ *Reporte Final:* No se hallaron activos con ventaja estadística clara hoy. El sistema prioriza la preservación de capital.")
else:
    enviar_telegram(f"✅ *Análisis Completo:* Se detectaron {encontrados} oportunidades estructurales para tu portafolio.")

# COPIA ESTO PARA PROBAR SI EL BOT ESTÁ VIVO
import yfinance as yf
import requests

TOKEN = '8173318113:AAFK_OM25CfTAmrmhR1pzwpvcQJWmWzbZg0'
CHAT_ID = '6550986355'

def enviar(msg):
    requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", data={'chat_id': CHAT_ID, 'text': msg})

enviar("🛰️ MODO TEST: El bot está vivo. Escaneando Argentina...")

# Probamos con las 3 más activas
for t in ['YPF', 'GGAL', 'AAPL']:
    data = yf.download(t, period="1mo", progress=False)
    precio = data['Close'].iloc[-1]
    enviar(f"✅ Conexión con {t} exitosa. Precio: ${precio:.2f}")

enviar("Fin de la prueba de conexión.")
