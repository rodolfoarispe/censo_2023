# Censo 2023 - Analisis de brecha

Este repositorio contiene herramientas para analizar la brecha entre
poblacion en pobreza y cobertura de programas sociales a nivel de
corregimiento usando DuckDB.

## Requisitos

- Python 3.9+
- Dependencias:
  - duckdb
  - pandas
  - openpyxl
  - geopandas
  - folium

Instalacion rapida:

```bash
pip install duckdb pandas openpyxl geopandas folium
```

Nota: Asegúrate de activar el venv antes de ejecutar:

```bash
source ~/vEnv/pandas/bin/activate
```

## Datos necesarios

- `censo_2023.duckdb` (base de datos DuckDB con tablas del censo)
- `planilla` debe existir dentro de la base de datos

## Generar reportes

### Excel de análisis

El script principal es:

```bash
python generar_excel_simple.py
```

Salida:

- Un archivo `analisis_brecha_pobreza_YYYYMMDD_HHMM.xlsx`
- Hojas incluidas:
  - Top 50 Brechas
  - Casos Criticos
  - Por Provincia
  - Sobreatencion
  - Analisis Completo
  - Resumen Ejecutivo

### Mapas interactivos (Choropleth)

Visualiza cobertura vs pobreza en mapas geográficos interactivos:

```bash
# Un solo mapa específico
python choropleth_cobertura.py --metric cobertura --output mapa_cobertura.html

# Todas las métricas disponibles
python generar_mapas.py --output-dir ./mapas

# Mostrar directamente en navegador
python choropleth_cobertura.py --metric gap --show
```

**Métricas disponibles:**
- `cobertura`: % de beneficiarios vs pobres (🟢 rojo bajo → verde alto)
- `gap`: Personas sin cobertura (🔴 amarillo bajo → rojo alto)
- `pobreza_general`: % de pobreza general (🔵 azul)
- `pobreza_extrema`: % de pobreza extrema (⚫ rojo oscuro)

**Archivos generados:**
- `mapa_cobertura_YYYYMMDD_HHMM.html` (~97 MB cada uno)
- Mapas interactivos con tooltip de información

**Datos geográficos:**
- Fuente shapefile: `/home/rodolfoarispe/Descargas/Panama_Corregimientos_Boundaries_2024/`
- Documentación: `data/geo/README.md`
- 693 corregimientos mapeados (de 699 en la BD)

## Notas

- El enlace geografico se hace con el codigo compuesto:
  `provincia * 10000 + distrito * 100 + corregimiento`.
- La tabla `mapa_pobreza` se usa como referencia para pobreza.
- En elegibilidad, un registro con `NO ELEGIBLE` puede tener informe social que lo
  declare elegible (no elegible por Proxy, elegible por informe).
