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

# --- 1. CREDENCIALES DE TELEGRAM ---
TOKEN = '8173318113:AAFK_OM25CfTAmrmhR1pzwpvcQJWmWzbZg0'
CHAT_ID = '6550986355'

def enviar_telegram(mensaje, fig=None):
    """Envía texto y opcionalmente un gráfico generado en memoria a Telegram."""
    try:
        # Enviar texto
        url_texto = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.post(url_texto, data={'chat_id': CHAT_ID, 'text': mensaje, 'parse_mode': 'Markdown'})
        
        # Enviar imagen sin guardarla en el disco duro
        if fig is not None:
            buf = io.BytesIO()
            fig.savefig(buf, format='png', bbox_inches='tight', dpi=150, facecolor='#111111')
            buf.seek(0)
            url_foto = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
            requests.post(url_foto, data={'chat_id': CHAT_ID}, files={'photo': buf})
            buf.close()
    except Exception as e:
        print(f"\n[!] Error enviando a Telegram: {e}")

# --- 2. UNIVERSO DE ACTIVOS ---
print("Inicializando Escáner Autónomo... Conectando a @Nahuelsi_bot...")
argentinas = ['YPF', 'GGAL', 'BMA', 'PAM', 'VIST', 'TGS', 'CEPU', 'CRESY', 'LOMA', 'TEO', 
              'EDN', 'IRS', 'SUPV', 'BBAR', 'TXAR.BA', 'ALUA.BA', 'TGNO4.BA', 'TRAN.BA', 
              'PAMP.BA', 'COME.BA', 'BYMA.BA', 'VALO.BA', 'MIRG.BA', 'CVH.BA', 'AGRO.BA']

url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
headers = {'User-Agent': 'Mozilla/5.0'}
try:
    tabla = pd.read_html(url, storage_options=headers)[0]
    tickers_sp500 = [t.replace('.', '-') for t in tabla['Symbol'].tolist()]
except:
    tickers_sp500 = ['AAPL', 'MSFT', 'AMZN', 'NVDA', 'GOOGL', 'META', 'TSLA', 'BRK-B', 'JPM']

universo = argentinas + tickers_sp500[:75]
print(f"Universo consolidado: {len(universo)} activos.\n")

# --- 3. FUNCIONES DEL MOTOR (SWING TRADING V8) ---
def preparar_datos(df):
    df = df.copy()
    df['SMA_20'] = df['Close'].rolling(20).mean()
    df['SMA_50'] = df['Close'].rolling(50).mean()
    df['Std_Dev'] = df['Close'].rolling(20).std()
    df['Bollinger_Upper'] = df['SMA_20'] + (df['Std_Dev'] * 2)
    df['Bollinger_Lower'] = df['SMA_20'] - (df['Std_Dev'] * 2)
    df['Vol_SMA_20'] = df['Volume'].rolling(20).mean()
    
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    df['TR'] = df[['High', 'Low', 'Close']].apply(lambda x: max(x['High'] - x['Low'], abs(x['High'] - x['Close']), abs(x['Low'] - x['Close'])), axis=1)
    df['ATR'] = df['TR'].rolling(14).mean()
    df['Var_5D'] = df['Close'].pct_change(5)
    return df.dropna()

def generar_grafico_memoria(ticker, df_plot, stop_loss, take_profit, señal):
    """Crea el gráfico en memoria (sin mostrarlo en PC) para enviarlo a Telegram."""
    df_plot = df_plot.iloc[-100:].copy() 
    precio_actual = df_plot['Close'].iloc[-1]
    
    fig, ax = plt.subplots(figsize=(10, 5))
    fig.patch.set_facecolor('#111111')
    ax.set_facecolor('#111111')
    
    ax.plot(df_plot.index, df_plot['Close'], label='Precio', color='white', linewidth=2)
    ax.plot(df_plot.index, df_plot['SMA_50'], label='SMA 50', color='#00FFFF', linestyle='--', alpha=0.8)
    ax.fill_between(df_plot.index, df_plot['Bollinger_Lower'], df_plot['Bollinger_Upper'], color='#FF00FF', alpha=0.1)
    
    ax.axhline(precio_actual, color='#FFA500', linestyle='-', linewidth=2, label=f'Entrada: ${precio_actual:.2f}')
    ax.axhline(stop_loss, color='#FF3333', linestyle='-', linewidth=2, label=f'Stop Loss: ${stop_loss:.2f}')
    ax.axhline(take_profit, color='#33FF33', linestyle='-', linewidth=2, label=f'Take Profit: ${take_profit:.2f}')
    
    ax.set_title(f'{ticker} | {señal}', color='white', fontsize=14, fontweight='bold')
    ax.tick_params(colors='white')
    ax.legend(loc='upper left', facecolor='#222222', edgecolor='white', labelcolor='white')
    ax.grid(color='gray', linestyle=':', alpha=0.3)
    
    plt.close(fig) # Cerramos la figura en la PC para no consumir RAM infinita
    return fig

# --- 4. EJECUCIÓN DEL ESCÁNER ---
enviar_telegram("🤖 *Escáner Cuantitativo Iniciado*\nAnalizando el mercado...")
resultados = []
activos_procesados = 0

for ticker in universo:
    activos_procesados += 1
    sys.stdout.write(f"\rAnalizando terminal... [{activos_procesados}/{len(universo)}]: {ticker}    ")
    sys.stdout.flush()
    
    try:
        data = yf.download(ticker, period="2y", progress=False)
        if isinstance(data.columns, pd.MultiIndex): data.columns = data.columns.get_level_values(0)
        if data.empty or 'Close' not in data.columns or len(data) < 200: continue
            
        for col in ['Open', 'High', 'Low', 'Close', 'Volume']: data[col] = data[col].squeeze()
            
        data = preparar_datos(data)
        
        data['Retorno_Futuro'] = (data['Close'].shift(-5) - data['Close']) / data['Close']
        data['Target'] = np.where(data['Retorno_Futuro'] > 0.02, 1, 0)
        data = data.dropna()
        
        features = ['Close', 'Volume', 'SMA_20', 'RSI', 'Bollinger_Lower', 'Vol_SMA_20', 'ATR']
        X = data[features]
        y = data['Target']
        if len(X) < 100: continue
            
        model = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42)
        model.fit(X.iloc[:int(len(X)*0.8)], y.iloc[:int(len(y)*0.8)])
        
        importancias = model.feature_importances_
        driver_principal = features[np.argmax(importancias)]
        
        ultima_fila = X.iloc[-1:]
        precio_actual, rsi_actual, bollinger_inf = float(ultima_fila['Close'].iloc[0]), float(ultima_fila['RSI'].iloc[0]), float(ultima_fila['Bollinger_Lower'].iloc[0])
        volumen_actual, volumen_medio = float(ultima_fila['Volume'].iloc[0]), float(ultima_fila['Vol_SMA_20'].iloc[0])
        sma_50, atr = float(data['SMA_50'].iloc[-1]), float(data['ATR'].iloc[-1])
        prob_suba = model.predict_proba(ultima_fila)[0][1]
        
        señal, stop_loss, take_profit = 'NEUTRAL', 0.0, 0.0
        
        if rsi_actual < 30 and precio_actual < bollinger_inf and volumen_actual > (volumen_medio * 1.5):
            señal, stop_loss, take_profit = 'COMPRA POR REBOTE', precio_actual - (atr * 1.5), precio_actual + (atr * 4)
        elif prob_suba > 0.65 and rsi_actual < 65 and precio_actual > sma_50:
            señal, stop_loss, take_profit = 'COMPRA DE TENDENCIA', precio_actual - (atr * 2), precio_actual + (atr * 4)
            
        if 'COMPRA' in señal:
            mensaje = (
                f"🚨 *ALERTA TÁCTICA: {ticker}*\n"
                f"Estrategia: `{señal}`\n\n"
                f"💵 Entrada: *${precio_actual:.2f}*\n"
                f"🛑 Stop Loss: *${stop_loss:.2f}*\n"
                f"🎯 Take Profit: *${take_profit:.2f}*\n\n"
                f"🧠 Motor IA: `{driver_principal}`"
            )
            # Generamos el gráfico invisible y lo mandamos
            figura = generar_grafico_memoria(ticker, data, stop_loss, take_profit, señal)
            enviar_telegram(mensaje, figura)
            resultados.append(ticker)
            
    except Exception as e: pass 

# --- 5. CIERRE DEL REPORTE ---
if len(resultados) == 0:
    enviar_telegram("🛡️ *Análisis Finalizado*\nNo se encontraron oportunidades con ventaja estadística hoy. Protegiendo capital. 💵")
    print("\n[!] Análisis finalizado sin señales. Reporte enviado a Telegram.")
else:
    enviar_telegram(f"✅ *Escaneo Terminado*\nSe enviaron {len(resultados)} alertas técnicas.")
    print(f"\n[+] Análisis finalizado. {len(resultados)} alertas enviadas a @Nahuelsi_bot.")
