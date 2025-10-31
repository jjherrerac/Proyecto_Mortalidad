# -----------------------------------------------------------------------------
# Mortalidad en Colombia (demo) - App completa (solo GeoJSON local)
# - Barras mensuales por departamento o total (Muertes / Índice relativo demo)
# - Mapa con círculos (tamaño relativo a "muertes" demo) y resaltado opcional
# -----------------------------------------------------------------------------

from dash import Dash, html, dcc
from dash.dependencies import Input, Output
import plotly.express as px
import pandas as pd
import numpy as np
import json
from pathlib import Path

# =========================
# RUTAS Y LECTURAS
# =========================
BASE = Path(__file__).parent
FILE_GEO = BASE / "data" / "departamentos.geojson"

with open(FILE_GEO, "r", encoding="utf-8") as f:
    geo = json.load(f)

# =========================
# CONSTRUIR df_map (puntos desde el GeoJSON)
# =========================
rows = []
for feat in geo.get("features", []):
    props = feat.get("properties", {}) or {}
    geom = feat.get("geometry", {}) or {}
    if geom.get("type") == "Point":
        lon, lat = geom.get("coordinates", [None, None])
        nombre = props.get("NOMBRE_DPT") or props.get("NOMBRE_DEPTO") or props.get("DEPARTAMENTO")
        if nombre and lat is not None and lon is not None:
            rows.append({"NOMBRE_DPT": nombre.strip(), "LAT": lat, "LON": lon})

df_map = pd.DataFrame(rows).dropna()
if len(df_map) < 5:
    print("⚠️ Aviso: El GeoJSON cargó pocos puntos. Verifica que tenga geometrías 'Point' por departamento.")

# Asignar "muertes" demo (reproducible y creciente por orden alfabético)
base_val = 1800
paso = 40
df_map = df_map.sort_values("NOMBRE_DPT").reset_index(drop=True)
df_map["MUERTES"] = [base_val + i * paso for i in range(len(df_map))]
df_map["LABEL"] = df_map["NOMBRE_DPT"]

# =========================
# SERIE MENSUAL DEMO Y DESGLOSE POR DPTO
# =========================
MESES = ["Enero","Febrero","Marzo","Abril","Mayo","Junio",
         "Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"]
VALORES = np.array([21354,17974,19952,19233,20292,20742,
                    21372,21161,19778,20490,20330,21678], dtype=float)

# Pesos normalizados para repartir el total de cada dpto por mes
pesos = VALORES / VALORES.sum()

# Construir una tabla mensual por dpto (demo)
dept_month = []
for _, r in df_map.iterrows():
    # muertes mensuales del dpto = total_dpto * pesos
    muertes_mes = (r["MUERTES"] * pesos).round().astype(int)
    for mes, val in zip(MESES, muertes_mes):
        dept_month.append({"NOMBRE_DPT": r["NOMBRE_DPT"], "MES": mes, "MUERTES": int(val)})

dept_month = pd.DataFrame(dept_month)

# Series auxiliares para barras
national_month = dept_month.groupby("MES", as_index=False)["MUERTES"].sum()

# =========================
# FIGURAS BASE (solo estilos; datos dinámicos en callbacks)
# =========================
def barras(dep: str, metrica: str) -> px.bar:
    if dep == "Todos":
        g = national_month.copy()
        titulo = "Distribución de defunciones por mes (Total)"
    else:
        g = dept_month[dept_month["NOMBRE_DPT"] == dep].copy()
        if g.empty:
            g = pd.DataFrame({"MES": MESES, "MUERTES": 0})
        titulo = f"Distribución de defunciones por mes ({dep})"

    if metrica == "Índice relativo (demo)":
        max_val = g["MUERTES"].max()
        g["VAL"] = np.where(max_val == 0, 0, (g["MUERTES"] / max_val) * 100)
        ylab = "Índice relativo (demo)"
    else:
        g["VAL"] = g["MUERTES"]
        ylab = "Muertes (n)"

    fig = px.bar(g, x="MES", y="VAL", title=titulo, labels={"VAL": ylab, "MES": "MES"})
    fig.update_traces(marker_color="#5A78FF")
    fig.update_layout(margin=dict(l=20, r=20, t=60, b=20))
    return fig, g

def kpis_text(g: pd.DataFrame, metrica: str) -> str:
    total = int(g["MUERTES"].sum())
    # KPIs dependen del vector VAL (muertes o índice relativo)
    pico_row = g.loc[g["VAL"].idxmax()] if len(g) else {"MES": "-", "VAL": 0}
    min_row  = g.loc[g["VAL"].idxmin()] if len(g) else {"MES": "-", "VAL": 0}

    if metrica == "Muertes (n)":
        pico_txt = f"{pico_row['MES']}: {int(pico_row['VAL']):,}"
        min_txt  = f"{min_row['MES']}: {int(min_row['VAL']):,}"
    else:
        pico_txt = f"{pico_row['MES']}: {pico_row['VAL']:.1f}"
        min_txt  = f"{min_row['MES']}: {min_row['VAL']:.1f}"

    return f"Total anual: {total:,} — Pico: {pico_txt} — Mínimo: {min_txt}"

def mapa(df_plot: pd.DataFrame, depto: str | None) -> px.scatter_mapbox:
    fig = px.scatter_mapbox(
        df_plot,
        lat="LAT",
        lon="LON",
        size="MUERTES",
        color="MUERTES",
        color_continuous_scale="Reds",
        size_max=50,
        zoom=4.3 if not depto else 5.2,
        height=520,
        hover_name="NOMBRE_DPT",
        hover_data={"MUERTES": True, "LAT": False, "LON": False},
    )
    fig.update_traces(
        text=df_plot.get("LABEL"),
        textposition="top center",
        textfont=dict(size=12, color="#222"),
        hovertemplate="<b>%{text}</b><br>Muertes: %{marker.size:,}<extra></extra>",
    )
    fig.update_layout(
        mapbox_style="open-street-map",
        margin=dict(l=20, r=20, t=60, b=20),
        coloraxis_colorbar=dict(title="MUERTES"),
    )
    return fig

# =========================
# DASH APP
# =========================
app = Dash(__name__)

app.layout = html.Div(
    style={"maxWidth": "980px", "margin": "0 auto", "fontFamily": "Arial, sans-serif"},
    children=[
        html.H3("Actividad 4 — Mortalidad en Colombia (2019)"),

        # Controles de barras
        html.Div(
            style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "10px"},
            children=[
                html.Div([
                    html.Label("Departamento (para barras):"),
                    dcc.Dropdown(
                        id="dep_barras",
                        options=["Todos"] + sorted(df_map["NOMBRE_DPT"].unique().tolist()),
                        value="Todos",
                        clearable=False,
                    ),
                ]),
                html.Div([
                    html.Label("Métrica:"),
                    dcc.Dropdown(
                        id="metrica",
                        options=["Muertes (n)", "Índice relativo (demo)"],
                        value="Índice relativo (demo)",
                        clearable=False,
                    ),
                ]),
            ],
        ),

        # KPIs y barras
        html.Div(id="kpi_text", style={"marginTop": "6px", "marginBottom": "6px", "fontSize": "14px", "color": "#444"}),
        dcc.Graph(id="fig_barras"),

        html.Hr(),

        # Control del mapa
        html.Label("Resaltar en el mapa (opcional):"),
        dcc.Dropdown(
            id="sel-depto",
            options=[{"label": d, "value": d} for d in sorted(df_map["NOMBRE_DPT"].unique())],
            value=None,            # None = ver todos
            placeholder="Todos los departamentos",
            clearable=True,
            style={"maxWidth": "480px", "marginBottom": "10px"}
        ),

        dcc.Graph(id="fig_map"),
        html.Div(id="card-depto", style={"marginTop": "6px", "fontSize": "14px", "color": "#555"}),
    ],
)

# =========================
# CALLBACKS
# =========================
@app.callback(
    Output("fig_barras", "figure"),
    Output("kpi_text", "children"),
    Input("dep_barras", "value"),
    Input("metrica", "value"),
)
def actualizar_barras(dep_barras, metrica):
    fig, g = barras(dep_barras, metrica)
    kpi = kpis_text(g, metrica)
    return fig, kpi

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

    fig = mapa(df_plot, depto)

    if depto and not df_plot.empty:
        total = int(df_plot["MUERTES"].iloc[0])
        card = f"🧭 {nota} — Muertes: {total:,}"
    else:
        total = int(df_map["MUERTES"].sum())
        card = f"🧭 {nota} — Muertes (suma de todos los puntos): {total:,}"

    return fig, card

# =========================
# MAIN
# =========================
if __name__ == "__main__":
    app.run(debug=True)














































