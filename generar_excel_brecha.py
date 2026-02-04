#!/usr/bin/env python3
"""
Generador de Excel con análisis completo de brecha pobreza vs cobertura
"""
import sys
from pathlib import Path
import pandas as pd
import duckdb
from datetime import datetime

def conectar_duckdb(db_path):
    """Conecta a DuckDB"""
    try:
        return duckdb.connect(db_path)
    except Exception as e:
        print(f"❌ Error conectando a DuckDB: {e}")
        sys.exit(1)

def generar_excel_completo(db_path, output_file):
    """Genera Excel con múltiples hojas de análisis"""
    con = conectar_duckdb(db_path)
    
    print("📊 Generando análisis completo de brecha pobreza...")
    
    # 1. RESUMEN EJECUTIVO
    print("  📋 Hoja 1: Resumen Ejecutivo")
    resumen_query = """
    SELECT 
        'Población Total' as Indicador,
        FORMAT('{:,.0f}', SUM(m.total_personas)) as Valor,
        'personas' as Unidad
    FROM (
        SELECT *, (codigo_provincia * 10000 + codigo_distrito * 100 + codigo_corregimiento) as Id_Correg_Calc
        FROM mapa_pobreza WHERE total_personas > 0
    ) m
    UNION ALL
    SELECT 
        'Personas en Pobreza',
        FORMAT('{:,.0f}', SUM(m.total_personas * m.pct_pobreza_general_personas)),
        'personas'
    FROM (SELECT *, (codigo_provincia * 10000 + codigo_distrito * 100 + codigo_corregimiento) as Id_Correg_Calc FROM mapa_pobreza WHERE total_personas > 0) m
    UNION ALL
    SELECT 
        'Tasa Nacional de Pobreza',
        ROUND(SUM(m.total_personas * m.pct_pobreza_general_personas) * 100.0 / SUM(m.total_personas), 1) || '%',
        'porcentaje'
    FROM (SELECT *, (codigo_provincia * 10000 + codigo_distrito * 100 + codigo_corregimiento) as Id_Correg_Calc FROM mapa_pobreza WHERE total_personas > 0) m
    UNION ALL
    SELECT 'Total Beneficiarios', '186,225', 'personas'
    UNION ALL
    SELECT 
        'Cobertura Nacional',
        ROUND(186225 * 100.0 / SUM(m.total_personas * m.pct_pobreza_general_personas), 1) || '%',
        'porcentaje'
    FROM (SELECT *, (codigo_provincia * 10000 + codigo_distrito * 100 + codigo_corregimiento) as Id_Correg_Calc FROM mapa_pobreza WHERE total_personas > 0) m
    """
    
    # 2. TOP BRECHAS ABSOLUTAS
    print("  📈 Hoja 2: Top Brechas Absolutas")
    top_brechas_query = """
    WITH cobertura_por_correg AS (
        SELECT Id_Correg, COUNT(*) as total_beneficiarios
        FROM planilla GROUP BY Id_Correg
    ),
    id_correg_mapa AS (
        SELECT *, (codigo_provincia * 10000 + codigo_distrito * 100 + codigo_corregimiento) as Id_Correg_Calc
        FROM mapa_pobreza WHERE total_personas > 0
    )
    SELECT 
        m.provincia,
        m.distrito,
        m.corregimiento,
        m.total_personas as poblacion_total,
        ROUND(m.pct_pobreza_general_personas * 100, 1) as pobreza_pct,
        ROUND(m.pct_pobreza_extrema_personas * 100, 1) as pobreza_extrema_pct,
        ROUND(m.total_personas * m.pct_pobreza_general_personas) as personas_pobreza_general,
        ROUND(m.total_personas * m.pct_pobreza_extrema_personas) as personas_pobreza_extrema,
        COALESCE(c.total_beneficiarios, 0) as total_beneficiarios,
        ROUND(COALESCE(c.total_beneficiarios, 0) * 100.0 / NULLIF(m.total_personas * m.pct_pobreza_general_personas, 0), 1) as cobertura_pct,
        ROUND(m.total_personas * m.pct_pobreza_general_personas - COALESCE(c.total_beneficiarios, 0)) as gap_atencion_absoluto,
        CASE 
            WHEN m.pct_pobreza_general_personas >= 0.5 AND COALESCE(c.total_beneficiarios, 0) = 0 THEN 'CRÍTICO'
            WHEN m.pct_pobreza_general_personas >= 0.3 AND COALESCE(c.total_beneficiarios, 0) * 100.0 / NULLIF(m.total_personas * m.pct_pobreza_general_personas, 0) < 10 THEN 'ALTO'
            WHEN m.pct_pobreza_general_personas >= 0.2 AND COALESCE(c.total_beneficiarios, 0) * 100.0 / NULLIF(m.total_personas * m.pct_pobreza_general_personas, 0) < 25 THEN 'MEDIO'
            ELSE 'BAJO'
        END as nivel_brecha
    FROM id_correg_mapa m
    LEFT JOIN cobertura_por_correg c ON m.Id_Correg_Calc = c.Id_Correg
    ORDER BY gap_atencion_absoluto DESC
    LIMIT 50
    """
    
    # 3. CASOS CRÍTICOS
    print("  🚨 Hoja 3: Casos Críticos")
    criticos_query = """
    WITH cobertura_por_correg AS (
        SELECT Id_Correg, COUNT(*) as total_beneficiarios
        FROM planilla GROUP BY Id_Correg
    ),
    id_correg_mapa AS (
        SELECT *, (codigo_provincia * 10000 + codigo_distrito * 100 + codigo_corregimiento) as Id_Correg_Calc
        FROM mapa_pobreza WHERE total_personas > 0
    )
    SELECT 
        m.provincia,
        m.distrito,
        m.corregimiento,
        m.total_personas as poblacion_total,
        ROUND(m.pct_pobreza_general_personas * 100, 1) as pobreza_pct,
        ROUND(m.pct_pobreza_extrema_personas * 100, 1) as pobreza_extrema_pct,
        ROUND(m.total_personas * m.pct_pobreza_general_personas) as personas_pobreza,
        COALESCE(c.total_beneficiarios, 0) as beneficiarios,
        ROUND(COALESCE(c.total_beneficiarios, 0) * 100.0 / NULLIF(m.total_personas * m.pct_pobreza_general_personas, 0), 1) as cobertura_pct,
        'CRÍTICO: Alta pobreza + Baja cobertura' as clasificacion
    FROM id_correg_mapa m
    LEFT JOIN cobertura_por_correg c ON m.Id_Correg_Calc = c.Id_Correg
    WHERE 
        m.pct_pobreza_general_personas >= 0.5 
        AND COALESCE(c.total_beneficiarios, 0) * 100.0 / NULLIF(m.total_personas * m.pct_pobreza_general_personas, 0) < 20
    ORDER BY m.pct_pobreza_general_personas DESC, personas_pobreza DESC
    LIMIT 50
    """
    
    # 4. ANÁLISIS POR PROGRAMA
    print("  📊 Hoja 4: Cobertura por Programa")
    programas_query = """
    WITH cobertura_detallada AS (
        SELECT 
            p.Id_Correg,
            p.Provincia, p.Distrito, p.Corregimiento,
            COUNT(*) as total_beneficiarios,
            COUNT(CASE WHEN p.Programa = 'B/. 120 A LOS 65' THEN 1 END) as ben_120_65,
            COUNT(CASE WHEN p.Programa = 'RED DE OPORTUNIDADES' THEN 1 END) as ben_red_oport,
            COUNT(CASE WHEN p.Programa = 'ANGEL GUARDIAN' THEN 1 END) as ben_angel_guardian,
            COUNT(CASE WHEN p.Programa = 'SENAPAN' THEN 1 END) as ben_senapan
        FROM planilla p
        GROUP BY p.Id_Correg, p.Provincia, p.Distrito, p.Corregimiento
    )
    SELECT 
        Provincia,
        Distrito,
        Corregimiento,
        total_beneficiarios,
        ben_120_65 as 'B/. 120 A LOS 65',
        ben_red_oport as 'Red de Oportunidades',
        ben_angel_guardian as 'Angel Guardian',
        ben_senapan as 'SENAPAN'
    FROM cobertura_detallada
    WHERE total_beneficiarios > 0
    ORDER BY total_beneficiarios DESC
    LIMIT 100
    """
    
    # 5. ESTADÍSTICAS POR PROVINCIA
    print("  🗺️ Hoja 5: Estadísticas por Provincia")
    provincias_query = """
    WITH cobertura_provincia AS (
        SELECT 
            p.Provincia,
            COUNT(*) as total_beneficiarios,
            COUNT(DISTINCT p.Id_Correg) as corregimientos_atendidos
        FROM planilla p
        GROUP BY p.Provincia
    ),
    pobreza_provincia AS (
        SELECT 
            provincia,
            SUM(total_personas) as poblacion,
            SUM(total_personas * pct_pobreza_general_personas) as personas_pobreza,
            COUNT(*) as total_corregimientos
        FROM mapa_pobreza
        WHERE total_personas > 0
        GROUP BY provincia
    )
    SELECT 
        pp.provincia,
        FORMAT('{:,.0f}', pp.poblacion) as poblacion_total,
        FORMAT('{:,.0f}', pp.personas_pobreza) as personas_pobreza,
        ROUND(pp.personas_pobreza * 100.0 / pp.poblacion, 1) as tasa_pobreza_pct,
        COALESCE(cp.total_beneficiarios, 0) as total_beneficiarios,
        ROUND(COALESCE(cp.total_beneficiarios, 0) * 100.0 / pp.personas_pobreza, 1) as cobertura_pct,
        COALESCE(cp.corregimientos_atendidos, 0) as corregimientos_atendidos,
        pp.total_corregimientos,
        ROUND(COALESCE(cp.corregimientos_atendidos, 0) * 100.0 / pp.total_corregimientos, 1) as cobertura_geografica_pct
    FROM pobreza_provincia pp
    LEFT JOIN cobertura_provincia cp ON pp.provincia = cp.Provincia
    ORDER BY pp.personas_pobreza DESC
    """
    
    # Ejecutar queries y crear DataFrames
    try:
        df_resumen = con.execute(resumen_query).fetchdf()
        df_brechas = con.execute(top_brechas_query).fetchdf()
        df_criticos = con.execute(criticos_query).fetchdf()
        df_programas = con.execute(programas_query).fetchdf()
        df_provincias = con.execute(provincias_query).fetchdf()
    except Exception as e:
        print(f"❌ Error ejecutando queries: {e}")
        return False
    
    # Crear Excel con múltiples hojas
    print(f"💾 Creando archivo Excel: {output_file}")
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        
        # Hoja 1: Resumen Ejecutivo
        df_resumen.to_excel(writer, sheet_name='Resumen Ejecutivo', index=False)
        
        # Hoja 2: Top Brechas
        df_brechas.to_excel(writer, sheet_name='Top Brechas Absolutas', index=False)
        
        # Hoja 3: Casos Críticos
        df_criticos.to_excel(writer, sheet_name='Casos Críticos', index=False)
        
        # Hoja 4: Por Programa
        df_programas.to_excel(writer, sheet_name='Cobertura por Programa', index=False)
        
        # Hoja 5: Por Provincia
        df_provincias.to_excel(writer, sheet_name='Estadísticas Provinciales', index=False)
        
        # Hoja 6: Metadata
        metadata = pd.DataFrame({
            'Información': [
                'Fecha de Generación',
                'Base de Datos',
                'Total Corregimientos',
                'Total Beneficiarios',
                'Programas Analizados',
                'Metodología'
            ],
            'Valor': [
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'censo_2023.duckdb',
                '703',
                '186,225',
                'B/. 120 A LOS 65, Red de Oportunidades, Angel Guardian, SENAPAN',
                'Enlace por ID geográfico compuesto: provincia*10000 + distrito*100 + corregimiento'
            ]
        })
        metadata.to_excel(writer, sheet_name='Metadata', index=False)
    
    con.close()
    return True

if __name__ == "__main__":
    base_dir = Path(__file__).parent
    db_path = str(base_dir / "censo_2023.duckdb")
    output_file = f"analisis_brecha_pobreza_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    
    if not Path(db_path).exists():
        print(f"❌ No se encontró: {db_path}")
        sys.exit(1)
    
    if generar_excel_completo(db_path, output_file):
        print(f"✅ Excel generado exitosamente: {output_file}")
        
        # Mostrar estadísticas del archivo
        file_size = Path(output_file).stat().st_size / (1024 * 1024)
        print(f"📁 Tamaño: {file_size:.1f} MB")
        print(f"📊 6 hojas de análisis incluidas")
    else:
        print("❌ Error generando Excel")
        sys.exit(1)
