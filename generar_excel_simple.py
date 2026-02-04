#!/usr/bin/env python3
"""
Generador de Excel simplificado para análisis de brecha pobreza
"""
import sys
from pathlib import Path
import pandas as pd
import duckdb
from datetime import datetime

def conectar_duckdb(db_path):
    """Conecta a DuckDB"""
    return duckdb.connect(db_path)

def generar_excel_simple(db_path, output_file):
    """Genera Excel con análisis de brecha"""
    con = conectar_duckdb(db_path)
    
    print("📊 Generando Excel de análisis de brecha...")
    
    # Query principal: Top brechas
    print("  📈 Procesando brechas por corregimiento...")
    query_principal = """
    WITH cobertura_por_correg AS (
        SELECT 
            p.Id_Correg,
            COUNT(*) as total_beneficiarios,
            COUNT(CASE WHEN p.Programa = 'B/. 120 A LOS 65' THEN 1 END) as ben_120_65,
            COUNT(CASE WHEN p.Programa = 'RED DE OPORTUNIDADES' THEN 1 END) as ben_red_oport,
            COUNT(CASE WHEN p.Programa = 'ANGEL GUARDIAN' THEN 1 END) as ben_angel_guardian,
            COUNT(CASE WHEN p.Programa = 'SENAPAN' THEN 1 END) as ben_senapan
        FROM planilla p
        GROUP BY p.Id_Correg
    ),
    id_correg_mapa AS (
        SELECT 
            *,
            (codigo_provincia * 10000 + codigo_distrito * 100 + codigo_corregimiento) as Id_Correg_Calc
        FROM mapa_pobreza
        WHERE total_personas > 0
    )
    SELECT 
        m.provincia,
        m.distrito,
        m.corregimiento,
        m.total_personas as poblacion_total,
        ROUND(m.pct_pobreza_general_personas * 100, 1) as pobreza_general_pct,
        ROUND(m.pct_pobreza_extrema_personas * 100, 1) as pobreza_extrema_pct,
        ROUND(m.total_personas * m.pct_pobreza_general_personas) as personas_pobreza_general,
        ROUND(m.total_personas * m.pct_pobreza_extrema_personas) as personas_pobreza_extrema,
        COALESCE(c.total_beneficiarios, 0) as total_beneficiarios,
        COALESCE(c.ben_120_65, 0) as ben_120_65,
        COALESCE(c.ben_red_oport, 0) as ben_red_oportunidades,
        COALESCE(c.ben_angel_guardian, 0) as ben_angel_guardian,
        COALESCE(c.ben_senapan, 0) as ben_senapan,
        ROUND(COALESCE(c.total_beneficiarios, 0) * 100.0 / 
              NULLIF(m.total_personas * m.pct_pobreza_general_personas, 0), 1) as cobertura_pobreza_pct,
        ROUND(m.total_personas * m.pct_pobreza_general_personas - 
              COALESCE(c.total_beneficiarios, 0)) as gap_atencion_absoluto,
        CASE 
            WHEN m.pct_pobreza_general_personas >= 0.7 THEN 'EXTREMO'
            WHEN m.pct_pobreza_general_personas >= 0.5 THEN 'ALTO'
            WHEN m.pct_pobreza_general_personas >= 0.3 THEN 'MODERADO'
            ELSE 'BAJO'
        END as nivel_pobreza,
        CASE 
            WHEN COALESCE(c.total_beneficiarios, 0) = 0 THEN 'SIN COBERTURA'
            WHEN COALESCE(c.total_beneficiarios, 0) * 100.0 / NULLIF(m.total_personas * m.pct_pobreza_general_personas, 0) < 10 THEN 'BAJA'
            WHEN COALESCE(c.total_beneficiarios, 0) * 100.0 / NULLIF(m.total_personas * m.pct_pobreza_general_personas, 0) < 25 THEN 'MEDIA'
            ELSE 'ALTA'
        END as nivel_cobertura
    FROM id_correg_mapa m
    LEFT JOIN cobertura_por_correg c ON m.Id_Correg_Calc = c.Id_Correg
    ORDER BY gap_atencion_absoluto DESC
    """
    
    # Ejecutar query
    df_principal = con.execute(query_principal).fetchdf()
    
    # Query resumen por provincia
    print("  🗺️ Procesando estadísticas provinciales...")
    query_provincias = """
    WITH stats_provincia AS (
        SELECT 
            m.provincia,
            SUM(m.total_personas) as poblacion_total,
            SUM(m.total_personas * m.pct_pobreza_general_personas) as personas_pobreza,
            COUNT(*) as total_corregimientos
        FROM mapa_pobreza m
        WHERE m.total_personas > 0
        GROUP BY m.provincia
    ),
    beneficiarios_provincia AS (
        SELECT 
            Provincia,
            COUNT(*) as total_beneficiarios,
            COUNT(DISTINCT Id_Correg) as corregimientos_atendidos
        FROM planilla
        GROUP BY Provincia
    )
    SELECT 
        sp.provincia,
        sp.poblacion_total,
        ROUND(sp.personas_pobreza) as personas_pobreza,
        ROUND(sp.personas_pobreza * 100.0 / sp.poblacion_total, 1) as tasa_pobreza_pct,
        COALESCE(bp.total_beneficiarios, 0) as total_beneficiarios,
        ROUND(COALESCE(bp.total_beneficiarios, 0) * 100.0 / sp.personas_pobreza, 1) as cobertura_pct,
        COALESCE(bp.corregimientos_atendidos, 0) as corregimientos_atendidos,
        sp.total_corregimientos,
        ROUND(COALESCE(bp.corregimientos_atendidos, 0) * 100.0 / sp.total_corregimientos, 1) as cobertura_geografica_pct
    FROM stats_provincia sp
    LEFT JOIN beneficiarios_provincia bp ON sp.provincia = bp.Provincia
    ORDER BY sp.personas_pobreza DESC
    """
    
    df_provincias = con.execute(query_provincias).fetchdf()
    
    # Query casos críticos
    print("  🚨 Identificando casos críticos...")
    df_criticos = df_principal[
        (df_principal['pobreza_general_pct'] >= 50) & 
        (df_principal['cobertura_pobreza_pct'] < 20)
    ].head(30).copy()
    
    # Top gaps absolutos
    df_top_gaps = df_principal.head(50).copy()
    
    con.close()
    
    # Crear Excel
    print(f"💾 Creando archivo: {output_file}")
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        
        # Hoja 1: Top Gaps Absolutos
        df_top_gaps.to_excel(writer, sheet_name='Top 50 Brechas', index=False)
        
        # Hoja 2: Casos Críticos
        df_criticos.to_excel(writer, sheet_name='Casos Críticos', index=False)
        
        # Hoja 3: Por Provincia
        df_provincias.to_excel(writer, sheet_name='Por Provincia', index=False)
        
        # Hoja 4: Análisis completo (todos los corregimientos)
        df_principal.to_excel(writer, sheet_name='Análisis Completo', index=False)
        
        # Hoja 5: Resumen
        resumen_data = {
            'Indicador': [
                'Total Corregimientos Analizados',
                'Población Total',
                'Personas en Pobreza General',
                'Tasa Nacional de Pobreza (%)',
                'Total Beneficiarios',
                'Cobertura Nacional (%)',
                'Corregimientos con Pobreza >50%',
                'Corregimientos Sin Cobertura',
                'Gap Nacional (personas sin atender)'
            ],
            'Valor': [
                len(df_principal),
                f"{df_principal['poblacion_total'].sum():,.0f}",
                f"{df_principal['personas_pobreza_general'].sum():,.0f}",
                f"{df_principal['personas_pobreza_general'].sum() * 100 / df_principal['poblacion_total'].sum():.1f}%",
                f"{df_principal['total_beneficiarios'].sum():,.0f}",
                f"{df_principal['total_beneficiarios'].sum() * 100 / df_principal['personas_pobreza_general'].sum():.1f}%",
                len(df_principal[df_principal['pobreza_general_pct'] >= 50]),
                len(df_principal[df_principal['total_beneficiarios'] == 0]),
                f"{df_principal['gap_atencion_absoluto'].sum():,.0f}"
            ]
        }
        pd.DataFrame(resumen_data).to_excel(writer, sheet_name='Resumen Ejecutivo', index=False)
    
    return True

if __name__ == "__main__":
    base_dir = Path(__file__).parent
    db_path = str(base_dir / "censo_2023.duckdb")
    timestamp = datetime.now().strftime('%Y%m%d_%H%M')
    output_file = f"analisis_brecha_pobreza_{timestamp}.xlsx"
    
    if not Path(db_path).exists():
        print(f"❌ No se encontró: {db_path}")
        sys.exit(1)
    
    try:
        if generar_excel_simple(db_path, output_file):
            print(f"✅ Excel generado: {output_file}")
            
            # Mostrar estadísticas
            file_size = Path(output_file).stat().st_size / (1024 * 1024)
            print(f"📁 Tamaño: {file_size:.1f} MB")
            print(f"📊 5 hojas incluidas:")
            print(f"   • Top 50 Brechas")
            print(f"   • Casos Críticos")  
            print(f"   • Por Provincia")
            print(f"   • Análisis Completo")
            print(f"   • Resumen Ejecutivo")
        else:
            print("❌ Error generando Excel")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
