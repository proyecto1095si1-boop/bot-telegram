import yfinance as yf
import pandas as pd
import numpy as np
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.patches as patches
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

# --- UNIVERSO INTRADÍA (Alta Liquidez) ---
activos_sniper = {
    '🚀 TECH USA': ['AAPL', 'NVDA', 'TSLA', 'AMD', 'META'],
    '🇦🇷 ADRs ARG': ['GGAL', 'YPF', 'PAM', 'BMA'],
    '🌍 ÍNDICES': ['SPY', 'QQQ', 'IWM']
}

def motor_sniper_smc(ticker):
    df = pd.DataFrame()
    for intento in range(3):
        try:
            t = yf.Ticker(ticker)
            df = t.history(period="5d", interval="15m", timeout=10)
            if not df.empty and len(df) > 50: break
        except: time.sleep(2)
    
    if df.empty or len(df) < 50: return None
    
    # --- INDICADORES BÁSICOS ---
    df['EMA_9'] = df['Close'].ewm(span=9, adjust=False).mean()
    df['EMA_21'] = df['Close'].ewm(span=21, adjust=False).mean()
    
    df['Date'] = df.index.date
    df['Typical_Price'] = (df['High'] + df['Low'] + df['Close']) / 3
    df['VWAP'] = (df['Typical_Price'] * df['Volume']).groupby(df['Date']).cumsum() / df['Volume'].groupby(df['Date']).cumsum()
    
    # --- SMART MONEY CONCEPTS (SMC) ---
    # 1. Identificar Order Blocks (Últimos 40 periodos)
    df_reciente = df.iloc[-40:]
    max_idx = df_reciente['High'].idxmax()
    min_idx = df_reciente['Low'].idxmin()
    
    # Supply Zone (Bloque de Órdenes Bajista)
    supply_top = df_reciente.loc[max_idx, 'High']
    supply_bot = min(df_reciente.loc[max_idx, 'Open'], df_reciente.loc[max_idx, 'Close'])
    
    # Demand Zone (Bloque de Órdenes Alcista)
    demand_bot = df_reciente.loc[min_idx, 'Low']
    demand_top = max(df_reciente.loc[min_idx, 'Open'], df_reciente.loc[min_idx, 'Close'])
    
    # 2. Identificar Imbalances / FVG (Fair Value Gaps) en las últimas 15 velas
    fvg_bullish = None
    fvg_bearish = None
    
    for i in range(len(df)-15, len(df)-2):
        # Bullish FVG (Hueco alcista)
        if df['Low'].iloc[i+2] > df['High'].iloc[i]:
            fvg_bullish = (df['High'].iloc[i], df['Low'].iloc[i+2])
        # Bearish FVG (Hueco bajista)
        if df['High'].iloc[i+2] < df['Low'].iloc[i]:
            fvg_bearish = (df['Low'].iloc[i], df['High'].iloc[i+2])

    precio_act = float(df['Close'].iloc[-1])
    vwap_act = float(df['VWAP'].iloc[-1])
    
    # Lógica de Trading SMC
    estado = "ESPERANDO ZONA ⚪"
    accion = "OBSERVAR 👀"
    
    # Si el precio toca la zona de demanda (bancos comprando)
    if demand_bot <= precio_act <= (demand_top * 1.005):
        estado = "EN ZONA DE DEMANDA (ORDER BLOCK) 🟢"
        accion = "LONG (COMPRAR) 🚀"
        stop_loss = demand_bot * 0.995
        take_profit = supply_bot
    # Si el precio toca la zona de oferta (bancos vendiendo)
    elif (supply_bot * 0.995) <= precio_act <= supply_top:
        estado = "EN ZONA DE OFERTA (ORDER BLOCK) 🔴"
        accion = "SHORT (VENDER) 🩸"
        stop_loss = supply_top * 1.005
        take_profit = demand_top
    else:
        # Neutro
        stop_loss = precio_act * 0.99
        take_profit = precio_act * 1.01

    return df, {
        'precio': precio_act, 'vwap': vwap_act, 'accion': accion, 'estado': estado,
        'sl': stop_loss, 'tp': take_profit, 
        'supply': (supply_bot, supply_top), 'demand': (demand_bot, demand_top),
        'fvg_bull': fvg_bullish, 'fvg_bear': fvg_bearish
    }

hoy_str = datetime.now().strftime('%d/%m/%Y %H:%M')
enviar_telegram(f"🧠 *SNIPER SMC V2.0*\nBuscando Liquidez Institucional (15m) | {hoy_str}\n_Rastreando Order Blocks y Fair Value Gaps..._")

for sector, activos in activos_sniper.items():
    for ticker in activos:
        try:
            time.sleep(random.uniform(1.0, 2.0)) 
            res = motor_sniper_smc(ticker)
            if not res: continue
            df, data = res
            
            # Solo alertar si hay acción real (para no saturar Telegram de "Observar")
            if data['accion'] == "OBSERVAR 👀":
                continue
            
            p = data['precio']
            
            msj = (f"🎯 *{ticker}* | SETUP INSTITUCIONAL (15m)\n"
                   f"🚦 Señal: *{data['accion']}*\n"
                   f"🏦 Estado: `{data['estado']}`\n\n"
                   f"💰 Spot: *${p:.2f}* | VWAP: `${data['vwap']:.2f}`\n\n"
                   f"🛡️ *PARÁMETROS SMC:*\n"
                   f"• Target Liquidez (TP): `${data['tp']:.2f}`\n"
                   f"• Invalidación (SL): `${data['sl']:.2f}`")

            # --- GRÁFICO SMC ---
            plt.style.use('dark_background')
            fig = plt.figure(figsize=(11, 7))
            fig.patch.set_facecolor('#0b0f19')
            gs = gridspec.GridSpec(2, 1, height_ratios=[3, 1], hspace=0.1)
            
            ax1 = fig.add_subplot(gs[0])
            ax1.set_facecolor('#0b0f19')
            
            df_plot = df.iloc[-60:] 
            
            # Líneas base
            ax1.plot(df_plot.index, df_plot['Close'], color='#e2e8f0', linewidth=2, label='Precio')
            ax1.plot(df_plot.index, df_plot['VWAP'], color='#eab308', linestyle='-.', linewidth=1.5, alpha=0.8, label='VWAP')
            
            # DIBUJAR ORDER BLOCKS (Cajas Transparentes)
            sup_bot, sup_top = data['supply']
            dem_bot, dem_top = data['demand']
            
            ax1.axhspan(sup_bot, sup_top, color='#ef4444', alpha=0.2, label='Supply (Order Block Bajista)')
            ax1.axhspan(dem_bot, dem_top, color='#22c55e', alpha=0.2, label='Demand (Order Block Alcista)')
            
            # DIBUJAR IMBALANCES (FVG)
            if data['fvg_bull']:
                ax1.axhspan(data['fvg_bull'][0], data['fvg_bull'][1], color='#3b82f6', alpha=0.15, hatch='//', label='FVG Alcista (Imán)')
            if data['fvg_bear']:
                ax1.axhspan(data['fvg_bear'][0], data['fvg_bear'][1], color='#f97316', alpha=0.15, hatch='\\\\', label='FVG Bajista (Imán)')
            
            ax1.set_title(f"SMC Sniper: {ticker} | Zonas de Alta Probabilidad", color='white', loc='left', fontsize=12, fontweight='bold')
            ax1.legend(loc='upper left', fontsize='x-small', framealpha=0.2)
            ax1.grid(color='#1e293b', alpha=0.4, linestyle=':')
            ax1.tick_params(labelbottom=False) 
            
            # Panel Volumen
            ax2 = fig.add_subplot(gs[1])
            ax2.set_facecolor('#0b0f19')
            
            colores_vol = ['#4ade80' if c >= o else '#ef4444' for c, o in zip(df_plot['Close'], df_plot['Open'])]
            ax2.bar(df_plot.index, df_plot['Volume'], color=colores_vol, alpha=0.6, width=0.01)
            
            ax2.set_ylabel('Volumen', color='gray', fontsize=9)
            ax2.grid(color='#1e293b', alpha=0.4, linestyle=':')
            ax2.tick_params(axis='x', rotation=45, colors='gray')
            ax2.tick_params(axis='y', colors='gray')
            
            ax1.spines['top'].set_visible(False); ax1.spines['right'].set_visible(False)
            ax2.spines['top'].set_visible(False); ax2.spines['right'].set_visible(False)
            
            enviar_telegram(msj, fig)
            
        except Exception as e:
            continue

enviar_telegram("🛑 *RADAR SMC FINALIZADO*")
