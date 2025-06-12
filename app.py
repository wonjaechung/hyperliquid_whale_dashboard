# app.py
import streamlit as st
import requests
import pandas as pd
import matplotlib.pyplot as plt
from collections import Counter, defaultdict
from hyperliquid.utils import constants
from st_aggrid import AgGrid, GridOptionsBuilder, DataReturnMode, GridUpdateMode

# ── AI Tutor imports ─────────────────────────────────────────────────────────
import openai
from streamlit_chat import message

# ── Configuration ──────────────────────────────────────────────────────────
CSV_PATH = "top30_wallets.csv"
BASE_URL = constants.MAINNET_API_URL

# ── OpenAI 설정 ───────────────────────────────────────────────────────────
openai.api_key = st.secrets["OPENAI_API_KEY"]

# ── HTTP helpers ───────────────────────────────────────────────────────────
def info_http(payload: dict):
    r = requests.post(f"{BASE_URL}/info", json=payload)
    r.raise_for_status()
    return r.json()

def get_portfolio(wallet: str):
    return info_http({"type": "portfolio", "user": wallet})

def get_clearinghouse_state(wallet: str):
    return info_http({"type": "clearinghouseState", "user": wallet})

# ── Load leaderboard with Unrealized PnL ────────────────────────────────────
@st.cache_data(ttl=600)
def load_leaderboard():
    df = pd.read_csv(CSV_PATH)
    df["Rank"] = df.index + 1
    unrealized = []
    for w in df["Wallet"]:
        try:
            stt = get_clearinghouse_state(w)
            up = sum(float(ap["position"].get("unrealizedPnl") or 0.0)
                     for ap in stt.get("assetPositions", []))
        except:
            up = 0.0
        unrealized.append(up)
    df["Unrealized PnL"] = unrealized
    return df[[
        "Rank","Wallet","Account Value","PNL",
        "ROI","Volume","Unrealized PnL"
    ]]

# ── Top-10 summary ─────────────────────────────────────────────────────────
@st.cache_data(ttl=600)
def compute_top10_summary(wallets):
    periods = [("All-Time","allTime"),("24H","day"),
               ("7D","week"),("30D","month")]
    rows = []
    for label,key in periods:
        pnls,rois = [],[]
        for w in wallets:
            try:
                pf = get_portfolio(w)
                data = next(i[1] for i in pf if i[0]==key)
                hist = data.get("pnlHistory",[])
                delta = (float(hist[-1][1]) - float(hist[0][1])
                         if len(hist)>=2 else 0.0)
                pnls.append(delta)
                if label!="All-Time":
                    av = data.get("accountValueHistory",[])
                    if len(av)>=2:
                        start=float(av[0][1]); rois.append(delta/start if start else 0.0)
            except: pass
        avg_pnl = sum(pnls)/len(pnls) if pnls else 0.0
        if label=="All-Time":
            rows.append({"Period":label,"Avg P&L (USD)":avg_pnl,"Avg ROI (%)":"—"})
        else:
            avg_roi = sum(rois)/len(rois) if rois else 0.0
            rows.append({"Period":label,"Avg P&L (USD)":avg_pnl,"Avg ROI (%)":avg_roi*100})
    return pd.DataFrame(rows)

st.title("Hyperliquid Whale Dashboard")

# manage search_addr in session_state
if "search_addr" not in st.session_state:
    st.session_state.search_addr = ""
search_input = st.sidebar.text_input(
    "🔎 Search Address (hex)",
    value=st.session_state.search_addr,
    key="search_addr"
).strip()

# load leaderboard
df_leader     = load_leaderboard()
top_n         = 10
wallets_top10 = df_leader["Wallet"].head(top_n).tolist()

# ── Custom Report 섹션 ───────────────────────────────────────────────────────
st.sidebar.markdown("## 📋 Custom Report")
raw_text = st.sidebar.text_area(
    "Enter wallet addresses (one per line or comma-separated):",
    height=100
).strip()

if st.sidebar.button("🖨️ Generate Report"):
    custom_wallets = []
    if raw_text:
        custom_wallets = [
            w.strip()
            for part in raw_text.splitlines()
            for w in part.split(",")
            if w.strip()
        ]
    if not custom_wallets:
        st.sidebar.warning("하나 이상의 지갑 주소를 입력해주세요.")
    else:
        # --- 1) Summary ---
        df_cust_summary = compute_top10_summary(custom_wallets)
        st.subheader(f"Custom Report: P&L Summary ({len(custom_wallets)} wallets)")
        st.table(df_cust_summary.style.format({
            "Avg P&L (USD)": "{:,.2f}",
            "Avg ROI (%)":   lambda x: f"{x:.2f}%" if isinstance(x,(int,float)) else x
        }))

        # --- 2) Aggregate Metrics ---
        unrealized_total = 0.0
        coin_counter     = Counter()
        coin_upnls       = defaultdict(float)
        coin_volumes     = defaultdict(float)
        coin_sentiment   = defaultdict(lambda: {"Long":0,"Short":0})

        for w in custom_wallets:
            try:
                state = get_clearinghouse_state(w)
                for ap in state.get("assetPositions", []):
                    p   = ap["position"]
                    amt = float(p.get("szi") or 0.0)
                    upnl= float(p.get("unrealizedPnl") or 0.0)
                    val = float(p.get("positionValue") or 0.0)
                    c   = p.get("coin")

                    unrealized_total += upnl
                    if c:
                        coin_counter[c]  += 1
                        coin_upnls[c]    += upnl
                        coin_volumes[c]  += val
                        side = "Long" if amt>0 else "Short"
                        coin_sentiment[c][side] += 1
            except:
                pass

        popular_coin  = coin_counter.most_common(1)[0][0] if coin_counter else "—"
        pop_long      = coin_sentiment[popular_coin]["Long"]
        pop_short     = coin_sentiment[popular_coin]["Short"]
        trending_coin = max(coin_volumes, key=coin_volumes.get) if coin_volumes else "—"
        top_coin, top_upnl     = max(coin_upnls.items(), key=lambda kv:kv[1]) if coin_upnls else ("—",0.0)
        worst_coin, worst_upnl = min(coin_upnls.items(), key=lambda kv:kv[1]) if coin_upnls else ("—",0.0)

        st.subheader("Custom Report: Aggregate Metrics")
        st.markdown(f"💰 **Unrealized PnL (USD):** ${unrealized_total:,.2f}")
        st.markdown(f"🐋 **Popular Whale Position: {popular_coin}** ({pop_long} Long / {pop_short} Short)")
        st.markdown(f"🔥 **Trending Coin (by Open Interest):** {trending_coin}")
        st.markdown(f"🏆 **Top Unrealized PnL Coin:** {top_coin} (+${top_upnl:,.2f})")
        st.markdown(f"⚠️ **Worst Unrealized PnL Coin:** {worst_coin} (${worst_upnl:,.2f})")

        # Avg Entry/Liq table for custom report
        top_coins = [c for c,_ in coin_counter.most_common(10)]
        entries = defaultdict(list)
        liqs    = defaultdict(list)
        for w in custom_wallets:
            try:
                state = get_clearinghouse_state(w)
                for ap in state.get("assetPositions", []):
                    p = ap["position"]
                    c = p.get("coin")
                    if c in top_coins:
                        entries[c].append(float(p.get("entryPx") or 0.0))
                        liqs[c].append(float(p.get("liquidationPx") or 0.0))
            except:
                pass

        rows = []
        for c in top_coins:
            e = sum(entries[c])/len(entries[c]) if entries[c] else 0
            l = sum(liqs[c])/len(liqs[c]) if liqs[c] else 0
            rows.append({"Coin":c, "Avg Entry":e, "Avg Liq":l})
        df_eql = pd.DataFrame(rows)

        st.subheader("Custom Report: Avg Entry & Liq")
        st.table(df_eql.style.format({"Avg Entry":"{:,.2f}", "Avg Liq":"{:,.2f}"}))

        # show back button and stop further rendering
        st.button("← Back to Leaderboard", on_click=lambda: st.session_state.update({"search_addr": ""}))
        st.stop()
# ── leaderboard vs individual wallet 모드 ───────────────────────────────────
#
if search_input == "":
    # Top-10 P&L Summary
    st.markdown(
        "<h2 style='color:#0072C3; font-size:1rem;'>"
        f"Top {top_n} P&L Summary</h2>",
        unsafe_allow_html=True
    )
    df_summary = compute_top10_summary(wallets_top10)
    st.table(df_summary.style.format({
        "Avg P&L (USD)": "{:,.2f}",
        "Avg ROI (%)":   lambda x: f"{x:.2f}%" if isinstance(x,(int,float)) else x
    }))

    # Top-10 Aggregate Metrics (same logic)
    unrealized_total = 0.0
    coin_counter     = Counter()
    coin_upnls       = defaultdict(float)
    coin_volumes     = defaultdict(float)
    coin_sentiment   = defaultdict(lambda: {"Long":0,"Short":0})

    for w in wallets_top10:
        try:
            state = get_clearinghouse_state(w)
            for ap in state.get("assetPositions", []):
                p   = ap["position"]
                amt = float(p.get("szi") or 0.0)
                upnl= float(p.get("unrealizedPnl") or 0.0)
                val = float(p.get("positionValue") or 0.0)
                c   = p.get("coin")

                unrealized_total += upnl
                if c:
                    coin_counter[c]  += 1
                    coin_upnls[c]    += upnl
                    coin_volumes[c]  += val
                    side = "Long" if amt>0 else "Short"
                    coin_sentiment[c][side] += 1
        except:
            pass

    popular_coin  = coin_counter.most_common(1)[0][0] if coin_counter else "—"
    pop_long      = coin_sentiment[popular_coin]["Long"]
    pop_short     = coin_sentiment[popular_coin]["Short"]
    trending_coin = max(coin_volumes, key=coin_volumes.get) if coin_volumes else "—"
    top_coin, top_upnl     = max(coin_upnls.items(), key=lambda kv:kv[1]) if coin_upnls else ("—",0.0)
    worst_coin, worst_upnl = min(coin_upnls.items(), key=lambda kv:kv[1]) if coin_upnls else ("—",0.0)

    st.markdown(
        "<h2 style='color:#0072C3; font-size:1rem;'>"
        "Top-10 Aggregate Metrics</h2>",
        unsafe_allow_html=True
    )
    st.markdown(f"💰 **Unrealized PnL (USD):** ${unrealized_total:,.2f}")
    st.markdown(f"🐋 **Popular Whale Position:** {popular_coin} ({pop_long} Long / {pop_short} Short)")
    st.markdown(f"🔥 **Trending Coin (by Open Interest):** {trending_coin}")
    st.markdown(f"🏆 **Top Unrealized PnL Coin:** {top_coin} (+${top_upnl:,.2f})")
    st.markdown(f"⚠️ **Worst Unrealized PnL Coin:** {worst_coin} (${worst_upnl:,.2f})")

    # Avg Entry/Liq table for top-10
    top_coins = [c for c,_ in coin_counter.most_common(10)]
    entries = defaultdict(list)
    liqs    = defaultdict(list)
    for w in wallets_top10:
        try:
            state = get_clearinghouse_state(w)
            for ap in state.get("assetPositions", []):
                p = ap["position"]; c = p.get("coin")
                if c in top_coins:
                    entries[c].append(float(p.get("entryPx") or 0.0))
                    liqs[c].append(float(p.get("liquidationPx") or 0.0))
        except:
            pass
    rows = []
    for c in top_coins:
        e = sum(entries[c])/len(entries[c]) if entries[c] else 0
        l = sum(liqs[c])/len(liqs[c]) if liqs[c] else 0
        rows.append({"Coin":c, "Avg Entry":e, "Avg Liq":l})
    df_eql = pd.DataFrame(rows)

    st.markdown(
        "<h2 style='color:#0072C3; font-size:1rem;'>"
        "Top-10 Avg Entry & Liq</h2>",
        unsafe_allow_html=True
    )
    st.table(df_eql.style.format({"Avg Entry":"{:,.2f}", "Avg Liq":"{:,.2f}"} ))

    st.markdown("---")
    st.markdown("**☑️ 체크박스를 클릭하여 지갑을 선택하세요.**")

    # Leaderboard Grid
    gb = GridOptionsBuilder.from_dataframe(df_leader)
    gb.configure_selection("multiple", use_checkbox=True)
    gb.configure_column("Rank", width=60)
    gb.configure_column("Wallet", width=250)
    grid_opts = gb.build()

    grid_resp = AgGrid(
        df_leader,
        gridOptions=grid_opts,
        update_mode=GridUpdateMode.SELECTION_CHANGED,
        data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
        fit_columns_on_grid_load=True
    )

    raw = grid_resp.get("selected_rows")
    if isinstance(raw, pd.DataFrame):
        wallets_to_show = raw.to_dict("records")
    elif isinstance(raw, list):
        wallets_to_show = raw
    else:
        wallets_to_show = []

else:
    # individual wallet mode
    def _reset_search():
        st.session_state.search_addr = ""
    st.button("← Back to Leaderboard", on_click=_reset_search)
    wallets_to_show = [{"Wallet": search_input}]

# ── Wallet Details ─────────────────────────────────────────────────────────
for entry in wallets_to_show:
    wallet = entry["Wallet"]
    st.subheader(f"Address: {wallet}")

    # P&L Chart & Metrics
    try:
        pf       = get_portfolio(wallet)
        all_time = next(i[1] for i in pf if i[0] == "allTime")
        df_pnl   = pd.DataFrame(all_time["pnlHistory"], columns=["time","pnl"])
        df_pnl["pnl"]   = df_pnl["pnl"].astype(float)
        df_pnl["time"]  = pd.to_datetime(df_pnl["time"], unit="ms")

        total = df_pnl["pnl"].iloc[-1]
        now   = df_pnl["time"].iloc[-1]
        def delta(days):
            sl = df_pnl[df_pnl["time"] >= now - pd.Timedelta(days=days)]
            return (sl["pnl"].iloc[-1] - sl["pnl"].iloc[0]) if len(sl)>1 else 0.0

        c1,c2,c3,c4 = st.columns(4)
        c1.metric("Total P&L", f"{total:,.2f}")
        av_d = next(i[1] for i in pf if i[0]=="day")["accountValueHistory"]
        sd   = float(av_d[0][1]) if len(av_d)>=2 else None
        c2.metric("24H P&L", f"{delta(1):,.2f}", delta=f"{delta(1)/sd*100:.2f}%" if sd else None)
        av_w = next(i[1] for i in pf if i[0]=="week")["accountValueHistory"]
        sw   = float(av_w[0][1]) if len(av_w)>=2 else None
        c3.metric("7D P&L", f"{delta(7):,.2f}", delta=f"{delta(7)/sw*100:.2f}%" if sw else None)
        av_m = next(i[1] for i in pf if i[0]=="month")["accountValueHistory"]
        sm   = float(av_m[0][1]) if len(av_m)>=2 else None
        c4.metric("30D P&L", f"{delta(30):,.2f}", delta=f"{delta(30)/sm*100:.2f}%" if sm else None)

        fig, ax = plt.subplots(figsize=(8,3))
        ax.fill_between(df_pnl["time"], df_pnl["pnl"], step="mid", alpha=0.3)
        ax.plot(df_pnl["time"], df_pnl["pnl"], linewidth=2)
        ax.axhline(0, color="gray", linewidth=0.8)
        ax.set_xlabel("Time"); ax.set_ylabel("P&L (USD)")
        plt.xticks(rotation=30)
        st.pyplot(fig)
    except Exception as e:
        st.error(f"Error fetching P&L for {wallet}: {e}")
        continue

    # Positions + CSV export
    try:
        state = get_clearinghouse_state(wallet)
        pos   = []
        for ap in state.get("assetPositions", []):
            p   = ap["position"]
            val = float(p.get("positionValue") or 0.0)
            if val == 0: continue
            amt = float(p.get("szi") or 0.0)
            pnl = float(p.get("unrealizedPnl") or 0.0)
            pos.append({
                "Symbol":         p.get("coin",""),
                "Side":           "Long" if amt>0 else "Short",
                "Leverage":       f"{p['leverage']['value']}X {'Cross' if p['leverage']['type']=='cross' else 'Isolated'}",
                "Value (USD)":    val,
                "Amount":         amt,
                "Entry Price":    float(p.get("entryPx") or 0.0),
                "Unrealised PnL": pnl,
                "Funding Fee":    float((p.get("cumFunding") or {}).get("allTime") or 0.0),
                "Liq. Price":     float(p.get("liquidationPx") or 0.0),
            })
        df_pos = pd.DataFrame(pos)
        if not df_pos.empty:
            st.table(df_pos.style.format({
                "Value (USD)":    "{:,.2f}",
                "Amount":         "{:,.4f}",
                "Entry Price":    "{:,.2f}",
                "Unrealised PnL": "{:,.2f}",
                "Funding Fee":    "{:,.2f}",
                "Liq. Price":     "{:,.2f}"
            }))
            csv = df_pos.to_csv(index=False)
            st.download_button(
                label="📥 Export positions as CSV",
                data=csv,
                file_name=f"{wallet}_positions.csv",
                mime="text/csv"
            )
        else:
            st.info("No active positions.")
    except Exception as e:
        st.error(f"Error fetching positions for {wallet}: {e}")

    st.markdown("---")

# ── AI Tutor Chat ──────────────────────────────────────────────────────────
st.sidebar.markdown("## 🤖 AI 튜터에게 물어보기")
user_q = st.sidebar.text_input("궁금한 점을 입력하세요…", key="user_q")
if st.sidebar.button("전송", key="send_q"):
    context = df_cust_summary.to_csv(index=False) if 'df_cust_summary' in locals() else ''
    prompt = (
        "당신은 중학생에게 금융 대시보드를 쉽게 설명하는 친절한 선생님입니다.\n"
        f"데이터:\n```\n{context}\n```\n"
        f"질문: {user_q}\n"
        "전문용어 없이, 가장 쉬운 말로 설명해주세요."
    )
    resp = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[
            {"role":"system","content":"당신은 중학생 수준으로 설명하는 AI 튜터입니다."},
            {"role":"user","content":prompt}
        ],
        temperature=0.7
    )
    answer = resp.choices[0].message.content.strip()
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    st.session_state.chat_history.append((user_q, answer))

# display chat history
if "chat_history" in st.session_state:
    for q, a in st.session_state.chat_history:
        message(q, is_user=True)
        message(a, is_user=False)

