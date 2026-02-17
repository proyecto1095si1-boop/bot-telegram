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

# --- UNIVERSO MAESTRO LOCAL ---
# Ahora la sección Argentina mira EXCLUSIVAMENTE la Bolsa de Buenos Aires en PESOS (.BA)
mercados = {
    '🇦🇷 MERVAL (ARS)': ['YPFD.BA', 'GGAL.BA', 'BMA.BA', 'PAMP.BA', 'CEPU.BA', 'TGSU2.BA', 'ALUA.BA', 'TXAR.BA', 'EDN.BA', 'LOMA.BA', 'BBAR.BA', 'SUPV.BA', 'CRES.BA', 'TGNO4.BA', 'COME.BA'],
    '🇺🇸 USA (USD)': ['AAPL', 'MSFT', 'NVDA', 'AMZN', 'GOOGL', 'META', 'TSLA', 'JPM', 'V', 'XOM', 'WMT', 'LLY', 'AVGO', 'PYPL', 'MELI'],
    '🇬🇧 UK (GBP)': ['SHEL.L', 'BP.L', 'HSBA.L', 'AZN.L', 'GSK.L', 'ULVR.L', 'RIO.L', 'BARC.L', 'VOD.L', 'REL.L', 'RR.L', 'LLOY.L', 'AAL.L', 'DGE.L', 'BA.L']
}

def motor_fibonacci_ia(ticker):
    df = pd.DataFrame()
    for intento in range(3):
        try:
            t = yf.Ticker(ticker)
            df = t.history(period="3y", interval="1d", timeout=10)
            if not df.empty and len(df) > 200: break
        except: time.sleep(2)
    
    if df.empty or len(df) < 200: return None
    
    # Indicadores
    df['SMA_50'] = df['Close'].rolling(50).mean()
    df['SMA_200'] = df['Close'].rolling(200).mean()
    
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    df['RSI'] = 100 - (100 / (1 + (gain/loss)))
    
    ema12 = df['Close'].ewm(span=12, adjust=False).mean()
    ema26 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = ema12 - ema26
    
    df['STD'] = df['Close'].rolling(20).std()
    df['BB_Upper'] = df['SMA_50'] + (df['STD'] * 2)
    df['BB_Lower'] = df['SMA_50'] - (df['STD'] * 2)
    
    # --- IA: PREDICCIÓN DE RETORNOS ---
    dias_proy = 60
    df['Target_Ret'] = (df['Close'].shift(-dias_proy) / df['Close']) - 1.0
    train = df.dropna()
    
    features = ['Close', 'SMA_50', 'SMA_200', 'RSI', 'MACD']
    scaler = StandardScaler()
    
    # Si por algún motivo no hay suficientes datos limpios, ignoramos
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
    
    soporte_200 = float(df['SMA_200'].iloc[-1])
    if pred_ia_cruda < precio_act and precio_act > soporte_200:
        pred_ia = max(pred_ia_cruda, soporte_200 * 0.95)
    else:
        pred_ia = pred_ia_cruda

    try:
        info = t.info
        rec = str(info.get('recommendationKey', 'HOLD')).upper()
        pe_ratio = info.get('forwardPE', 'N/A')
    except:
        rec = "N/A"
        pe_ratio = "N/A"

    return df, {'pred': float(pred_ia), 'rec': rec, 'pe': pe_ratio, 'precio': precio_act, 'std': float(df['STD'].iloc[-1])}

hoy_str = datetime.now().strftime('%d/%m/%Y')
enviar_telegram(f"✨ *TERMINAL ESTRUCTURAL V30.1*\nAuditando con Motor de Retornos y Fibonacci | {hoy_str}\n_Sincronizando Merval Local (ARS)..._")

for region, activos in mercados.items():
    bandera_nombre = region.split()[0] + " " + region.split()[1] # Ej: 🇦🇷 MERVAL
    moneda = region.split('(')[1].replace(')', '') # Extrae ARS, USD, GBP
    
    enviar_telegram(f"📁 *ANALIZANDO: {region}*")
    
    for ticker in activos:
        try:
            time.sleep(random.uniform(1.5, 3.5)) 
            res = motor_fibonacci_ia(ticker)
            if not res: continue
            df, data = res
            
            p = data['precio']
            diff = ((data['pred'] / p) - 1) * 100
            emoji = "🟢" if diff > 0 else "🔴"
            
            valor_pe = data['pe']
            if isinstance(valor_pe, (int, float)): pe_formateado = str(round(valor_pe, 1))
            else: pe_formateado = str(valor_pe)
                
            valor_rsi = float(df['RSI'].iloc[-1])
            rsi_formateado = str(round(valor_rsi, 1))
            
            msj = (f"{bandera_nombre} *{ticker}* | `{data['rec']}`\n"
                   f"💰 Spot: *${p:,.2f} {moneda}* | P/E: `{pe_formateado}`\n"
                   f"🧠 IA Target Q2: *${data['pred']:,.2f} {moneda}* ({diff:+.2f}% {emoji})\n"
                   f"📊 RSI: `{rsi_formateado}` | Riesgo: `±{data['std']:.2f}`")

            # GRÁFICO CON FIBONACCI
            plt.style.use('dark_background')
            fig = plt.figure(figsize=(11, 7))
            fig.patch.set_facecolor('#0b0f19')
            gs = gridspec.GridSpec(2, 1, height_ratios=[3, 1], hspace=0.1)
            
            ax1 = fig.add_subplot(gs[0])
            ax1.set_facecolor('#0b0f19')
            df_plot = df.iloc[-150:] 
            
            ax1.plot(df_plot.index, df_plot['Close'], color='#22d3ee', linewidth=2, label='Cotización')
            ax1.fill_between(df_plot.index, df_plot['BB_Lower'], df_plot['BB_Upper'], color='#38bdf8', alpha=0.05)
            ax1.plot(df_plot.index, df_plot['SMA_200'], color='#f472b6', linestyle='--', alpha=0.6, label='SMA 200 (Tendencia)')
            
            # --- DIBUJAR FIBONACCI ---
            max_price = df_plot['Close'].max()
            min_price = df_plot['Close'].min()
            diferencia = max_price - min_price
            fib_618 = max_price - (diferencia * 0.618)
            fib_382 = max_price - (diferencia * 0.382)
            
            ax1.axhline(fib_618, color='#eab308', linestyle=':', alpha=0.7, label='Fib 61.8% (Soporte Fuerte)')
            ax1.axhline(fib_382, color='#fb923c', linestyle=':', alpha=0.5, label='Fib 38.2%')
            
            fecha_futura = df.index[-1] + timedelta(days=60)
            ax1.plot([df.index[-1], fecha_futura], [p, data['pred']], color='#4ade80' if diff > 0 else '#ef4444', linestyle='--', linewidth=2.5, marker='o', markersize=6, label='Ruta IA')
            
            margen_error = data['std'] * 1.5
            color_cono = '#4ade80' if diff > 0 else '#ef4444'
            ax1.fill_between([df.index[-1], fecha_futura], [p, data['pred'] + margen_error], [p, data['pred'] - margen_error], color=color_cono, alpha=0.15)
            
            ax1.set_title(f"Terminal V30.1: {ticker} | Zonas Fibonacci | Moneda: {moneda}", color='white', loc='left', fontsize=12, fontweight='bold')
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

enviar_telegram("✅ *AUDITORÍA FIBONACCI LOCAL FINALIZADA*")
