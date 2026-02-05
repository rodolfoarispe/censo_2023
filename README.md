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

Instalacion rapida:

```bash
pip install duckdb pandas openpyxl
```

## Datos necesarios

- `censo_2023.duckdb` (base de datos DuckDB con tablas del censo)
- `planilla` debe existir dentro de la base de datos

## Generar Excel de analisis

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

## Notas

- El enlace geografico se hace con el codigo compuesto:
  `provincia * 10000 + distrito * 100 + corregimiento`.
- La tabla `mapa_pobreza` se usa como referencia para pobreza.
- En elegibilidad, un registro con `NO ELEGIBLE` puede tener informe social que lo
  declare elegible (no elegible por Proxy, elegible por informe).
