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

# --- UNIVERSO DE DIVIDENDOS ---
tickers_dividendos = [
    'KO', 'JNJ', 'PG', 'PEP', 'XOM', 'CVX', 'ABBV', 'T', 'VZ', 'MO', 
    'PFE', 'IBM', 'MMM', 'MCD', 'AAPL', 'MSFT', 'VALE', 'PBR'
]

def cazar_dividendos():
    hoy = datetime.now()
    limite_dias = hoy + timedelta(days=30)
    oportunidades = []
    lista_general = [] # Para guardar a las mejores pagadoras globales
    
    for ticker in tickers_dividendos:
        try:
            time.sleep(1) 
            t = yf.Ticker(ticker)
            info = t.info
            
            yield_crudo = info.get('dividendYield')
            tasa_anual_usd = info.get('dividendRate')
            ex_div_timestamp = info.get('exDividendDate')
            precio_actual = info.get('previousClose', 0)
            
            if yield_crudo is not None and tasa_anual_usd is not None and precio_actual > 0:
                yield_real = float(yield_crudo) * 100
                
                # Filtro Anti-Bugs
                if yield_real > 15.0 or (ticker in ['MSFT', 'AAPL'] and yield_real > 3.0):
                    continue 
                
                pago_trimestral_estimado = float(tasa_anual_usd) / 4
                
                # Guardamos todas las válidas para el Radar de Guardia
                lista_general.append({
                    'ticker': ticker,
                    'yield': yield_real,
                    'pago_usd_aprox': pago_trimestral_estimado,
                    'precio': float(precio_actual)
                })
                
                # Filtramos las que tienen pago inminente
                if ex_div_timestamp is not None:
                    fecha_ex_div = datetime.fromtimestamp(ex_div_timestamp)
                    if hoy <= fecha_ex_div <= limite_dias:
                        oportunidades.append({
                            'ticker': ticker,
                            'yield': yield_real,
                            'pago_usd_aprox': pago_trimestral_estimado,
                            'fecha_limite': fecha_ex_div,
                            'precio': float(precio_actual)
                        })
        except Exception as e:
            continue
            
    return oportunidades, lista_general

hoy_str = datetime.now().strftime('%d/%m/%Y')
enviar_telegram(f"💸 *CAZADOR DE RENTA PASIVA V32.1* | {hoy_str}\n_Analizando flujos de efectivo..._")

oportunidades, lista_general = cazar_dividendos()

if not oportunidades:
    # --- RADAR DE GUARDIA (FALLBACK) ---
    lista_general.sort(key=lambda x: x['yield'], reverse=True)
    top_3 = lista_general[:3]
    
    msj_fallback = ("✅ *SIN PAGOS INMINENTES (30 DÍAS)*\n"
                    "Ninguna de las empresas verificadas corta cupón pronto.\n\n"
                    "👀 *RADAR DE GUARDIA (Top 3 Mejores Pagadoras):*\n"
                    "Mantené estas en la mira para cuando anuncien fecha:\n\n")
    
    for emp in top_3:
        msj_fallback += (f"👑 *{emp['ticker']}*\n"
                         f"• Yield Anual: `{emp['yield']:.2f}%`\n"
                         f"• Spot Actual: `${emp['precio']:.2f}`\n"
                         f"• Pago Estimado (1 acción): `+${emp['pago_usd_aprox']:.2f} USD` trimestral\n\n")
    
    enviar_telegram(msj_fallback)

else:
    # (Código normal si hay oportunidades)
    oportunidades.sort(key=lambda x: x['pago_usd_aprox'], reverse=True)
    
    for op in oportunidades:
        tck = op['ticker']
        yield_pct = op['yield']
        fecha_obj = op['fecha_limite']
        precio = op['precio']
        pago_usd = op['pago_usd_aprox']
        
        dias_faltantes = (fecha_obj - datetime.now()).days
        fecha_txt = fecha_obj.strftime('%d de %b, %Y')
        
        mensaje = (f"💰 *ALERTA DE PAGO: {tck}*\n"
                   f"Rendimiento Anual: `{yield_pct:.2f}%`\n"
                   f"Spot Actual: `${precio:.2f}`\n"
                   f"⏳ Límite para comprar: *{dias_faltantes} días* (`{fecha_txt}`)\n\n"
                   f"💡 *SIMULADOR DE RENTA:*\n"
                   f"Si compras **1 acción** hoy a `${precio:.2f}`,\n"
                   f"cobrarías aprox **${pago_usd:.2f} USD** en efectivo.")

        plt.style.use('dark_background')
        fig, ax = plt.subplots(figsize=(7, 3.5))
        fig.patch.set_facecolor('#0b0f19')
        ax.set_facecolor('#0b0f19')
        ax.axis('off')
        
        ax.text(0.05, 0.80, f"CUPÓN DE PAGO: {tck}", color='#eab308', fontsize=18, fontweight='bold', ha='left') 
        ax.text(0.05, 0.55, f"Yield Anual: {yield_pct:.2f}%", color='#4ade80', fontsize=14, fontweight='bold', ha='left')
        ax.text(0.05, 0.35, f"Comprar antes del: {fecha_txt} (En {dias_faltantes} días)", color='white', fontsize=12, ha='left')
        ax.text(0.05, 0.10, f"Estimado por 1 acción: +${pago_usd:.2f} USD", color='#22d3ee', fontsize=13, fontweight='bold', ha='left')
        
        rect = plt.Rectangle((0, 0), 1, 1, fill=False, color='#eab308', linewidth=3, transform=ax.transAxes)
        ax.add_patch(rect)
        
        enviar_telegram(mensaje, fig)

enviar_telegram("🏁 *ESCANEO DE DIVIDENDOS FINALIZADO*")
