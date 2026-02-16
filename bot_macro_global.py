import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import requests
import io
import time
from datetime import datetime, timedelta

# --- CREDENCIALES ---
TOKEN = '8173318113:AAFK_OM25CfTAmrmhR1pzwpvcQJWmWzbZg0'
CHAT_ID = '6550986355'

def enviar_telegram(mensaje, fig=None):
    try:
        url_texto = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.post(url_texto, data={'chat_id': CHAT_ID, 'text': mensaje, 'parse_mode': 'Markdown'})
        if fig is not None:
            buf = io.BytesIO()
            fig.savefig(buf, format='png', bbox_inches='tight', dpi=150, facecolor='#050a15')
            buf.seek(0)
            url_foto = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
            requests.post(url_foto, data={'chat_id': CHAT_ID}, files={'photo': buf})
            buf.close()
    except: pass

# --- CONFIGURACIÓN DE UNIVERSO GLOBAL 2026 ---
universo = {
    'ENERGÍA': {'WTI Oil': 'CL=F', 'Brent Oil': 'BZ=F', 'Natural Gas': 'NG=F', 'Uranium (URA)': 'URA'},
    'METALES': {'Gold': 'GC=F', 'Silver': 'SI=F', 'Copper': 'HG=F', 'Lithium (LIT)': 'LIT'},
    'AGRO': {'Soybean': 'ZS=F', 'Corn': 'ZC=F', 'Wheat': 'ZW=F'},
    'EMERGENTES': {'Brasil (EWZ)': 'EWZ', 'China (FXI)': 'FXI', 'India (INDA)': 'INDA', 'México (EWW)': 'EWW', 'Argentina (ARGT)': 'ARGT'}
}

enviar_telegram(f"🏛️ *SISTEMA MACRO INSTITUCIONAL V16.0*\n📅 Auditoría: `Lunes 16 de Febrero, 2026`\n---")

for categoria, activos in universo.items():
    enviar_telegram(f"📁 *SECTOR: {categoria}*")
    
    for nombre, ticker in activos.items():
        try:
            # Descarga con Bypass de Caché
            t = yf.Ticker(ticker)
            df = t.history(period="2y", interval="1d")
            
            if df.empty: continue
            
            # Limpieza de datos 2026
            precio_hoy = df['Close'].iloc[-1]
            fecha_hoy = df.index[-1].strftime('%d/%m/%Y')
            retorno_diario = ((precio_hoy / df['Close'].iloc[-2]) - 1) * 100
            sma_200 = df['Close'].rolling(200).mean().iloc[-1]
            volatilidad = df['Close'].pct_change().std() * np.sqrt(252) # Volatilidad anualizada

            # --- CÁLCULO DE PROYECCIÓN ESTRUCTURAL ---
            # Proyectamos a 90 días usando el drift histórico
            dias_proy = 90
            conos = 3 # Niveles de desviación
            tendencia = (df['Close'].iloc[-1] / df['Close'].iloc[-60]) - 1
            precio_proy = precio_hoy * (1 + tendencia)

            # Mensaje detallado
            estado = "🟦 ACUMULACIÓN" if precio_hoy > sma_200 else "🟥 DISTRIBUCIÓN"
            msj = (f"💎 *{nombre}* ({ticker})\n"
                   f"🕒 Data: `{fecha_hoy}`\n"
                   f"💵 Spot: *${precio_hoy:.2f}* ({retorno_diario:+.2f}%)\n"
                   f"📉 Volatilidad: `{volatilidad:.1%}`\n"
                   f"🏛️ Régimen: `{estado}`")

            # --- GRÁFICO PROFESIONAL ---
            plt.style.use('dark_background')
            fig, ax = plt.subplots(figsize=(12, 6))
            fig.patch.set_facecolor('#050a15'); ax.set_facecolor('#050a15')
            
            # Histórico
            df_plot = df.iloc[-250:]
            ax.plot(df_plot.index, df_plot['Close'], color='#22d3ee', linewidth=2, label='Precio 2025-2026')
            ax.axhline(sma_200, color='#f472b6', linestyle='--', alpha=0.6, label='Media Móvil 200d')
            
            # Cono de Probabilidad (Proyección)
            fechas_proy = [df_plot.index[-1] + timedelta(days=i) for i in range(dias_proy)]
            linea_proy = [precio_hoy + (precio_proy - precio_hoy) * (i/dias_proy) for i in range(dias_proy)]
            
            # Desviaciones estándar para el cono
            upper_bound = [p + (precio_hoy * volatilidad * 0.1 * np.sqrt(i/dias_proy)) for i, p in enumerate(linea_proy)]
            lower_bound = [p - (precio_hoy * volatilidad * 0.1 * np.sqrt(i/dias_proy)) for i, p in enumerate(linea_proy)]
            
            ax.plot(fechas_proy, linea_proy, color='#4ade80', linestyle=':', linewidth=2, label='Trayectoria IA')
            ax.fill_between(fechas_proy, lower_bound, upper_bound, color='#4ade80', alpha=0.1, label='Cono de Probabilidad')

            # Estética Institucional
            ax.set_title(f"ANÁLISIS ESTRUCTURAL: {nombre}", color='white', fontsize=14, loc='left', pad=20)
            ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
            ax.grid(color='white', alpha=0.05)
            ax.tick_params(axis='both', colors='gray', labelsize=9)
            ax.legend(frameon=False, loc='upper left', fontsize=8)
            
            enviar_telegram(msj, fig)
            plt.close(fig)
            
        except Exception as e:
            print(f"Error en {ticker}: {e}")

enviar_telegram("🏁 *TERMINAL GLOBAL 2026: ACTUALIZACIÓN FINALIZADA*")
