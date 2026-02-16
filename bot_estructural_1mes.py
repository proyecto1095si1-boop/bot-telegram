import yfinance as yf
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
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
            fig.savefig(buf, format='png', bbox_inches='tight', dpi=140, facecolor='#060b16')
            buf.seek(0)
            url_foto = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
            requests.post(url_foto, data={'chat_id': CHAT_ID}, files={'photo': buf})
            buf.close()
    except: pass

# --- UNIVERSO 45 ---
mercados = {
    '🇦🇷 ARG': ['YPF', 'GGAL', 'BMA', 'PAM', 'VIST', 'TGS', 'CEPU', 'ALUA.BA', 'TXAR.BA', 'EDN', 'LOMA', 'BBAR', 'SUPV', 'CRESY', 'TGNO4.BA'],
    '🇺🇸 USA': ['AAPL', 'MSFT', 'NVDA', 'AMZN', 'GOOGL', 'META', 'TSLA', 'JPM', 'V', 'XOM', 'WMT', 'LLY', 'AVGO', 'PYPL', 'MELI'],
    '🇬🇧 UK': ['SHEL.L', 'BP.L', 'HSBA.L', 'AZN.L', 'GSK.L', 'ULVR.L', 'RIO.L', 'BARC.L', 'VOD.L', 'REL.L', 'RR.L', 'LLOY.L', 'AAL.L', 'DGE.L', 'BA.L']
}

def procesar_insight(ticker, bandera):
    t = yf.Ticker(ticker)
    # Descarga directa para evitar bloqueos
    df = t.history(period="2y", interval="1d")
    if df.empty: return None
    
    # Análisis Técnico
    df['SMA_50'] = df['Close'].rolling(50).mean()
    df['SMA_200'] = df['Close'].rolling(200).mean()
    df['RSI'] = 100 - (100 / (1 + (df['Close'].diff().where(df['Close'].diff() > 0, 0).rolling(14).mean() / 
                                  -df['Close'].diff().where(df['Close'].diff() < 0, 0).rolling(14).mean())))
    
    precio = df['Close'].iloc[-1]
    
    # IA: Proyección con sesgo de recuperación
    df['Target'] = df['Close'].shift(-60)
    train = df.dropna()
    features = ['Close', 'RSI']
    # Usamos RandomForest que es menos propenso a tendencias bajistas infinitas
    model = RandomForestRegressor(n_estimators=100).fit(train[features].iloc[:-60], train['Target'].iloc[:-60])
    pred_ia = model.predict(df[features].iloc[-1:])[0]
    
    # Resumen de Noticias (Simulado con lógica de sentimiento sobre titulares)
    news = t.news[:3]
    titulares = [n['title'] for n in news]
    resumen_ia = "Análisis de Sentimiento: "
    if any(word in " ".join(titulares).lower() for word in ['buy', 'growth', 'profit', 'up']):
        resumen_ia += "🟢 Optimismo en el sector."
    elif any(word in " ".join(titulares).lower() for word in ['fall', 'risk', 'loss', 'down']):
        resumen_ia += "🟡 Precaución por volatilidad."
    else:
        resumen_ia += "⚪ Estabilidad informativa."

    return df, {'pred': pred_ia, 'news': titulares, 'resumen': resumen_ia, 'precio': precio}

enviar_telegram("🧠 *INSIGHT ENGINE V21.0 - FULL GLOBAL*\nAuditando 45 activos con Resumen de Noticias e IA Proyectiva...")

for region, lista in mercados.items():
    bandera = region.split()[0]
    for ticker in lista:
        try:
            res = procesar_insight(ticker, bandera)
            if not res: continue
            df, data = res
            
            p = data['precio']
            diff = ((data['pred'] / p) - 1) * 100
            trend_emoji = "🚀" if diff > 0 else "📉"
            
            # Resumen de noticias formateado
            news_txt = ""
            for t in data['news'][:2]: news_txt += f"• {t}\n"

            msj = (f"{bandera} *{ticker}*\n"
                   f"💰 Precio: `${p:.2f}`\n"
                   f"🧠 IA Proyección (3 meses): *${data['pred']:.2f}* ({diff:+.1f}% {trend_emoji})\n"
                   f"📊 *{data['resumen']}*\n"
                   f"📰 *Últimas Noticias:*\n{news_txt}")

            # Gráfico
            plt.style.use('dark_background')
            fig, ax = plt.subplots(figsize=(10, 4))
            fig.patch.set_facecolor('#060b16'); ax.set_facecolor('#060b16')
            ax.plot(df.index[-150:], df['Close'].iloc[-150:], color='#22d3ee', label='Precio')
            ax.plot([df.index[-1], df.index[-1]+timedelta(days=60)], [p, data['pred']], color='#4ade80', linestyle='--')
            ax.set_title(f"{bandera} {ticker} - Insight 2026", color='white')
            
            enviar_telegram(msj, fig)
            plt.close(fig)
        except: continue

enviar_telegram("✅ *Escaneo Global 2026 Finalizado.*")
