# -----------------------------------------------------------------------------
# Panel de mortalidad — Colombia (demo)
#   - Visión general: Barras + Mapa (datos demo a partir del GeoJSON local)
#   - Municipios (torta): 10 departamentos; municipios desde Excel en ./data
#       (Columnas buscadas por similitud: Departamento y Municipio)
#   - Causas (Top 10): Tabla con código, nombre y total de casos (desde ./data)
#   - Muertes por sexo (barras apiladas): Comparación H/M por departamento
#   - Distribución por edad (histograma): GRUPO_EDAD1 con categorías y rangos
#   - Tendencia mensual (líneas): Total nacional por mes (interactiva)
# -----------------------------------------------------------------------------

from dash import Dash, html, dcc, dash_table
from dash.dependencies import Input, Output
import plotly.express as px
import pandas as pd
import numpy as np
import json
from pathlib import Path
import unicodedata
import os

# =============================================================================
# Utilidades
# =============================================================================
def _norm(s: str) -> str:
    if s is None:
        return ""
    s = str(s).strip().upper()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = " ".join(s.split())
    return s

def _leer_divipola_desde_excel(data_dir: Path) -> pd.DataFrame:
    if not data_dir.exists():
        return pd.DataFrame()
    frames = []
    for p in data_dir.glob("*.xlsx"):
        try:
            sheets = pd.read_excel(p, sheet_name=None, engine="openpyxl")
        except Exception:
            continue
        for _, df in sheets.items():
            if not isinstance(df, pd.DataFrame) or df.empty:
                continue
            norm_cols = {_norm(c): c for c in df.columns}
            dep_key = None
            for k, original in norm_cols.items():
                if any(t in k for t in ["DEPART", "DEPTO", "DPTO", "DEPARTAMENTO"]):
                    dep_key = original; break
            mun_key = None
            for k, original in norm_cols.items():
                if any(t in k for t in ["MUNICIP", "MPIO", "MUNICIPIO"]):
                    mun_key = original; break
            if dep_key and mun_key:
                tmp = df[[dep_key, mun_key]].copy()
                tmp.columns = ["DEPARTAMENTO", "MUNICIPIO"]
                tmp = tmp.dropna()
                if not tmp.empty:
                    frames.append(tmp)
    if not frames:
        return pd.DataFrame()
    out = pd.concat(frames, ignore_index=True).dropna()
    out["DEPARTAMENTO"] = out["DEPARTAMENTO"].astype(str).str.strip()
    out["MUNICIPIO"] = out["MUNICIPIO"].astype(str).str.strip()
    out["DEP_NORM"] = out["DEPARTAMENTO"].map(_norm)
    out["MUN_NORM"] = out["MUNICIPIO"].map(_norm)
    out = out[(out["DEP_NORM"] != "") & (out["MUN_NORM"] != "")]
    return out.drop_duplicates(subset=["DEP_NORM", "MUN_NORM"])

# ====== lector de causas (CSV/XLSX) con encabezados flexibles =========
def _norm_low(s: str) -> str:
    if s is None: return ""
    s = str(s).strip().lower()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = " ".join(s.split())
    return s

def _leer_causas_desde_data(data_dir: Path) -> pd.DataFrame:
    csv_path  = data_dir / "causas_mortalidad.csv"
    xlsx_path = data_dir / "causas_mortalidad.xlsx"
    if csv_path.exists():
        df = pd.read_csv(csv_path)
    elif xlsx_path.exists():
        df = pd.read_excel(xlsx_path, sheet_name=0, engine="openpyxl")
    else:
        df = pd.DataFrame({
            "CODIGO": ["I21","C34","I10","E11","J18","C16","N17","I64","A41","V89"],
            "NOMBRE": [
                "Infarto agudo de miocardio","Cáncer de pulmón","Hipertensión esencial",
                "Diabetes mellitus tipo 2","Neumonía","Cáncer gástrico","Falla renal aguda",
                "Accidente cerebrovascular","Sepsis","Accidentes de transporte"],
            "CASOS": [18234,15012,14320,13980,13210,9105,8702,8540,8012,7925]
        })
    cnorm = {_norm_low(c): c for c in df.columns}
    cod_col = next((cnorm[c] for c in cnorm if any(k in c for k in ["cod","codigo","code"])), None) or "CODIGO"
    nom_col = next((cnorm[c] for c in cnorm if any(k in c for k in ["nombre","causa","descripcion"])), None) or "NOMBRE"
    cas_col = next((cnorm[c] for c in cnorm if any(k in c for k in ["casos","total","defunciones","muertes"])), None) or "CASOS"
    out = df[[cod_col, nom_col, cas_col]].copy()
    out.columns = ["CODIGO","NOMBRE","CASOS"]
    out["CODIGO"] = out["CODIGO"].astype(str).str.strip()
    out["NOMBRE"] = out["NOMBRE"].astype(str).str.strip()
    out["CASOS"]  = pd.to_numeric(out["CASOS"], errors="coerce").fillna(0).astype(int)
    return out

# =============================================================================
# Datos base (GeoJSON + mensual demo)
# =============================================================================
BASE = Path(__file__).parent
DATA_DIR = BASE / "data"

FILE_GEO = DATA_DIR / "departamentos.geojson"
with open(FILE_GEO, "r", encoding="utf-8") as f:
    geo = json.load(f)

rows = []
for feat in geo.get("features", []):
    props = feat.get("properties", {}) or {}
    geom = feat.get("geometry", {}) or {}
    if geom.get("type") == "Point":
        lon, lat = geom.get("coordinates", [None, None])
        nombre = props.get("NOMBRE_DPT") or props.get("NOMBRE_DEPTO") or props.get("DEPARTAMENTO")
        if nombre and lat is not None and lon is not None:
            rows.append({"NOMBRE_DPT": nombre.strip(), "LAT": float(lat), "LON": float(lon)})
df_map = pd.DataFrame(rows).dropna().sort_values("NOMBRE_DPT").reset_index(drop=True)

base_val, paso = 60, 2
df_map["MUERTES"] = [base_val + i * paso for i in range(len(df_map))]
df_map["LABEL"] = df_map["NOMBRE_DPT"]

MESES = ["Enero","Febrero","Marzo","Abril","Mayo","Junio","Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"]
VALORES = np.array([19,17,18,18,19,20,21,20,18,19,19,21], dtype=float)
pesos = VALORES / VALORES.sum()

dept_month_rows = []
for _, r in df_map.iterrows():
    muertes_mes = (r["MUERTES"] * pesos).round().astype(int)
    for mes, val in zip(MESES, muertes_mes):
        dept_month_rows.append({"NOMBRE_DPT": r["NOMBRE_DPT"], "MES": mes, "MUERTES": int(val)})
dept_month = pd.DataFrame(dept_month_rows)
national_month = dept_month.groupby("MES", as_index=False)["MUERTES"].sum()

def fig_barras(dep: str, metrica: str):
    if dep == "Todos":
        g = national_month.copy(); titulo = "Distribución de defunciones por mes (Total)"
    else:
        g = dept_month[dept_month["NOMBRE_DPT"] == dep].copy()
        if g.empty: g = pd.DataFrame({"MES": MESES, "MUERTES": 0})
        titulo = f"Distribución de defunciones por mes ({dep})"
    if metrica == "indice":
        max_val = g["MUERTES"].max()
        g["VAL"] = 0 if max_val == 0 else (g["MUERTES"] / max_val) * 100.0
        ylab = "Índice relativo (demo)"
    else:
        g["VAL"] = g["MUERTES"]; ylab = "Muertes (n)"
    fig = px.bar(g, x="MES", y="VAL", title=titulo, labels={"VAL": ylab, "MES": "MES"})
    fig.update_layout(xaxis=dict(categoryorder="array", categoryarray=MESES),
                      margin=dict(l=20, r=20, t=60, b=20))
    fig.update_traces(marker_color="#5A78FF")
    return fig, g

def kpis(g: pd.DataFrame, metrica: str) -> str:
    total = int(g["MUERTES"].sum())
    if len(g):
        idx_max = g["VAL"].astype(float).idxmax(); idx_min = g["VAL"].astype(float).idxmin()
        pico_mes, pico_val = g.loc[idx_max, "MES"], g.loc[idx_max, "VAL"]
        mini_mes, mini_val = g.loc[idx_min, "MES"], g.loc[idx_min, "VAL"]
    else:
        pico_mes, pico_val, mini_mes, mini_val = "-", 0, "-", 0
    if metrica == "muertes":
        pico_txt = f"{pico_mes}: {int(float(pico_val)):,}"
        min_txt  = f"{mini_mes}: {int(float(mini_val)):,}"
    else:
        pico_txt = f"{pico_mes}: {float(pico_val):.1f}"
        min_txt  = f"{mini_mes}: {float(mini_val):.1f}"
    return f"Total anual: {total:,} — Pico: {pico_txt} — Mínimo: {min_txt}"

def fig_mapa(df_plot: pd.DataFrame, depto: str | None):
    fig = px.scatter_mapbox(
        df_plot, lat="LAT", lon="LON", size="MUERTES", color="MUERTES",
        color_continuous_scale="Reds", size_max=35, zoom=4.3 if not depto else 5.2,
        height=540, hover_name="NOMBRE_DPT",
        hover_data={"MUERTES": True, "LAT": False, "LON": False},
    )
    fig.update_traces(text=df_plot.get("LABEL"), textposition="top center",
                      textfont=dict(size=12, color="#222"),
                      hovertemplate="<b>%{text}</b><br>Muertes: %{marker.size:,}<extra></extra>")
    fig.update_layout(mapbox_style="open-street-map",
                      margin=dict(l=20, r=20, t=60, b=20),
                      coloraxis_colorbar=dict(title="MUERTES"))
    return fig

# =============================================================================
# Municipios (desde Excel) + Respaldo para 10 departamentos
# =============================================================================
DIVI = _leer_divipola_desde_excel(DATA_DIR)
TARGET_DEPS = ["Cundinamarca","Antioquia","Valle del Cauca","Atlántico","Bolívar","Boyacá","Santander","Cauca","Nariño","Tolima"]
BACKUP_RAW = {
    "Cundinamarca":["Bogotá D.C.","Soacha","Chía","Zipaquirá","Facatativá","Fusagasugá","Girardot","Madrid","Mosquera","Villeta","La Mesa","Cajicá","Sibaté","Tocancipá","Funza"],
    "Antioquia":["Medellín","Bello","Itagüí","Envigado","Rionegro","Turbo","Apartadó","La Estrella","Caldas","Sabaneta","Copacabana","Girardota","La Ceja","Marinilla","Santa Rosa de Osos"],
    "Valle del Cauca":["Cali","Palmira","Buenaventura","Tuluá","Buga","Cartago","Yumbo","Jamundí","Candelaria","Sevilla","Zarzal","Caicedonia","La Unión","Roldanillo","Guacarí"],
    "Atlántico":["Barranquilla","Soledad","Malambo","Sabanalarga","Galapa","Puerto Colombia","Baranoa","Palmar de Varela","Santo Tomás","Ponedera","Polonuevo","Candelaria","Luruaco","Campo de la Cruz","Juan de Acosta"],
    "Bolívar":["Cartagena","Magangué","Arjona","Turbaco","El Carmen de Bolívar","San Juan Nepomuceno","Mompós","María La Baja","San Jacinto","San Estanislao","Cicuco","Santa Rosa","Villanueva","Arenal","Clemencia"],
    "Boyacá":["Tunja","Sogamoso","Duitama","Chiquinquirá","Moniquirá","Paipa","Nobsa","Samacá","Tota","Soatá","Garagoa","Puerto Boyacá","Villa de Leyva","Tibasosa","Tenza"],
    "Santander":["Bucaramanga","Floridablanca","Girón","Piedecuesta","Barrancabermeja","San Gil","Socorro","Barbosa","Vélez","Málaga","Cimitarra","Lebrija","Puerto Wilches","Rionegro","Zapatoca"],
    "Cauca":["Popayán","Santander de Quilichao","Puerto Tejada","Guachené","Miranda","Patía","Timbío","Piendamó","El Tambo","Morales","Caloto","Toribío","Silvia","Puracé","Inzá"],
    "Nariño":["Pasto","Tumaco","Ipiales","Túquerres","Samaniego","Mallama","Barbacoas","La Unión","Sandoná","El Charco","Buesaco","Cumbal","Aldana","La Tola","Olaya Herrera"],
    "Tolima":["Ibagué","Espinal","Honda","Melgar","Lérida","Mariquita","Chaparral","Líbano","Fresno","Guamo","Coello","Coyaima","Natagaima","Saldaña","Purificación"],
}
BACKUP = {_norm(k): v for k, v in BACKUP_RAW.items()}

def municipios_por_departamento(dep: str) -> list[str]:
    dep_norm = _norm(dep)
    if not DIVI.empty:
        m = (DIVI[DIVI["DEP_NORM"] == dep_norm].sort_values("MUN_NORM")["MUNICIPIO"].astype(str).unique().tolist())
        if m: return m
    return BACKUP.get(dep_norm, [])

# ====== Causas (Top 10)
CAUSAS = _leer_causas_desde_data(DATA_DIR)
TOP10_CAUSAS = CAUSAS.sort_values("CASOS", ascending=False).head(10).reset_index(drop=True)

# ====== Muertes por SEXO (demo reproducible)
def _sexo_demo(df_deptos: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, r in df_deptos.iterrows():
        dpto = r["NOMBRE_DPT"]; total = int(r["MUERTES"])
        h_share = 0.52 + ((hash(_norm(dpto)) % 11) - 5) / 100.0
        h = int(round(total * h_share)); m = total - h
        rows += [{"NOMBRE_DPT": dpto, "SEXO": "Hombres", "MUERTES": h},
                 {"NOMBRE_DPT": dpto, "SEXO": "Mujeres", "MUERTES": m}]
    out = pd.DataFrame(rows)
    orden = (out.groupby("NOMBRE_DPT")["MUERTES"].sum().sort_values(ascending=False).index.tolist())
    out["NOMBRE_DPT"] = pd.Categorical(out["NOMBRE_DPT"], categories=orden, ordered=True)
    return out
DF_SEXO = _sexo_demo(df_map)

# ====== Referencia de GRUPO_EDAD1 (con categorías y rangos) + demo
EDAD_REF = [
    {"COD":"0–4",  "CATEG":"Mortalidad neonatal",      "RANGO":"Menor de 1 mes"},
    {"COD":"5–6",  "CATEG":"Mortalidad infantil",      "RANGO":"1 a 11 meses"},
    {"COD":"7–8",  "CATEG":"Primera infancia",         "RANGO":"1 a 4 años"},
    {"COD":"9–10", "CATEG":"Niñez",                    "RANGO":"5 a 14 años"},
    {"COD":"11",   "CATEG":"Adolescencia",             "RANGO":"15 a 19 años"},
    {"COD":"12–13","CATEG":"Juventud",                 "RANGO":"20 a 29 años"},
    {"COD":"14–16","CATEG":"Adultez temprana",         "RANGO":"30 a 44 años"},
    {"COD":"17–19","CATEG":"Adultez intermedia",       "RANGO":"45 a 59 años"},
    {"COD":"20–24","CATEG":"Vejez",                    "RANGO":"60 a 84 años"},
    {"COD":"25–28","CATEG":"Longevidad / Centenarios", "RANGO":"85 a 100+ años"},
    {"COD":"29",   "CATEG":"Edad desconocida",         "RANGO":"Sin información"},
]
GRUPOS_EDAD_COD = [d["COD"] for d in EDAD_REF]
MAP_CATEG = {d["COD"]: d["CATEG"] for d in EDAD_REF}
MAP_RANGO = {d["COD"]: d["RANGO"] for d in EDAD_REF}
TICKTEXT_EDAD = [f"{cod} · {MAP_CATEG[cod]}" for cod in GRUPOS_EDAD_COD]

PESOS_EDAD = np.array([0.01,0.02,0.03,0.05,0.05,0.10,0.16,0.22,0.22,0.13,0.01], dtype=float)
PESOS_EDAD = PESOS_EDAD / PESOS_EDAD.sum()

def _edad_demo(df_deptos: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, r in df_deptos.iterrows():
        dpto = r["NOMBRE_DPT"]; total = int(r["MUERTES"])
        seed = abs(hash(_norm(dpto))) % (2**32)
        rng = np.random.default_rng(seed)
        jitter = rng.normal(1.0, 0.03, size=len(GRUPOS_EDAD_COD))
        w = (PESOS_EDAD * jitter).clip(min=0.001); w = w / w.sum()
        vals = np.round(total * w).astype(int)
        diff = total - int(vals.sum())
        if diff != 0: vals[np.argmax(w)] += diff
        for cod, v in zip(GRUPOS_EDAD_COD, vals):
            rows.append({"NOMBRE_DPT": dpto, "COD": cod, "MUERTES": int(v)})
    return pd.DataFrame(rows)

DF_EDAD = _edad_demo(df_map)

# =============================================================================
# App y Layout
# =============================================================================
app = Dash(__name__, suppress_callback_exceptions=True)
server = app.server

app.layout = html.Div(
    style={"maxWidth": "1080px", "margin": "0 auto", "fontFamily": "Arial, sans-serif"},
    children=[
        html.H3("Panel de mortalidad — Colombia (demo)"),
        dcc.Tabs(
            id="tabs",
            value="tab-general",
            children=[
                dcc.Tab(
                    label="Visión general",
                    value="tab-general",
                    children=[
                        html.Div(
                            style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "12px"},
                            children=[
                                html.Div([
                                    html.Label("Departamento (para barras):"),
                                    dcc.Dropdown(id="dep_barras",
                                        options=["Todos"] + sorted(df_map["NOMBRE_DPT"].unique().tolist()),
                                        value="Todos", clearable=False),
                                ]),
                                html.Div([
                                    html.Label("Métrica:"),
                                    dcc.Dropdown(id="metrica",
                                        options=[{"label":"Índice relativo (demo)","value":"indice"},
                                                 {"label":"Muertes (n)","value":"muertes"}],
                                        value="indice", clearable=False),
                                ]),
                            ],
                        ),
                        html.Div(id="kpi_text", style={"margin":"6px 0 10px","fontSize":"14px","color":"#444"}),
                        dcc.Graph(id="fig_barras"),
                        html.Hr(),
                        html.Label("Resaltar en el mapa (opcional):"),
                        dcc.Dropdown(
                            id="sel-depto",
                            options=[{"label": d, "value": d} for d in sorted(df_map["NOMBRE_DPT"].unique())],
                            value=None, placeholder="Todos los departamentos", clearable=True,
                            style={"maxWidth":"520px","marginBottom":"10px"},
                        ),
                        dcc.Graph(id="fig_map"),
                        html.Div(id="card-depto", style={"marginTop":"6px","fontSize":"14px","color":"#555"}),
                    ],
                ),

                dcc.Tab(
                    label="Municipios (torta)",
                    value="tab-muni",
                    children=[
                        html.Div(
                            style={"display":"flex","gap":"16px","alignItems":"flex-end","margin":"12px 0"},
                            children=[
                                html.Div([
                                    html.Label("Departamento (10 disponibles):"),
                                    dcc.Dropdown(id="dep_muni",
                                        options=[{"label":d,"value":d} for d in TARGET_DEPS],
                                        value=TARGET_DEPS[0], clearable=False, style={"minWidth":"340px"}),
                                ], style={"flex":1}),
                                html.Div([
                                    html.Label("Número de municipios a mostrar (Top N):"),
                                    dcc.Slider(id="topn", min=5, max=20, step=1, value=12,
                                               tooltip={"placement":"bottom","always_visible":True}),
                                ], style={"flex":2}),
                            ],
                        ),
                        dcc.Graph(id="fig_pie"),
                        html.Small("Nombres de municipios desde Excel en ./data (columnas de Departamento y Municipio).",
                                   style={"color":"#666"}),
                    ],
                ),

                dcc.Tab(
                    label="Causas (Top 10)",
                    value="tab-causas",
                    children=[
                        html.Div(style={"margin":"12px 0"}, children=[
                            html.P("Listado de las 10 principales causas de muerte en Colombia (ordenadas de mayor a menor)."),
                            dash_table.DataTable(
                                id="tabla-top10-causas",
                                data=TOP10_CAUSAS.to_dict("records"),
                                columns=[
                                    {"name":"Código","id":"CODIGO","type":"text"},
                                    {"name":"Nombre de la causa","id":"NOMBRE","type":"text"},
                                    {"name":"Total de casos","id":"CASOS","type":"numeric"},
                                ],
                                sort_action="native", filter_action="native", page_action="none",
                                export_format="csv", export_headers="display",
                                style_table={"overflowX":"auto"},
                                style_header={"backgroundColor":"#f5f5f5","fontWeight":"bold","border":"1px solid #ddd"},
                                style_cell={"padding":"10px","border":"1px solid #eee","fontSize":"14px"},
                                style_data_conditional=[
                                    {"if":{"row_index":"odd"},"backgroundColor":"#fafafa"},
                                    {"if":{"column_id":"CASOS"},"textAlign":"right"},
                                ],
                            ),
                            html.Small("Fuente: ./data/causas_mortalidad.csv o .xlsx (los nombres de columnas son flexibles).",
                                       style={"color":"#666","display":"block","marginTop":"8px"}),
                        ]),
                    ],
                ),

                dcc.Tab(
                    label="Muertes por sexo",
                    value="tab-sexo",
                    children=[
                        html.Div(style={"display":"flex","gap":"12px","alignItems":"center","margin":"10px 0"}, children=[
                            html.Label("Modo:"),
                            dcc.RadioItems(id="modo_sexo",
                                options=[{"label":" Totales","value":"abs"},{"label":" Porcentaje","value":"pct"}],
                                value="abs", inline=True),
                        ]),
                        dcc.Graph(id="fig_sexo"),
                        html.Small("Barras apiladas por departamento (Hombres/Mujeres). "
                                   "Si no hay datos por sexo, se usa una partición demo reproducible.",
                                   style={"color":"#666"}),
                    ],
                ),

                dcc.Tab(
                    label="Distribución por edad (histograma)",
                    value="tab-edad",
                    children=[
                        html.Div(style={"display":"flex","gap":"16px","alignItems":"center","margin":"12px 0"}, children=[
                            html.Div(style={"minWidth":"320px"}, children=[
                                html.Label("Departamento:"),
                                dcc.Dropdown(
                                    id="dep_edad",
                                    options=[{"label":"Todos","value":"Todos"}] +
                                            [{"label":d,"value":d} for d in df_map["NOMBRE_DPT"].unique()],
                                    value="Todos", clearable=False),
                            ]),
                            html.Div(children=[
                                html.Label("Modo:"),
                                dcc.RadioItems(id="modo_edad",
                                    options=[{"label":" Totales","value":"abs"},{"label":" Porcentaje","value":"pct"}],
                                    value="abs", inline=True),
                            ]),
                        ]),
                        dcc.Graph(id="fig_edad"),
                        html.Small("Eje X con Código DANE + Categoría. Tooltip incluye categoría y rango de edad.",
                                   style={"color":"#666"}),
                    ],
                ),

                # ---- Pestaña: líneas mensuales (INTERACTIVA)
                dcc.Tab(
                    label="Tendencia mensual (líneas)",
                    value="tab-lineas",
                    children=[
                        html.Div(style={"margin":"12px 0"}, children=[
                            html.P("Gráfico de líneas: total de muertes por mes (demo). Selecciona las series y la métrica."),
                            html.Div(style={"display":"flex","gap":"12px","flexWrap":"wrap","alignItems":"end"}, children=[
                                html.Div(style={"minWidth":"320px"}, children=[
                                    html.Label("Series a mostrar:"),
                                    dcc.Dropdown(
                                        id="series_lineas",
                                        options=[{"label":"Colombia (Total)","value":"__COL__"}] +
                                                [{"label":d,"value":d} for d in sorted(df_map["NOMBRE_DPT"].unique())],
                                        value=["__COL__"], multi=True, clearable=False
                                    ),
                                ]),
                                html.Div(children=[
                                    html.Label("Métrica:"),
                                    dcc.RadioItems(
                                        id="metrica_lineas",
                                        options=[{"label":" Totales","value":"abs"},
                                                 {"label":" Índice relativo (100 = mes pico)","value":"idx"}],
                                        value="abs", inline=True
                                    ),
                                ]),
                                html.Div(children=[
                                    html.Label("Modo de línea:"),
                                    dcc.RadioItems(
                                        id="modo_lineas",
                                        options=[{"label":" Líneas","value":"lines"},
                                                 {"label":" Líneas + marcadores","value":"lines+markers"}],
                                        value="lines+markers", inline=True
                                    ),
                                ]),
                            ]),
                            dcc.Graph(id="fig_lineas"),
                            html.Small("Fuente: serie mensual agregada a partir del demo por departamento.",
                                       style={"color":"#666"})
                        ])
                    ],
                ),
            ],
        ),
    ],
)

# =============================================================================
# Callbacks
# =============================================================================
@app.callback(
    Output("fig_barras", "figure"),
    Output("kpi_text", "children"),
    Input("dep_barras", "value"),
    Input("metrica", "value"),
)
def actualizar_barras(dep_barras, metrica):
    fig, g = fig_barras(dep_barras, metrica)
    return fig, kpis(g, metrica)

@app.callback(
    Output("fig_map", "figure"),
    Output("card-depto", "children"),
    Input("sel-depto", "value"),
)
def actualizar_mapa_y_card(depto):
    if depto:
        df_plot = df_map[df_map["NOMBRE_DPT"] == depto].copy()
        nota = f"Departamento seleccionado: {depto}"
    else:
        df_plot = df_map.copy()
        nota = "Mostrando todos los departamentos"
    fig = fig_mapa(df_plot, depto)
    if depto and not df_plot.empty:
        total = int(df_plot["MUERTES"].iloc[0])
        card = f"🧭 {nota} — Muertes: {total:,}"
    else:
        total = int(df_map["MUERTES"].sum())
        card = f"🧭 {nota} — Muertes (suma de todos los puntos): {total:,}"
    return fig, card

@app.callback(
    Output("fig_pie", "figure"),
    Input("dep_muni", "value"),
    Input("topn", "value"),
)
def actualizar_pie(dep, topn):
    muns = municipios_por_departamento(dep)
    muns = sorted(muns, key=_norm)[: max(1, int(topn))]
    if not muns:
        muns = ["(Sin municipios)"]
    rng = np.random.default_rng(abs(hash(_norm(dep))) % (2**32))
    valores = np.clip(rng.normal(loc=100, scale=25, size=len(muns)), 10, None)
    df = pd.DataFrame({"Municipio": muns, "Muertes (demo)": valores})
    fig = px.pie(df, names="Municipio", values="Muertes (demo)",
                 title=f"{dep}: municipios (Top {len(df)})", hole=0.45)
    fig.update_traces(textposition="inside", textinfo="label+percent")
    total = int(df["Muertes (demo)"].sum())
    fig.update_layout(annotations=[dict(text=f"Total demo:<br><b>{total:,}</b>",
                                        x=0.5, y=0.5, showarrow=False, font=dict(size=13))],
                      margin=dict(l=20, r=20, t=60, b=20))
    return fig

@app.callback(
    Output("fig_sexo", "figure"),
    Input("modo_sexo", "value"),
)
def actualizar_barras_sexo(modo):
    df = DF_SEXO.copy()
    titulo = "Muertes por sexo y departamento (totales)" if modo == "abs" else \
             "Muertes por sexo y departamento (% dentro de cada dpto.)"
    if modo == "pct":
        df["TOTAL"] = df.groupby("NOMBRE_DPT")["MUERTES"].transform("sum")
        df["VAL"] = (df["MUERTES"] / df["TOTAL"]) * 100.0
        y_col, y_lab, text = "VAL", "Porcentaje (%)", df["VAL"].round(1).astype(str) + "%"
    else:
        y_col, y_lab, text = "MUERTES", "Muertes (n)", None
    fig = px.bar(df.sort_values(["NOMBRE_DPT","SEXO"]), x="NOMBRE_DPT", y=y_col, color="SEXO",
                 barmode="stack", title=titulo, labels={"NOMBRE_DPT":"Departamento", y_col: y_lab}, text=text)
    fig.update_layout(xaxis=dict(tickangle=-30), margin=dict(l=20, r=20, t=60, b=80), legend_title_text="Sexo")
    return fig

# --- Histograma por edad (con nombres y rangos en el eje/tooltip)
@app.callback(
    Output("fig_edad", "figure"),
    Input("dep_edad", "value"),
    Input("modo_edad", "value"),
)
def actualizar_histograma_edad(dep, modo):
    if dep == "Todos":
        g = DF_EDAD.groupby("COD", as_index=False)["MUERTES"].sum()
        titulo_base = "Distribución por edad (Todos los departamentos)"
    else:
        g = DF_EDAD[DF_EDAD["NOMBRE_DPT"] == dep].groupby("COD", as_index=False)["MUERTES"].sum()
        titulo_base = f"Distribución por edad ({dep})"

    g = g.set_index("COD").reindex(GRUPOS_EDAD_COD).fillna(0).reset_index()
    g["CATEGORIA"] = g["COD"].map(MAP_CATEG)
    g["RANGO"]     = g["COD"].map(MAP_RANGO)

    if modo == "pct":
        total = g["MUERTES"].sum()
        g["VAL"] = 0 if total == 0 else (g["MUERTES"] / total) * 100.0
        y_col, y_lab, text = "VAL", "Porcentaje (%)", g["VAL"].round(1).astype(str) + "%"
        titulo = titulo_base + " — % dentro del total"
    else:
        g["VAL"] = g["MUERTES"]
        y_col, y_lab, text = "VAL", "Muertes (n)", None
        titulo = titulo_base + " — totales"

    fig = px.bar(
        g, x="COD", y=y_col, title=titulo,
        labels={"COD":"Código · Categoría (GRUPO_EDAD1)", y_col: y_lab},
        hover_data={"CATEGORIA": True, "RANGO": True, "MUERTES": True, "VAL": False},
        text=text
    )
    fig.update_layout(
        xaxis=dict(
            categoryorder="array",
            categoryarray=GRUPOS_EDAD_COD,
            tickmode="array",
            tickvals=GRUPOS_EDAD_COD,
            ticktext=TICKTEXT_EDAD,
            tickangle=-10,
        ),
        margin=dict(l=20, r=20, t=60, b=80),
    )
    fig.update_traces(
        hovertemplate="<b>%{x}</b><br>Categoría: %{customdata[0]}<br>Rango: %{customdata[1]}"
                      "<br>Muertes: %{customdata[2]:,}<extra></extra>"
    )
    return fig

# --- NUEVO: Líneas mensuales interactivas
@app.callback(
    Output("fig_lineas", "figure"),
    Input("series_lineas", "value"),
    Input("metrica_lineas", "value"),
    Input("modo_lineas", "value"),
)
def actualizar_lineas(series_sel, metrica, modo):
    # fallback
    if not series_sel:
        series_sel = ["__COL__"]

    frames = []
    for s in series_sel:
        if s == "__COL__":
            g = national_month.copy()
            g["Serie"] = "Colombia"
        else:
            g = (dept_month[dept_month["NOMBRE_DPT"] == s]
                 .groupby("MES", as_index=False)["MUERTES"].sum())
            g["Serie"] = s
        # asegurar todos los meses
        g = g.set_index("MES").reindex(MESES).fillna(0).reset_index()
        # métrica
        if metrica == "idx":
            maxv = g["MUERTES"].max()
            g["VAL"] = 0 if maxv == 0 else (g["MUERTES"] / maxv) * 100.0
        else:
            g["VAL"] = g["MUERTES"]
        frames.append(g[["MES","VAL","Serie"]])

    plot = pd.concat(frames, ignore_index=True)
    cat_mes = pd.Categorical(plot["MES"], categories=MESES, ordered=True)
    plot = plot.assign(MES=cat_mes).sort_values(["Serie","MES"])

    ylab = "Índice (máx=100)" if metrica == "idx" else "Muertes (n)"
    fig = px.line(
        plot, x="MES", y="VAL", color="Serie",
        markers=(modo == "lines+markers"),
        labels={"MES":"Mes","VAL": ylab, "Serie":"Serie"},
        title="Tendencia mensual del total de muertes (demo)"
    )
    fig.update_layout(
        xaxis=dict(categoryorder="array", categoryarray=MESES),
        margin=dict(l=20, r=20, t=60, b=40),
        height=480,
        hovermode="x unified",
    )
    fig.update_traces(connectgaps=True, line_width=3)
    return fig

# =============================================================================
# Main
# =============================================================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    app.run_server(host="0.0.0.0", port=port, debug=False)















































































