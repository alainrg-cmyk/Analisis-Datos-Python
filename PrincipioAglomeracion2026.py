# =========================
# MAPA ZMVM: PBT (%) + POT (Jenks)
# =========================
import os
os.environ["OMP_NUM_THREADS"] = "1"
import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as Pylance
import contextily as cx
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from mapclassify import NaturalBreaks
from adjustText import adjust_text
from matplotlib.lines import Line2D
from shapely.geometry import Point
# -------------------------
# 1. PARÁMETROS EXPLÍCITOS
# -------------------------
CRS_PROJ = "EPSG:32614"          # UTM 14N WGS84
JENKS_K = 6
FIG_SIZE_A4 = (11.69, 8.27)      # pulgadas, A4 horizontal
DPI_OUT = 300

SHAPE_PATH = "ZMVM_Base_Trabajo.shp"
CSV_PATH = "SAIC_ZMVM.csv"

OUT_PNG = "ZMVM_PBT_POT_2018.png"
OUT_TIFF = "ZMVM_PBT_POT_2018.tiff"
# -------------------------
# 2. CARGA DE DATOS
# -------------------------
#gdf = gpd.read_file(SHAPE_PATH)

gdf = gpd.read_file("ZMVM_Base_Trabajo.shp")
gdf["CVMUN"] = gdf["CVMUN"].astype(str).str.strip()

#df = pd.read_csv(CSV_PATH)

df = pd.read_csv(
    "SAIC_ZMVM.csv",
    sep=",",               # separador REAL
    encoding="utf-8-sig",  # elimina BOM
    engine="python"        # ignora irregularidades
)

# Limpieza obligatoria
df.columns = (
    df.columns
      .str.strip()
      .str.replace(" ", "", regex=False)
)

print(df.columns.tolist())
df["CVMUN"] = df["CVMUN"].astype(str).str.zfill(5)
df["PBT"] = pd.to_numeric(df["PBT"], errors="coerce")
df["POT"] = pd.to_numeric(df["POT"], errors="coerce")
gdf = gdf.merge(
    df[["CVMUN", "Munalcaldia", "PBT", "POT"]],
    on="CVMUN",
    how="left",
    validate="one_to_one"
)
print(gdf.columns)

assert len(gdf) == 76, "No hay 76 municipios"
assert gdf["PBT"].isna().sum() == 0, "PBT con NaN"
assert gdf["POT"].isna().sum() == 0, "POT con NaN"

# -------------------------
# 4. CÁLCULOS
# -------------------------
# PBT %
total_pbt = gdf["PBT"].sum()
gdf["PBT_PCT"] = (gdf["PBT"] / total_pbt) * 100

# Proyección
gdf = gdf.to_crs(CRS_PROJ)
# -------------------------
# GEODataFrame PARA ETIQUETAS
# -------------------------
label_gdf = gdf.copy()
label_gdf["label_point"] = label_gdf.geometry.centroid

# Centroides
gdf["centroid"] = gdf.geometry.centroid
centroids = gpd.GeoDataFrame(gdf.drop(columns="geometry"),
                             geometry="centroid",
                             crs=CRS_PROJ)
# -------------------------
# 5. JENKS PARA POT
# -------------------------
jenks = NaturalBreaks(centroids["POT"], k=JENKS_K)
centroids["POT_CLASS"] = jenks.yb
jenks_bins = jenks.bins

# Tamaños de símbolos (claros y legibles)
size_map = [20, 40, 70, 110, 160, 220]
centroids["size"] = centroids["POT_CLASS"].map(lambda x: size_map[x])
# -------------------------
# 6. FIGURA
# -------------------------
fig, ax = plt.subplots(1, 1, figsize=FIG_SIZE_A4)
'''
# -------------------------
# AJUSTE DE MÁRGENES DEL EJE
# -------------------------
ax.set_position([0.03, 0.05, 0.94, 0.90])
'''
# Coropleta PBT %
gdf.plot(
    column="PBT_PCT",
    cmap="YlOrRd",
    linewidth=0.3,
    edgecolor="gray",
    legend=True,
    legend_kwds={
        "label": "Producción Bruta Total (PBT % ZMVM)",
        "orientation": "vertical",
        "shrink": 0.65
    },
    ax=ax
)
# Centroides POT
centroids.plot(
    ax=ax,
    markersize=centroids["size"],
    color="none",
    edgecolor="black",
    linewidth=0.6
)

# -------------------------
# 7. LEYENDA DE TAMAÑOS (POT)
# -------------------------
handles = []
labels = []

lower = 0
for i, upper in enumerate(jenks_bins):
    handles.append(Line2D(
        [0], [0],
        marker='o',
        color='w',
        markerfacecolor='none',
        markeredgecolor='black',
        markersize=(size_map[i] ** 0.3)
    ))
    labels.append(f"{int(lower):,} – {int(upper):,}")
    lower = upper

leg2 = ax.legend(
    handles, labels,
    title="Población Ocupada Total (POT Jenks, k=6)",
    loc="lower left",
    frameon=True
)
ax.add_artist(leg2)
# -------------------------
# 7B. ETIQUETAS CON HALO (TIPO QGIS)
# -------------------------

texts = []

for idx, row in label_gdf.iterrows():
    txt = ax.text(
        row["label_point"].x,
        row["label_point"].y,
        row["Munalcaldia"],
        fontsize=6.5,
        ha="center",
        va="center",
        color="black",
        zorder=10,
        path_effects=[
            pe.Stroke(linewidth=0.8, foreground="white"),
            pe.Normal()
        ]
    )
    texts.append(txt)

# -------------------------
# 7C. AJUSTE ANTI-SOLAPAMIENTO
# -------------------------
adjust_text(
    texts,
    ax=ax,
    expand_points=(1.2, 1.4),
    expand_text=(1.2, 1.4),
    force_text=0.8,
    force_points=0.5,
    arrowprops=dict(
        arrowstyle="-",
        color="gray",
        lw=0.4
    )
)

# -------------------------
# 8. DISEÑO CARTOGRÁFICO
# -------------------------
ax.set_title(
    "AGLOMERACION ECONÓMICA\n"
    "Zona Metropolitana del Valle de México\n"
    "PBT municipal (% del total ZMVM) y POT (centroides, Jenks k=6)\n"
    "2018",
    fontsize=12
)

ax.axis("off")

# Norte (simple, sin cursilería)
ax.annotate(
    "N",
    xy=(0.95, 0.15), xytext=(0.95, 0.05),
    arrowprops=dict(facecolor="black", width=3, headwidth=8),
    ha="center", va="center", fontsize=12,
    xycoords=ax.transAxes
)

# Escala gráfica aproximada (20 km)
x0, y0, x1, y1 = gdf.total_bounds
scale_len = 20000  # metros
ax.plot([x0 + 5000, x0 + 5000 + scale_len], [y0 + 5000, y0 + 5000], lw=3, color="black")
ax.text(x0 + 5000, y0 + 8000, "0", fontsize=8)
ax.text(x0 + 5000 + scale_len, y0 + 8000, "20 km", fontsize=8, ha="right")

# Créditos
fig.text(
    0.5, 0.02,
    "Fuente: INEGI, Censos Económicos 2018. Elaboración propia.\n"
    "Proyección: UTM Zona 14N (EPSG:32614). Clasificación POT: Jenks (k=6).",
    ha="center", fontsize=8
)
# -------------------------
# 9. EXPORTACIÓN
# -------------------------
#plt.savefig(OUT_PNG, dpi=DPI_OUT, bbox_inches="tight")
#plt.savefig(OUT_TIFF, dpi=DPI_OUT, bbox_inches="tight")
plt.show()