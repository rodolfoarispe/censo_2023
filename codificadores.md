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
| `Cedula` | VARCHAR | Cédula del beneficiario |
| `Nombre` | VARCHAR | Nombre completo |
| `Programa` | VARCHAR | Nombre del programa social |
| `Sexo` | VARCHAR | Género (Hombre/Mujer) |
| `id_correg` | BIGINT | ID geográfico compuesto del corregimiento |
| `Fecha_Nacimiento` | DATE | Fecha de nacimiento del beneficiario |
| `Fecha_Ultima_FUPS` | TIMESTAMP | Fecha de última actualización FUPS |
| `Elegibilidad` | VARCHAR | Estado de elegibilidad (ver interpretación abajo) |
| `Fecha_Elegibilidad` | TIMESTAMP | Fecha de determinación de elegibilidad |
| `Menores_18` | BIGINT | Cantidad de menores de 18 años en el hogar |

### Interpretación de Elegibilidad

| Valor en BD | Interpretación | Descripción |
|-------------|----------------|-------------|
| `ELEGIBLE` | ELEGIBLE | Cumple criterios del PMT |
| `NO ELEGIBLE` | NO ELEGIBLE | No cumple criterios del PMT |
| `NULL` + `Fecha_Ultima_FUPS IS NULL` | SIN FUPS | Sin encuesta FUPS realizada |
| `NULL` + `Fecha_Ultima_FUPS IS NOT NULL` | SIN PMT | Con FUPS pero sin cálculo de Proxy Means Test |

```sql
-- Query para interpretar elegibilidad
SELECT
    CASE
        WHEN Elegibilidad IS NOT NULL THEN Elegibilidad
        WHEN Fecha_Ultima_FUPS IS NULL THEN 'SIN FUPS'
        ELSE 'SIN PMT'
    END as elegibilidad_interpretada
FROM planilla;
```

### Programas disponibles

- **B/. 120 A LOS 65**: Pensión para adultos mayores
- **RED DE OPORTUNIDADES**: Transferencias condicionadas
- **ANGEL GUARDIAN**: Apoyo a personas con discapacidad
- **SENAPAN**: Seguridad alimentaria

### Enlace geográfico planilla ↔ mapa_pobreza

El campo `id_correg` es un código compuesto:
```
id_correg = codigo_provincia * 10000 + codigo_distrito * 100 + codigo_corregimiento
```

Ejemplo: Corregimiento 80105 = Provincia 8, Distrito 1, Corregimiento 5

```sql
-- Unir planilla con mapa de pobreza
SELECT
    m.provincia, m.distrito, m.corregimiento,
    COUNT(*) as beneficiarios
FROM planilla p
JOIN mapa_pobreza m
    ON p.id_correg = (m.codigo_provincia * 10000 + m.codigo_distrito * 100 + m.codigo_corregimiento)
GROUP BY m.provincia, m.distrito, m.corregimiento;
```

### Ejemplo: Beneficiarios por género y programa

```sql
SELECT
    Programa,
    Sexo,
    COUNT(*) as cantidad,
    SUM(Menores_18) as menores_asociados
FROM planilla
GROUP BY Programa, Sexo
ORDER BY Programa, Sexo;
```

### Ejemplo: Análisis de elegibilidad

```sql
SELECT
    Programa,
    Elegibilidad,
    COUNT(*) as cantidad
FROM planilla
GROUP BY Programa, Elegibilidad
ORDER BY Programa, cantidad DESC;
```
