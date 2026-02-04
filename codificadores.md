# Codificadores Geográficos - Censo 2023

## Estructura de códigos

Los datos del censo utilizan códigos geográficos jerárquicos:

```
PROVINCIA (2 dígitos) → DISTRITO (2 dígitos) → CORREGIMIENTO (2 dígitos)
```

## Tablas principales

| Tabla | Descripción | Registros |
|-------|-------------|-----------|
| `personas` | Datos individuales del censo | 4,064,780 |
| `hogares` | Datos por hogar | 1,230,757 |
| `viviendas` | Datos por vivienda | 1,595,492 |
| `mapa_pobreza` | Índices de pobreza por corregimiento | 703 |

## Campos de enlace

### Tablas del censo (personas, hogares, viviendas)

| Campo | Tipo | Ejemplo | Descripción |
|-------|------|---------|-------------|
| `PROVINCIA` | VARCHAR | '08' | Código provincia (con cero) |
| `DISTRITO` | VARCHAR | '01' | Código distrito (con cero) |
| `CORREG` | VARCHAR | '05' | Código corregimiento (con cero) |
| `LLAVEVIV` | VARCHAR | | Llave única de vivienda |
| `HOGAR` | VARCHAR | | Identificador de hogar |

### Tabla mapa_pobreza

| Campo | Tipo | Ejemplo | Descripción |
|-------|------|---------|-------------|
| `codigo_provincia` | INT | 8 | Código provincia (sin cero) |
| `codigo_distrito` | INT | 1 | Código distrito (sin cero) |
| `codigo_corregimiento` | INT | 5 | Código corregimiento (sin cero) |
| `provincia` | VARCHAR | 'Panamá' | Nombre de la provincia |
| `distrito` | VARCHAR | 'Panamá' | Nombre del distrito |
| `corregimiento` | VARCHAR | 'Bella Vista' | Nombre del corregimiento |

## Conversión para JOINs

Los códigos del censo son VARCHAR con ceros iniciales, mientras que mapa_pobreza usa INT.

```sql
-- DuckDB: Convertir para unir censo con mapa de pobreza
SELECT *
FROM personas p
JOIN mapa_pobreza m
  ON CAST(p.PROVINCIA AS INT) = m.codigo_provincia
  AND CAST(p.DISTRITO AS INT) = m.codigo_distrito
  AND CAST(p.CORREG AS INT) = m.codigo_corregimiento
```

## Catálogos auxiliares

| Tabla | Descripción |
|-------|-------------|
| `cat_lugares` | Lugares poblados (13,906 registros) |
| `cat_barrios` | Barrios urbanos (3,743 registros) |
| `cat_actividad` | Actividades económicas (657 registros) |
| `cat_distritos` | Distritos y corregimientos (13 registros) |

## Ejemplos de consultas

### Población por provincia
```sql
SELECT PROVINCIA, COUNT(*) as poblacion
FROM personas
GROUP BY PROVINCIA
ORDER BY poblacion DESC
```

### Análisis combinado: demografía + pobreza
```sql
SELECT
    m.provincia,
    m.distrito,
    m.corregimiento,
    COUNT(p.NPERSONA) as poblacion_censo,
    m.pct_pobreza_general_personas,
    m.pct_pobreza_extrema_personas
FROM mapa_pobreza m
LEFT JOIN personas p
    ON CAST(p.PROVINCIA AS INT) = m.codigo_provincia
    AND CAST(p.DISTRITO AS INT) = m.codigo_distrito
    AND CAST(p.CORREG AS INT) = m.codigo_corregimiento
GROUP BY m.provincia, m.distrito, m.corregimiento,
         m.pct_pobreza_general_personas, m.pct_pobreza_extrema_personas
ORDER BY m.pct_pobreza_general_personas DESC
LIMIT 10
```

### Estructura de edades por área
```sql
SELECT
    CASE AREA WHEN '1' THEN 'Urbana' ELSE 'Rural' END as area,
    CASE
        WHEN P03_EDAD < 18 THEN 'Menor'
        WHEN P03_EDAD < 65 THEN 'Adulto'
        ELSE 'Adulto mayor'
    END as grupo_edad,
    COUNT(*) as cantidad
FROM personas
GROUP BY 1, 2
ORDER BY 1, 2
```

## Tabla planilla

| Tabla | Descripción | Registros |
|-------|-------------|-----------|
| `planilla` | Beneficiarios de programas sociales | 186,225 |

### Campos de la tabla planilla

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `IdEntrada` | BIGINT | ID único de registro |
| `Cedula` | VARCHAR | Cédula del beneficiario |
| `Nombre` | VARCHAR | Nombre completo |
| `Provincia` | VARCHAR | Nombre de la provincia |
| `Distrito` | VARCHAR | Nombre del distrito |
| `Corregimiento` | VARCHAR | Nombre del corregimiento |
| `Id_Correg` | BIGINT | ID geográfico del corregimiento |
| `Programa` | VARCHAR | Nombre del programa social |
| `Sede` | VARCHAR | Sede del programa |

### Programas disponibles

- **B/. 120 A LOS 65**: 116,495 beneficiarios
- **RED DE OPORTUNIDADES**: 42,591 beneficiarios
- **ANGEL GUARDIAN**: 19,851 beneficiarios
- **SENAPAN**: 7,288 beneficiarios

### Ejemplo: Unir planilla con datos del censo

```sql
-- Beneficiarios de programas por género
SELECT 
    p.PROGRAMA as programa,
    CASE WHEN c.P02_SEXO = '1' THEN 'Masculino' ELSE 'Femenino' END as genero,
    COUNT(*) as cantidad
FROM planilla p
LEFT JOIN personas c 
    ON p.Cedula = c.CEDULA
GROUP BY p.PROGRAMA, c.P02_SEXO
ORDER BY p.PROGRAMA, genero;
```

### Ejemplo: Cobertura geográfica de beneficiarios

```sql
SELECT 
    p.Provincia,
    p.Distrito,
    COUNT(*) as beneficiarios,
    COUNT(DISTINCT p.Cedula) as personas_unicas
FROM planilla p
GROUP BY p.Provincia, p.Distrito
ORDER BY beneficiarios DESC;
```
