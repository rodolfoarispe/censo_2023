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


def load_detailed_beneficiaries():
    """Carga datos desglosados de beneficiarios por programa y menores de 18"""
    conn = duckdb.connect(DB_PATH)
    
    # Query: beneficiarios por programa y menores de 18 de la planilla por corregimiento
    detailed_data = conn.execute("""
        SELECT 
            id_correg,
            COALESCE(SUM(CASE WHEN Programa = 'ANGEL GUARDIAN' THEN 1 ELSE 0 END), 0) as benef_angel_guardian,
            COALESCE(SUM(CASE WHEN Programa = 'B/. 120 A LOS 65' THEN 1 ELSE 0 END), 0) as benef_120_65,
            COALESCE(SUM(CASE WHEN Programa = 'RED DE OPORTUNIDADES' THEN 1 ELSE 0 END), 0) as benef_red_oportunidades,
            COALESCE(SUM(CASE WHEN Programa = 'SENAPAN' THEN 1 ELSE 0 END), 0) as benef_senapan,
            COALESCE(SUM(Menores_18), 0) as menores_18_beneficiarios
        FROM planilla
        GROUP BY id_correg
    """).df()
    
    conn.close()
    return detailed_data


def load_census_minors():
    """Carga cantidad de menores de 18 del censo por corregimiento"""
    conn = duckdb.connect(DB_PATH)
    
    # Query: menores de 18 años del censo por corregimiento
    census_minors = conn.execute("""
        SELECT 
            CONCAT(
                LPAD(PROVINCIA, 2, '0'),
                LPAD(DISTRITO, 2, '0'),
                LPAD(CORREG, 2, '0')
            )::BIGINT as id_correg,
            COUNT(*) as menores_18_censo
        FROM personas
        WHERE CAST(P03_EDAD AS INTEGER) < 18 AND P03_EDAD IS NOT NULL
        GROUP BY PROVINCIA, DISTRITO, CORREG
    """).df()
    
    conn.close()
    return census_minors


def load_data():
    """Carga datos geográficos desde GeoParquet (o shapefile si no existe)"""
    import os

    # Intentar cargar GeoParquet primero (más eficiente)
    if os.path.exists(GEOPARQUET_PATH):
        print(f"📥 Cargando {GEOPARQUET_PATH}...")
        gdf = gpd.read_parquet(GEOPARQUET_PATH)
        print(f"   ✓ {len(gdf)} corregimientos cargados")
        
        # Enriquecer con datos desglosados de beneficiarios
        print(f"📥 Cargando datos desglosados por programa...")
        detailed_benef = load_detailed_beneficiaries()
        gdf = gdf.merge(detailed_benef, left_on='id_corr_int', right_on='id_correg', how='left')
        
        # Enriquecer con menores de 18 del censo
        print(f"📥 Cargando menores de 18 del censo...")
        census_minors = load_census_minors()
        gdf = gdf.merge(census_minors, left_on='id_corr_int', right_on='id_correg', how='left')
        
        # Llenar NaN con 0
        for col in ['benef_angel_guardian', 'benef_120_65', 'benef_red_oportunidades', 'benef_senapan', 'menores_18_beneficiarios', 'menores_18_censo']:
            gdf[col] = gdf[col].fillna(0).astype('int64')
        print(f"   ✓ Datos desglosados agregados")
        
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

        # Crear popup con información jerárquica (general a específico)
        # Obtener valores con defaults para compatibilidad
        benef_angel = int(row.get('benef_angel_guardian', 0))
        benef_120_65 = int(row.get('benef_120_65', 0))
        benef_red_oport = int(row.get('benef_red_oportunidades', 0))
        benef_senapan = int(row.get('benef_senapan', 0))
        menores_18_censo = int(row.get('menores_18_censo', 0))
        menores_18_benef = int(row.get('menores_18_beneficiarios', 0))
        
        popup_html = f"""
        <div style="font-family: Arial; font-size: 11px; width: 280px;">
            <!-- UBICACIÓN -->
            <div style="background-color: #f5f5f5; padding: 5px; border-radius: 3px; margin-bottom: 8px;">
                <b style="font-size: 13px;">{corr_name}</b><br>
                <span style="color: #666;">{dist_name}, {prov_name}</span>
            </div>
            
            <!-- CONTEXTO DEMOGRÁFICO (General a Específico) -->
            <div style="margin-bottom: 8px;">
                <b style="color: #333;">Población Total:</b> {row['total_personas']:,.0f}<br>
                <b style="color: #d9534f;">Pobres Extremos:</b> {row['pobres_extremos']:,.0f} ({row['pct_pobreza_extrema_personas']:.1f}%)<br>
                <b style="color: #f0ad4e;">Pobres Generales:</b> {row['pobres_general']:,.0f} ({row['pct_pobreza_general_personas']:.1f}%)<br>
                <b style="color: #5bc0de;">Menores de 18 (Censo):</b> {menores_18_censo:,.0f}
            </div>
            
            <hr style="margin: 6px 0; border: none; border-top: 1px solid #ddd;">
            
            <!-- COBERTURA DE PROGRAMAS -->
            <div style="margin-bottom: 8px;">
                <b style="color: #333;">Beneficiarios Totales:</b> {row['beneficiarios_total']:,.0f}<br>
                <b style="color: #27ae60;">{color_config['name']}:</b> {formatted_value}
            </div>
            
            <!-- DESGLOSE POR PROGRAMA Y MENORES BENEFICIARIOS -->
            <div style="background-color: #fffacd; padding: 5px; border-left: 3px solid #ffc107; margin-bottom: 8px;">
                <b style="font-size: 10px; color: #333;">Beneficiarios por Programa:</b><br>
                <span style="font-size: 10px;">
                    • B/. 120 a los 65: {benef_120_65:,.0f}<br>
                    • Red de Oportunidades: {benef_red_oport:,.0f}<br>
                    • Ángel Guardián: {benef_angel:,.0f}<br>
                    • SENAPAN: {benef_senapan:,.0f}
                </span><br>
                <b style="font-size: 10px; color: #333;">Menores de 18:</b> <span style="font-size: 10px;">{menores_18_benef:,.0f}</span>
            </div>
            
            <!-- GAP DE COBERTURA -->
            <div style="background-color: #ffe6e6; padding: 5px; border-left: 3px solid #dc3545; margin-bottom: 4px;">
                <b style="color: #c82333;">Gap (Sin Cobertura):</b> {row['gap']:,.0f}
            </div>
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

    # Preparar datos para búsqueda (Provincia → Distrito → Corregimiento)
    # IMPORTANTE: Usar gdf_wgs84 para obtener coordenadas correctas (lat/lon)
    provincias_data = {}
    corregimientos_coords = {}  # Guardar coordenadas para búsqueda
    
    for idx, row in gdf_wgs84.iterrows():
        prov_name = row.get('provincia_nombre') or row.get('provincia', 'N/A')
        dist_name = row.get('distrito_nombre') or row.get('distrito', 'N/A')
        corr_name = row.get('corregimiento_nombre') or row.get('corregimiento', 'N/A')
        
        # Calcular centroide EN WGS84 (ya está transformado en gdf_wgs84)
        try:
            centroide = row.geometry.centroid
            lat = centroide.y
            lon = centroide.x
        except:
            lat = center_lat
            lon = center_lon
        
        # Guardar corregimiento con sus coordenadas (WGS84)
        corregimientos_coords[corr_name] = {'lat': lat, 'lon': lon}
        
        if prov_name not in provincias_data:
            provincias_data[prov_name] = {}
        if dist_name not in provincias_data[prov_name]:
            provincias_data[prov_name][dist_name] = []
        if corr_name not in provincias_data[prov_name][dist_name]:
            provincias_data[prov_name][dist_name].append({
                'name': corr_name,
                'lat': lat,
                'lon': lon
            })
    
    # Convertir a JSON para JavaScript
    import json
    provincias_json = json.dumps(provincias_data)
    corregimientos_coords_json = json.dumps(corregimientos_coords)
    
    # Agregar panel de búsqueda en esquina superior izquierda
    search_panel_html = f"""
    <div style="position: fixed; 
            top: 10px; left: 10px; width: 280px; height: auto; 
            background-color: white; border:2px solid #333; z-index:9999; 
            font-size:12px; padding: 12px; border-radius: 5px;
            box-shadow: 0 2px 6px rgba(0,0,0,0.3);">
        
        <p style="margin: 0 0 8px 0; font-weight: bold; font-size: 13px;">🔍 Buscar Corregimiento</p>
        
        <div style="margin-bottom: 8px;">
            <label style="display: block; font-size: 11px; color: #666; margin-bottom: 2px;">Provincia:</label>
            <select id="provincia-select" style="width: 100%; padding: 5px; font-size: 11px; border: 1px solid #ccc; border-radius: 3px;">
                <option value="">-- Seleccionar Provincia --</option>
            </select>
        </div>
        
        <div style="margin-bottom: 8px;">
            <label style="display: block; font-size: 11px; color: #666; margin-bottom: 2px;">Distrito:</label>
            <select id="distrito-select" style="width: 100%; padding: 5px; font-size: 11px; border: 1px solid #ccc; border-radius: 3px;" disabled>
                <option value="">-- Seleccionar Distrito --</option>
            </select>
        </div>
        
        <div style="margin-bottom: 8px;">
            <label style="display: block; font-size: 11px; color: #666; margin-bottom: 2px;">Corregimiento:</label>
            <select id="corregimiento-select" style="width: 100%; padding: 5px; font-size: 11px; border: 1px solid #ccc; border-radius: 3px;" disabled>
                <option value="">-- Seleccionar Corregimiento --</option>
            </select>
        </div>
        
        <button id="zoom-button" style="width: 100%; padding: 6px; background-color: #4CAF50; color: white; border: none; border-radius: 3px; cursor: pointer; font-weight: bold; font-size: 11px;" disabled>
            📍 Ir a Ubicación
        </button>
        
        <p style="margin: 8px 0 0 0; font-size: 9px; color: #999;">
            Selecciona provincia, distrito y corregimiento para navegar
        </p>
    </div>
    """
    m.get_root().html.add_child(folium.Element(search_panel_html))
    
    # Agregar JavaScript para interactividad de búsqueda (CON DEBUG)
    search_script = f"""
    <script>
    console.log('🗺️ Script de búsqueda cargado');
    
    var provinciasData = {provincias_json};
    var corregimientosCoords = {corregimientos_coords_json};
    
    console.log('📍 Corregimientos disponibles:', Object.keys(corregimientosCoords).length);
    
    // Inicializar búsqueda
    function inicializarBusqueda() {{
        console.log('⏱️ Inicializando búsqueda...');
        
        var provinciaSelect = document.getElementById('provincia-select');
        var distritosSelect = document.getElementById('distrito-select');
        var corregimientosSelect = document.getElementById('corregimiento-select');
        var zoomButton = document.getElementById('zoom-button');
        
        if (!provinciaSelect) {{
            console.log('⏳ Panel no encontrado, reintentando...');
            setTimeout(inicializarBusqueda, 100);
            return;
        }}
        
        console.log('✅ Panel de búsqueda encontrado');
        
        // Llenar provincias
        var provincias = Object.keys(provinciasData).sort();
        console.log('🏘️ Provincias cargadas:', provincias);
        
        provincias.forEach(function(provincia) {{
            var option = document.createElement('option');
            option.value = provincia;
            option.text = provincia;
            provinciaSelect.appendChild(option);
        }});
        
        // Cambio de provincia
        provinciaSelect.addEventListener('change', function() {{
            console.log('📍 Provincia seleccionada:', this.value);
            distritosSelect.innerHTML = '<option value="">-- Seleccionar Distrito --</option>';
            corregimientosSelect.innerHTML = '<option value="">-- Seleccionar Corregimiento --</option>';
            corregimientosSelect.disabled = true;
            zoomButton.disabled = true;
            
            if (this.value === '') {{
                distritosSelect.disabled = true;
                return;
            }}
            
            distritosSelect.disabled = false;
            Object.keys(provinciasData[this.value]).sort().forEach(function(distrito) {{
                var option = document.createElement('option');
                option.value = distrito;
                option.text = distrito;
                distritosSelect.appendChild(option);
            }});
        }});
        
        // Cambio de distrito
        distritosSelect.addEventListener('change', function() {{
            console.log('🏢 Distrito seleccionado:', this.value);
            corregimientosSelect.innerHTML = '<option value="">-- Seleccionar Corregimiento --</option>';
            zoomButton.disabled = true;
            
            if (this.value === '') {{
                corregimientosSelect.disabled = true;
                return;
            }}
            
            corregimientosSelect.disabled = false;
            var corregimientos = provinciasData[provinciaSelect.value][this.value];
            corregimientos.forEach(function(correg) {{
                var option = document.createElement('option');
                option.value = correg.name;
                option.text = correg.name;
                corregimientosSelect.appendChild(option);
            }});
        }});
        
        // Cambio de corregimiento
        corregimientosSelect.addEventListener('change', function() {{
            console.log('🏘️ Corregimiento seleccionado:', this.value);
            zoomButton.disabled = (this.value === '');
            console.log('🔘 Botón zoom habilitado:', !zoomButton.disabled);
        }});
        
        // Click en botón: buscar el GeoJSON y hacer zoom
        zoomButton.addEventListener('click', function() {{
            console.log('🔘 ¡Botón clickeado!');
            
            var corregimientoNombre = corregimientosSelect.value;
            console.log('🔍 Buscando corregimiento:', corregimientoNombre);
            
            if (!corregimientoNombre) {{
                console.log('❌ No hay corregimiento seleccionado');
                return;
            }}
            
            var coords = corregimientosCoords[corregimientoNombre];
            console.log('📍 Coordenadas encontradas:', coords);
            
            if (!coords) {{
                console.log('❌ Coordenadas no encontradas para:', corregimientoNombre);
                return;
            }}
            
            console.log('✅ Intentando zoom a:', coords.lat, coords.lon);
            
            // Buscar en Leaflet todos los layers y hacer click
            var layersControl = document.querySelectorAll('.leaflet-interactive');
            console.log('🎯 Layers encontrados:', layersControl.length);
            
            layersControl.forEach(function(layer, index) {{
                var event = new MouseEvent('click', {{
                    bubbles: true,
                    cancelable: true,
                    view: window
                }});
                layer.dispatchEvent(event);
            }});
            
            // Intentar hacer zoom - buscar el mapa en variables globales
            setTimeout(function() {{
                var leafletMap = null;
                
                // Buscar en window todas las variables Leaflet (Folium crea map_<hash>)
                console.log('🔎 Buscando mapa en window...');
                for (var key in window) {{
                    try {{
                        if (window[key] && window[key].setView && typeof window[key].setView === 'function') {{
                            leafletMap = window[key];
                            console.log('🗺️ ¡Mapa encontrado!:', key);
                            break;
                        }}
                    }} catch(e) {{
                        // Ignorar errores de acceso a propiedades
                    }}
                }}
                
                // Alternativa: buscar en div._leaflet_map
                if (!leafletMap) {{
                    var mapDiv = document.querySelector('[id^="map"]');
                    if (mapDiv && mapDiv._leaflet_map) {{
                        leafletMap = mapDiv._leaflet_map;
                        console.log('🗺️ Mapa encontrado en div._leaflet_map');
                    }}
                }}
                
                if (leafletMap && typeof leafletMap.setView === 'function') {{
                    console.log('✅ Zoom ejecutado a:', coords.lat, coords.lon);
                    leafletMap.setView([coords.lat, coords.lon], 10);
                    
                    // Intentar hacer click en el GeoJSON para mostrar popup
                    setTimeout(function() {{
                        var geoJsonLayers = document.querySelectorAll('path[class*="leaflet"]');
                        console.log('📍 Buscando GeoJSON layers para popup:', geoJsonLayers.length);
                        
                        // Buscar el layer que corresponde al corregimiento
                        for (var i = 0; i < geoJsonLayers.length; i++) {{
                            var event = new MouseEvent('click', {{
                                bubbles: true,
                                cancelable: true,
                                view: window
                            }});
                            geoJsonLayers[i].dispatchEvent(event);
                        }}
                    }}, 200);
                }} else {{
                    console.log('❌ No se pudo hacer zoom - mapa no disponible');
                }}
            }}, 300);
        }});
    }}
    
    console.log('⏱️ document.readyState:', document.readyState);
    
    // Inicializar cuando esté listo
    if (document.readyState === 'loading') {{
        document.addEventListener('DOMContentLoaded', inicializarBusqueda);
    }} else {{
        inicializarBusqueda();
    }}
    </script>
    """
    m.get_root().html.add_child(folium.Element(search_script))

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
            Datos: Censo/MDP 2023<br>
            Planilla: 20261
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
