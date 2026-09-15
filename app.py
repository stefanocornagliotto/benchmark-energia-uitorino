"""
Benchmark Materia Prima Gas&Power — Unione Industriali Torino
Dashboard Streamlit: confronto Convenzioni MMPOWER/MMGAS vs Top 10 offerte di mercato.

Esecuzione locale:
    streamlit run app.py

Deploy: https://share.streamlit.io  (repo Cornagli8/benchmark-energia-uitorino)
"""
import base64
import json
import re
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ------------------------------------------------------------------
# Config Plotly: disabilita zoom/pan/autoscale (UX mobile),
# mantiene fullscreen Streamlit. Rimuove anche il bottone toImage di
# Plotly: il download avviene tramite il custom button "Scarica PNG
# sezione" sotto ogni grafico (composito titolo + descrizione + chart).
# ------------------------------------------------------------------
CHART_CONFIG_NO_TOUCH = {
    "displayModeBar": False,
    "displaylogo": False,
    "scrollZoom": False,
    "doubleClick": False,
    "staticPlot": False,  # consentiamo hover per tooltip
}

# ------------------------------------------------------------------
# Config pagina + palette
# ------------------------------------------------------------------
st.set_page_config(
    page_title="Benchmark Materia Prima Gas&Power — Unione Industriali Torino",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

C_CONV_ELE   = "#6BAED6"   # azzurro carta (Convenzione MMPOWER)
C_MERC_ELE   = "#2C5784"   # blu navy soft (Top 10 ELE)
C_CONV_GAS   = "#F0A35E"   # arancione pastello (Convenzione MMGAS)
C_MERC_GAS   = "#B4495C"   # granata/bordeaux (Top 10 GAS)
C_TEXT_DARK  = "#1F2937"
C_TEXT_MUTED = "#6B7280"

ICON_ELE = "⚡"
ICON_GAS = "🔥"

LABEL_CONV_ELE = "Convenzione MMPOWER"
LABEL_MERC_ELE = "Top 10 Offerte attive sul Mercato (ELE)"
LABEL_CONV_GAS = "Convenzione MMGAS"
LABEL_MERC_GAS = "Top 10 Offerte attive sul Mercato (GAS)"

# Ordini canonici
ORDINE_ELE = ["BT <=6 kW", "BT 6-50 kW", "BT >50 kW", "MT"]
ORDINE_GAS = ["Acqua Calda", "Riscaldamento + Acqua Calda",
              "Riscaldamento", "Uso Tecnologico + Riscaldamento"]

# Etichette abbreviate per leggibilita' grafici GAS (orizzontali, no diagonale)
GAS_LABEL_SHORT = {
    "Acqua Calda": "Acqua Calda",
    "Riscaldamento + Acqua Calda": "Risc. + Acqua Calda",
    "Riscaldamento": "Riscaldamento",
    "Uso Tecnologico + Riscaldamento": "Uso Tec. + Risc.",
}


def _short_gas(t):
    return GAS_LABEL_SHORT.get(t, t)


# ------------------------------------------------------------------
# CSS
# ------------------------------------------------------------------
st.markdown(
    """
<style>
    .block-container { padding-top: 1.6rem; padding-bottom: 3rem; max-width: 1280px; }
    h1, h2, h3 { color: #0F172A; }
    h1 { border-bottom: 4px solid #6BAED6; padding-bottom: .4rem; margin-top: .6rem;
         text-align: center; }
    h2 { margin-top: 2.2rem; padding-left: .4rem; border-left: 5px solid #6BAED6; }
    h2.gas-section { border-left-color: #F0A35E; }

    /* Header loghi: 3 colonne con immagini centrate verticalmente, dimensioni
       indipendenti per ogni logo. MMPOWER spinto a sinistra, MMGAS a destra,
       UI centrato. */
    .logo-row {
        display: flex; justify-content: space-between; align-items: center;
        gap: 1rem; margin: .4rem 0 1.4rem 0; padding: 0 .5rem;
    }
    .logo-cell {
        flex: 1; display: flex; align-items: center; min-height: 140px;
    }
    .logo-cell img {
        display: block; max-width: 100%; height: auto;
        object-fit: contain;
    }
    .logo-cell.mmpower { justify-content: flex-start; }       /* a SINISTRA */
    .logo-cell.ui      { justify-content: center; }           /* CENTRO */
    .logo-cell.mmgas   { justify-content: flex-end; }         /* a DESTRA */
    .logo-cell.mmpower img { max-height: 115px; max-width: 280px; }
    .logo-cell.ui      img { max-height: 155px; max-width: 340px; } /* piu' grande */
    .logo-cell.mmgas   img { max-height: 115px; max-width: 280px; }

    .logo-pill {
        background: linear-gradient(180deg, #FFFFFF 0%, #F1F5F9 100%);
        border: 1px solid #CBD5E1; border-radius: 10px;
        padding: .55rem 1.3rem; font-weight: 700;
        color: #1F2937; box-shadow: 0 1px 3px rgba(0,0,0,.05);
    }
    .logo-pill.mmpower { color: #2C5784; border-color: #6BAED6; }
    .logo-pill.ui-torino { color: #0F172A; background: #FFFFFF; font-size: 1.05rem;
                           padding: .55rem 1.6rem; border-color: #94A3B8; }
    .logo-pill.mmgas { color: #B4495C; border-color: #F0A35E; }

    /* Riquadro periodo */
    .periodo-box {
        background: linear-gradient(180deg, #FFFFFF 0%, #F8FAFC 100%);
        border: 1px solid #CBD5E1; border-radius: 12px;
        padding: 1rem 1.4rem; margin: 1.2rem 0 1.6rem 0;
        display: flex; align-items: center; gap: 1rem;
        box-shadow: 0 1px 3px rgba(0,0,0,.04);
    }
    .periodo-label { font-size: .82rem; color: #6B7280; font-weight: 600;
                     text-transform: uppercase; letter-spacing: .5px; }
    .periodo-value { font-size: 1.3rem; font-weight: 700; color: #0F172A; margin-left:.4rem;}
    .periodo-meta { color: #6B7280; font-size: .9rem; margin-left:auto; }

    .desc-box {
        background-color: #F8FAFC; border-left: 3px solid #6BAED6;
        padding: .9rem 1.1rem; border-radius: 6px; margin: .8rem 0 1.4rem 0;
        color: #374151; font-size: .96rem;
    }
    .desc-box.gas { border-left-color: #F0A35E; }

    .footer-block {
        background-color: #F8FAFC; border: 1px solid #E5E7EB;
        border-radius: 10px; padding: 1.4rem 1.6rem; margin-top: 2.5rem;
    }

    .forn-pill {
        display: inline-block; padding: .3rem .7rem; margin: .25rem;
        background: #FFFFFF; border: 1px solid #D1D5DB; border-radius: 999px;
        font-size: .88rem; color: #1F2937;
    }
    .forn-pill a { color: #2C5784; text-decoration: none; }
    .forn-pill a:hover { text-decoration: underline; }

    .num-evidenza {
        display: inline-block; background: linear-gradient(180deg,#F8FAFC,#E0E7FF);
        color: #1E3A8A; padding: .1rem .5rem; border-radius: 6px;
        font-weight: 700;
    }
</style>
""",
    unsafe_allow_html=True,
)


# ------------------------------------------------------------------
# Caricamento dati
# ------------------------------------------------------------------
def carica_dati():
    p = Path(__file__).parent / "data" / "data.json"
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


D = carica_dati()
if D is None:
    st.error(
        "⚠️ File `data/data.json` non trovato.\n\n"
        "Esegui la **cella 5.6** del notebook `Benchmark Confronto.ipynb` per generarlo, "
        "poi `git push` per aggiornare l'app online."
    )
    st.stop()

# Backward compatibility: se il data.json è in formato vecchio (no multi-mese),
# lo trasformiamo on-the-fly in formato v4 (mesi_disponibili / dati_per_mese)
if "dati_per_mese" not in D:
    _mese = D.get("meta", {}).get("mese_riferimento", "2026-03")
    D = {
        "version": 0,
        "meta": {
            "mese_default": _mese,
            "coeff_perdita_BT": D.get("meta", {}).get("coeff_perdita_BT", 0.10),
            "coeff_perdita_MT": D.get("meta", {}).get("coeff_perdita_MT", 0.038),
            "top_n": D.get("meta", {}).get("top_n", 10),
            "n_offerte_totali": D.get("meta", {}).get("n_offerte_totali", 0),
        },
        "mesi_disponibili": [_mese],
        "dati_per_mese": {_mese: {
            "meta_mese": {
                "mese": _mese,
                "PUN_eur_kWh": D.get("meta", {}).get("PUN_eur_kWh", 0),
                "PUN_TOT_eur_kWh": D.get("meta", {}).get("PUN_eur_kWh", 0),
                "PUN_BT_eur_kWh":  D.get("meta", {}).get("PUN_eur_kWh", 0),
                "PUN_MT_eur_kWh":  D.get("meta", {}).get("PUN_eur_kWh", 0),
                "PSV_eur_Smc": D.get("meta", {}).get("PSV_eur_Smc", 0),
                "generazione_BT": D.get("meta", {}).get("generazione_BT", 0),
                "perdite_BT":     D.get("meta", {}).get("perdite_BT", 0),
                "mp_conv_BT":     D.get("meta", {}).get("mp_conv_BT", 0),
                "generazione_MT": D.get("meta", {}).get("generazione_MT", 0),
                "perdite_MT":     D.get("meta", {}).get("perdite_MT", 0),
                "mp_conv_MT":     D.get("meta", {}).get("mp_conv_MT", 0),
                "consumo_ele_totale_kwh": D.get("meta", {}).get("consumo_ele_totale_kwh", 0),
                "consumo_gas_totale_smc": D.get("meta", {}).get("consumo_gas_totale_smc", 0),
                "n_offerte_totali": D.get("meta", {}).get("n_offerte_totali", 0),
            },
            "confronto": D.get("confronto", []),
            "generale":  D.get("generale", []),
            "sensitivity": D.get("sensitivity", {"fattori": [1.0], "per_fascia": {}}),
        }},
        "offerte_tutte": D.get("offerte_tutte", []),
        "fornitori": D.get("fornitori", []),
        "fornitori_non_monitorati": D.get("fornitori_non_monitorati", []),
        "portali": D.get("portali", []),
    }

mesi_disp = D["mesi_disponibili"]
if not mesi_disp:
    st.warning("⚠️ Nessun mese disponibile nel file dati.")
    st.stop()


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------
def mese_label(yyyymm: str) -> str:
    mesi = ["", "Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno",
            "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"]
    # Caso aggregato: ritorna stringa speciale
    if yyyymm == "__aggregato__" or "-" not in str(yyyymm):
        return "Tutti i mesi disponibili"
    y, m = yyyymm.split("-")
    return f"{mesi[int(m)]} {y}"


def _mese_aa(yyyymm: str) -> str:
    """Etichetta compatta 'mar-26'; per l'aggregato ritorna stringa vuota
    (il caption omette la parte 'mese-aa')."""
    ab = ["", "gen", "feb", "mar", "apr", "mag", "giu",
          "lug", "ago", "set", "ott", "nov", "dic"]
    if yyyymm == "__aggregato__" or "-" not in str(yyyymm):
        return ""
    y, m = yyyymm.split("-")
    return f"{ab[int(m)]}-{y[-2:]}"


def interp_sens(key: str, fattore: float, fallback_value: float = None) -> float:
    """Interpola linearmente il benchmark mercato sul fattore di consumo.
    Se per_fascia non disponibile (dati vecchi), usa il vettore totale ELE/GAS.
    Se nemmeno quello c'e', ritorna fallback_value."""
    fs = sens["fattori"]
    vs = sens.get("per_fascia", {}).get(key)
    if not vs:
        # Fallback: usa il vettore aggregato ELE o GAS (sens["ELE"]/sens["GAS"])
        comm = key.split("|")[0]
        vs = sens.get(comm)
    if not vs:
        return fallback_value
    if fattore <= fs[0]:
        return vs[0]
    if fattore >= fs[-1]:
        return vs[-1]
    for i in range(len(fs) - 1):
        if fs[i] <= fattore <= fs[i + 1]:
            t = (fattore - fs[i]) / (fs[i + 1] - fs[i])
            return vs[i] + t * (vs[i + 1] - vs[i])
    return vs[-1]


# ------------------------------------------------------------------
# HEADER: 3 loghi + titolo + periodo di osservazione
# ------------------------------------------------------------------
loghi_dir = Path(__file__).parent
logo_files = {
    "mmpower": loghi_dir / "logo_mmpower.png",
    "ui":      loghi_dir / "logo_ui.png",
    "mmgas":   loghi_dir / "logo_mmgas.png",
}


def _logo_img_or_placeholder(key, placeholder_html):
    p = logo_files[key]
    if p.exists():
        b64 = base64.b64encode(p.read_bytes()).decode("ascii")
        return f'<img src="data:image/png;base64,{b64}" alt="{key}" />'
    return placeholder_html


st.markdown(
    f"""
<div class="logo-row">
  <div class="logo-cell mmpower">{_logo_img_or_placeholder("mmpower",
       '<div class="logo-pill mmpower">⚡ MMPOWER</div>')}</div>
  <div class="logo-cell ui">{_logo_img_or_placeholder("ui",
       '<div class="logo-pill ui-torino">UNIONE INDUSTRIALI TORINO</div>')}</div>
  <div class="logo-cell mmgas">{_logo_img_or_placeholder("mmgas",
       '<div class="logo-pill mmgas">🔥 MMGAS</div>')}</div>
</div>
""",
    unsafe_allow_html=True,
)

mancanti = [k for k, p in logo_files.items() if not p.exists()]
if mancanti:
    st.caption(
        "<div style='text-align:center; color:#9CA3AF; font-size:.78rem;'>"
        "💡 Per sostituire i placeholder, salva "
        + ", ".join(f"<code>logo_{k}.png</code>" for k in mancanti)
        + " nella cartella <code>pubblica_grafici/</code>.</div>",
        unsafe_allow_html=True,
    )

# Titolo + descrizione introduttiva in un unico blocco con barra blu in fondo
st.markdown(
    """
<div style="text-align:center; border-bottom: 4px solid #6BAED6;
            padding-bottom: 1rem; margin: .6rem 0 1.6rem 0;">

  <h1 style="margin: 0 0 .7rem 0; padding: 0; border: none;
             font-family: 'Inter', 'Segoe UI Variable', 'Segoe UI',
                          system-ui, -apple-system, 'Helvetica Neue', sans-serif;
             font-size: 2.9rem; font-weight: 800; letter-spacing: -0.025em;
             line-height: 1.1; color: #0F172A;">
    Benchmark Materia Prima Gas&amp;Power
  </h1>

  <p style="font-family: Georgia, 'Bookman Old Style', Cambria, serif;
            font-style: italic; font-size: 1.05rem; line-height: 1.55;
            color:#4B5563; margin: 0 auto; max-width: 880px;">
    Confronto fra il Prezzo per la Materia prima delle Convenzioni
    <span style="color:#6BAED6; font-style:normal; font-weight:700;">MMPOWER</span> e
    <span style="color:#F0A35E; font-style:normal; font-weight:700;">MMGAS</span>
    dell'Unione Industriali Torino e quello di cui alle 10 migliori offerte
    indicizzate attive sul mercato libero italiano, su diversi periodi di
    osservazione. Pagina interattiva con grafici per classe&nbsp;/&nbsp;tipologia
    e schede operative delle convenzioni in essere.
  </p>
</div>
""",
    unsafe_allow_html=True,
)

# --- Funzione: calcola un mese sintetico 'aggregato' su tutti i mesi disponibili,
#               con prezzi mediati ponderando sui consumi del mese. ---
KEY_AGGREGATO = "__aggregato__"


def aggrega_mesi(D_in):
    """Ritorna un dict con la struttura di dati_per_mese[m] aggregato sui mesi
    disponibili. Pesi = consumi (kWh per ELE, Smc per GAS) di ciascun mese.
    consumo_mese di confronto = SOMMA dei consumi del mese per (commodity, tipologia);
    n_utenze = MEDIA arrotondata (le stesse utenze nei mesi)."""
    mesi_dict = D_in.get("dati_per_mese", {})
    if not mesi_dict:
        return None
    mesi_keys = sorted(mesi_dict.keys())
    metas = [mesi_dict[k]["meta_mese"] for k in mesi_keys]

    # Pesi totali ELE/GAS/BT/MT
    cons_ele = [float(m.get("consumo_ele_totale_kwh", 0)) for m in metas]
    cons_gas = [float(m.get("consumo_gas_totale_smc", 0)) for m in metas]
    cons_bt = []
    cons_mt = []
    for k in mesi_keys:
        ele_recs = [r for r in mesi_dict[k]["confronto"] if r["commodity"] == "ELE"]
        cons_bt.append(sum(float(r["consumo_mese"])
                            for r in ele_recs if str(r["tipologia"]).startswith("BT")))
        cons_mt.append(sum(float(r["consumo_mese"])
                            for r in ele_recs if r["tipologia"] == "MT"))
    tot_ele, tot_gas = sum(cons_ele), sum(cons_gas)
    tot_bt, tot_mt = sum(cons_bt), sum(cons_mt)

    def _wa(values, weights):
        s = sum(weights)
        if s == 0:
            return sum(values) / len(values) if values else 0.0
        return sum(v * w for v, w in zip(values, weights)) / s

    def _ele(key): return _wa([float(m.get(key, 0)) for m in metas], cons_ele)
    def _gas(key): return _wa([float(m.get(key, 0)) for m in metas], cons_gas)
    def _bt(key):  return _wa([float(m.get(key, 0)) for m in metas], cons_bt)
    def _mt(key):  return _wa([float(m.get(key, 0)) for m in metas], cons_mt)

    meta_aggr = {
        "mese": KEY_AGGREGATO,
        "PUN_eur_kWh":      _ele("PUN_eur_kWh"),
        "PSV_eur_Smc":      _gas("PSV_eur_Smc"),
        "generazione_BT":   _bt("generazione_BT"),
        "perdite_BT":       _bt("perdite_BT"),
        "mp_conv_BT":       _bt("mp_conv_BT"),
        "generazione_MT":   _mt("generazione_MT"),
        "perdite_MT":       _mt("perdite_MT"),
        "mp_conv_MT":       _mt("mp_conv_MT"),
        "consumo_ele_totale_kwh": tot_ele,
        "consumo_gas_totale_smc": tot_gas,
        "PUN_TOT_eur_kWh":  _ele("PUN_TOT_eur_kWh"),
        "PUN_BT_eur_kWh":   _bt("PUN_BT_eur_kWh"),
        "PUN_MT_eur_kWh":   _mt("PUN_MT_eur_kWh"),
        "PUN_F1_eur_kWh":   _ele("PUN_F1_eur_kWh"),
        "PUN_F2_eur_kWh":   _ele("PUN_F2_eur_kWh"),
        "PUN_F3_eur_kWh":   _ele("PUN_F3_eur_kWh"),
    }

    # Aggrega confronto per (commodity, tipologia)
    by_tip = {}
    for k in mesi_keys:
        for r in mesi_dict[k]["confronto"]:
            by_tip.setdefault((r["commodity"], r["tipologia"]), []).append(r)
    new_conf = []
    for (comm, tip), recs in by_tip.items():
        cons = [float(r["consumo_mese"]) for r in recs]
        mp_avg = _wa([float(r["materia_prima_conv"]) for r in recs], cons)
        merc_avg = _wa([float(r["benchmark_mercato"]) for r in recs], cons)
        n_avg = round(sum(int(r["n_utenze"]) for r in recs) / len(recs))
        new_conf.append({
            "commodity": comm, "tipologia": tip,
            "generazione_conv": None, "perdite_conv": None,
            "materia_prima_conv": round(mp_avg, 2), "unita_mp": recs[0]["unita_mp"],
            "consumo_mese": sum(cons), "n_utenze": int(n_avg),
            "benchmark_mercato": round(merc_avg, 2),
            "n_offerte_usate": recs[0].get("n_offerte_usate", 10),
            "delta_mercato_vs_conv": round(merc_avg - mp_avg, 2),
            "delta_%": round((merc_avg - mp_avg) / mp_avg * 100, 1) if mp_avg else 0,
        })

    # Generale aggregato
    new_gen = []
    ele_sub = [r for r in new_conf if r["commodity"] == "ELE"]
    gas_sub = [r for r in new_conf if r["commodity"] == "GAS"]
    if ele_sub:
        mp_c = sum(r["materia_prima_conv"] for r in ele_sub) / len(ele_sub)
        m_c = sum(r["benchmark_mercato"] for r in ele_sub) / len(ele_sub)
        new_gen.append({"commodity": "ELE", "unita": "€/MWh",
                         "MP_convenzione": round(mp_c, 2),
                         "benchmark_mercato": round(m_c, 2),
                         "criterio": "media semplice 4 fasce (BT/MT equo)",
                         "delta": round(m_c - mp_c, 2),
                         "delta_%": round((m_c - mp_c) / mp_c * 100, 1) if mp_c else 0})
    if gas_sub:
        w_tot = sum(r["consumo_mese"] for r in gas_sub)
        mp_c = sum(r["materia_prima_conv"] * r["consumo_mese"]
                    for r in gas_sub) / w_tot if w_tot else 0
        m_c = sum(r["benchmark_mercato"] * r["consumo_mese"]
                   for r in gas_sub) / w_tot if w_tot else 0
        new_gen.append({"commodity": "GAS", "unita": "c€/Smc",
                         "MP_convenzione": round(mp_c, 2),
                         "benchmark_mercato": round(m_c, 2),
                         "criterio": "media ponderata sui consumi",
                         "delta": round(m_c - mp_c, 2),
                         "delta_%": round((m_c - mp_c) / mp_c * 100, 1) if mp_c else 0})

    # Sensitivity per_fascia: media ponderata sui consumi della fascia attraverso i mesi
    fattori = mesi_dict[mesi_keys[0]].get("sensitivity", {}).get("fattori", [])
    sens_per = {}
    for (comm, tip), recs in by_tip.items():
        key = f"{comm}|{tip}"
        weights = [float(r["consumo_mese"]) for r in recs]
        all_vals = []
        for k in mesi_keys:
            v = mesi_dict[k].get("sensitivity", {}).get("per_fascia", {}).get(key)
            if v:
                all_vals.append(v)
        if not all_vals:
            continue
        # Allinea al numero di fattori del mese piu' breve
        n = min(len(v) for v in all_vals)
        agg_vals = []
        for i in range(n):
            vs = [v[i] for v in all_vals]
            ws = weights[:len(vs)]
            agg_vals.append(round(_wa(vs, ws), 3))
        sens_per[key] = agg_vals
    sens_aggr = {"fattori": fattori, "per_fascia": sens_per}

    return {"meta_mese": meta_aggr, "confronto": new_conf,
            "generale": new_gen, "sensitivity": sens_aggr}


# --- Lista mesi + opzione 'Tutti i mesi disponibili' ---
mesi_options = list(mesi_disp)
if len(mesi_disp) > 1:
    mesi_options.append(KEY_AGGREGATO)


def _label_mese_o_aggregato(m):
    if m == KEY_AGGREGATO:
        return f"📊 Tutti i mesi disponibili ({len(mesi_disp)})"
    return mese_label(m)


# --- Dropdown SELEZIONE MESE (in alto, governa tutti i grafici) ---
mese_default = D.get("meta", {}).get("mese_default", mesi_disp[-1])
if mese_default not in mesi_disp:
    mese_default = mesi_disp[-1]

col_sel_lbl, col_sel_drop, col_sel_fill = st.columns([1, 2, 2])
with col_sel_lbl:
    st.markdown(
        "<div style='padding-top:.55rem; font-weight:700; color:#1F2937;'>"
        "📅 Periodo di osservazione:</div>",
        unsafe_allow_html=True,
    )
with col_sel_drop:
    if len(mesi_options) > 1:
        mese_sel = st.selectbox(
            "Mese", mesi_options, index=mesi_options.index(mese_default),
            format_func=_label_mese_o_aggregato, key="mese_sel",
            label_visibility="collapsed",
        )
    else:
        mese_sel = mese_default
        st.markdown(
            f"<div style='padding-top:.55rem;color:#6B7280;'>"
            f"{mese_label(mese_sel)} <span style='color:#9CA3AF;font-size:.85rem;'>"
            f"(unico mese disponibile)</span></div>",
            unsafe_allow_html=True,
        )

# --- Estrai i dati del mese selezionato (o aggregato calcolato al volo) ---
if mese_sel == KEY_AGGREGATO:
    dati_mese = aggrega_mesi(D)
else:
    dati_mese = D["dati_per_mese"][mese_sel]
meta = dati_mese["meta_mese"]
df_conf = pd.DataFrame(dati_mese["confronto"])
df_gen = pd.DataFrame(dati_mese["generale"])
sens = dati_mese["sensitivity"]
meta["n_offerte_totali"] = meta.get("n_offerte_totali") or D["meta"].get("n_offerte_totali", 0)
meta["coeff_perdita_BT"] = D["meta"].get("coeff_perdita_BT", 0.10)
meta["coeff_perdita_MT"] = D["meta"].get("coeff_perdita_MT", 0.038)

if len(df_conf) == 0:
    st.warning(f"⚠️ Nessun dato per il mese {mese_label(mese_sel)}.")
    st.stop()


# ------------------------------------------------------------------
# Helper benchmark: ricalcola live il prezzo "all-in" delle offerte
# ELE:  p = base + spread + (base+spread)*coeff_perdita + (quota_anno/12)/cons_singolo
# GAS:  p = base + spread + quota_anno / cons_singolo_annuo   (Opt.4)
#
# La formula GAS applica il metodo Opt.4: la quota fissa dell'offerta
# (€/PDR/anno) e' ripartita sul consumo aggregato annuale per PDR della
# tipologia (Smc/PDR/anno) invece che sul consumo mensile. Questo evita
# valori artefatti nei mesi con consumo trascurabile (es. Acqua Calda
# estiva) dove la vecchia formula spalmata mensile esplodeva.
# ------------------------------------------------------------------
offerte_anon = D.get("offerte_anonime", [])
TOP_N_GENERALE = 5


def _prezzi_offerte_mese(commodity: str, base_price: float,
                          cons_singolo: float, coeff_perdita: float,
                          cons_singolo_annuo=None):
    """Ricostruisce i prezzi mensili di CIASCUNA offerta (non ordinati, con
    indice globale preservato). Ritorna una lista [(idx, prezzo €/kWh o €/Smc), ...].
    Se cons_singolo non è positivo o non ci sono offerte, ritorna [].

    cons_singolo_annuo: per il gas (Opt.4), rappresenta il consumo aggregato
    annuo per PDR della tipologia sul periodo di osservazione (Smc/PDR/anno).
    Se non fornito o non positivo, il gas fa fallback alla formula mensile
    (comportamento pre-Opt.4).
    """
    if cons_singolo <= 0 or not offerte_anon:
        return []
    out = []
    for i, o in enumerate(offerte_anon):
        if o["commodity"] != commodity:
            continue
        spread = float(o["spread"])
        quota = float(o["quota_eur_anno"])
        # Opt.4 (GAS e ELE): quota fissa ripartita sul consumo annuo aggregato
        # della classe/tipologia. Riflette la struttura contrattuale reale
        # delle offerte PLACET (spread €/kWh|Smc + quota fissa €/POD|PDR/anno).
        if cons_singolo_annuo and cons_singolo_annuo > 0:
            quota_unit = quota / cons_singolo_annuo
        else:
            quota_unit = (quota / 12.0) / cons_singolo if cons_singolo else 0.0
        p = base_price + spread + (base_price + spread) * coeff_perdita + quota_unit
        out.append((i, p))
    return out


def _bench_periodo(commodity: str, tipologia=None, top_n: int = 10) -> float:
    """Benchmark del periodo (singolo o aggregato).

    Vista singolo mese: per il mese selezionato, ricostruisce i prezzi di tutte
    le offerte del commodity con i parametri della sezione, ordina crescente,
    prende la media dei primi top_n → benchmark.

    Vista aggregata ("Tutti i periodi disponibili"): per CIASCUNA offerta si
    calcola il prezzo medio ponderato sui consumi mensili (l'offerta è quindi
    valutata come 'contratto stabile sul periodo', non ricomposta mese per
    mese). Le offerte così mediate vengono poi ordinate e le prime top_n
    aggregate per media aritmetica → benchmark aggregato. Questo criterio
    riflette la scelta contrattuale reale: un cliente non cambia offerta ogni
    mese, quindi il benchmark aggregato deve rispecchiare la performance
    dell'offerta come contratto duraturo sul periodo osservato.

    tipologia=None → vista generale (sezione 1): considera tutte le
        classi/tipologie del commodity, base = PUN_TOT (ELE) | PSV (GAS),
        coeff = coeff_mix BT/MT del mese (ELE) | 0 (GAS).
    tipologia="..." → singola classe/tipologia (sezioni 2/3): base = PUN della
        classe (BT/MT) | PSV, coeff specifico della classe.
    """
    mesi_iter = list(mesi_disp) if _is_aggregato else [mese_sel]
    cb_default = float(D.get("meta", {}).get("coeff_perdita_BT", 0.10))
    cm_default = float(D.get("meta", {}).get("coeff_perdita_MT", 0.038))

    # Opt.4 (GAS e ELE): precalcolo il consumo annuo aggregato per POD/PDR
    # della classe/tipologia (o del totale commodity se tipologia=None) su
    # TUTTI i mesi disponibili. Questo valore e' stabile (non dipende dal
    # mese selezionato) ed e' usato per ripartire la quota fissa annua di
    # ciascuna offerta.
    cons_singolo_annuo_gas = None
    _cons_ann_tot = 0.0
    _n_ut_max = 0
    _n_mesi_disp = 0
    for _m in mesi_disp:
        _dm = D.get("dati_per_mese", {}).get(_m)
        if not _dm:
            continue
        _recs = [r for r in _dm["confronto"] if r["commodity"] == commodity]
        if tipologia is not None:
            _recs = [r for r in _recs if r["tipologia"] == tipologia]
        if not _recs:
            continue
        _n_mesi_disp += 1
        for _r in _recs:
            _cons_ann_tot += float(_r["consumo_mese"])
            _n_ut_max = max(_n_ut_max, int(_r["n_utenze"]))
    if _n_ut_max > 0 and _cons_ann_tot > 0 and _n_mesi_disp > 0:
        # Annualizza: la somma sui mesi osservati va scalata a 12 mesi
        # per rappresentare correttamente il consumo annuo per POD/PDR
        # (la quota fissa delle offerte e' espressa in EUR/anno).
        cons_singolo_annuo_gas = (_cons_ann_tot / _n_ut_max) * (12.0 / _n_mesi_disp)

    # Per ogni mese: prezzi di ciascuna offerta + consumo totale del mese
    # per la classe/tipologia richiesta.
    prezzi_per_offerta: dict[int, list[float]] = {}
    cons_per_mese_utile: list[float] = []  # allineato con l'ordine di riempimento

    for mese in mesi_iter:
        dm = D.get("dati_per_mese", {}).get(mese)
        if not dm:
            continue
        meta_m = dm["meta_mese"]
        recs = [r for r in dm["confronto"] if r["commodity"] == commodity]
        if tipologia is not None:
            recs = [r for r in recs if r["tipologia"] == tipologia]
        if not recs:
            continue
        cons_mese = sum(float(r["consumo_mese"]) for r in recs)
        n_ut = sum(int(r["n_utenze"]) for r in recs)
        if cons_mese <= 0 or n_ut <= 0:
            continue
        cons_singolo = cons_mese / n_ut
        if commodity == "ELE":
            if tipologia is None:
                base = float(meta_m.get("PUN_TOT_eur_kWh")
                             or meta_m.get("PUN_eur_kWh", 0))
                cons_bt = sum(float(r["consumo_mese"]) for r in recs
                              if str(r["tipologia"]).startswith("BT"))
                cons_mt = sum(float(r["consumo_mese"]) for r in recs
                              if r["tipologia"] == "MT")
                coeff = ((cb_default * cons_bt + cm_default * cons_mt)
                         / cons_mese) if cons_mese > 0 else cb_default
            elif tipologia == "MT":
                base = float(meta_m.get("PUN_MT_eur_kWh")
                             or meta_m.get("PUN_eur_kWh", 0))
                coeff = cm_default
            else:
                base = float(meta_m.get("PUN_BT_eur_kWh")
                             or meta_m.get("PUN_eur_kWh", 0))
                coeff = cb_default
        else:
            base = float(meta_m.get("PSV_eur_Smc", 0))
            coeff = 0.0

        prezzi_mese = _prezzi_offerte_mese(commodity, base, cons_singolo, coeff,
                                            cons_singolo_annuo=cons_singolo_annuo_gas)
        if not prezzi_mese:
            continue
        for offer_idx, p in prezzi_mese:
            prezzi_per_offerta.setdefault(offer_idx, []).append(p)
        cons_per_mese_utile.append(cons_mese)

    if not prezzi_per_offerta:
        return 0.0

    # Media ponderata sui consumi mensili PER OGNI OFFERTA.
    # Nel caso singolo mese la lista ha 1 elemento → prezzo del mese stesso.
    prezzi_medi = []
    tot_cons = sum(cons_per_mese_utile)
    for offer_idx, prezzi_off in prezzi_per_offerta.items():
        if len(prezzi_off) != len(cons_per_mese_utile):
            # Offerta non calcolata in tutti i mesi (raro): media semplice
            prezzo_medio = sum(prezzi_off) / len(prezzi_off)
        elif tot_cons > 0:
            prezzo_medio = sum(p * c for p, c in
                                zip(prezzi_off, cons_per_mese_utile)) / tot_cons
        else:
            prezzo_medio = sum(prezzi_off) / len(prezzi_off)
        prezzi_medi.append(prezzo_medio)

    # Ordina crescente e prendi top_n.
    prezzi_medi.sort()
    top = prezzi_medi[:min(top_n, len(prezzi_medi))]
    if not top:
        return 0.0
    mean_price = sum(top) / len(top)
    return mean_price * (1000 if commodity == "ELE" else 100)


def _generale_top5(commodity: str):
    """Sezione 1 — Confronto generale. MP_convenzione = media ponderata sui
    consumi delle 4 classi/tipologie. Benchmark calcolato con Approccio B
    (media ponderata dei benchmark mensili)."""
    df_c = df_conf[df_conf["commodity"] == commodity].copy()
    if df_c.empty:
        return {"MP_convenzione": 0.0, "benchmark_mercato": 0.0}
    cons = df_c["consumo_mese"].astype(float)
    mp_conv = float((df_c["materia_prima_conv"].astype(float) * cons).sum()
                    / cons.sum()) if cons.sum() > 0 else 0.0
    bench = _bench_periodo(commodity, tipologia=None, top_n=TOP_N_GENERALE)
    return {"MP_convenzione": round(mp_conv, 2),
            "benchmark_mercato": round(float(bench or 0), 2)}

# --- Riquadro PERIODO DI OSSERVAZIONE ---
# Singolo mese: mostra i PUN ARERA per fasce orarie (F1/F2/F3) e il PSV.
# Aggregato 'Tutti i mesi': mostra PUN/PSV ponderati ai consumi.
_pun_tot = meta.get("PUN_TOT_eur_kWh") or meta.get("PUN_eur_kWh", 0)
_pun_bt  = meta.get("PUN_BT_eur_kWh")  or meta.get("PUN_eur_kWh", 0)
_pun_mt  = meta.get("PUN_MT_eur_kWh")  or meta.get("PUN_eur_kWh", 0)
_pun_f1  = meta.get("PUN_F1_eur_kWh") or 0
_pun_f2  = meta.get("PUN_F2_eur_kWh") or 0
_pun_f3  = meta.get("PUN_F3_eur_kWh") or 0
_is_aggregato = (mese_sel == KEY_AGGREGATO)
# Numero di mesi su cui è calcolato il dato corrente. Serve a normalizzare
# i consumi-per-utenza nei ricalcoli del benchmark: la formula impiega un
# consumo MENSILE (quota fissa annua / 12), ma in modalità aggregata il
# campo "consumo_mese" è la SOMMA su N mesi → va divisa per N.
_n_mesi_aggr = len(mesi_disp) if _is_aggregato else 1

_label_pun = "PUN ponderato ai consumi per fasce" if _is_aggregato else "PUN per fasce"
_label_psv = "PSV ponderato ai consumi" if _is_aggregato else "PSV"

# IMPORTANTE: tutto l'HTML del riquadro deve stare su una sola riga (o senza
# indentazione iniziale) per non essere interpretato come code block da Streamlit.
_html_periodo = (
    f'<div class="periodo-box">'
    f'<div style="display:flex; flex-direction:column; flex:1;">'
    f'<span class="periodo-label">📅 Periodo di osservazione</span>'
    f'<span class="periodo-value">{mese_label(meta["mese"])}</span>'
    f'</div>'
    f'<div style="display:flex; flex-direction:column; gap:.25rem; text-align:right; '
    f'border-left:1px solid #CBD5E1; padding-left:1.2rem;">'
    f'<span style="color:#374151; font-size:.9rem;">'
    f'<span style="color:#6B7280;">{_label_pun}</span>&nbsp;&nbsp;'
    f'<b style="color:#16A34A;">F1 {_pun_f1:.4f}</b>&nbsp;·&nbsp;'
    f'<b style="color:#16A34A;">F2 {_pun_f2:.4f}</b>&nbsp;·&nbsp;'
    f'<b style="color:#16A34A;">F3 {_pun_f3:.4f}</b>&nbsp;'
    f'<b style="color:#16A34A;">€/kWh</b>'
    f'</span>'
    f'<span style="color:#374151; font-size:.9rem;">'
    f'<span style="color:#6B7280;">{_label_psv}</span>&nbsp;'
    f'<b style="color:#16A34A;">{meta["PSV_eur_Smc"]:.4f} €/Smc</b>'
    f'</span>'
    f'</div></div>'
)
st.markdown(_html_periodo, unsafe_allow_html=True)


# ------------------------------------------------------------------
# SEZIONE 1 — Confronto generale
# ------------------------------------------------------------------
st.header("1️⃣ Confronto generale")

st.markdown(
    f"""
<div class="desc-box">
Confronto fra il <b>Prezzo per la Materia prima riconosciuta dalle
Convenzioni</b> e il <b>benchmark</b> calcolato come media delle <b>{TOP_N_GENERALE} migliori
offerte attive sul mercato libero</b>, applicate a un'utenza media del campione
convenzionato. Per ciascuna offerta il prezzo è ricostruito come
<i>PUN/PSV indicizzato + spread + eventuali altri corrispettivi fissi o
variabili al consumo</i>; per il solo <b>elettrico</b> si aggiungono le
<b>perdite di rete</b>.
La quotazione di riferimento è il <b>PUN&nbsp;TOT</b> (PUN ponderato per fasce, mediato
BT/MT sui consumi reali) per l'elettrico e il <b>PSV</b> per il gas.
</div>
""",
    unsafe_allow_html=True,
)

g_ele = _generale_top5("ELE")
g_gas = _generale_top5("GAS")
LABEL_TOP5_ELE = f"Top {TOP_N_GENERALE} Offerte attive sul Mercato (ELE)"
LABEL_TOP5_GAS = f"Top {TOP_N_GENERALE} Offerte attive sul Mercato (GAS)"


def bar_confronto_v2(val_conv, val_merc, color_conv, color_merc, titolo,
                     label_conv, label_merc, unita):
    """Bar chart con legenda IN BASSO, barre piu' larghe, delta evidenziato."""
    delta = val_merc - val_conv
    delta_pct = (delta / val_conv * 100) if val_conv else 0
    color_delta = "#B4495C" if delta > 0 else "#2F855A"
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=[label_conv], y=[val_conv], name=label_conv,
        marker=dict(color=color_conv, line=dict(color="#FFFFFF", width=2)),
        text=[f"<b>{val_conv:.2f}</b>"], textposition="outside",
        textfont=dict(size=15, color=C_TEXT_DARK), width=0.65,
    ))
    fig.add_trace(go.Bar(
        x=[label_merc], y=[val_merc], name=label_merc,
        marker=dict(color=color_merc, line=dict(color="#FFFFFF", width=2)),
        text=[f"<b>{val_merc:.2f}</b>"], textposition="outside",
        textfont=dict(size=15, color=C_TEXT_DARK), width=0.65,
    ))
    fig.update_layout(
        title=dict(text=titolo, font=dict(size=16, color=C_TEXT_DARK)),
        showlegend=True,
        dragmode=False,  # disabilita zoom/pan/select tramite drag o touch
        legend=dict(
            orientation="h", x=0.5, xanchor="center",
            y=-0.18, yanchor="top",
            bgcolor="#F8FAFC", bordercolor="#CBD5E1", borderwidth=1,
            font=dict(size=11),
        ),
        height=460, plot_bgcolor="#FFFFFF", paper_bgcolor="#FFFFFF",
        yaxis=dict(title=unita, gridcolor="#E5E7EB", zerolinecolor="#E5E7EB",
                    fixedrange=True),
        xaxis=dict(showticklabels=False, range=[-0.6, 1.6], fixedrange=True),
        bargap=0.18,
        margin=dict(t=80, b=110, l=60, r=40),
        annotations=[
            dict(
                x=0.5, y=1.13, xref="paper", yref="paper",
                text=(f"<span style='color:{color_delta}; font-weight:700; "
                      f"font-size:1.05rem;'>Δ {delta:+.2f} {unita} "
                      f"({delta_pct:+.1f}%)</span>"),
                showarrow=False,
            ),
        ],
    )
    return fig


col_ele, col_gas = st.columns(2)
with col_ele:
    st.plotly_chart(bar_confronto_v2(
        g_ele["MP_convenzione"], g_ele["benchmark_mercato"],
        C_CONV_ELE, C_MERC_ELE,
        f"{ICON_ELE} Elettrico — €/MWh",
        LABEL_CONV_ELE, LABEL_TOP5_ELE, "€/MWh",
    ), use_container_width=True, config=CHART_CONFIG_NO_TOUCH)
with col_gas:
    st.plotly_chart(bar_confronto_v2(
        g_gas["MP_convenzione"], g_gas["benchmark_mercato"],
        C_CONV_GAS, C_MERC_GAS,
        f"{ICON_GAS} Gas — c€/Smc",
        LABEL_CONV_GAS, LABEL_TOP5_GAS, "c€/Smc",
    ), use_container_width=True, config=CHART_CONFIG_NO_TOUCH)


# ------------------------------------------------------------------
# Grafico a barre raggruppate (riusato in §2, §3, §4)
# ------------------------------------------------------------------
def _auto_yrange(y_conv, y_merc, floor=0, step=5, pad=0.12):
    """Range Y con floor fisso (100 €/MWh per ELE, 20 c€/Smc per GAS) e top
    calcolato dinamicamente sui valori del mese visualizzato, lasciando un
    margine in alto per non far uscire le etichette numeriche dal frame."""
    vals = [v for v in (list(y_conv) + list(y_merc)) if v is not None]
    if not vals:
        return None
    vmax = max(vals)
    rng = max(vmax - floor, 1.0)
    ymax = vmax + rng * pad
    import math
    ymax = math.ceil(ymax / step) * step
    return [floor, ymax]


def bar_gruppi(x_labels, y_conv, y_merc, color_conv, color_merc,
               label_conv, label_merc, unita, height=480, xtickangle=0,
               yrange=None):
    fig = go.Figure()
    fig.add_trace(go.Bar(
        name=label_conv, x=x_labels, y=y_conv,
        marker=dict(color=color_conv, line=dict(color="#FFFFFF", width=1.5)),
        text=[f"<b>{v:.2f}</b>" for v in y_conv],
        textposition="outside", textfont=dict(size=12, color=C_TEXT_DARK),
    ))
    fig.add_trace(go.Bar(
        name=label_merc, x=x_labels, y=y_merc,
        marker=dict(color=color_merc, line=dict(color="#FFFFFF", width=1.5)),
        text=[f"<b>{v:.2f}</b>" for v in y_merc],
        textposition="outside", textfont=dict(size=12, color=C_TEXT_DARK),
    ))
    yaxis_kwargs = dict(title=unita, gridcolor="#E5E7EB")
    if yrange is not None:
        yaxis_kwargs["range"] = yrange
    yaxis_kwargs["fixedrange"] = True  # blocca scroll/pinch verticali (mobile)
    fig.update_layout(
        barmode="group", height=height,
        plot_bgcolor="#FFFFFF", paper_bgcolor="#FFFFFF",
        dragmode=False,  # disabilita zoom/pan/select tramite drag o touch
        yaxis=yaxis_kwargs,
        xaxis=dict(title="", tickangle=xtickangle, fixedrange=True),
        bargap=0.25, bargroupgap=0.08,
        # Legenda in basso al centro (stessa forma del grafico 1)
        showlegend=True,
        legend=dict(
            orientation="h", x=0.5, xanchor="center",
            y=-0.18, yanchor="top",
            bgcolor="#F8FAFC", bordercolor="#CBD5E1", borderwidth=1,
            font=dict(size=11),
        ),
        margin=dict(t=40, b=110, l=60, r=40),
    )
    return fig


# ------------------------------------------------------------------
# Helpers e statistiche consumo (usati nelle sezioni 2 e 3)
# ------------------------------------------------------------------
def _fmt_thousands(n) -> str:
    """Formatta un intero con separatore migliaia stile italiano (punti)."""
    return f"{int(n):,}".replace(",", ".")


def _stat_cat(comm: str, tip: str):
    """Estrae (cons_totale, n_utenze, cons_medio) per la fascia indicata."""
    sub = df_conf[(df_conf["commodity"] == comm)
                  & (df_conf["tipologia"] == tip)]
    if sub.empty:
        return 0.0, 0, 0.0
    cons = float(sub["consumo_mese"].iloc[0])
    n = int(sub["n_utenze"].iloc[0])
    return cons, n, (cons / n if n else 0.0)


# 4 classi di potenza ELE: dati base
_cons_3,   _n_3,   cons_3_medio   = _stat_cat("ELE", "BT <=6 kW")
_cons_40,  _n_40,  cons_40_medio  = _stat_cat("ELE", "BT 6-50 kW")
_cons_btH, _n_btH, cons_btH_medio = _stat_cat("ELE", "BT >50 kW")
_cons_mt,  _n_mt,  cons_mt_medio  = _stat_cat("ELE", "MT")

def _cons_label(cons_aggr, unita_singola):
    """Etichetta del consumo medio per il riquadro descrittivo.
    Su 'Tutti i mesi': 'X u totali sul periodo (media di Y u/mese)'.
    Su singolo mese: 'Y u'."""
    if _is_aggregato:
        totale = _fmt_thousands(round(cons_aggr))
        medio = _fmt_thousands(round(cons_aggr / _n_mesi_aggr))
        return (f"{totale} {unita_singola} totali sul periodo "
                f"<span style='color:#6B7280;'>(media di {medio} "
                f"{unita_singola}/mese)</span>")
    return f"{_fmt_thousands(round(cons_aggr))} {unita_singola}"


# ------------------------------------------------------------------
# SEZIONE 2 — Per classe di potenza (Elettrico)
# ------------------------------------------------------------------
st.header(f"2️⃣ {ICON_ELE} Per classe di potenza (Elettrico)")

# Prepara df_ele ordinato secondo ORDINE_ELE
df_ele = df_conf[df_conf["commodity"] == "ELE"].copy()
df_ele["_order"] = df_ele["tipologia"].apply(
    lambda t: ORDINE_ELE.index(t) if t in ORDINE_ELE else 99)
df_ele = df_ele.sort_values("_order").reset_index(drop=True)


st.markdown(
    f"""
<div class="desc-box">
Dettaglio per <b>classe di potenza disponibile</b>. Il Prezzo per la Materia prima
della Convenzione è calcolato per ciascuna delle quattro classi di potenza (media
ponderata sui consumi dei POD di ciascuna classe); le <b>Top N di mercato</b>
sono ricalcolate per ciascuna classe di potenza, in quanto le performance delle
migliori offerte possono variare in funzione delle caratteristiche di consumo
tipico delle classi indicate. Utilizza lo slider qui sotto per scegliere il
numero di offerte da considerare nella media (da 1 a 10).
<hr style="border:none; border-top:1px solid #E5E7EB; margin:.8rem 0 .7rem 0;">
🧮 Consumo medio per Classe di Potenza del Periodo d'osservazione
<b>{mese_label(meta['mese'])}</b>
(media reale sulle utenze POD del campione):<br>
&nbsp;&nbsp;⚡ Consumo medio di un'Utenza <b>BT ≤6 kW</b>:
{_cons_label(cons_3_medio, "kWh")}<br>
&nbsp;&nbsp;⚡ Consumo medio di un'Utenza <b>BT 6–50 kW</b>:
{_cons_label(cons_40_medio, "kWh")}<br>
&nbsp;&nbsp;⚡ Consumo medio di un'Utenza <b>BT &gt;50 kW</b>:
{_cons_label(cons_btH_medio, "kWh")}<br>
&nbsp;&nbsp;⚡ Consumo medio di un'Utenza in <b>Media Tensione (MT)</b>:
{_cons_label(cons_mt_medio, "kWh")}
</div>
""",
    unsafe_allow_html=True,
)

top_n_ele = st.slider(
    "🔢 Numero di offerte considerate nella Top N (Elettrico)",
    min_value=1, max_value=10, value=10, step=1, key="top_n_ele",
    help="La media è calcolata sulle Top N offerte più convenienti, "
         "ricalcolate per ciascuna classe di potenza. Default: 10.",
)


def _recompute_bench_ele(row):
    # Approccio B: media ponderata dei benchmark mensili per QUESTA classe.
    return round(_bench_periodo("ELE", tipologia=row["tipologia"],
                                top_n=top_n_ele), 2)


df_ele["benchmark_mercato"] = df_ele.apply(_recompute_bench_ele, axis=1)

# 4 classi di potenza dirette dal df_ele (ordinato secondo ORDINE_ELE)
cat = df_ele["tipologia"].tolist()
y_c = df_ele["materia_prima_conv"].astype(float).tolist()
y_m = df_ele["benchmark_mercato"].astype(float).tolist()

LABEL_TOPN_ELE = f"Top {top_n_ele} Offerte attive sul Mercato (ELE)"
st.plotly_chart(
    bar_gruppi(cat, y_c, y_m, C_CONV_ELE, C_MERC_ELE,
               LABEL_CONV_ELE, LABEL_TOPN_ELE, "€/MWh",
               yrange=_auto_yrange(y_c, y_m, floor=60, step=5)),
    use_container_width=True, config=CHART_CONFIG_NO_TOUCH,
)


# ------------------------------------------------------------------
# SEZIONE 3 — Per tipologia d'uso (Gas)
# ------------------------------------------------------------------
st.markdown("<h2 class='gas-section'>3️⃣ 🔥 Per tipologia d'uso (Gas)</h2>",
            unsafe_allow_html=True)

# Riquadro consumi medi per tipologia d'uso (GAS) — dal df_conf nell'ordine canonico
_gas_rows = []
for _tip_gas in ORDINE_GAS:
    _, _, _cons_med_g = _stat_cat("GAS", _tip_gas)
    _gas_rows.append(
        f"&nbsp;&nbsp;🔥 Consumo medio di un'Utenza con <b>Tipologia {_tip_gas}</b>: "
        f"{_cons_label(_cons_med_g, 'Smc')}"
    )
st.markdown(
    f"""
<div class="desc-box gas">
Dettaglio per <b>tipologia d'uso del gas</b>. Il Prezzo per la Materia prima
della Convenzione è calcolato distintamente <b>per ciascuna delle quattro
tipologie d'uso</b> (media ponderata sui consumi e importi reali del mese, per
ogni tipologia); le <b>Top N di mercato</b> sono ricalcolate per ciascuna
tipologia, in quanto le performance delle migliori offerte possono variare in
funzione delle caratteristiche di consumo tipico delle tipologie indicate.
Utilizza lo slider qui sotto per scegliere il numero di offerte da considerare
nella media (da 1 a 10).
<hr style="border:none; border-top:1px solid #E5E7EB; margin:.8rem 0 .7rem 0;">
🧮 Consumo medio per Tipologia d'uso del Periodo d'osservazione
<b>{mese_label(meta['mese'])}</b>
(media reale sulle utenze PDR del campione):<br>
{"<br>".join(_gas_rows)}
</div>
""",
    unsafe_allow_html=True,
)

top_n_gas = st.slider(
    "🔢 Numero di offerte considerate nella Top N (Gas)",
    min_value=1, max_value=10, value=10, step=1, key="top_n_gas",
    help="La media è calcolata sulle Top N offerte più convenienti, "
         "ricalcolate per ciascuna tipologia d'uso. Default: 10.",
)

df_gas = df_conf[df_conf["commodity"] == "GAS"].copy()
df_gas["_order"] = df_gas["tipologia"].apply(
    lambda t: ORDINE_GAS.index(t) if t in ORDINE_GAS else 99)
df_gas = df_gas.sort_values("_order").reset_index(drop=True)


def _recompute_bench_gas(row):
    # Approccio B: media ponderata dei benchmark mensili per QUESTA tipologia.
    return round(_bench_periodo("GAS", tipologia=row["tipologia"],
                                top_n=top_n_gas), 2)


df_gas["benchmark_mercato"] = df_gas.apply(_recompute_bench_gas, axis=1)

LABEL_TOPN_GAS = f"Top {top_n_gas} Offerte attive sul Mercato (GAS)"
_y_c_gas = df_gas["materia_prima_conv"].tolist()
_y_m_gas = df_gas["benchmark_mercato"].tolist()
st.plotly_chart(
    bar_gruppi([_short_gas(t) for t in df_gas["tipologia"].tolist()],
               _y_c_gas, _y_m_gas,
               C_CONV_GAS, C_MERC_GAS, LABEL_CONV_GAS, LABEL_TOPN_GAS, "c€/Smc",
               yrange=_auto_yrange(_y_c_gas, _y_m_gas, floor=30, step=2)),
    use_container_width=True, config=CHART_CONFIG_NO_TOUCH,
)


# ------------------------------------------------------------------
# METODOLOGIA + BIBLIOGRAFIA
# ------------------------------------------------------------------
st.header("📚 Metodologia")

# Calcolo data estrazione e conteggi offerte prima del markdown
data_estr_str = D.get("meta", {}).get("data_estrazione")
if not data_estr_str:
    import os
    try:
        ts = os.path.getmtime(Path(__file__).parent / "data" / "data.json")
        data_estr_str = pd.Timestamp(ts, unit="s").strftime("%Y-%m-%d")
    except Exception:
        data_estr_str = ""
data_estr_it = ""
if data_estr_str:
    try:
        data_estr_it = pd.Timestamp(data_estr_str).strftime("%d/%m/%Y")
    except Exception:
        data_estr_it = data_estr_str

n_off_tot = meta.get("n_offerte_totali") or D.get("meta", {}).get("n_offerte_totali", 0)
n_off_ele = D.get("meta", {}).get("n_offerte_ele")
n_off_gas = D.get("meta", {}).get("n_offerte_gas")
if n_off_ele is None or n_off_gas is None:
    _ot = D.get("offerte_tutte", [])
    n_off_ele = sum(1 for o in _ot if o.get("commodity") == "ELE")
    n_off_gas = sum(1 for o in _ot if o.get("commodity") == "GAS")

# UN SOLO st.markdown con tutto dentro lo stesso footer-block
st.markdown(
    f"""
<div class="footer-block">

<h4 style="margin-top:0;">🔬 Come è costruito il benchmark</h4>

<ol style="line-height:1.6;">
<li style="margin-bottom: 1.2rem;"><b>Convenzione MMPOWER</b> — Il Prezzo della
Materia prima è composto dalle voci <i>Generazione</i> e <i>Perdite di rete</i>
calcolate a partire dai <b>dati reali</b> di fornitura delle aziende
convenzionate (media ponderata sui consumi effettivi del periodo di osservazione).</li>

<li style="margin-bottom: 1.2rem;"><b>Convenzione MMGAS</b> — Il Prezzo della
Materia prima del gas è calcolato per ciascuna tipologia d'uso a partire dai
<b>dati reali</b> di fornitura delle aziende convenzionate (importo "materia
prima" diviso per i Smc consumati del mese).</li>

<li style="margin-bottom: 1.2rem;"><b>Mercato</b> — Per ogni offerta indicizzata
raccolta il prezzo è ricostruito <b>per ciascuna classe/tipologia</b> per
ciascun mese del periodo di osservazione. I corrispettivi fissi
€/utenza presenti nelle varie offerte vengono ripartiti sul <b>consumo
annuo</b> per ottenere un termine unitario €/MWh costante:<br><br>
&nbsp;&nbsp;&nbsp;⚡ <b>Prezzo mese EE</b>:&nbsp;
<code>P_mese = PUNx + spread + altri_corr_var + (PUNx + spread) × k + (altri_corr_fissi × n_utenze) ÷ Ce,x</code><br>
&nbsp;&nbsp;&nbsp;&nbsp;<i>dove k è il coefficiente di perdite di rete
({meta['coeff_perdita_BT']*100:.0f}&nbsp;% BT, {meta['coeff_perdita_MT']*100:.1f}&nbsp;% MT)
e Ce,x è il consumo elettrico annuo della classe x.</i><br><br>
&nbsp;&nbsp;&nbsp;🔥 <b>Prezzo mese Gas</b>:&nbsp;
<code>P_mese = PSV + spread + altri_corr_var + (altri_corr_fissi × n_utenze) ÷ Cg,y</code>&nbsp;
<i>con Cg,y consumo gas annuo della tipologia y</i>.<br><br>
Quando si seleziona <b>"Tutti i periodi disponibili"</b>, il benchmark
aggregato è costruito rispecchiando la <b>logica contrattuale della
fornitura</b> (una singola offerta indicizzata è sottoscritta per l'intero
periodo, non cambiata ogni mese): per ciascuna offerta si calcola il
<b>prezzo medio ponderato sui consumi mensili</b>, e solo dopo si
selezionano le <i>N</i> offerte più convenienti la cui media aritmetica
costituisce il benchmark:<br><br>
&nbsp;&nbsp;&nbsp;⚡🔥 <b>Prezzo medio dell'offerta sul periodo</b>:&nbsp;
<code>P_offerta = somma(P_mese × Consumo_mese) ÷ somma(Consumo_mese)</code><br>
&nbsp;&nbsp;&nbsp;⚡🔥 <b>Benchmark aggregato</b>:&nbsp; media aritmetica
delle <i>N</i> P_offerta più basse (con <i>N</i> definito dalla sezione).</li>

<li style="margin-bottom: 1.2rem;"><b>PUNx: PUN Ponderato per Fasce</b> — Viene
utilizzato un <b>PUNx ponderato secondo le Fasce orarie</b> ex Delibera ARERA
n.&nbsp;181/06 e s.m.i., sia differenziato per classe di tensione (PUN&nbsp;BT,
PUN&nbsp;MT) sia aggregato totale (PUN&nbsp;TOT). Questo consente di rappresentare
in modo più aderente alla realtà il prezzo effettivamente pagato per l'energia
prelevata da rete pubblica, considerato che la distribuzione temporale del
consumo può risultare statisticamente diversa fra utenze a Bassa Tensione e a
Media Tensione.<br><br>
Per il periodo di osservazione <b>{mese_label(meta['mese'])}</b>:<br>
&nbsp;&nbsp;&nbsp;&nbsp;⚡ <b>PUN TOT</b>: {_pun_tot:.4f} €/kWh — usato per il benchmark generale (sezione 1) sull'utenza media del campione convenzionato<br>
&nbsp;&nbsp;&nbsp;&nbsp;⚡ <b>PUN BT</b>: {_pun_bt:.4f} €/kWh — usato per le classi BT (sezione 2)<br>
&nbsp;&nbsp;&nbsp;&nbsp;⚡ <b>PUN MT</b>: {_pun_mt:.4f} €/kWh — usato per la classe MT (sezione 2)<br><br>
Il <b>PUN TOT</b> è la media ponderata tra PUN BT e PUN MT sui consumi reali del
periodo di osservazione del campione corrente; i prezzi <b>PUN BT</b> e
<b>PUN MT</b> corrispondono alle medie ponderate dei prezzi PUN per fascia ARERA
per le percentuali dei consumi storici per fascia, del periodo osservato, delle
utenze convenzionate.</li>

<li style="margin-bottom: 1.2rem;"><b>Fonte dei prezzi all'ingrosso</b> — I prezzi
PUN utilizzati nei calcoli del PUNx al paragrafo 4 e il prezzo PSV utilizzato
nella formula al paragrafo 3 corrispondono ai prezzi pubblicati da ARERA al link
<a href="https://www.arera.it/consumatori/offerte-standard-per-i-clienti-finali-placet" target="_blank"><b>"Offerte standard per i clienti finali — PLACET"</b></a>.</li>

<li style="margin-bottom: 1.2rem;"><b>Selezione delle migliori offerte</b> —
I prezzi delle offerte raccolte vengono ordinati in modo crescente e ne viene
calcolata la media aritmetica delle più convenienti. Il numero di offerte
considerate varia per sezione:
<ul>
  <li><b>Sezione 1</b> (confronto generale): <b>Top 5</b>, applicate a un'utenza
  media del campione convenzionato, con base <b>PUN&nbsp;TOT</b> con perdite di
  rete BT/MT ponderate sui consumi del periodo (elettrico) o <b>PSV</b> (gas).</li>
  <li><b>Sezioni 2 e 3</b> (per classe di potenza / tipologia d'uso): <b>Top N
  configurabile da 1 a 10</b> tramite slider dedicato. Le offerte vengono
  ricalcolate per ciascuna classe/tipologia, utilizzando PUN BT/MT con
  rispettive perdite di rete o PSV.</li>
</ul></li>

<li style="margin-bottom: 1.2rem;"><b>Offerte monitorate</b> — In data
<b>{data_estr_it or '—'}</b> sono state raccolte e analizzate complessivamente
<span class="num-evidenza">{n_off_tot} offerte indicizzate</span> attive sul
mercato libero italiano, provenienti sia dai siti istituzionali dei fornitori
sia dai principali portali comparatori, di cui <b>{n_off_ele}</b> per l'energia
elettrica e <b>{n_off_gas}</b> per il gas.</li>
</ol>

</div>
""",
    unsafe_allow_html=True,
)


# ------------------------------------------------------------------
# BIBLIOGRAFIA: tutti i link a fornitori, offerte, portali
# ------------------------------------------------------------------
# ------------------------------------------------------------------
# CONVENZIONI IN ESSERE — schede + download news in PDF
# ------------------------------------------------------------------
st.header("📰 Le Convenzioni in essere")

st.markdown(
    """
<div class="desc-box">
Le Convenzioni <b>MMPOWER</b> (per l'energia elettrica) e <b>MMGAS</b> (per il
gas) sono contratti <b>biennali di fornitura a prezzo variabile</b>,
rispettivamente indicizzati al <b>PUN</b> e al <b>PSV</b>, riservati esclusivamente
alle aziende associate all'Unione Industriali Torino. Si tratta di <b>contratti a
tempo determinato senza tacito rinnovo</b>, sono <b>tuttora attivi ed è possibile
aderirvi</b>. In prossimità della scadenza l'Area Gas &amp; Power Acquisti e Regolazione proporrà, sempre
per le aziende associate e con priorità alle aziende già convenzionate, una nuova
convenzione per il biennio successivo selezionata tramite gara tra i principali
fornitori del mercato.
</div>
""",
    unsafe_allow_html=True,
)

cN1, cN2 = st.columns(2)

# ---------- MMPOWER ----------
with cN1:
    st.markdown(
        """
<div style="border:1px solid #6BAED6; border-radius:12px; padding:1rem 1.2rem;
            background:linear-gradient(180deg,#FFFFFF,#F0F7FC);
            min-height:280px; display:flex; flex-direction:column;">
<h4 style="color:#2C5784; margin-top:0;">⚡ Convenzione MMPOWER 2026-2027</h4>
<p style="color:#6B7280; margin:.2rem 0 1rem 0; font-size:.9rem;">
Fornitore: <b>Iren Mercato S.p.A.</b></p>

<ul style="font-size:.95rem; line-height:1.5; flex:1;">
<li><b>Soglia consumo</b>: <b>3.000.000 kWh/anno</b> per singola utenza</li>
<li><b>Periodo di fornitura</b>: <b>fino al 31/12/2027</b></li>
<li><b>Opzione 100% energia verde</b> (su richiesta del singolo cliente)</li>
</ul>
</div>
""",
        unsafe_allow_html=True,
    )
    st.link_button(
        label="📰 Vai alla news completa MMPOWER *",
        url="https://www.ui.torino.it/news/prezzi-energia-elettrica-2026-2027-nuova-convenzione-mmpower-con-iren-mercato-spa",
        type="primary",
    )

# ---------- MMGAS ----------
with cN2:
    st.markdown(
        """
<div style="border:1px solid #F0A35E; border-radius:12px; padding:1rem 1.2rem;
            background:linear-gradient(180deg,#FFFFFF,#FCF5EE);
            min-height:280px; display:flex; flex-direction:column;">
<h4 style="color:#B4495C; margin-top:0;">🔥 Convenzione MMGAS 2025/26 — 2026/27</h4>
<p style="color:#6B7280; margin:.2rem 0 1rem 0; font-size:.9rem;">
Fornitore: <b>Eni Plenitude S.p.A.</b></p>

<ul style="font-size:.95rem; line-height:1.5; flex:1;">
<li><b>Soglia consumo</b>: <b>200.000 Smc/anno</b> per singolo cliente</li>
<li><b>Periodo di fornitura</b>: <b>fino al 30/09/2027</b></li>
<li><b>Opzione 100% CO₂ compensata</b> (su richiesta del singolo cliente)</li>
</ul>
</div>
""",
        unsafe_allow_html=True,
    )
    st.link_button(
        label="📰 Vai alla news completa MMGAS *",
        url="https://www.ui.torino.it/news/gas-nuova-convenzione-biennale-unione-eni-plenitude-anni-termici-20252026-e-20262027",
        type="primary",
    )

# Banner contatti DOPO i pulsanti di download
st.markdown(
    """
<p style="text-align:center; margin: 1.2rem 0 .6rem 0; padding:.8rem;
background:#F8FAFC; border-radius:8px; border:1px solid #E5E7EB;">
✉️ <b>Per informazioni o adesione alle Convenzioni, o per analisi e
confronti sulle offerte di mercato attive</b>:
<a href="mailto:s.cornagliotto@ui.torino.it">s.cornagliotto@ui.torino.it</a>
&nbsp;·&nbsp; ☎ 011 5718278
</p>
""",
    unsafe_allow_html=True,
)

# Nota con asterisco SUBITO dopo il banner contatti
st.markdown(
    """
<p style="color:#6B7280; font-size:.88rem; font-style:italic; margin-top:.6rem;">
* la scadenza di adesione indicata nelle news ufficiali si riferiva al solo avvio
della fornitura nel primo mese del biennio. È possibile aderire con avvio della
fornitura alla prima data utile prevista in accordo col fornitore.
</p>
""",
    unsafe_allow_html=True,
)


# Sezione Sitografia rimossa: i riferimenti rilevanti (ARERA PLACET) sono
# integrati nella Metodologia. Il PDF delle offerte resta riservato e disponibile
# solo all'Area Gas & Power Acquisti e Regolazione (non pubblicato sulla pagina).

# ------------------------------------------------------------------
# METODOLOGIA APPROFONDITA (download PDF + sorgente .tex)
# ------------------------------------------------------------------
st.header("📘 Metodologia approfondita")

st.markdown(
    """
<div class="desc-box">
Per una descrizione completa di algoritmi e parametri utilizzati nel benchmark,
è disponibile un documento metodologico separato. Quest'ultimo include anche
l'elenco completo delle offerte indicizzate raccolte, in forma anonima: ciascuna
offerta è identificata come <i>Offerta N EE</i> (o <i>GAS</i>), con relativa
Fonte (Sito Fornitore o Sito Comparatore) e le condizioni economiche applicate.
</div>
""",
    unsafe_allow_html=True,
)

_metodo_dir = Path(__file__).parent / "metodologia"
_pdf_path = _metodo_dir / "metodologia.pdf"
if _pdf_path.exists():
    st.download_button(
        label="📄 Scarica metodologia (PDF)",
        data=_pdf_path.read_bytes(),
        file_name="Metodologia_Benchmark_MateriaPrima.pdf",
        mime="application/pdf",
        type="primary",
        key="dl_metodo_pdf",
    )
else:
    st.info("Metodologia PDF non disponibile.")

st.markdown(
    f"""
<hr style="margin-top:2rem;">
<p style="text-align:center; color:#9CA3AF; font-size:.85rem;">
Unione Industriali Torino · Gas &amp; Power Acquisti e Regolazione · periodo di osservazione {mese_label(meta['mese'])}
</p>
""",
    unsafe_allow_html=True,
)
