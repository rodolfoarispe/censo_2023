#!/usr/bin/env python3
"""
Script para generar mapas interactivos (choropleth) de cobertura vs pobreza en Panamá.

Uso:
    # Mapa de cobertura %
    python choropleth_cobertura.py --metric cobertura --output mapa_cobertura.html

    # Mapa de gap absoluto
    python choropleth_cobertura.py --metric gap --output mapa_gap.html

    # Mapa de pobreza extrema
    python choropleth_cobertura.py --metric pobreza_extrema --output mapa_pobreza_extrema.html

    # Mostrar en navegador
    python choropleth_cobertura.py --metric cobertura --output mapa.html --show
"""

import argparse
import os
import geopandas as gpd
import duckdb
import folium
from folium import plugins
import pandas as pd
import webbrowser
import tempfile

# Configuración
GEOPARQUET_PATH = "data/geo/corregimientos.parquet"
SHAPEFILE_PATH = "/home/rodolfoarispe/Descargas/Panama_Corregimientos_Boundaries_2024/Corregimientos_2024.shp"
DB_PATH = "censo_2023.duckdb"


def load_data():
    """Carga datos geográficos desde GeoParquet (o shapefile si no existe)"""
    import os

    # Intentar cargar GeoParquet primero (más eficiente)
    if os.path.exists(GEOPARQUET_PATH):
        print(f"📥 Cargando {GEOPARQUET_PATH}...")
        gdf = gpd.read_parquet(GEOPARQUET_PATH)
        print(f"   ✓ {len(gdf)} corregimientos cargados")
        return gdf

    # Fallback: cargar shapefile y crear GeoParquet
    print("📥 Cargando shapefile (no se encontró GeoParquet)...")
    gdf = gpd.read_file(SHAPEFILE_PATH)
    gdf["id_corr_int"] = gdf["ID_CORR"].astype(int)

    print("📥 Cargando datos de BD...")
    conn = duckdb.connect(DB_PATH)

    # Query de datos con cobertura
    db_data = conn.execute(
        """
        SELECT 
            m.codigo_provincia * 10000 + m.codigo_distrito * 100 + m.codigo_corregimiento as id_corr_int,
            m.provincia,
            m.distrito,
            m.corregimiento,
            m.codigo_provincia,
            m.codigo_distrito,
            m.codigo_corregimiento,
            m.total_personas,
            m.pct_pobreza_general_personas,
            m.pct_pobreza_extrema_personas,
            COUNT(DISTINCT p.cedula) as beneficiarios_total
        FROM mapa_pobreza m
        LEFT JOIN planilla p ON 
            m.codigo_provincia * 10000 + m.codigo_distrito * 100 + m.codigo_corregimiento = p.id_correg
        GROUP BY 
            m.codigo_provincia, m.codigo_distrito, m.codigo_corregimiento,
            m.provincia, m.distrito, m.corregimiento,
            m.total_personas, m.pct_pobreza_general_personas, m.pct_pobreza_extrema_personas
        ORDER BY id_corr_int
    """
    ).df()

    conn.close()

    # Merge
    gdf = gdf.merge(db_data, on="id_corr_int", how="left")

    # Calcular métricas
    gdf["pobres_general"] = (
        gdf["total_personas"] * gdf["pct_pobreza_general_personas"]
    ).round(0)
    gdf["pobres_extremos"] = (
        gdf["total_personas"] * gdf["pct_pobreza_extrema_personas"]
    ).round(0)
    gdf["pobres_total"] = gdf["pobres_general"]
    gdf["beneficiarios_total"] = gdf["beneficiarios_total"].fillna(0).astype("int64")
    gdf["gap"] = gdf["pobres_total"] - gdf["beneficiarios_total"]
    gdf["cobertura_pct"] = (
        (gdf["beneficiarios_total"] / gdf["pobres_total"] * 100).fillna(0).round(2)
    )

    # Renombrar para claridad
    gdf = gdf.rename(
        columns={
            "Provincia": "provincia_nombre",
            "Distrito": "distrito_nombre",
            "Corregimie": "corregimiento_nombre",
            "Area_HA": "area_hectareas",
            "ID_CORR": "id_corr_str",
        }
    )

    return gdf


def get_color_scale(metric):
    """Retorna configuración de colores según métrica"""
    if metric == "cobertura":
        return {
            "name": "Cobertura (%)",
            "column": "cobertura_pct",
            "vmin": 0,
            "vmax": 100,
            "colormap": "RdYlGn",  # Rojo -> Amarillo -> Verde
            "tooltip_format": "{:.2f}%",
        }
    elif metric == "gap":
        return {
            "name": "Gap (personas sin cobertura)",
            "column": "gap",
            "vmin": 0,
            "vmax": None,  # Auto
            "colormap": "YlOrRd",  # Amarillo -> Naranja -> Rojo
            "tooltip_format": "{:,.0f}",
        }
    elif metric == "pobreza_extrema":
        return {
            "name": "Pobreza Extrema (%)",
            "column": "pct_pobreza_extrema_personas",
            "vmin": 0,
            "vmax": None,
            "colormap": "Reds",
            "tooltip_format": "{:.2f}%",
        }
    elif metric == "pobreza_general":
        return {
            "name": "Pobreza General (%)",
            "column": "pct_pobreza_general_personas",
            "vmin": 0,
            "vmax": None,
            "colormap": "Blues",
            "tooltip_format": "{:.2f}%",
        }
    else:
        raise ValueError(f"Métrica no válida: {metric}")


def create_choropleth(gdf, metric="cobertura", output_file="mapa_cobertura.html"):
    """Crea mapa interactivo tipo choropleth"""

    color_config = get_color_scale(metric)
    column = color_config["column"]

    print(f"\n📊 Creando choropleth para: {color_config['name']}")
    print(f"   Min: {gdf[column].min():.2f}")
    print(f"   Max: {gdf[column].max():.2f}")
    print(f"   Promedio: {gdf[column].mean():.2f}")

    # Transformar a WGS84 para folium
    gdf_wgs84 = gdf.to_crs(epsg=4326)
    
    # Centro de Panamá (bien centrado)
    center_lat = 8.9824
    center_lon = -79.5199

    # Crear mapa base
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=7,
        tiles="CartoDB positron",
        prefer_canvas=True,
    )
    
    # Ajustar zoom a los bounds de los datos (zoom automático)
    bounds = gdf_wgs84.geometry.total_bounds  # [minx, miny, maxx, maxy]
    m.fit_bounds([[bounds[1], bounds[0]], [bounds[3], bounds[2]]])

    # Normalizar colores
    vmin = color_config["vmin"]
    vmax = color_config["vmax"] or gdf[column].max()

    # Función para obtener color
    def get_feature_color(value):
        if pd.isna(value):
            return "#888888"
        
        # Evitar división por cero
        if vmax == vmin:
            normalized = 0.5
        else:
            normalized = (value - vmin) / (vmax - vmin)
        
        normalized = max(0, min(1, normalized))  # Clamp 0-1

        # Mapeo de colores RGB
        if color_config["colormap"] == "RdYlGn":
            # Rojo → Amarillo → Verde
            if normalized < 0.5:
                # Rojo a Amarillo
                r = 255
                g = int(normalized * 2 * 255)
                b = 0
            else:
                # Amarillo a Verde
                r = int((1 - normalized) * 2 * 255)
                g = 255
                b = 0
            
        elif color_config["colormap"] == "YlOrRd":
            # Amarillo → Naranja → Rojo
            if normalized < 0.33:
                r = 255
                g = int(255 - normalized / 0.33 * 100)
                b = 0
            elif normalized < 0.67:
                r = 255
                g = int(155 - (normalized - 0.33) / 0.33 * 155)
                b = 0
            else:
                r = 255
                g = int((1 - normalized) / 0.33 * 100)
                b = 0
            
        elif color_config["colormap"] == "Reds":
            # Blanco a Rojo
            r = int(100 + normalized * 155)  # 100-255
            g = int(100 - normalized * 100)  # 100-0
            b = int(100 - normalized * 100)  # 100-0
            
        elif color_config["colormap"] == "Blues":
            # Blanco a Azul
            r = int(100 - normalized * 100)  # 100-0
            g = int(100 - normalized * 100)  # 100-0
            b = int(100 + normalized * 155)  # 100-255
        else:
            r = int(200 * normalized)
            g = int(200 * normalized)
            b = int(200 * normalized)
        
        return f"#{int(r):02x}{int(g):02x}{int(b):02x}"

    # Agregar features GeoJSON al mapa (usando WGS84)
    for idx, row in gdf_wgs84.iterrows():
        # Obtener el valor del GeoDataFrame original (mismo índice)
        value = gdf.loc[idx, column]
        color = get_feature_color(value)
        formatted_value = color_config["tooltip_format"].format(value)

        # Usar nombre de corregimiento (compatibilidad con GeoParquet y shapefile)
        corr_name = row.get('corregimiento_nombre') or row.get('corregimiento', 'N/A')
        dist_name = row.get('distrito_nombre') or row.get('distrito', 'N/A')
        prov_name = row.get('provincia_nombre') or row.get('provincia', 'N/A')

        # Crear popup con información
        popup_html = f"""
        <div style="font-family: Arial; font-size: 12px; width: 200px;">
            <b>{corr_name}</b><br>
            {dist_name}, {prov_name}<br>
            <hr style="margin: 5px 0;">
            <b>{color_config['name']}:</b> {formatted_value}<br>
            <b>Pobres totales:</b> {row['pobres_total']:,.0f}<br>
            <b>Beneficiarios:</b> {row['beneficiarios_total']:,.0f}<br>
            <b>Gap:</b> {row['gap']:,.0f}<br>
        </div>
        """

        # Crear GeoJSON feature desde geometría WGS84
        feature = {
            "type": "Feature",
            "geometry": row.geometry.__geo_interface__,
            "properties": {"name": corr_name}
        }

        folium.GeoJson(
            data=feature,
            style_function=lambda x, color=color: {
                "fillColor": color, 
                "color": "#333333",
                "weight": 0.5,
                "opacity": 0.7,
                "fillOpacity": 0.8
            },
            popup=folium.Popup(popup_html, max_width=250),
            tooltip=folium.Tooltip(
                f"{corr_name}: {formatted_value}", sticky=False
            ),
        ).add_to(m)

    # Agregar escala de colores (leyenda aproximada)
    legend_html = f"""
    <div style="position: fixed; 
            bottom: 50px; right: 50px; width: 250px; height: auto; 
            background-color: white; border:2px solid grey; z-index:9999; 
            font-size:12px; padding: 10px; border-radius: 5px;">
        <p style="margin: 0 0 10px 0; font-weight: bold;">{color_config['name']}</p>
        <div style="display: flex; align-items: center; margin: 5px 0;">
            <div style="width: 20px; height: 20px; background-color: #00cc00; margin-right: 5px;"></div>
            <span>Alto (>{vmax * 0.75:.0f})</span>
        </div>
        <div style="display: flex; align-items: center; margin: 5px 0;">
            <div style="width: 20px; height: 20px; background-color: #ffff00; margin-right: 5px;"></div>
            <span>Medio ({vmax * 0.5:.0f} - {vmax * 0.75:.0f})</span>
        </div>
        <div style="display: flex; align-items: center; margin: 5px 0;">
            <div style="width: 20px; height: 20px; background-color: #ff0000; margin-right: 5px;"></div>
            <span>Bajo ({vmin:.0f} - {vmax * 0.5:.0f})</span>
        </div>
        <p style="margin: 10px 0 0 0; font-size: 10px; color: #666;">
            Datos: Censo 2023<br>
            Actualizado: Feb 2026
        </p>
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))

    # Guardar
    m.save(output_file)
    print(f"✓ Mapa guardado: {output_file}")

    return output_file


def main():
    parser = argparse.ArgumentParser(
        description="Genera mapas interactivos de cobertura vs pobreza"
    )
    parser.add_argument(
        "--metric",
        default="cobertura",
        choices=["cobertura", "gap", "pobreza_general", "pobreza_extrema"],
        help="Métrica a visualizar",
    )
    parser.add_argument(
        "--output", default="mapa_cobertura.html", help="Archivo de salida HTML"
    )
    parser.add_argument(
        "--show", action="store_true", help="Abrir en navegador después de crear"
    )

    args = parser.parse_args()

    try:
        # Cargar datos
        gdf = load_data()

        # Crear choropleth
        output_file = create_choropleth(gdf, metric=args.metric, output_file=args.output)

        if args.show:
            print(f"\n🌐 Abriendo en navegador...")
            webbrowser.open(f"file://{os.path.abspath(output_file)}")

    except Exception as e:
        print(f"❌ Error: {e}")
        raise


if __name__ == "__main__":
    main()
