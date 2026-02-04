-- ANÁLISIS DE BRECHA: POBREZA vs COBERTURA DE PROGRAMAS SOCIALES
-- Compara necesidad (pobreza) con atención (beneficiarios) por corregimiento

WITH cobertura_por_correg AS (
    -- Calcular beneficiarios por corregimiento y programa
    SELECT
        p.id_correg,
        COUNT(*) as total_beneficiarios,
        COUNT(CASE WHEN p.Programa = 'B/. 120 A LOS 65' THEN 1 END) as ben_120_65,
        COUNT(CASE WHEN p.Programa = 'RED DE OPORTUNIDADES' THEN 1 END) as ben_red_oport,
        COUNT(CASE WHEN p.Programa = 'ANGEL GUARDIAN' THEN 1 END) as ben_angel_guardian,
        COUNT(CASE WHEN p.Programa = 'SENAPAN' THEN 1 END) as ben_senapan,
        COUNT(CASE WHEN p.Sexo = 'Mujer' THEN 1 END) as ben_femenino,
        COUNT(CASE WHEN p.Sexo = 'Hombre' THEN 1 END) as ben_masculino,
        SUM(COALESCE(p.Menores_18, 0)) as total_menores_18,
        -- Elegibilidad interpretada: NULL + sin FUPS = SIN FUPS, NULL + con FUPS = SIN PMT
        COUNT(CASE WHEN p.Elegibilidad = 'ELEGIBLE' THEN 1 END) as elegibles,
        COUNT(CASE WHEN p.Elegibilidad = 'NO ELEGIBLE' THEN 1 END) as no_elegibles,
        COUNT(CASE WHEN p.Elegibilidad IS NULL AND p.Fecha_Ultima_FUPS IS NULL THEN 1 END) as sin_fups,
        COUNT(CASE WHEN p.Elegibilidad IS NULL AND p.Fecha_Ultima_FUPS IS NOT NULL THEN 1 END) as sin_pmt
    FROM planilla p
    GROUP BY p.id_correg
),
id_correg_mapa AS (
    -- Crear ID compuesto para enlace con planilla
    SELECT 
        *,
        (codigo_provincia * 10000 + codigo_distrito * 100 + codigo_corregimiento) as Id_Correg_Calc
    FROM mapa_pobreza
    WHERE total_personas > 0
),
analisis_brecha AS (
    SELECT 
        m.provincia,
        m.distrito,
        m.corregimiento,
        m.total_personas,
        
        -- Indicadores de pobreza
        ROUND(m.pct_pobreza_general_personas * 100, 1) as pobreza_general_pct,
        ROUND(m.pct_pobreza_extrema_personas * 100, 1) as pobreza_extrema_pct,
        ROUND(m.total_personas * m.pct_pobreza_general_personas) as personas_pobreza_general,
        ROUND(m.total_personas * m.pct_pobreza_extrema_personas) as personas_pobreza_extrema,
        
        -- Beneficiarios por programa
        COALESCE(c.total_beneficiarios, 0) as total_beneficiarios,
        COALESCE(c.ben_120_65, 0) as ben_120_65,
        COALESCE(c.ben_red_oport, 0) as ben_red_oport,
        COALESCE(c.ben_angel_guardian, 0) as ben_angel_guardian,
        COALESCE(c.ben_senapan, 0) as ben_senapan,
        
        -- Métricas de cobertura (% de personas en pobreza que reciben ayuda)
        ROUND(
            COALESCE(c.total_beneficiarios, 0) * 100.0 / 
            NULLIF(m.total_personas * m.pct_pobreza_general_personas, 0), 2
        ) as cobertura_pobreza_general_pct,
        ROUND(
            COALESCE(c.total_beneficiarios, 0) * 100.0 / 
            NULLIF(m.total_personas * m.pct_pobreza_extrema_personas, 0), 2
        ) as cobertura_pobreza_extrema_pct,
        
        -- Gap de atención (personas en pobreza sin cobertura)
        ROUND(m.total_personas * m.pct_pobreza_general_personas - COALESCE(c.total_beneficiarios, 0)) as gap_pobreza_general,
        ROUND(m.total_personas * m.pct_pobreza_extrema_personas - COALESCE(c.total_beneficiarios, 0)) as gap_pobreza_extrema,
        
        -- Clasificación de brecha
        CASE 
            WHEN m.pct_pobreza_general_personas >= 0.5 AND COALESCE(c.total_beneficiarios, 0) = 0 
                THEN 'CRÍTICO: Alta pobreza, sin cobertura'
            WHEN m.pct_pobreza_general_personas >= 0.3 AND 
                 COALESCE(c.total_beneficiarios, 0) * 100.0 / NULLIF(m.total_personas * m.pct_pobreza_general_personas, 0) < 10
                THEN 'ALTO: Pobreza moderada-alta, baja cobertura'
            WHEN m.pct_pobreza_general_personas >= 0.2 AND 
                 COALESCE(c.total_beneficiarios, 0) * 100.0 / NULLIF(m.total_personas * m.pct_pobreza_general_personas, 0) < 25
                THEN 'MEDIO: Necesita atención'
            ELSE 'BAJO: Cobertura aceptable'
        END as nivel_brecha
        
    FROM id_correg_mapa m
    LEFT JOIN cobertura_por_correg c ON m.Id_Correg_Calc = c.id_correg
)
SELECT * FROM analisis_brecha
ORDER BY gap_pobreza_general DESC;
