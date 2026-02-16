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

# --- CREDENCIALES ---
TOKEN = '8173318113:AAFK_OM25CfTAmrmhR1pzwpvcQJWmWzbZg0'
CHAT_ID = '6550986355'

def enviar_telegram(mensaje, fig=None):
    try:
        url_texto = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.post(url_texto, data={'chat_id': CHAT_ID, 'text': mensaje, 'parse_mode': 'Markdown'})
        if fig is not None:
            buf = io.BytesIO()
            fig.savefig(buf, format='png', bbox_inches='tight', dpi=140, facecolor='#050a15')
            buf.seek(0)
            url_foto = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
            requests.post(url_foto, data={'chat_id': CHAT_ID}, files={'photo': buf})
            buf.close()
    except: pass

# --- UNIVERSO 15x3 (45 ACTIVOS) ---
mercados = {
    '🇦🇷 MERVAL (ARG)': [
        'YPF', 'GGAL', 'BMA', 'PAM', 'VIST', 'TGS', 'CEPU', 'ALUA.BA', 'TXAR.BA', 
        'EDN', 'LOMA', 'BBAR', 'SUPV', 'CRESY', 'TGNO4.BA'
    ],
    '🇺🇸 S&P 500 (USA)': [
        'AAPL', 'MSFT', 'NVDA', 'AMZN', 'GOOGL', 'META', 'TSLA', 'BRK-B', 'JPM', 
        'UNH', 'V', 'JNJ', 'XOM', 'WMT', 'LLY'
    ],
    '🇬🇧 FTSE 100 (UK)': [
        'SHEL.L', 'BP.L', 'HSBA.L', 'AZN.L', 'GSK.L', 'ULVR.L', 'RIO.L', 'BARC.L', 
        'VOD.L', 'REL.L', 'RR.L', 'LLOY.L', 'AAL.L', 'DGE.L', 'BA.L'
    ]
}

def analizar_quant_pro(ticker):
    t = yf.Ticker(ticker)
    df = t.history(period="2y", interval="1d")
    if df.empty or len(df) < 100: return None
    
    # INDICADORES QUANT
    df['SMA_50'] = df['Close'].rolling(50).mean()
    df['SMA_200'] = df['Close'].rolling(200).mean()
    df['RSI'] = 100 - (100 / (1 + (df['Close'].diff().where(df['Close'].diff() > 0, 0).rolling(14).mean() / 
                                  -df['Close'].diff().where(df['Close'].diff() < 0, 0).rolling(14).mean())))
    
    # CÁLCULO DE VOLUMEN INTELIGENTE (OBV Simplificado)
    df['OBV'] = (np.sign(df['Close'].diff()) * df['Volume']).fillna(0).cumsum()
    vol_confirm = "✅ ACUMULANDO" if df['OBV'].iloc[-1] > df['OBV'].iloc[-20] else "⚠️ DISTRIBUYENDO"
    
    # FUNDAMENTALES
    info = t.info
    cap = info.get('marketCap', 0) / 1e9
    pe = info.get('trailingPE', 0)
    
    # IA: PROYECCIÓN GRADIENT BOOSTING (45 DÍAS)
    df['Target'] = df['Close'].shift(-45)
    train = df.dropna()
    features = ['Close', 'RSI', 'OBV']
    model = GradientBoostingRegressor(n_estimators=100).fit(train[features].iloc[:-45], train['Target'].iloc[:-45])
    pred = model.predict(df[features].iloc[-1:])[0]
    
    return df, {'pred': pred, 'confirm': vol_confirm, 'cap': cap, 'pe': pe, 'news': t.news[:1]}

enviar_telegram("🏛️ *TERMINAL QUANT GLOBAL V20.0*\nAuditando 45 Activos Críticos...\n_Fecha: Lunes 16 de Febrero, 2026_")

for mercado, activos in mercados.items():
    enviar_telegram(f"📁 *INICIANDO SECTOR: {mercado}*")
    
    for ticker in activos:
        try:
            res = analizar_quant_pro(ticker)
            if not res: continue
            df, meta = res
            
            precio = df['Close'].iloc[-1]
            var = ((precio / df['Close'].iloc[-2]) - 1) * 100
            dist_200 = ((precio / df['SMA_200'].iloc[-1]) - 1) * 100
            titular = meta['news'][0]['title'] if meta['news'] else "Sin noticias."

            msj = (f"*{ticker}* | {mercado[:2]}\n"
                   f"💰 Precio: `${precio:.2f}` ({var:+.2f}%)\n"
                   f"🏗️ Institucionales: `{meta['confirm']}`\n"
                   f"🏛️ Distancia SMA 200: `{dist_200:+.2f}%` | P/E: `{meta['pe']:.1f}`\n"
                   f"🧠 IA Target: *${meta['pred']:.2f}* ({(meta['pred']/precio-1):+.1%})\n"
                   f"📰 `{titular}`")

            # GRÁFICO PROFESIONAL
            plt.style.use('dark_background')
            fig, ax = plt.subplots(figsize=(11, 5))
            fig.patch.set_facecolor('#050a15'); ax.set_facecolor('#050a15')
            
            # Eje de Precio
            ax.plot(df.index[-180:], df['Close'].iloc[-180:], color='#00f2ff', linewidth=2, label='Precio 2026')
            ax.plot(df.index[-180:], df['SMA_200'].iloc[-180:], color='#ff00ff', linestyle='--', alpha=0.5)
            
            # Línea de Proyección
            fecha_fut = df.index[-1] + timedelta(days=45)
            ax.plot([df.index[-1], fecha_fut], [precio, meta['pred']], color='#4ade80', linestyle=':', linewidth=3)
            
            ax.set_title(f"Quantum Flow: {ticker}", color='white', loc='left')
            ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
            ax.grid(alpha=0.05)
            
            enviar_telegram(msj, fig)
            plt.close(fig)
            
        except: continue

enviar_telegram("✅ *AUDITORÍA GLOBAL 45 COMPLETADA*")
