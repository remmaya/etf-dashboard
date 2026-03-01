# app.py
import streamlit as st
import yfinance as yf
import pandas as pd

from core import macd, rsi, slice_period, ETF_INFO

# ETF_INFO のキー（ティッカー）をそのまま使う：8銘柄全部が対象
TARGET_ETFS = list(ETF_INFO.keys())

st.set_page_config(page_title="ETF Dashboard", layout="centered")
st.title("ETF Dashboard（Price / MACD / RSI）")

# ----------------------------------------
# サイドバー（建値・期間・表示形式）
# ----------------------------------------
with st.sidebar:
    st.header("表示設定")

    period = st.selectbox("期間", ["All", "1Y", "3M", "1M"], index=1)
    currency = st.radio("建値", ["USD", "JPY"], index=1)
    view_mode = st.radio("表示内容", ["Price", "MACD+RSI"], index=0)

    st.markdown("---")
    if st.button("🔄 データ更新"):
        # キャッシュクリア & 再実行
        st.cache_data.clear()
        st.rerun()

# ----------------------------------------
# データ取得（cache付き）
# ----------------------------------------
@st.cache_data
def load_data():
    tickers = TARGET_ETFS + ["USDJPY=X"]
    df = yf.download(tickers, period="2y", auto_adjust=True)["Close"]
    return df

raw = load_data()

# USDJPY（為替）
fx = raw["USDJPY=X"].dropna()

# ----------------------------------------
# 各ETFをカード式で縦に並べて表示
# ----------------------------------------
for ticker in TARGET_ETFS:

    if ticker not in raw:
        continue

    usd_series = raw[ticker].dropna()

    # 円建て or ドル建て
    if currency == "JPY":
        fx_aligned = fx.reindex(usd_series.index).ffill()
        price = usd_series * fx_aligned
        cur = "JPY"
    else:
        price = usd_series
        cur = "USD"

    df = pd.DataFrame({"Close": price})
    df = slice_period(df, period)
    if df.empty:
        continue

    perf_pct = (df["Close"].iloc[-1] / df["Close"].iloc[0] - 1) * 100

    label = ETF_INFO.get(ticker, ticker)
    title = f"{ticker}（{label}）｜ {perf_pct:+.2f}%"

    with st.expander(title):

        if view_mode == "Price":
            import plotly.graph_objects as go

            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df.index, y=df["Close"],
                mode="lines", name="Price"
            ))
            fig.update_layout(
                height=280,
                margin=dict(l=20, r=20, t=40, b=20),
                title=f"{ticker}（{label}） [{cur}]",
            )
            st.plotly_chart(fig, use_container_width=True)

        else:  # MACD+RSI
            import plotly.graph_objects as go

            macd_line, signal_line = macd(df["Close"])
            rsi_line = rsi(df["Close"])

            # --- MACD ---
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df.index, y=macd_line, name="MACD"
            ))
            fig.add_trace(go.Scatter(
                x=df.index, y=signal_line, name="Signal"
            ))
            fig.update_layout(
                height=300,
                margin=dict(l=20, r=20, t=40, b=20),
                title=f"{ticker}（{label}） MACD [{cur}]",
            )
            st.plotly_chart(fig, use_container_width=True)

            # --- RSI ---
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(
                x=df.index, y=rsi_line, name="RSI"
            ))
            for lvl in [30, 50, 70]:
                fig2.add_hline(y=lvl, line_dash="dot")

            fig2.update_layout(
                height=200,
                margin=dict(l=20, r=20, t=20, b=20),
                title=f"{ticker}（{label}） RSI [{cur}]",
            )
            st.plotly_chart(fig2, use_container_width=True)