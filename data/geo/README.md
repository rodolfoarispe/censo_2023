# Datos Geográficos de Corregimientos

Este directorio contiene datos y configuración para generar mapas interactivos de cobertura vs pobreza en Panamá.

## Archivos

### `corregimientos.parquet` ⭐
Datos geográficos de corregimientos en formato GeoParquet (35 MB).

**Características:**
- Contiene geometría completa (Polygon + MultiPolygon)
- Datos de cobertura vs pobreza pre-calculados
- Formato eficiente y portable (no necesita shapefile externo)
- Cargado automáticamente por scripts

### `ID_CORR_mapping.json`
Mapeo de discrepancias entre el shapefile de corregimientos y los datos de la BD.

**Estructura:**
```json
{
  "total_shapefile": 699,
  "total_db": 699,
  "coinciden": 693,
  "solo_en_shapefile": [100001, ...],
  "solo_en_bd": [10403, ...],
  "nota": "Los IDs pueden estar obsoletos o sin geometría"
}
```

**Códigos ID**
- Formato: XXXXXX (6 dígitos)
- Estructura: PP DI CC
  - PP: Provincia (01-13)
  - DI: Distrito (01-08 aprox)
  - CC: Corregimiento (01-07 aprox)
- Ejemplo: `010102` = Provincia 01, Distrito 01, Corregimiento 02

## Generar Mapas

Usar el script `choropleth_cobertura.py` desde la raíz del proyecto:

```bash
# Activar venv
source ~/vEnv/pandas/bin/activate

# Mapa de cobertura (%)
python choropleth_cobertura.py --metric cobertura --output mapa_cobertura.html

# Mapa de gap (personas sin cobertura)
python choropleth_cobertura.py --metric gap --output mapa_gap.html

# Mapa de pobreza extrema
python choropleth_cobertura.py --metric pobreza_extrema --output mapa_pobreza_extrema.html

# Mapa de pobreza general
python choropleth_cobertura.py --metric pobreza_general --output mapa_pobreza_general.html

# Mostrar en navegador
python choropleth_cobertura.py --metric cobertura --show

# Generar todos los mapas
python generar_mapas.py --output-dir ./mapas
```

**Nota:** El script usa `data/geo/corregimientos.parquet` automáticamente. ✓ No necesita el shapefile externo.

**Características de los mapas:**
- ✓ Centrado automáticamente en Panamá
- ✓ Zoom automático para ver todo el país completo
- ✓ Colores cromáticos por métrica (RdYlGn, YlOrRd, etc)
- ✓ Tooltips al pasar mouse
- ✓ Popups con información detallada al hacer click
- ✓ Tiles CartoDB positron para mejor legibilidad

## Datos Disponibles

El script carga datos desde:
- **Geometría**: `corregimientos.parquet` (este directorio)
  - Fallback: Shapefile en `/home/rodolfoarispe/Descargas/...` si GeoParquet no existe
- **BD**: `censo_2023.duckdb` (tabla `mapa_pobreza` + `planilla`)

Métricas por corregimiento:
- `cobertura_pct`: % de beneficiarios vs pobres
- `gap`: Número de personas sin cobertura
- `pobres_total`: Total de personas en pobreza
- `pobres_extremos`: Personas en pobreza extrema
- `beneficiarios_total`: Personas con beneficiarios registrados
- `pct_pobreza_general_personas`: % pobreza general
- `pct_pobreza_extrema_personas`: % pobreza extrema

## Próximos Pasos (Optimizaciones)

1. **Simplificación de geometría**: Reducir coordenadas para disminuir tamaño (5-10 MB)
   - Trade-off: precisión vs tamaño
   - Beneficio: Mapas HTML más pequeños (~5-10 MB vs 97 MB)

2. **Tiles personalizados**: Usar tiles de Mapbox o similar para mejor visualización

3. **Filtros interactivos**: Agregar controles para filtrar por provincia, distrito, rango de cobertura

4. **Exportar a TopoJSON**: Reducir tamaño para sitios web estáticos

5. **Dashboard web**: Integrar con Folium Server o Streamlit para análisis interactivo

## Notas Técnicas

- **CRS**: EPSG:32617 (WGS84 UTM Zone 17N)
- **Geometría**: Polygon + MultiPolygon
- **Fuente shapefile**: Panama_Corregimientos_Boundaries_2024
- **Compatibilidad**: 693/699 corregimientos coinciden con datos de censo

## Referencias

- Script: `../../choropleth_cobertura.py`
- BD: `../../censo_2023.duckdb`
- Datos originales: `~/.../Prov-Dist_Corr_2023.xlsx`
