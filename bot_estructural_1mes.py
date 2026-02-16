import yfinance as yf
import pandas as pd
import numpy as np
from sklearn.ensemble import GradientBoostingRegressor
import matplotlib.pyplot as plt
import requests
import io
import warnings
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
            fig.savefig(buf, format='png', bbox_inches='tight', dpi=140, facecolor='#020617')
            buf.seek(0)
            url_foto = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
            requests.post(url_foto, data={'chat_id': CHAT_ID}, files={'photo': buf})
            buf.close()
            plt.close(fig) # Liberar memoria crucial
    except: pass

# --- UNIVERSO MAESTRO 45 (Sincronizado 2026) ---
mercados = {
    '🇦🇷 ARG': ['YPF', 'GGAL', 'BMA', 'PAM', 'VIST', 'TGS', 'CEPU', 'ALUA.BA', 'TXAR.BA', 'EDN', 'LOMA', 'BBAR', 'SUPV', 'CRESY', 'TGNO4.BA'],
    '🇺🇸 USA': ['AAPL', 'MSFT', 'NVDA', 'AMZN', 'GOOGL', 'META', 'TSLA', 'JPM', 'V', 'XOM', 'WMT', 'LLY', 'AVGO', 'PYPL', 'MELI'],
    '🇬🇧 UK': ['SHEL.L', 'BP.L', 'HSBA.L', 'AZN.L', 'GSK.L', 'ULVR.L', 'RIO.L', 'BARC.L', 'VOD.L', 'REL.L', 'RR.L', 'LLOY.L', 'AAL.L', 'DGE.L', 'BA.L']
}

def motor_insight_pro(ticker):
    t = yf.Ticker(ticker)
    df = t.history(period="3y", interval="1d")
    if df.empty or len(df) < 150: return None
    
    # --- ANÁLISIS TÉCNICO ---
    df['SMA_50'] = df['Close'].rolling(50).mean()
    df['SMA_200'] = df['Close'].rolling(200).mean()
    df['Volatilidad'] = df['Close'].pct_change().rolling(20).std()
    
    # --- IA PROYECTIVA (GRADIENT BOOSTING) ---
    df['Target'] = df['Close'].shift(-60)
    train = df.dropna()
    # Entrenamos con precio, volatilidad y volumen para mayor realismo
    features = ['Close', 'Volatilidad', 'Volume']
    model = GradientBoostingRegressor(n_estimators=100, learning_rate=0.1, max_depth=4)
    model.fit(train[features].iloc[:-60], train['Target'].iloc[:-60])
    
    pred_ia = model.predict(df[features].iloc[-1:])[0]
    
    # --- FUNDAMENTOS Y NOTICIAS ---
    info = t.info
    fundamental = {
        'pe': info.get('forwardPE', 'N/A'),
        'target_analista': info.get('targetMeanPrice', 'N/A'),
        'recomendacion': info.get('recommendationKey', 'N/A').upper()
    }
    
    news = t.news[:3]
    resumen = " | ".join([n['title'] for n in news]) if news else "Sin noticias hoy."
    
    return df, {'pred': pred_ia, 'fund': fundamental, 'news': resumen, 'precio': df['Close'].iloc[-1]}

enviar_telegram("🏛️ *TERMINAL QUANT GLOBAL V25.0*\nAuditando 45 activos: Argentina • USA • Londres\n_Fecha: Lunes 16 de Febrero, 2026_")

for region, activos in mercados.items():
    bandera = region.split()[0]
    for ticker in activos:
        try:
            res = motor_insight_pro(ticker)
            if not res: continue
            df, data = res
            
            p = data['precio']
            diff = ((data['pred'] / p) - 1) * 100
            emoji = "🚀" if diff > 0 else "⚠️"
            
            msj = (f"{bandera} *{ticker}* | `{data['fund']['recomendacion']}`\n"
                   f"💰 Precio: *${p:.2f}* | P/E: `{data['fund']['pe']}`\n"
                   f"🧠 IA 60d: *${data['pred']:.2f}* ({diff:+.1f}% {emoji})\n"
                   f"🎯 Target Analistas: `${data['fund']['target_analista']}`\n"
                   f"📰 *Noticias:* _{data['news']}_")

            # --- GRÁFICO PROFESIONAL ---
            plt.style.use('dark_background')
            fig, ax = plt.subplots(figsize=(11, 5))
            fig.patch.set_facecolor('#020617'); ax.set_facecolor('#020617')
            
            # Histórico
            df_plot = df.iloc[-180:]
            ax.plot(df_plot.index, df_plot['Close'], color='#38bdf8', linewidth=2, label='Precio')
            ax.plot(df_plot.index, df_plot['SMA_200'], color='#f472b6', alpha=0.5, label='Media 200d')
            
            # Proyección IA
            fecha_futura = df.index[-1] + timedelta(days=60)
            ax.plot([df.index[-1], fecha_futura], [p, data['pred']], color='#4ade80', linestyle='--', marker='o', label='IA')
            
            ax.set_title(f"{bandera} {ticker} - Proyección Abril 2026", color='white', loc='left')
            ax.grid(alpha=0.05); ax.legend(fontsize='small')
            
            enviar_telegram(msj, fig)
            
        except Exception as e:
            print(f"Error en {ticker}: {e}")
            continue

enviar_telegram("✅ *TERMINAL 2026: ANÁLISIS GLOBAL COMPLETADO*")
