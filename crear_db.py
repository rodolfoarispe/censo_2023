#!/usr/bin/env python3
"""
Script para crear la base de datos DuckDB del Censo 2023 de Panamá.

Uso:
    python crear_db.py [--mapa-pobreza archivo.xlsx]

Requisitos:
    pip install duckdb pyreadstat pandas openpyxl

Este script:
1. Une los archivos zip divididos (si aplica)
2. Extrae los archivos .sav del censo
3. Carga los datos en DuckDB
4. Opcionalmente carga el mapa de pobreza
"""
import argparse
import os
import subprocess
import tempfile
import shutil
from pathlib import Path

def unir_zip(base_dir: Path, temp_dir: Path) -> Path:
    """Une archivos zip divididos y extrae el contenido."""
    split_zip = base_dir / "censo_2023_split.zip"
    single_zip = base_dir / "censo_2023.zip"

    if split_zip.exists():
        print("📦 Uniendo archivos zip divididos...")
        joined_zip = temp_dir / "censo_2023_joined.zip"
        subprocess.run(
            ["zip", "-s", "0", str(split_zip), "--out", str(joined_zip)],
            check=True, capture_output=True
        )
        return joined_zip
    elif single_zip.exists():
        return single_zip
    else:
        raise FileNotFoundError("No se encontró censo_2023.zip ni censo_2023_split.zip")

def extraer_zip(zip_path: Path, dest_dir: Path):
    """Extrae el contenido del zip."""
    print(f"📂 Extrayendo {zip_path.name}...")
    subprocess.run(
        ["unzip", "-o", str(zip_path), "-d", str(dest_dir)],
        check=True, capture_output=True
    )

def cargar_sav(archivo: Path, nombre_tabla: str, con):
    """Carga un archivo .sav en DuckDB."""
    import pyreadstat

    print(f"  Cargando {archivo.name}...")
    df, meta = pyreadstat.read_sav(archivo)
    print(f"    → {len(df):,} registros, {len(df.columns)} columnas")

    con.execute(f"DROP TABLE IF EXISTS {nombre_tabla}")
    con.register("df_temp", df)
    con.execute(f"CREATE TABLE {nombre_tabla} AS SELECT * FROM df_temp")
    con.unregister("df_temp")

def cargar_xlsx(archivo: Path, nombre_tabla: str, con, skiprows: int = 0):
    """Carga un archivo .xlsx en DuckDB."""
    import pandas as pd

    print(f"  Cargando {archivo.name}...")
    df = pd.read_excel(archivo, skiprows=skiprows)
    print(f"    → {len(df):,} registros, {len(df.columns)} columnas")

    con.execute(f"DROP TABLE IF EXISTS {nombre_tabla}")
    con.register("df_temp", df)
    con.execute(f"CREATE TABLE {nombre_tabla} AS SELECT * FROM df_temp")
    con.unregister("df_temp")

def cargar_mapa_pobreza(archivo: Path, con):
    """Carga el mapa de pobreza con estructura correcta."""
    import pandas as pd

    print(f"  Cargando {archivo.name}...")

    # El archivo tiene headers en múltiples filas, saltamos las primeras 4
    df = pd.read_excel(archivo, skiprows=4, header=None)

    # Asignar nombres de columnas
    columnas = [
        'numero', 'codigo_provincia', 'codigo_distrito', 'codigo_corregimiento',
        'provincia', 'distrito', 'corregimiento', 'num_hogares', 'total_personas',
        'pct_pobreza_general_personas', 'pct_pobreza_extrema_personas',
        'personas_pobreza_general', 'personas_pobreza_extrema',
        'pct_pobreza_general_hogares', 'pct_pobreza_extrema_hogares',
        'hogares_pobreza_general', 'hogares_pobreza_extrema'
    ]

    df.columns = columnas[:len(df.columns)]

    # Filtrar filas válidas (donde codigo_provincia es numérico)
    df = df[pd.to_numeric(df['codigo_provincia'], errors='coerce').notna()]

    # Convertir tipos
    for col in ['codigo_provincia', 'codigo_distrito', 'codigo_corregimiento',
                'num_hogares', 'total_personas']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').astype('Int64')

    for col in df.columns:
        if col.startswith('pct_') or col.startswith('personas_') or col.startswith('hogares_'):
            df[col] = pd.to_numeric(df[col], errors='coerce')

    print(f"    → {len(df):,} registros procesados")

    con.execute("DROP TABLE IF EXISTS mapa_pobreza")
    con.register("df_temp", df)
    con.execute("CREATE TABLE mapa_pobreza AS SELECT * FROM df_temp")
    con.unregister("df_temp")

def main():
    parser = argparse.ArgumentParser(
        description="Crear base de datos DuckDB del Censo 2023",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        '--mapa-pobreza', '-m',
        help='Archivo Excel con el mapa de pobreza del MEF'
    )
    parser.add_argument(
        '--output', '-o',
        default='censo_2023.duckdb',
        help='Nombre del archivo de salida (default: censo_2023.duckdb)'
    )
    args = parser.parse_args()

    import duckdb

    base_dir = Path(__file__).parent
    db_path = base_dir / args.output

    print("=" * 60)
    print("CREACIÓN DE BASE DE DATOS - CENSO 2023 PANAMÁ")
    print("=" * 60)

    # Crear directorio temporal
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Unir y extraer zip
        zip_path = unir_zip(base_dir, temp_path)
        extraer_zip(zip_path, temp_path)

        # Buscar directorio de datos
        censo_dir = temp_path / "PYV_2023 CENSO 2023 INEC"
        if not censo_dir.exists():
            # Buscar en subdirectorios
            for d in temp_path.iterdir():
                if d.is_dir() and "CENSO" in d.name.upper():
                    censo_dir = d
                    break

        if not censo_dir.exists():
            raise FileNotFoundError(f"No se encontró directorio del censo en {temp_path}")

        print(f"\n📁 Directorio de datos: {censo_dir.name}")

        # Conectar a DuckDB
        if db_path.exists():
            db_path.unlink()
        con = duckdb.connect(str(db_path))

        # Cargar archivos .sav principales
        print("\n📊 Cargando tablas principales del censo...")
        archivos_sav = [
            ("CEN2023_PERSONA.sav", "personas"),
            ("CEN2023_HOGAR.sav", "hogares"),
            ("CEN2023_VIVIENDA.sav", "viviendas"),
        ]

        for archivo, tabla in archivos_sav:
            ruta = censo_dir / archivo
            if ruta.exists():
                cargar_sav(ruta, tabla, con)
            else:
                print(f"  ⚠️  No encontrado: {archivo}")

        # Cargar catálogos
        print("\n📚 Cargando catálogos...")
        catalogos = [
            ("Actividad_2023.xlsx", "cat_actividad"),
            ("Barrios_urbanos_2023.xlsx", "cat_barrios"),
            ("Lugares_poblados_2023.xlsx", "cat_lugares"),
            ("Prov-Dist_Corr_2023.xlsx", "cat_distritos"),
        ]

        for archivo, tabla in catalogos:
            ruta = censo_dir / archivo
            if ruta.exists():
                try:
                    cargar_xlsx(ruta, tabla, con)
                except Exception as e:
                    print(f"  ⚠️  Error en {archivo}: {e}")

        # Cargar mapa de pobreza si se proporciona
        if args.mapa_pobreza:
            mapa_path = Path(args.mapa_pobreza)
            if mapa_path.exists():
                print("\n📈 Cargando mapa de pobreza...")
                cargar_mapa_pobreza(mapa_path, con)
            else:
                print(f"\n⚠️  No se encontró: {args.mapa_pobreza}")

        # Mostrar resumen
        print("\n" + "=" * 60)
        print("RESUMEN DE LA BASE DE DATOS")
        print("=" * 60)

        tablas = con.execute("SHOW TABLES").fetchall()
        for (tabla,) in tablas:
            count = con.execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()[0]
            print(f"  {tabla}: {count:,} registros")

        con.close()

        # Mostrar tamaño final
        size_mb = db_path.stat().st_size / (1024 * 1024)
        print(f"\n✅ Base de datos creada: {db_path.name}")
        print(f"   Tamaño: {size_mb:.1f} MB")

if __name__ == "__main__":
    main()
