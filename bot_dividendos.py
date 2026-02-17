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

# --- UNIVERSO DE DIVIDENDOS (Reyes y Aristócratas) ---
tickers_dividendos = [
    'KO', 'JNJ', 'PG', 'PEP', 'XOM', 'CVX', 'ABBV', 'T', 'VZ', 'MO', 
    'PFE', 'IBM', 'MMM', 'MCD', 'AAPL', 'MSFT', 'VALE', 'PBR'
]

def cazar_dividendos():
    hoy = datetime.now()
    limite_dias = hoy + timedelta(days=30)
    oportunidades = []
    
    for ticker in tickers_dividendos:
        try:
            time.sleep(1) # Pausa anti-bloqueo
            t = yf.Ticker(ticker)
            info = t.info
            
            # Extraer porcentaje de rendimiento anual
            yield_val = info.get('dividendYield', None)
            # Extraer fecha límite para comprar
            ex_div_timestamp = info.get('exDividendDate', None)
            
            if yield_val is not None and ex_div_timestamp is not None:
                # Convertir timestamp a fecha legible
                fecha_ex_div = datetime.fromtimestamp(ex_div_timestamp)
                
                # Solo nos interesan las que pagan pronto (próximos 30 días)
                if hoy <= fecha_ex_div <= limite_dias:
                    oportunidades.append({
                        'ticker': ticker,
                        'yield': float(yield_val) * 100, # Convertir a porcentaje
                        'fecha_limite': fecha_ex_div,
                        'precio': float(info.get('previousClose', 0))
                    })
        except Exception as e:
            print(f"Error analizando {ticker}: {e}")
            continue
            
    return oportunidades

hoy_str = datetime.now().strftime('%d/%m/%Y')
enviar_telegram(f"💸 *CAZADOR DE DIVIDENDOS ACTIVADO* | {hoy_str}\n_Buscando rentas pasivas para los próximos 30 días..._")

oportunidades = cazar_dividendos()

if not oportunidades:
    enviar_telegram("✅ *SIN ALERTAS DE RENTA*\nNinguna de las empresas principales corta cupón en los próximos 30 días.")
else:
    # Ordenar por el dividendo más alto
    oportunidades.sort(key=lambda x: x['yield'], reverse=True)
    
    for op in oportunidades:
        tck = op['ticker']
        yield_pct = op['yield']
        fecha_obj = op['fecha_limite']
        precio = op['precio']
        
        dias_faltantes = (fecha_obj - datetime.now()).days
        fecha_txt = fecha_obj.strftime('%d de %b, %Y')
        yield_txt = f"{yield_pct:.2f}%"
        precio_txt = f"${precio:.2f}"
        
        mensaje = (f"💰 *ALERTA DE PAGO: {tck}*\n"
                   f"Rendimiento Anualizado: `{yield_txt}`\n"
                   f"⏳ Límite para comprar: *{dias_faltantes} días* (`{fecha_txt}`)\n"
                   f"Spot Actual: `{precio_txt}`\n\n"
                   f"_Nota: Debes tener la acción comprada ANTES de la fecha límite para cobrar._")

        # --- TARJETA DE RENTA PASIVA (DORADA) ---
        plt.style.use('dark_background')
        fig, ax = plt.subplots(figsize=(6, 3))
        fig.patch.set_facecolor('#0b0f19')
        ax.set_facecolor('#0b0f19')
        
        ax.axis('off')
        
        # Textos de la tarjeta
        ax.text(0.05, 0.75, f"CUPÓN DE PAGO: {tck}", color='#eab308', fontsize=18, fontweight='bold', ha='left') # Dorado
        ax.text(0.05, 0.50, f"Rendimiento (Yield): {yield_txt} Anual", color='#4ade80', fontsize=14, fontweight='bold', ha='left')
        ax.text(0.05, 0.25, f"Comprar antes del: {fecha_txt}", color='white', fontsize=12, ha='left')
        ax.text(0.05, 0.05, f"Precio de la acción: {precio_txt}", color='#94a3b8', fontsize=10, ha='left')
        
        # Borde decorativo dorado
        rect = plt.Rectangle((0, 0), 1, 1, fill=False, color='#eab308', linewidth=4, transform=ax.transAxes)
        ax.add_patch(rect)
        
        enviar_telegram(mensaje, fig)

enviar_telegram("🏁 *ESCANEO DE DIVIDENDOS FINALIZADO*")
