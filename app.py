import os
import json
import math
import re
from datetime import datetime

import numpy as np
import pandas as pd
import streamlit as st
from zoneinfo import ZoneInfo

import folium
from folium import LayerControl
from folium.plugins import HeatMap
from streamlit_folium import st_folium

import altair as alt
import streamlit.components.v1 as components
from urllib.error import HTTPError
from branca.element import Template, MacroElement

# =============================
# Config geral
# =============================
st.set_page_config(
    page_title="Viveiros - Monitoramento",
    layout="wide",
    initial_sidebar_state="collapsed"
)

TZ = ZoneInfo("America/Fortaleza")

# =============================
# Estilos Modernizados
# =============================
st.markdown("""
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}

/* Header moderno com gradiente sofisticado */
.app-header {
    background: linear-gradient(135deg, #0c2461 0%, #1e3799 25%, #4a69bd 50%, #6a89cc 100%);
    padding: 2.5rem 2.5rem 2rem 2.5rem;
    border-radius: 0 0 24px 24px;
    margin: -1rem -1rem 2.5rem -1rem;
    color: white;
    box-shadow: 0 8px 32px rgba(0,0,0,0.12);
    position: relative;
    overflow: hidden;
}
.app-header::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 4px;
    background: linear-gradient(90deg, #00b894, #0984e3, #00cec9);
}
.app-header h1 {
    margin: 0;
    font-size: 2.4rem;
    font-weight: 800;
    background: linear-gradient(135deg, #ffffff 0%, #e0f7fa 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    letter-spacing: -0.5px;
}
.app-header p {
    margin: 0.8rem 0 0 0;
    font-size: 1.15rem;
    opacity: 0.9;
    font-weight: 400;
}

/* Cards KPI modernos com hover */
.kpi-card {
    background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
    border-radius: 20px;
    padding: 1.5rem 1.2rem;
    box-shadow: 0 4px 20px rgba(0,0,0,0.08);
    border: 1px solid rgba(255,255,255,0.8);
    backdrop-filter: blur(10px);
    transition: all 0.3s ease;
    position: relative;
    overflow: hidden;
}
.kpi-card::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 4px;
    background: linear-gradient(90deg, #00b894, #0984e3);
}
.kpi-card:hover {
    transform: translateY(-5px);
    box-shadow: 0 8px 30px rgba(0,0,0,0.15);
}
.kpi-label {
    font-size: 0.85rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #636e72;
    margin-bottom: 0.5rem;
    font-weight: 600;
}
.kpi-value {
    font-size: 2rem;
    font-weight: 800;
    color: #2d3436;
    margin-bottom: 0.3rem;
    background: linear-gradient(135deg, #2d3436 0%, #636e72 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}
.kpi-sub {
    font-size: 0.8rem;
    color: #b2bec3;
    font-weight: 500;
}

/* Seções modernas */
.section-title {
    font-weight: 700;
    font-size: 1.3rem;
    margin: 1rem 0 1.2rem 0;
    color: #2d3436;
    padding-bottom: 0.5rem;
    border-bottom: 3px solid #0984e3;
    display: inline-block;
}

/* Container principal */
.main {
    background: #f8f9fa;
}

/* Animações suaves */
@keyframes fadeIn {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
}
.fade-in {
    animation: fadeIn 0.5s ease-in-out;
}

/* Scrollbar personalizada */
::-webkit-scrollbar {
    width: 6px;
}
::-webkit-scrollbar-track {
    background: #f1f1f1;
    border-radius: 10px;
}
::-webkit-scrollbar-thumb {
    background: linear-gradient(135deg, #74b9ff, #0984e3);
    border-radius: 10px;
}
::-webkit-scrollbar-thumb:hover {
    background: linear-gradient(135deg, #0984e3, #074b83);
}
</style>
""", unsafe_allow_html=True)

# =============================
# Funções auxiliares
# =============================
def load_from_gsheet_csv(sheet_id: str, gid: str = "0", sep: str = ","):
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    try:
        df = pd.read_csv(url, sep=sep)
    except HTTPError as e:
        st.error(f"Erro HTTP ao acessar o Google Sheets: {e}")
        raise
    except Exception as e:
        st.error(f"Erro ao ler o CSV do Google Sheets: {e}")
        raise
    return df

def gdrive_extract_id(url: str):
    if not isinstance(url, str):
        return None
    url = url.strip()
    m = re.search(r"/d/([a-zA-Z0-9_-]{10,})", url)
    if m:
        return m.group(1)
    m = re.search(r"[?&]id=([a-zA-Z0-9_-]{10,})", url)
    if m:
        return m.group(1)
    return None

def drive_image_urls(file_id: str):
    thumb = f"https://drive.google.com/thumbnail?id={file_id}&sz=w450"
    big = f"https://drive.google.com/thumbnail?id={file_id}&sz=w2048"
    return thumb, big

def to_number(v):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return np.nan
    s = str(v).strip()
    if s == "":
        return np.nan
    # Trata casos com vírgula como decimal
    if "," in s and s.count(",") == 1 and s.count(".") <= 1:
        s = s.replace(".", "").replace(",", ".")
    else:
        s = s.replace(",", ".")
    try:
        return float(s)
    except Exception:
        try:
            return float(s.replace(" ", ""))
        except Exception:
            return np.nan

def to_float(v):
    if v is None:
        return None
    try:
        return float(str(v).replace(",", "."))
    except Exception:
        return None

# Galeria no modelo antigo, com auto_open
def render_lightgallery_images(items: list, height_px=420, auto_open: bool = False):
    if not items:
        st.info("📷 Nenhuma foto encontrada para os filtros atuais.")
        return

    anchors = []
    for it in items:
        anchors.append(
            f"""
            <a class="gallery-item" href="{it['src']}" data-sub-html="{it.get('caption','')}">
                <img src="{it['thumb']}" loading="lazy"/>
            </a>
            """
        )
    items_html = "\n".join(anchors)

    auto_open_js = """
        const firstItem = container.querySelector('.gallery-item');
        if (firstItem) {
          firstItem.click();
        }
    """ if auto_open else ""

    html = f"""
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/lightgallery@2.7.2/css/lightgallery-bundle.min.css">
    <style>
      .lg-backdrop {{ background: rgba(0,0,0,0.92); }}
      .gallery-container {{
          display:flex;
          flex-wrap:wrap;
          gap: 12px;
          align-items:flex-start;
      }}
      .gallery-item img {{
          height: 120px;
          width:auto;
          border-radius: 12px;
          box-shadow: 0 4px 12px rgba(0,0,0,.25);
          transition: transform 0.25s ease, box-shadow 0.25s ease;
      }}
      .gallery-item:hover img {{
          transform: scale(1.04);
          box-shadow: 0 6px 18px rgba(0,0,0,.32);
      }}
    </style>
    <div id="lg-gallery" class="gallery-container">{items_html}</div>

    <script src="https://cdn.jsdelivr.net/npm/lightgallery@2.7.2/lightgallery.umd.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/lightgallery@2.7.2/plugins/zoom/lg-zoom.umd.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/lightgallery@2.7.2/plugins/thumbnail/lg-thumbnail.umd.js"></script>

    <script>
      window.addEventListener('load', () => {{
        const container = document.getElementById('lg-gallery');
        if (!container) return;
        const lgInstance = lightGallery(container, {{
          selector: '.gallery-item',
          zoom: true,
          thumbnail: true,
          download: false,
          loop: true,
          plugins: [lgZoom, lgThumbnail]
        }});
        {auto_open_js}
      }});
    </script>
    """
    components.html(html, height=height_px, scrolling=True)

def make_popup_html(row):
    safe = lambda v: "-" if v in [None, "", np.nan] else str(v)

    campos = [
        ("CÓDIGO", "🔢"),
        ("Nome", "👤"),
        ("Ocorrências", "⚠️"),
        ("Nº Viveiros total", "🐟"),
        ("Atual Viveiros Total", "✅"),
        ("Nº Viveiros cheio", "💧"),
        ("Atual Viveiros cheio", "💧"),
        ("Área (ha).1", "📐"),
        ("Atual Área (ha).1", "📐"),
        ("Prof. Média  (m)", "📏"),
        ("Atual Profun.", "📏"),
    ]

    linhas = []
    for col, icon in campos:
        if col not in row:
            continue
        val = row[col]
        linhas.append(
            f"""
            <div style="display:flex;justify-content:space-between;padding:4px 0;font-size:0.92em;border-bottom:1px solid rgba(255,255,255,0.1);">
                <span style="font-weight:500;">{icon} {col}:</span>
                <span style="font-weight:600;text-align:right;">{safe(val)}</span>
            </div>
            """
        )

    corpo = "\n".join(linhas)
    html = f"""
    <div style="
        font-family: 'Segoe UI', system-ui, sans-serif;
        padding: 16px;
        min-width:280px;
        max-width:380px;
        background: linear-gradient(135deg,#1e3799 0%,#0984e3 100%);
        border-radius: 20px;
        box-shadow: 0 12px 40px rgba(0,0,0,0.3);
        color: white;
        border: 2px solid rgba(255,255,255,0.2);
        backdrop-filter: blur(10px);
    ">
        <div style="
            background: rgba(255,255,255,0.15);
            padding: 10px 14px;
            border-radius: 14px;
            text-align:center;
            font-weight:700;
            font-size:1.1em;
            margin-bottom:12px;
            border: 1px solid rgba(255,255,255,0.2);
        ">
            🐟 Unidade de Viveiro
        </div>
        {corpo}
    </div>
    """
    return html

# =============================
# Header Modernizado
# =============================
st.markdown("""
<div class="app-header fade-in">
  <h1>🐟 Sistema de Monitoramento de Viveiros</h1>
  <p>Análise em tempo quase real das unidades de viveiros cadastradas</p>
</div>
""", unsafe_allow_html=True)

# =============================
# Barra de status e informações
# =============================
col_info1, col_info2, col_info3 = st.columns([2,1,1])

with col_info1:
    st.caption(
        f"🕐 Última atualização: {datetime.now(TZ).strftime('%d/%m/%Y %H:%M')} "
        f"(Horário de Fortaleza)"
    )

with col_info2:
    st.caption("📊 Dados sincronizados via Google Sheets")

with col_info3:
    if st.button("🔄 Atualizar Dados"):
        st.rerun()

# =============================
# Carrega dados
# =============================
SHEET_ID = "1pMMSJUPCpWmG2weFcEhI5T0hQNY5VVDNjjUxB5i0GoI"
GID = "2073960790"
SEP = ","

try:
    df = load_from_gsheet_csv(SHEET_ID, GID, sep=SEP)
except Exception:
    st.error("❌ Erro ao carregar dados da planilha. Verifique a conexão.")
    st.stop()

if df.empty:
    st.info("📋 Planilha sem dados disponíveis.")
    st.stop()

df = df.replace({np.nan: None})

# =============================
# Preparação de datas para filtros
# =============================
if "Data Filtro" in df.columns:
    df["_Data_dt"] = pd.to_datetime(df["Data Filtro"], errors="coerce", dayfirst=True)
    df["Ano_filtro"] = df["_Data_dt"].dt.year
    df["Mes_filtro_num"] = df["_Data_dt"].dt.month
    meses_map = {
        1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr",
        5: "Mai", 6: "Jun", 7: "Jul", 8: "Ago",
        9: "Set", 10: "Out", 11: "Nov", 12: "Dez",
    }
    df["Mes_filtro"] = df["Mes_filtro_num"].map(meses_map)
else:
    df["Ano_filtro"] = None
    df["Mes_filtro"] = None

# =============================
# Filtros Modernizados
# =============================
st.markdown("### 🔍 Filtros de Pesquisa")

with st.expander("Filtros avançados", expanded=True):
    col_f1, col_f2, col_f3 = st.columns([1.2, 1.2, 1.6])

    # Ano (Data Filtro)
    with col_f1:
        anos = []
        if "Ano_filtro" in df.columns:
            anos = sorted([a for a in df["Ano_filtro"].dropna().unique().tolist()])
        use_filter_ano = st.toggle("📅 Filtrar ano", value=False)
        if use_filter_ano and anos:
            ano_sel = st.multiselect(
                "Ano (Data Filtro)",
                options=anos,
                default=anos
            )
        else:
            ano_sel = None

    # Mês (Data Filtro)
    with col_f2:
        meses = []
        if "Mes_filtro" in df.columns:
            meses = [m for m in df["Mes_filtro"].dropna().unique().tolist()]
            if meses:
                ordem_meses = ["Jan","Fev","Mar","Abr","Mai","Jun",
                               "Jul","Ago","Set","Out","Nov","Dez"]
                meses = sorted(meses, key=lambda x: ordem_meses.index(x))
        use_filter_mes = st.toggle("🗓️ Filtrar mês", value=False)
        if use_filter_mes and meses:
            mes_sel = st.multiselect(
                "Mês (Data Filtro)",
                options=meses,
                default=meses
            )
        else:
            mes_sel = None

    # Busca por código ou nome
    with col_f3:
        search_text = st.text_input(
            "🔎 Buscar por CÓDIGO ou Nome",
            placeholder="Digite parte do código ou do nome"
        )

    col_f4, col_f5 = st.columns(2)

    with col_f4:
        ocorr_opts = sorted([o for o in df.get("Ocorrências", pd.Series()).dropna().unique().tolist()])
        ocorr_sel = st.multiselect(
            "⚠️ Filtrar Ocorrências",
            options=ocorr_opts,
            default=ocorr_opts if ocorr_opts else None
        )

    with col_f5:
        # Espaço para filtros adicionais no futuro
        pass

# =============================
# Aplicação dos filtros
# =============================
fdf = df.copy()

if use_filter_ano and "Ano_filtro" in fdf.columns and ano_sel:
    fdf = fdf[fdf["Ano_filtro"].isin(ano_sel)]

if use_filter_mes and "Mes_filtro" in fdf.columns and mes_sel:
    fdf = fdf[fdf["Mes_filtro"].isin(mes_sel)]

if ocorr_sel and "Ocorrências" in fdf.columns:
    fdf = fdf[fdf["Ocorrências"].isin(ocorr_sel)]

if search_text:
    txt = search_text.strip().lower()
    mask = pd.Series([False] * len(fdf))
    if "CÓDIGO" in fdf.columns:
        mask = mask | fdf["CÓDIGO"].astype(str).str.lower().str.contains(txt, na=False)
    if "Nome" in fdf.columns:
        mask = mask | fdf["Nome"].astype(str).str.lower().str.contains(txt, na=False)
    fdf = fdf[mask]

# =============================
# Cálculo de alertas de divergência
# =============================
for col in ["Nº Viveiros total", "Atual Viveiros Total",
            "Nº Viveiros cheio", "Atual Viveiros cheio",
            "Área (ha).1", "Atual Área (ha).1",
            "Prof. Média  (m)", "Atual Profun."]:
    if col in fdf.columns:
        fdf[col + "_num"] = fdf[col].apply(to_number)

div_cols = []

if {"Nº Viveiros total_num", "Atual Viveiros Total_num"}.issubset(fdf.columns):
    fdf["diff_viv_total"] = fdf["Atual Viveiros Total_num"] - fdf["Nº Viveiros total_num"]
    div_cols.append("diff_viv_total")

if {"Nº Viveiros cheio_num", "Atual Viveiros cheio_num"}.issubset(fdf.columns):
    fdf["diff_viv_cheio"] = fdf["Atual Viveiros cheio_num"] - fdf["Nº Viveiros cheio_num"]
    div_cols.append("diff_viv_cheio")

if {"Área (ha).1_num", "Atual Área (ha).1_num"}.issubset(fdf.columns):
    fdf["diff_area"] = fdf["Atual Área (ha).1_num"] - fdf["Área (ha).1_num"]
    div_cols.append("diff_area")

if {"Prof. Média  (m)_num", "Atual Profun._num"}.issubset(fdf.columns):
    fdf["diff_prof"] = fdf["Atual Profun._num"] - fdf["Prof. Média  (m)_num"]
    div_cols.append("diff_prof")

div_mask = pd.Series([False] * len(fdf))
for c in div_cols:
    div_mask = div_mask | (fdf[c].fillna(0) != 0)

alertas_df = fdf[div_mask].copy()

# =============================
# KPIs
# =============================
st.markdown("### 📈 Indicadores Principais")

base_df = fdf.copy()

total_unidades = len(base_df)

total_viveiros_total = base_df.get("Atual Viveiros Total_num", pd.Series(dtype=float)).fillna(0).sum()
total_viveiros_cheio = base_df.get("Atual Viveiros cheio_num", pd.Series(dtype=float)).fillna(0).sum()
total_area = base_df.get("Atual Área (ha).1_num", pd.Series(dtype=float)).fillna(0).sum()

k1, k2, k3, k4 = st.columns(4)

with k1:
    st.markdown(
        f"""
        <div class="kpi-card fade-in">
          <div class="kpi-label">Unidades de viveiros</div>
          <div class="kpi-value">{int(total_unidades)}</div>
          <div class="kpi-sub">Registros após filtros</div>
        </div>
        """,
        unsafe_allow_html=True
    )

with k2:
    st.markdown(
        f"""
        <div class="kpi-card fade-in">
          <div class="kpi-label">Viveiros cadastrados</div>
          <div class="kpi-value">
            {total_viveiros_total:,.0f}
          </div>
          <div class="kpi-sub">Soma de "Atual Viveiros Total"</div>
        </div>
        """.replace(",", "X").replace(".", ",").replace("X", "."),
        unsafe_allow_html=True
    )

with k3:
    st.markdown(
        f"""
        <div class="kpi-card fade-in">
          <div class="kpi-label">Viveiros cheios</div>
          <div class="kpi-value">
            {total_viveiros_cheio:,.0f}
          </div>
          <div class="kpi-sub">Soma de "Atual Viveiros cheio"</div>
        </div>
        """.replace(",", "X").replace(".", ",").replace("X", "."),
        unsafe_allow_html=True
    )

with k4:
    st.markdown(
        f"""
        <div class="kpi-card fade-in">
          <div class="kpi-label">Área total atual</div>
          <div class="kpi-value">
            {total_area:,.1f} ha
          </div>
          <div class="kpi-sub">Soma de "Atual Área (ha).1"</div>
        </div>
        """.replace(",", "X").replace(".", ",").replace("X", "."),
        unsafe_allow_html=True
    )

# =============================
# Alertas de divergência
# =============================
st.markdown("### 🚨 Alertas de divergência entre dados previstos e atuais")

if alertas_df.empty:
    st.success("Nenhuma divergência relevante encontrada entre os valores originais e os valores atuais.")
else:
    st.warning(
        f"Foram encontradas {len(alertas_df)} unidades com diferença entre dados originais e dados atuais. "
        "Revise estas unidades com atenção."
    )

    cols_alerta = ["CÓDIGO", "Nome",
                   "Nº Viveiros total", "Atual Viveiros Total",
                   "Nº Viveiros cheio", "Atual Viveiros cheio",
                   "Área (ha).1", "Atual Área (ha).1",
                   "Prof. Média  (m)", "Atual Profun."]

    cols_exist_alerta = [c for c in cols_alerta if c in alertas_df.columns]

    st.dataframe(
        alertas_df[cols_exist_alerta],
        use_container_width=True,
        height=250
    )

# =============================
# Layout Mapa + Fotos
# =============================
st.markdown("---")
st.markdown('<div class="section-title">🗺️ Visualização Geográfica</div>', unsafe_allow_html=True)

col_map, col_fotos = st.columns([1.2, 1])

map_data = None

with col_map:
    st.markdown("#### Mapa Interativo das Unidades")

    with st.container():
        fmap = folium.Map(
            location=[-5.0, -39.5],
            zoom_start=8,
            control_scale=True,
            tiles=None
        )

        folium.TileLayer("CartoDB Positron", name="CartoDB Positron").add_to(fmap)
        folium.TileLayer("OpenStreetMap", name="OpenStreetMap").add_to(fmap)
        folium.TileLayer(
            tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
            name="Imagem de Satélite",
            attr="Tiles © Esri"
        ).add_to(fmap)

        fg_pontos = folium.FeatureGroup(name="Unidades de Viveiros", show=True)
        pts = []

        lat_col = "Lati" if "Lati" in fdf.columns else None
        lon_col = "Long" if "Long" in fdf.columns else None

        for _, row in fdf.iterrows():
            if not lat_col or not lon_col:
                continue

            lat = to_float(row.get(lat_col))
            lon = to_float(row.get(lon_col))
            if lat is None or lon is None or math.isnan(lat) or math.isnan(lon):
                continue

            popup_html = make_popup_html(row)
            popup = folium.Popup(popup_html, max_width=380)

            tooltip_text = str(row.get("Nome", "Unidade"))
            cod = row.get("CÓDIGO")
            if cod:
                tooltip_text = f"{cod} • {tooltip_text}"

            folium.CircleMarker(
                location=[lat, lon],
                radius=8,
                color="#0984e3",
                fill=True,
                fill_color="#0984e3",
                fill_opacity=0.9,
                popup=popup,
                tooltip=tooltip_text,
                weight=2
            ).add_to(fg_pontos)

            pts.append((lat, lon))

        fg_pontos.add_to(fmap)

        # Heatmap usando Lati e Long
        if "Atual Viveiros Total_num" in fdf.columns and lat_col and lon_col:
            heat_rows = []
            for _, row in fdf.iterrows():
                lat = to_float(row.get(lat_col))
                lon = to_float(row.get(lon_col))
                value = row.get("Atual Viveiros Total_num")
                if (
                    lat is None or lon is None or
                    pd.isna(value) or value <= 0
                ):
                    continue
                heat_rows.append([lat, lon, float(value)])

            if heat_rows:
                fg_heat = folium.FeatureGroup(name="Mapa de calor (viveiros)", show=False)
                HeatMap(
                    heat_rows,
                    radius=25,
                    blur=20,
                    max_zoom=12
                ).add_to(fg_heat)
                fg_heat.add_to(fmap)

        if pts:
            fmap.fit_bounds([
                [min(p[0] for p in pts), min(p[1] for p in pts)],
                [max(p[0] for p in pts), max(p[1] for p in pts)],
            ])

        # Legenda recolhível
        legend_html = """
        {% macro html(this, kwargs) %}
        <div id="legend-viveiros" style="
            position: fixed;
            bottom: 40px;
            left: 10px;
            z-index: 9999;
            background: rgba(255,255,255,0.95);
            padding: 12px 16px;
            border: 1px solid #ddd;
            border-radius: 16px;
            font-size: 12px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.15);
            backdrop-filter: blur(10px);
            font-family: 'Segoe UI', system-ui, sans-serif;
        ">
          <div id="legend-viveiros-header" style="font-weight:700; margin-bottom:6px; color:#2d3436; font-size:13px; cursor:pointer;"
               onclick="
                 var body = document.getElementById('legend-viveiros-body');
                 if (body.style.display === 'none') {
                     body.style.display = 'block';
                     this.innerHTML = 'Unidades de Viveiros ▾';
                 } else {
                     body.style.display = 'none';
                     this.innerHTML = 'Unidades de Viveiros ▸';
                 }
               ">
            Unidades de Viveiros ▾
          </div>
          <div id="legend-viveiros-body" style="margin-top:4px;">
            <div style="display:flex;align-items:center;margin-bottom:4px;">
              <span style="display:inline-block;width:14px;height:14px;border-radius:50%;background:#0984e3;margin-right:6px;border:2px solid white;box-shadow:0 1px 3px rgba(0,0,0,0.3);"></span>Unidade cadastrada
            </div>
            <div style="font-size:11px;color:#636e72;margin-top:4px;">
              Clique em um ponto para ver detalhes e fotos.
            </div>
          </div>
        </div>
        {% endmacro %}
        """
        legend = MacroElement()
        legend._template = Template(legend_html)
        fmap.get_root().add_child(legend)

        LayerControl(collapsed=True).add_to(fmap)

        map_data = st_folium(fmap, height=500, use_container_width=True)

with col_fotos:
    st.markdown("#### 📸 Galeria de Fotos")

    with st.container():
        foto_col = "Link Foto" if "Link Foto" in fdf.columns else None

        fdf_gallery = fdf.copy()
        clicked = False

        lat_col = "Lati" if "Lati" in fdf.columns else None
        lon_col = "Long" if "Long" in fdf.columns else None

        if map_data and 'last_object_clicked' in map_data and lat_col and lon_col:
            click_info = map_data.get("last_object_clicked") or map_data.get("last_clicked")
            if click_info:
                clicked = True
                click_lat = click_info["lat"]
                click_lon = click_info["lng"]

                tmp = fdf.copy()
                tmp["_lat"] = tmp[lat_col].apply(to_float)
                tmp["_lon"] = tmp[lon_col].apply(to_float)
                tmp = tmp.dropna(subset=["_lat", "_lon"])

                if not tmp.empty:
                    tmp["dist2"] = (tmp["_lat"] - click_lat) ** 2 + (tmp["_lon"] - click_lon) ** 2
                    tmp = tmp.sort_values("dist2")
                    fdf_gallery = tmp.head(1)

        if not foto_col:
            st.info("📷 Coluna de fotos não encontrada na planilha.")
        else:
            items = []
            vistos = set()

            for _, row in fdf_gallery.iterrows():
                link = row.get(foto_col)
                if not isinstance(link, str) or not link.strip():
                    continue
                if link in vistos:
                    continue
                vistos.add(link)

                nome = row.get("Nome", "")
                cod = row.get("CÓDIGO", "")
                caption_parts = [str(cod) if cod else None, str(nome) if nome else None]
                caption = " • ".join([p for p in caption_parts if p])

                fid = gdrive_extract_id(link)
                if fid:
                    thumb, big = drive_image_urls(fid)
                    items.append({"thumb": thumb, "src": big, "caption": caption})
                else:
                    items.append({"thumb": link, "src": link, "caption": caption})

            if clicked and items:
                st.success("📍 Visualizando fotos da unidade selecionada no mapa")
                auto_open = True
            else:
                if not items:
                    st.info("🗺️ Clique em uma unidade no mapa para ver fotos específicas")
                else:
                    st.info("🗺️ Clique em uma unidade no mapa para focar as fotos em um ponto específico")
                auto_open = False

            render_lightgallery_images(items, height_px=460, auto_open=auto_open)

# =============================
# Gráficos de Ocorrências
# =============================
st.markdown("---")
st.markdown('<div class="section-title">📊 Análise de Ocorrências</div>', unsafe_allow_html=True)

col_g1, col_g2 = st.columns(2)

with col_g1:
    if "Ocorrências" in fdf.columns:
        tmp = (
            fdf[["Ocorrências"]]
            .dropna()
            .groupby("Ocorrências")
            .size()
            .reset_index(name="contagem")
        )
        if tmp.empty:
            st.info("📊 Sem dados de Ocorrências para os filtros atuais")
        else:
            chart = (
                alt.Chart(tmp)
                .mark_bar(cornerRadius=8)
                .encode(
                    x=alt.X("Ocorrências:N", title="", sort="-y", axis=alt.Axis(labelAngle=0)),
                    y=alt.Y("contagem:Q", title="Quantidade de unidades"),
                    color=alt.Color("Ocorrências:N", legend=None),
                    tooltip=[
                        alt.Tooltip("Ocorrências:N", title="Ocorrência"),
                        alt.Tooltip("contagem:Q", title="Unidades")
                    ]
                )
                .properties(height=300, title="Distribuição por tipo de ocorrência")
                .configure_title(fontSize=16, font="Segoe UI", anchor="middle")
            )
            st.altair_chart(chart, use_container_width=True)
    else:
        st.info("📋 Coluna Ocorrências não encontrada.")

with col_g2:
    if "Ano_filtro" in fdf.columns and "Ocorrências" in fdf.columns:
        tmp = (
            fdf[["Ano_filtro", "Ocorrências"]]
            .dropna()
            .groupby(["Ano_filtro", "Ocorrências"])
            .size()
            .reset_index(name="contagem")
        )
        if tmp.empty:
            st.info("📊 Sem dados de Ocorrências por ano para os filtros atuais")
        else:
            chart = (
                alt.Chart(tmp)
                .mark_bar(cornerRadius=4)
                .encode(
                    x=alt.X("Ano_filtro:O", title="Ano"),
                    y=alt.Y("contagem:Q", title="Unidades"),
                    color=alt.Color("Ocorrências:N", title="Ocorrência"),
                    tooltip=[
                        alt.Tooltip("Ano_filtro:O", title="Ano"),
                        alt.Tooltip("Ocorrências:N", title="Ocorrência"),
                        alt.Tooltip("contagem:Q", title="Unidades")
                    ]
                )
                .properties(height=300, title="Ocorrências por ano")
                .configure_title(fontSize=16, font="Segoe UI", anchor="middle")
            )
            st.altair_chart(chart, use_container_width=True)
    else:
        st.info("📋 Dados de ano ou de Ocorrências não disponíveis para este gráfico.")

# =============================
# Tabela Detalhada
# =============================
st.markdown("---")
st.markdown('<div class="section-title">📋 Relatório Detalhado</div>', unsafe_allow_html=True)

cols_tabela = [
    "CÓDIGO", "Nome", "Ocorrências",
    "Nº Viveiros total", "Atual Viveiros Total",
    "Nº Viveiros cheio", "Atual Viveiros cheio",
    "Área (ha).1", "Atual Área (ha).1",
    "Prof. Média  (m)", "Atual Profun.",
    "Data Filtro"
]

cols_existentes = [c for c in cols_tabela if c in fdf.columns]
tabela = fdf[cols_existentes].copy()

st.dataframe(
    tabela,
    use_container_width=True,
    height=450
)

# =============================
# Footer
# =============================
st.markdown("---")
st.markdown("""
<div style="text-align:center; padding: 2rem 1rem; color: #636e72;">
    <div style="font-size: 0.9rem; margin-bottom: 0.5rem;">
        🐟 <strong>Sistema de Monitoramento de Viveiros</strong>
    </div>
    <div style="font-size: 0.8rem; opacity: 0.8;">
        Desenvolvido para apoiar a gestão, a fiscalização e a tomada de decisão com base em dados atualizados.
    </div>
</div>
""", unsafe_allow_html=True)
