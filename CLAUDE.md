# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Environment Setup

**IMPORTANT**: Always activate the virtual environment before running any Python script:

```bash
source ~/vEnv/pandas/bin/activate
```

## Primary Tool: pysql.py

`pysql.py` is the main utility for all SQL operations. Use it for queries, data exploration, and exports.

```bash
# Basic query (table format)
python pysql.py --duckdb censo_2023.duckdb -Q "SELECT * FROM personas LIMIT 5"

# Export to CSV
python pysql.py --duckdb censo_2023.duckdb -Q "SELECT * FROM mapa_pobreza" -o csv

# Export to Excel
python pysql.py --duckdb censo_2023.duckdb -Q "SELECT * FROM planilla" -o excel

# Run SQL file
python pysql.py --duckdb censo_2023.duckdb -i query.sql -o json

# MSSQL connection (SQL Auth)
python pysql.py -S servidor -U usuario -p password -d database -Q "SELECT @@VERSION"

# MSSQL connection (Windows Auth)
python pysql.py -S servidor -T -d database -Q "SELECT * FROM tabla"
```

Output formats: `table` (default), `csv`, `json`, `excel`

## Project Overview

Analytics toolkit for Panama's 2023 Census data, focused on analyzing the gap between poverty population and social program coverage at the corregimiento (district subdivision) level. Uses DuckDB as the analytical database.

## Key Commands

```bash
# Install dependencies
pip install duckdb pandas openpyxl pyreadstat tabulate

# Create the DuckDB database from census .sav files
python crear_db.py --mapa-pobreza <poverty_map.xlsx>

# Generate gap analysis Excel report
python generar_excel_simple.py

# Convert SPSS .sav to CSV (for preprocessing)
python convertir_sav.py <archivo.sav>

# Load planilla.csv into existing database
python cargar_planilla.py
```

## Database Schema

Main database: `censo_2023.duckdb`

### Census Tables
| Table | Records | Key Fields |
|-------|---------|------------|
| `personas` | 4M+ | PROVINCIA, DISTRITO, CORREG (VARCHAR with leading zeros), CEDULA |
| `hogares` | 1.2M+ | LLAVEVIV, HOGAR |
| `viviendas` | 1.6M+ | LLAVEVIV |
| `mapa_pobreza` | 703 | codigo_provincia, codigo_distrito, codigo_corregimiento (INT without zeros) |
| `planilla` | 186K | id_correg, Cedula, Programa, Sexo, Elegibilidad, Menores_18 |

### Tabla planilla (estructura actualizada)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `Cedula` | VARCHAR | Cédula del beneficiario |
| `Nombre` | VARCHAR | Nombre completo |
| `Programa` | VARCHAR | Programa social |
| `Sexo` | VARCHAR | Hombre/Mujer |
| `id_correg` | BIGINT | Código geográfico compuesto (minúsculas) |
| `Fecha_Nacimiento` | DATE | Fecha de nacimiento |
| `Fecha_Ultima_FUPS` | TIMESTAMP | Última actualización FUPS |
| `Elegibilidad` | VARCHAR | ELEGIBLE, NO ELEGIBLE, NULL (ver nota) |
| `Fecha_Elegibilidad` | TIMESTAMP | Fecha de elegibilidad |
| `Menores_18` | BIGINT | Menores de 18 en el hogar |

### Interpretación de Elegibilidad

Cuando `Elegibilidad` es NULL:
- Si `Fecha_Ultima_FUPS` es NULL → **SIN FUPS** (sin encuesta)
- Si `Fecha_Ultima_FUPS` existe → **SIN PMT** (sin cálculo Proxy Means Test)

### Geographic Code Conversion

Census tables use VARCHAR with leading zeros (`'08'`), while `mapa_pobreza` uses INT (`8`). For JOINs:

```sql
-- Census to mapa_pobreza
CAST(p.PROVINCIA AS INT) = m.codigo_provincia

-- Compound code for planilla (nota: id_correg en minúsculas)
codigo_provincia * 10000 + codigo_distrito * 100 + codigo_corregimiento = id_correg
```

### Social Programs in planilla
- B/. 120 A LOS 65 (pensión adultos mayores)
- RED DE OPORTUNIDADES (transferencias condicionadas)
- ANGEL GUARDIAN (personas con discapacidad)
- SENAPAN (seguridad alimentaria)

## Architecture

- **crear_db.py**: Extracts split ZIP files containing .sav census data, loads into DuckDB with optional poverty map
- **generar_excel_simple.py**: Main analysis script producing Excel with gap metrics (coverage vs poverty)
- **pysql.py**: Multi-database SQL client supporting DuckDB and MSSQL with table/csv/json/excel output
- **cargar_planilla.py**: Standalone loader for beneficiary data
- **convertir_sav.py**: SPSS to CSV converter using chunked reading for large files

## Output

`generar_excel_simple.py` produces `analisis_brecha_pobreza_YYYYMMDD_HHMM.xlsx` with sheets:
- Top 50 Brechas (largest absolute gaps)
- Casos Criticos (high poverty + low coverage)
- Por Provincia (provincial statistics)
- Sobreatencion (over-coverage cases)
- Analisis Completo (all corregimientos)
- Resumen Ejecutivo (national summary)
