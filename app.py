# app.py
import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

from core import macd, rsi, slice_period, ETF_INFO

# ETF_INFO のキー（ティッカー）をそのまま使う：8銘柄全部が対象
TARGET_ETFS = list(ETF_INFO.keys())

# ----------------------------------------
# ページ基本設定
# ----------------------------------------
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
@st.cache_data(ttl=60 * 60 * 6)  # 6時間キャッシュ
def load_data():
    tickers = TARGET_ETFS + ["USDJPY=X"]
    df = yf.download(tickers, period="2y", auto_adjust=True)["Close"]
    # 単一列のときでも DataFrame になるように調整
    if isinstance(df, pd.Series):
        df = df.to_frame()
    return df


raw = load_data()

# 為替（USD/JPY）
if "USDJPY=X" in raw.columns:
    fx = raw["USDJPY=X"].dropna()
else:
    fx = pd.Series(dtype=float)

# ----------------------------------------
# 各ETFを縦にそのまま表示（Expander なし）
# ----------------------------------------
for ticker in TARGET_ETFS:

    if ticker not in raw.columns:
        continue

    usd_series = raw[ticker].dropna()
    if usd_series.empty:
        continue

    # 円建て or ドル建て
    if currency == "JPY" and not fx.empty:
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

    # パフォーマンス（期間内の騰落率）
    perf_pct = (df["Close"].iloc[-1] / df["Close"].iloc[0] - 1) * 100
    label = ETF_INFO.get(ticker, ticker)

    # 見出し（タップ不要で常に表示）
    st.markdown(f"### {ticker}（{label}）｜ {perf_pct:+.2f}%  [{cur}]")

    # ------------------------------------------------
    # Price モード
    # ------------------------------------------------
    if view_mode == "Price":
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df["Close"],
                mode="lines",
                name="Price",
            )
        )
        fig.update_layout(
            height=280,
            margin=dict(l=20, r=20, t=40, b=20),
            showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True)

    # ------------------------------------------------
    # MACD + RSI モード
    # ------------------------------------------------
    else:
        # ----- MACD -----
        macd_line, signal_line = macd(df["Close"])
        rsi_line = rsi(df["Close"])

        macd_df = pd.DataFrame(
            {"MACD": macd_line, "Signal": signal_line}
        ).loc[df.index]

        fig_macd = go.Figure()

        # MACD（青）
        fig_macd.add_trace(
            go.Scatter(
                x=macd_df.index,
                y=macd_df["MACD"],
                name="MACD",
                line=dict(color="blue", width=2),
            )
        )

        # Signal（赤）
        fig_macd.add_trace(
            go.Scatter(
                x=macd_df.index,
                y=macd_df["Signal"],
                name="Signal",
                line=dict(color="red", width=2),
            )
        )

        fig_macd.update_layout(
            height=260,
            margin=dict(l=20, r=20, t=40, b=20),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1,
            ),
        )
        st.plotly_chart(fig_macd, use_container_width=True)

        # ----- RSI（棒グラフ） -----
        rsi_df = pd.DataFrame({"RSI": rsi_line}).loc[df.index]

        fig_rsi = go.Figure()

        # RSI を棒グラフで
        fig_rsi.add_trace(
            go.Bar(
                x=rsi_df.index,
                y=rsi_df["RSI"],
                name="RSI",
                marker_color="rgba(100, 100, 255, 0.6)",
            )
        )

        # 基準線 30 / 50 / 70
        for lvl in [30, 50, 70]:
            fig_rsi.add_hline(
                y=lvl,
                line_dash="dot",
                line_color="gray",
            )

        fig_rsi.update_layout(
            height=200,
            margin=dict(l=20, r=20, t=20, b=20),
            showlegend=False,
            yaxis=dict(range=[0, 100]),
        )

        st.plotly_chart(fig_rsi, use_container_width=True)

    # ETFごとに少し余白
    st.markdown("---")
