import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import requests
import io
import warnings
import time
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
            fig.savefig(buf, format='png', bbox_inches='tight', dpi=120, facecolor='#0b0f19')
            buf.seek(0)
            url_foto = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
            requests.post(url_foto, data={'chat_id': CHAT_ID}, files={'photo': buf})
            buf.close()
            plt.close('all') 
            gc.collect()     
    except Exception as e:
        print(f"Error Telegram: {e}")

# --- UNIVERSO DE MONITOREO DE BALANCES ---
# Aquí ponemos las empresas que más mueven el mercado
tickers_radar = [
    'AAPL', 'MSFT', 'NVDA', 'TSLA', 'AMZN', 'META', 'GOOGL', 'NFLX', 
    'JPM', 'V', 'WMT', 'XOM', 'MELI', 'GGAL', 'YPF', 'PAM', 'BMA'
]

def buscar_balances_proximos():
    hoy = datetime.now()
    limite_dias = hoy + timedelta(days=15) # Buscamos a 15 días vista
    
    alertas = []
    
    for ticker in tickers_radar:
        try:
            time.sleep(1) # Pausa para no saturar Yahoo
            t = yf.Ticker(ticker)
            
            # Obtener fechas de balances (Earnings Dates)
            fechas = t.get_earnings_dates(limit=3)
            if fechas is None or fechas.empty:
                continue
            
            # Limpiar zonas horarias para poder comparar con 'hoy'
            fechas.index = fechas.index.tz_localize(None)
            
            # Filtrar solo los balances que ocurren desde hoy hasta los próximos 15 días
            balances_futuros = fechas[(fechas.index >= hoy) & (fechas.index <= limite_dias)]
            
            if not balances_futuros.empty:
                fecha_balance = balances_futuros.index[0]
                eps_esperado = balances_futuros['EPS Estimate'].iloc[0]
                
                # Calcular volatilidad histórica para saber si es una acción "peligrosa" en los balances
                df_hist = t.history(period="6mo")
                volatilidad = "Desconocida"
                if not df_hist.empty:
                    vol_diaria = df_hist['Close'].pct_change().std() * 100
                    volatilidad = f"{vol_diaria:.1f}% diario"
                
                alertas.append({
                    'ticker': ticker,
                    'fecha': fecha_balance,
                    'eps': eps_esperado,
                    'volatilidad': volatilidad
                })
                
        except Exception as e:
            print(f"No se pudo obtener balance de {ticker}: {e}")
            continue
            
    return alertas

hoy_str = datetime.now().strftime('%d/%m/%Y')
enviar_telegram(f"📅 *RADAR DE BALANCES ACTIVADO* | {hoy_str}\n_Escaneando reportes trimestrales (Próximos 15 días)..._")

eventos = buscar_balances_proximos()

if not eventos:
    enviar_telegram("✅ *CALENDARIO DESPEJADO*\nNinguna de las empresas en el radar presenta balances en los próximos 15 días. Podés operar con tranquilidad.")
else:
    # Ordenar por fecha más próxima
    eventos.sort(key=lambda x: x['fecha'])
    
    for evento in eventos:
        tck = evento['ticker']
        fecha_obj = evento['fecha']
        dias_faltantes = (fecha_obj - datetime.now()).days
        
        # Formateo seguro para Python 3.10
        fecha_txt = fecha_obj.strftime('%d de %b, %Y')
        eps_val = evento['eps']
        
        if pd.isna(eps_val):
            eps_txt = "No revelado"
        else:
            eps_txt = f"${float(eps_val):.2f}"
            
        vol_txt = evento['volatilidad']
        
        mensaje = (f"⚠️ *ALERTA DE BALANCE: {tck}*\n"
                   f"Faltan *{dias_faltantes} días* para el reporte.\n"
                   f"🗓️ Fecha: `{fecha_txt}`\n"
                   f"🎯 EPS Esperado (Wall St): `{eps_txt}`\n"
                   f"📉 Riesgo/Volatilidad: `{vol_txt}`")

        # --- DIBUJAR TARJETA VISUAL DE ALERTA ---
        plt.style.use('dark_background')
        fig, ax = plt.subplots(figsize=(6, 3))
        fig.patch.set_facecolor('#0b0f19')
        ax.set_facecolor('#0b0f19')
        
        # Quitamos los ejes para que parezca una tarjeta de diseño
        ax.axis('off')
        
        # Textos de la tarjeta
        ax.text(0.05, 0.8, f"EARNINGS CALL: {tck}", color='#38bdf8', fontsize=18, fontweight='bold', ha='left')
        ax.text(0.05, 0.55, f"Fecha: {fecha_txt} (En {dias_faltantes} días)", color='white', fontsize=12, ha='left')
        ax.text(0.05, 0.35, f"EPS Estimado: {eps_txt}", color='#eab308', fontsize=12, fontweight='bold', ha='left')
        ax.text(0.05, 0.15, f"Volatilidad Histórica: {vol_txt}", color='#f43f5e', fontsize=10, ha='left')
        
        # Añadir un borde decorativo
        rect = plt.Rectangle((0, 0), 1, 1, fill=False, color='#1e293b', linewidth=3, transform=ax.transAxes)
        ax.add_patch(rect)
        
        enviar_telegram(mensaje, fig)

enviar_telegram("🏁 *ESCANEO DE CALENDARIO FINALIZADO*")
