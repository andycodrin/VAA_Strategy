"""
app.py
Interfata web pentru strategia VAA (Vigilant Asset Allocation), varianta Agresiva.
Ruleaza local cu: streamlit run app.py
"""

import streamlit as st
import pandas as pd
from logic import get_vaa_data

st.set_page_config(page_title="VAA Strategy", layout="wide")

st.title("VAA Strategy - Alocare Automata")
st.caption("Rebalansare lunara pe baza momentumului ponderat (12/4/2/1 pe 1/3/6/12 luni)")

col1, col2 = st.columns([1, 4])
with col1:
    refresh = st.button("Actualizeaza date", type="primary")
with col2:
    use_cache = st.checkbox("Foloseste cache (mai rapid, date pana la 6h vechi)", value=True)

if "vaa_data" not in st.session_state or refresh:
    with st.spinner("Se descarca preturile de la Yahoo Finance..."):
        try:
            off, dfe, verdict, winners = get_vaa_data(use_cache=use_cache and not refresh)
            st.session_state["vaa_data"] = (off, dfe, verdict, winners)
        except Exception as e:
            st.error(f"Eroare la calcularea strategiei: {e}")
            st.stop()

off, dfe, verdict, winners = st.session_state["vaa_data"]


def to_df(assets):
    df = pd.DataFrame(assets)
    df = df.rename(columns={
        "name": "Nume", "ticker": "ETF", "isin": "ISIN",
        "p0": "Pret curent", "p1": "Pret 1L", "p3": "Pret 3L",
        "p6": "Pret 6L", "p12": "Pret 12L", "score": "Momentum",
        "last_month": "Ultima luna",
    })
    cols = ["Nume", "ETF", "Pret curent", "Pret 1L", "Pret 3L", "Pret 6L", "Pret 12L", "Momentum", "Ultima luna", "ISIN"]
    df = df[cols]
    for c in ["Pret curent", "Pret 1L", "Pret 3L", "Pret 6L", "Pret 12L"]:
        df[c] = df[c].round(2)
    df["Momentum"] = df["Momentum"].round(2)
    return df


def style_table(df, winner_tickers):
    def _momentum_color(v):
        if isinstance(v, (int, float)):
            if v > 0:
                return "background-color: #1e5631; color: white"
            if v < 0:
                return "background-color: #7a2a2a; color: white"
        return ""

    def _winner_row(row):
        etf_field = str(row["ETF"])
        is_winner = any(w in etf_field for w in winner_tickers)
        if is_winner:
            return ["border: 2px solid #f2c14e; font-weight: bold"] * len(row)
        return [""] * len(row)

    styler = df.style
    fmt = {c: "{:.2f}" for c in ["Pret curent", "Pret 1L", "Pret 3L", "Pret 6L", "Pret 12L", "Momentum"]}
    styler = styler.format(fmt)

    if hasattr(styler, "map"):
        styler = styler.map(_momentum_color, subset=["Momentum"])
    else:
        styler = styler.applymap(_momentum_color, subset=["Momentum"])

    styler = styler.apply(_winner_row, axis=1)
    return styler


st.subheader("Active ofensive")
st.dataframe(style_table(to_df(off), winners), use_container_width=True, hide_index=True)

st.subheader("Active defensive")
st.dataframe(style_table(to_df(dfe), winners), use_container_width=True, hide_index=True)

st.divider()
if "100% OFENSIV" in verdict:
    st.success(f"**VERDICT: {verdict}**")
elif "50%" in verdict:
    st.warning(f"**VERDICT: {verdict}**")
else:
    st.error(f"**VERDICT: {verdict}**")

st.caption("Randurile incadrate cu chenar auriu indica ETF-ul/ETF-urile care trebuie cumparate conform verdictului curent.")

with st.expander("Regulile strategiei VAA"):
    st.markdown(
        """
        - Rebalansare in ultima zi a fiecarei luni.
        - Daca toate activele ofensive au momentum pozitiv -> 100% in ETF ofensiv cu cel mai bun scor.
        - Daca un activ ofensiv are momentum negativ -> 50% in cel mai bun activ ofensiv / 50% in cel mai bun activ defensiv.
        - Daca 2 sau mai multe active ofensive au momentum negativ -> 100% in cel mai bun activ defensiv.
        - Cele doua ETF-uri din sectorul "hot" (Energie) sunt tratate ca un singur semnal: daca oricare are
          momentum negativ, conteaza o singura data ca semnal negativ; cel cu momentum mai bun este cel recomandat.
        """
    )