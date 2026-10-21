"""
logic.py
Motor de calcul pentru strategia VAA (Vigilant Asset Allocation) - varianta Agresiva.
Descarca preturi istorice cu yfinance, calculeaza scorul de momentum ponderat
si aplica regulile de alocare definite in foaia Excel "Update Agresiv".
"""

import json
import os
from datetime import datetime, timedelta

import pandas as pd
import yfinance as yf

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "assets.json")
CACHE_PATH = os.path.join(os.path.dirname(__file__), "cache_prices.csv")
CACHE_MAX_AGE_HOURS = 6


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _cache_is_fresh():
    if not os.path.exists(CACHE_PATH):
        return False
    mtime = datetime.fromtimestamp(os.path.getmtime(CACHE_PATH))
    return datetime.now() - mtime < timedelta(hours=CACHE_MAX_AGE_HOURS)


def download_prices(tickers, use_cache=True):
    if use_cache and _cache_is_fresh():
        df = pd.read_csv(CACHE_PATH, index_col=0, parse_dates=True)
        if all(t in df.columns for t in tickers):
            return df

    raw = yf.download(
        tickers,
        period="2y",
        interval="1d",
        auto_adjust=True,
        progress=False,
        group_by="ticker",
    )

    prices = {}
    for t in tickers:
        try:
            prices[t] = raw[t]["Close"]
        except Exception:
            prices[t] = pd.Series(dtype=float)

    df = pd.DataFrame(prices)
    df = df.resample("BME").last().dropna(how="all")
    df.to_csv(CACHE_PATH)
    return df


def _score_asset(series: pd.Series):
    if series.dropna().shape[0] < 13:
        raise ValueError("Nu exista suficient istoric (minim 13 luni) pentru acest activ.")

    p0 = series.iloc[-1]
    p1 = series.iloc[-2]
    p3 = series.iloc[-4]
    p6 = series.iloc[-7]
    p12 = series.iloc[-13]

    r1 = (p0 / p1) - 1
    r3 = (p0 / p3) - 1
    r6 = (p0 / p6) - 1
    r12 = (p0 / p12) - 1

    score = (12 * r1) + (4 * r3) + (2 * r6) + (1 * r12)
    return p0, p1, p3, p6, p12, r1, score


def process_assets(asset_list, df: pd.DataFrame):
    processed = []
    for asset in asset_list:
        ticker = asset["ticker"]
        if ticker not in df.columns:
            continue
        series = df[ticker].dropna()
        p0, p1, p3, p6, p12, r1, score = _score_asset(series)
        processed.append({
            **asset,
            "p0": round(p0, 2),
            "p1": round(p1, 2),
            "p3": round(p3, 2),
            "p6": round(p6, 2),
            "p12": round(p12, 2),
            "score": round(score, 2),
            "last_month": f"{round(r1 * 100, 1)}%",
        })
    return processed


def group_energy_assets(off_processed):
    non_energy = [a for a in off_processed if "Energie" not in a["name"]]
    energy_assets = [a for a in off_processed if "Energie" in a["name"]]

    if not energy_assets:
        return non_energy

    best_energy = max(energy_assets, key=lambda x: x["score"])
    neg_count = sum(1 for a in energy_assets if a["score"] < 0)

    grouped_row = {
        **best_energy,
        "name": "Actiuni sector hot - Energie",
        "ticker": " / ".join(a["ticker"] for a in energy_assets),
        "isin": " / ".join(a["isin"] for a in energy_assets),
        "_energy_neg_signals": 1 if neg_count > 0 else 0,
        "_is_energy_group": True,
        "_best_energy_ticker": best_energy["ticker"],
    }

    return non_energy + [grouped_row]


def apply_vaa_rules(off_display, def_processed):
    total_neg_signals = 0
    for a in off_display:
        if a.get("_is_energy_group"):
            total_neg_signals += a["_energy_neg_signals"]
        elif a["score"] < 0:
            total_neg_signals += 1

    if not def_processed:
        raise ValueError("Lipsesc datele pentru activele defensive.")

    best_defensive = max(def_processed, key=lambda x: x["score"])
    best_offensive = max(off_display, key=lambda x: x["score"])

    best_offensive_ticker = best_offensive.get("_best_energy_ticker", best_offensive["ticker"])

    if total_neg_signals == 0:
        verdict = f"100% OFENSIV -> {best_offensive_ticker}"
        winners = [best_offensive_ticker]
    elif total_neg_signals == 1:
        verdict = f"50% OFENSIV ({best_offensive_ticker}) / 50% DEFENSIV ({best_defensive['ticker']})"
        winners = [best_offensive_ticker, best_defensive["ticker"]]
    else:
        verdict = f"100% DEFENSIV -> {best_defensive['ticker']}"
        winners = [best_defensive["ticker"]]

    return verdict, best_defensive, best_offensive_ticker, winners


def get_vaa_data(use_cache=True):
    config = load_config()
    all_tickers = [a["ticker"] for a in config["offensive"]] + [a["ticker"] for a in config["defensive"]]

    df = download_prices(all_tickers, use_cache=use_cache)

    off_processed = process_assets(config["offensive"], df)
    def_processed = process_assets(config["defensive"], df)

    off_display = group_energy_assets(off_processed)

    verdict, best_defensive, best_offensive_ticker, winners = apply_vaa_rules(off_display, def_processed)

    return off_display, def_processed, verdict, winners


if __name__ == "__main__":
    off, dfe, verdict, winners = get_vaa_data()
    print("=== OFENSIVE ===")
    for a in off:
        print(a)
    print("\n=== DEFENSIVE ===")
    for a in dfe:
        print(a)
    print(f"\nVERDICT: {verdict}")
    print(f"CASTIGATORI: {winners}")