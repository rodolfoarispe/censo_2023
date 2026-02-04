#!/usr/bin/env python3
"""
Script para cargar la planilla.csv en DuckDB
"""
import sys
from pathlib import Path
import pandas as pd

def cargar_csv(archivo: Path, nombre_tabla: str, db_path: str):
    """Carga un archivo .csv en DuckDB."""
    import duckdb
    
    print(f"📂 Leyendo {archivo.name}...")
    df = pd.read_csv(archivo, encoding='utf-8-sig')
    print(f"   → {len(df):,} registros, {len(df.columns)} columnas")
    
    print(f"🔗 Conectando a DuckDB: {db_path}...")
    con = duckdb.connect(db_path)
    
    print(f"💾 Creando tabla '{nombre_tabla}'...")
    con.execute(f"DROP TABLE IF EXISTS {nombre_tabla}")
    con.register("df_temp", df)
    con.execute(f"CREATE TABLE {nombre_tabla} AS SELECT * FROM df_temp")
    con.unregister("df_temp")
    
    # Mostrar info
    result = con.execute(f"SELECT COUNT(*) FROM {nombre_tabla}").fetchone()
    print(f"✅ Tabla '{nombre_tabla}' creada: {result[0]:,} registros")
    
    # Mostrar estructura
    cols = con.execute(f"DESCRIBE {nombre_tabla}").fetchall()
    print(f"\n📋 Estructura de {nombre_tabla}:")
    for col in cols:
        col_name = col[0]
        col_type = col[1]
        print(f"   {col_name}: {col_type}")
    
    con.close()

if __name__ == "__main__":
    base_dir = Path(__file__).parent
    db_path = str(base_dir / "censo_2023.duckdb")
    csv_path = base_dir / "planilla.csv"
    
    if not csv_path.exists():
        print(f"❌ No se encontró: {csv_path}")
        sys.exit(1)
    
    if not Path(db_path).exists():
        print(f"❌ No se encontró: {db_path}")
        sys.exit(1)
    
    cargar_csv(csv_path, "planilla", db_path)
    print("\n✨ Completado exitosamente")
