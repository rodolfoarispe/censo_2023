# Análisis de Brecha: Pobreza vs Cobertura de Programas Sociales

## Resumen Ejecutivo

Este análisis evalúa la **brecha entre necesidad y atención** a nivel de corregimiento en Panamá, comparando los niveles de pobreza (mapa_pobreza) con la cobertura de programas sociales (planilla de beneficiarios).

### Datos Analizados
- **703 corregimientos** con datos de pobreza
- **186,225 beneficiarios** de programas sociales
- **4 programas principales**: B/. 120 A LOS 65, Red de Oportunidades, Ángel Guardian, SENAPAN

## Principales Hallazgos

### 1. Corregimientos con Mayores Brechas de Atención

Los **15 corregimientos con mayor gap** entre personas en pobreza y beneficiarios atendidos:

| Provincia | Distrito | Corregimiento | Población | Pobreza % | Personas en Pobreza | Beneficiarios | Gap de Atención |
|-----------|----------|---------------|-----------|-----------|-------------------|---------------|-----------------|
| Panamá | PANAMÁ | LAS GARZAS | 43,558 | 38.1% | 16,574 | 529 | **16,045** |
| Panamá | PANAMÁ | 24 DE DICIEMBRE (P) | 79,406 | 20.6% | 16,389 | 1,577 | **14,812** |
| Panamá | PANAMÁ | TOCUMEN (P) | 89,155 | 16.2% | 14,443 | 1,746 | **12,697** |
| Panamá | PANAMÁ | CHILIBRE | 49,299 | 27.2% | 13,419 | 1,496 | **11,923** |
| Panamá | PANAMÁ | ERNESTO CÓRDOBA CAMPOS | 71,340 | 17.6% | 12,570 | 836 | **11,734** |

### 2. Casos Críticos: Alta Pobreza + Baja Cobertura

**15 corregimientos con pobreza ≥50% y cobertura <20%** (situación más crítica):

| Provincia | Distrito | Corregimiento | Pobreza % | Personas en Pobreza | Beneficiarios | Cobertura % |
|-----------|----------|---------------|-----------|-------------------|---------------|-------------|
| Comarca Ngäbe Buglé | MÜNA | KRÜA | **98.1%** | 2,846 | 406 | 14.3% |
| Comarca Ngäbe Buglé | MÜNA | PEÑA BLANCA | **97.6%** | 3,477 | 637 | 18.3% |
| Comarca Ngäbe Buglé | MÜNA | DIKO | **97.1%** | 2,520 | 289 | 11.5% |
| Comarca Ngäbe Buglé | MIRONÓ | HATO JOBO | **96.9%** | 2,253 | 338 | 15.0% |
| Comarca Ngäbe Buglé | BESIKO | NIBA | **96.8%** | 3,718 | 422 | 11.3% |

⚠️ **Patrón crítico**: La Comarca Ngäbe Buglé domina completamente esta lista con niveles de pobreza extremos (>90%) pero cobertura insuficiente.

### 3. Cobertura por Programa Social

| Programa | Corregimientos Atendidos | Total Beneficiarios | Provincias Cubiertas |
|----------|------------------------|-------------------|-------------------|
| **B/. 120 A LOS 65** | 696 | 116,495 | 13 |
| **RED DE OPORTUNIDADES** | 659 | 42,591 | 13 |
| **ANGEL GUARDIAN** | 675 | 19,851 | 13 |
| **SENAPAN** | 263 | 7,288 | 12 |

## Recomendaciones Prioritarias

### 🚨 Urgente - Comarca Ngäbe Buglé
- **Problema**: Pobreza extrema (90-98%) con cobertura insuficiente (<20%)
- **Acción**: Expansión inmediata de Red de Oportunidades y programas alimentarios
- **Meta**: Alcanzar al menos 50% de cobertura en corregimientos con >90% pobreza

### 🔴 Alta Prioridad - Área Metropolitana
- **Problema**: Grandes volúmenes absolutos sin atender (LAS GARZAS: 16K personas)
- **Acción**: Focalización urbana de B/. 120 A LOS 65 y Ángel Guardian
- **Meta**: Reducir gaps >10,000 personas en corregimientos urbanos

### 🟡 Media Prioridad - Expansión de SENAPAN
- **Problema**: Solo cubre 263 corregimientos (menos del 40% del total)
- **Acción**: Expandir cobertura geográfica, especialmente en provincias centrales

## Metodología

```sql
-- Query principal para calcular brechas
WITH cobertura_por_correg AS (
    SELECT 
        Id_Correg,
        COUNT(*) as total_beneficiarios,
        COUNT(CASE WHEN Programa = 'B/. 120 A LOS 65' THEN 1 END) as ben_120_65,
        -- ... otros programas
    FROM planilla 
    GROUP BY Id_Correg
),
gap_analysis AS (
    SELECT 
        m.provincia, m.distrito, m.corregimiento,
        m.total_personas * m.pct_pobreza_general_personas as personas_pobreza,
        COALESCE(c.total_beneficiarios, 0) as beneficiarios,
        (personas_pobreza - beneficiarios) as gap_atencion
    FROM mapa_pobreza m
    LEFT JOIN cobertura_por_correg c ON [enlace por ID geográfico]
)
```

## Archivos Generados

- `analisis_brecha_pobreza.sql` - Query completo para replicar análisis
- `reporte_brecha_pobreza.md` - Este reporte
- `cargar_planilla.py` - Script para cargar datos CSV a DuckDB

---
*Análisis generado el {{ fecha }} utilizando datos del Censo 2023 y planilla de beneficiarios de programas sociales*