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
# Usamos tu bot @Nahuelsi_bot
TOKEN = '8173318113:AAFK_OM25CfTAmrmhR1pzwpvcQJWmWzbZg0'
CHAT_ID = '6550986355'

def enviar_telegram(mensaje, fig=None):
    """Envía texto y gráfico estructural a Telegram."""
    try:
        url_texto = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.post(url_texto, data={'chat_id': CHAT_ID, 'text': mensaje, 'parse_mode': 'Markdown'})
        
        if fig is not None:
            buf = io.BytesIO()
            fig.savefig(buf, format='png', bbox_inches='tight', dpi=150, facecolor='#0a192f') # Azul muy oscuro para el bot macro
            buf.seek(0)
            url_foto = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
            requests.post(url_foto, data={'chat_id': CHAT_ID}, files={'photo': buf})
            buf.close()
    except Exception as e:
        pass

# --- 2. UNIVERSO DE ACTIVOS GLOBALES ---
print("Inicializando Radar Macro (1 Mes)... Conectando a @Nahuelsi_bot...")
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

# --- 3. FUNCIONES DEL MOTOR (POSITION TRADING 1 MES) ---
def preparar_datos_mensuales(df):
    df = df.copy()
    df['SMA_50'] = df['Close'].rolling(50).mean()
    df['SMA_200'] = df['Close'].rolling(200).mean() # EL RADAR MACRO
    df['Vol_SMA_21'] = df['Volume'].rolling(21).mean()
    
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(21).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(21).mean()
    rs = gain / loss
    df['RSI_Mensual'] = 100 - (100 / (1 + rs))
    
    df['TR'] = df[['High', 'Low', 'Close']].apply(lambda x: max(x['High'] - x['Low'], abs(x['High'] - x['Close']), abs(x['Low'] - x['Close'])), axis=1)
    df['ATR'] = df['TR'].rolling(21).mean()
    df['Var_1M_Pasado'] = df['Close'].pct_change(21)
    return df.dropna()

def generar_grafico_macro_memoria(ticker, df_plot, stop_loss, take_profit):
    """Crea el gráfico estructural en memoria para Telegram."""
    df_plot = df_plot.iloc[-250:].copy() # Mostramos casi 1 año para ver la SMA 200
    precio_actual = df_plot['Close'].iloc[-1]
    
    fig, ax = plt.subplots(figsize=(10, 5))
    fig.patch.set_facecolor('#0a192f')
    ax.set_facecolor('#0a192f')
    
    ax.plot(df_plot.index, df_plot['Close'], label='Precio', color='white', linewidth=1.5)
    ax.plot(df_plot.index, df_plot['SMA_50'], label='SMA 50', color='#00FFFF', linestyle='--', alpha=0.8)
    ax.plot(df_plot.index, df_plot['SMA_200'], label='SMA 200 (Macro)', color='#FF00FF', linewidth=2.5) # Línea magenta gruesa
    
    ax.axhline(precio_actual, color='#FFA500', linestyle='-', linewidth=2, label=f'Entrada: ${precio_actual:.2f}')
    ax.axhline(stop_loss, color='#FF3333', linestyle='-', linewidth=2, label=f'Stop Loss: ${stop_loss:.2f}')
    ax.axhline(take_profit, color='#33FF33', linestyle='-', linewidth=2, label=f'Take Profit: ${take_profit:.2f}')
    
    ax.set_title(f'Visión Estructural (1 Mes): {ticker}', color='white', fontsize=14, fontweight='bold')
    ax.tick_params(colors='white')
    ax.legend(loc='upper left', facecolor='#112240', edgecolor='white', labelcolor='white')
    ax.grid(color='gray', linestyle=':', alpha=0.3)
    
    plt.close(fig)
    return fig

# --- 4. EJECUCIÓN DEL ESCÁNER MACRO ---
enviar_telegram("🏛️ *Motor Estructural Iniciado*\nBuscando tendencias a 1 mes (Filtro SMA 200)...")
resultados = []
activos_procesados = 0

for ticker in universo:
    activos_procesados += 1
    sys.stdout.write(f"\rAnalizando macro... [{activos_procesados}/{len(universo)}]: {ticker}    ")
    sys.stdout.flush()
    
    try:
        data = yf.download(ticker, period="3y", progress=False)
        if isinstance(data.columns, pd.MultiIndex): data.columns = data.columns.get_level_values(0)
        if data.empty or 'Close' not in data.columns or len(data) < 300: continue
            
        for col in ['Open', 'High', 'Low', 'Close', 'Volume']: data[col] = data[col].squeeze()
            
        data = preparar_datos_mensuales(data)
        
        # TARGET 1 MES: 8% de retorno
        data['Retorno_Futuro_1M'] = (data['Close'].shift(-21) - data['Close']) / data['Close']
        data['Target'] = np.where(data['Retorno_Futuro_1M'] > 0.08, 1, 0)
        data = data.dropna()
        
        features = ['Close', 'Volume', 'SMA_50', 'SMA_200', 'RSI_Mensual', 'Vol_SMA_21', 'ATR']
        X = data[features]
        y = data['Target']
        if len(X) < 150: continue
            
        model = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42)
        model.fit(X.iloc[:int(len(X)*0.8)], y.iloc[:int(len(y)*0.8)])
        
        importancias = model.feature_importances_
        driver_principal = features[np.argmax(importancias)]
        
        ultima_fila = X.iloc[-1:]
        precio_actual = float(ultima_fila['Close'].iloc[0])
        sma_50 = float(data['SMA_50'].iloc[-1])
        sma_200 = float(data['SMA_200'].iloc[-1])
        atr = float(data['ATR'].iloc[-1])
        prob_suba = model.predict_proba(ultima_fila)[0][1]
        
        # FILTRO INSTITUCIONAL PARA PORTAFOLIO
        if prob_suba > 0.65 and precio_actual > sma_50 and precio_actual > sma_200:
            stop_loss = precio_actual - (atr * 3.5)  # Respiro amplio
            take_profit = precio_actual + (atr * 7.0) # Objetivo macro
            
            mensaje = (
                f"📈 *ALERTA ESTRUCTURAL: {ticker}*\n"
                f"Horizonte: `Portafolio (1 Mes)`\n\n"
                f"💵 Entrada: *${precio_actual:.2f}*\n"
                f"🛑 Stop Loss: *${stop_loss:.2f}*\n"
                f"🎯 Take Profit: *${take_profit:.2f}*\n\n"
                f"🛡️ Estado: `Sobre SMA 200`\n"
                f"🧠 Motor IA: `{driver_principal}`"
            )
            figura = generar_grafico_macro_memoria(ticker, data, stop_loss, take_profit)
            enviar_telegram(mensaje, figura)
            resultados.append(ticker)
            
    except Exception as e: pass 

# --- 5. CIERRE DEL REPORTE ---
if len(resultados) == 0:
    enviar_telegram("🛡️ *Análisis Estructural Finalizado*\nNinguna empresa superó el filtro de la SMA 200 con ventaja matemática mensual. Mantener liquidez.")
    print("\n[!] Análisis finalizado. El mercado no ofrece tendencias largas seguras hoy.")
else:
    enviar_telegram(f"✅ *Escaneo Terminado*\nSe enviaron {len(resultados)} alertas para el portafolio mensual.")
    print(f"\n[+] Análisis finalizado. {len(resultados)} alertas enviadas a @Nahuelsi_bot.")
