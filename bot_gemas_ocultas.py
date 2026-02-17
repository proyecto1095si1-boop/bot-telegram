import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import requests
import io
import warnings
import time
import gc
from datetime import datetime

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

# --- UNIVERSO DEL SCREENER (Top 80 Wall Street) ---
# Mezcla de SP500, Nasdaq y sectores defensivos
universo_screener = [
    'AAPL', 'MSFT', 'NVDA', 'AMZN', 'GOOGL', 'META', 'TSLA', 'BRK-B', 'LLY', 'AVGO',
    'V', 'JPM', 'UNH', 'MA', 'JNJ', 'XOM', 'HD', 'PG', 'COST', 'MRK',
    'ABBV', 'CVX', 'CRM', 'AMD', 'NFLX', 'PEP', 'KO', 'ADBE', 'WMT', 'TMO',
    'MCD', 'CSCO', 'INTC', 'DIS', 'INTU', 'AMGN', 'VZ', 'CAT', 'IBM', 'PFE',
    'NOW', 'UBER', 'GE', 'BA', 'QCOM', 'TXN', 'HON', 'COP', 'UNP', 'AXP',
    'NKE', 'GS', 'SPGI', 'RTX', 'LMT', 'BLK', 'SYK', 'MDT', 'C', 'PLD',
    'ISRG', 'T', 'MDLZ', 'CVS', 'GILD', 'REGN', 'VRTX', 'ADI', 'SLB', 'MO',
    'ZTS', 'SO', 'BDX', 'BSX', 'TJX', 'MMC', 'CME', 'DUK', 'SNPS', 'KLAC'
]

def escanear_gema(ticker):
    try:
        t = yf.Ticker(ticker)
        # Descargamos 1 año para tener la SMA 200 bien calculada
        df = t.history(period="1y", interval="1d", timeout=5)
        if df.empty or len(df) < 200: return None
        
        # Indicadores Básicos
        df['SMA_50'] = df['Close'].rolling(50).mean()
        df['SMA_200'] = df['Close'].rolling(200).mean()
        
        # RSI 14
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        df['RSI'] = 100 - (100 / (1 + (gain/loss)))
        
        # Volumen Relativo
        df['Vol_Mean_20'] = df['Volume'].rolling(20).mean()
        
        # Extraer últimos valores
        precio_act = float(df['Close'].iloc[-1])
        sma200_act = float(df['SMA_200'].iloc[-1])
        rsi_act = float(df['RSI'].iloc[-1])
        vol_act = float(df['Volume'].iloc[-1])
        vol_prom = float(df['Vol_Mean_20'].iloc[-1])
        
        # --- EL FILTRO DE LA TORMENTA PERFECTA ---
        # 1. Tendencia alcista a largo plazo (Precio > SMA 200)
        # 2. Sobrevendida en el corto plazo (RSI < 35)
        # 3. Interés Institucional (Volumen > 1.5x del promedio)
        
        if (precio_act > sma200_act) and (rsi_act < 35.0) and (vol_act > (vol_prom * 1.5)):
            return df, {'precio': precio_act, 'rsi': rsi_act, 'vol_ratio': vol_act / vol_prom}
            
    except Exception as e:
        pass
    
    return None

hoy_str = datetime.now().strftime('%d/%m/%Y')
enviar_telegram(f"💎 *MARKET SCREENER V1.0* | {hoy_str}\n_Escaneando 80 empresas líderes en busca de gemas ocultas (Pullback Institucional)..._")

gemas_encontradas = 0

for ticker in universo_screener:
    time.sleep(0.5) # Pausa cortita para no estresar a Yahoo
    resultado = escanear_gema(ticker)
    
    if resultado is not None:
        gemas_encontradas += 1
        df, data = resultado
        
        msj = (f"🚨 *GEMA ENCONTRADA: {ticker}*\n"
               f"Patrón: *Pullback Institucional* 📉📈\n\n"
               f"💰 Spot: `${data['precio']:.2f}`\n"
               f"📊 RSI: `{data['rsi']:.1f}` *(Sobrevendida)*\n"
               f"🌊 Volumen: `{data['vol_ratio']:.1f}x` mayor al promedio *(Smart Money)*\n\n"
               f"_Explicación: La acción está en tendencia alcista (arriba de SMA 200), pero acaba de sufrir una caída brusca y los grandes fondos están comprando el pánico._")

        # --- GRÁFICO TÁCTICO DE COMPRA ---
        plt.style.use('dark_background')
        fig = plt.figure(figsize=(11, 7))
        fig.patch.set_facecolor('#0b0f19')
        gs = gridspec.GridSpec(2, 1, height_ratios=[3, 1], hspace=0.1)
        
        ax1 = fig.add_subplot(gs[0])
        ax1.set_facecolor('#0b0f19')
        df_plot = df.iloc[-100:] # Vemos los últimos 4 meses
        
        # Dibujar precios y medias
        ax1.plot(df_plot.index, df_plot['Close'], color='#22d3ee', linewidth=2, label='Precio')
        ax1.plot(df_plot.index, df_plot['SMA_50'], color='#eab308', linestyle='--', alpha=0.8, label='SMA 50')
        ax1.plot(df_plot.index, df_plot['SMA_200'], color='#ec4899', linewidth=2, alpha=0.8, label='SMA 200 (Soporte Mayor)')
        
        # Resaltar la última vela donde se detectó la gema
        ax1.scatter(df_plot.index[-1], df_plot['Close'].iloc[-1], color='#4ade80', s=200, marker='^', zorder=5, label='Punto de Entrada')
        
        ax1.set_title(f"Radar de Gemas: {ticker} (Setup de Compra)", color='white', loc='left', fontsize=12, fontweight='bold')
        ax1.legend(loc='upper left', fontsize='small', framealpha=0.2)
        ax1.grid(color='#1e293b', alpha=0.4, linestyle=':')
        ax1.tick_params(labelbottom=False) 
        
        # Panel Inferior: RSI destacando la sobreventa
        ax2 = fig.add_subplot(gs[1])
        ax2.set_facecolor('#0b0f19')
        ax2.plot(df_plot.index, df_plot['RSI'], color='#c084fc', linewidth=1.5)
        ax2.axhline(35, color='#22c55e', linestyle='--', alpha=0.8, label='Zona de Compra') 
        ax2.fill_between(df_plot.index, df_plot['RSI'], 35, where=(df_plot['RSI'] <= 35), color='#22c55e', alpha=0.4)
        
        ax2.set_ylabel('RSI (14)', color='gray', fontsize=9)
        ax2.grid(color='#1e293b', alpha=0.4, linestyle=':')
        ax2.tick_params(axis='x', rotation=45, colors='gray')
        ax2.tick_params(axis='y', colors='gray')
        
        ax1.spines['top'].set_visible(False); ax1.spines['right'].set_visible(False)
        ax2.spines['top'].set_visible(False); ax2.spines['right'].set_visible(False)
        
        enviar_telegram(msj, fig)

if gemas_encontradas == 0:
    enviar_telegram("✅ *ESCANEO COMPLETADO*\nSe analizaron 80 acciones. No se detectaron setups de Tormenta Perfecta hoy. Mantenemos la liquidez. 💵")
else:
    enviar_telegram(f"🎯 *ESCANEO COMPLETADO*\nSe encontraron {gemas_encontradas} oportunidades de entrada institucional.")
