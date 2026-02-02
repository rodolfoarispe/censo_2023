# Librerias necesarias: pandas, pyreadstat
# Instalar con: pip install pandas pyreadstat

import sys
import os
import pyreadstat
from pyreadstat._readstat_parser import PyreadstatError

def main():
    """
    Convierte un archivo .sav a .csv.
    El nombre del archivo .sav se pasa como argumento de línea de comandos.
    """
    # Verificar si se proporcionó un argumento
    if len(sys.argv) != 2:
        print("Uso: python convertir_sav.py <archivo.sav>")
        print("Convierte un archivo SAV de SPSS a formato CSV.")
        sys.exit(1)

    input_file = sys.argv[1]

    # Verificar que el archivo de entrada exista
    if not os.path.exists(input_file):
        print(f"Error: El archivo '{input_file}' no existe.")
        sys.exit(1)

    # Verificar la extensión del archivo
    if not input_file.lower().endswith('.sav'):
        print(f"Error: El archivo '{input_file}' no parece ser un archivo .sav.")
        sys.exit(1)

    # Definir el nombre del archivo de salida
    output_csv = os.path.splitext(input_file)[0] + ".csv"
    chunk_size = 100000  # Procesa 100k registros a la vez

    print(f"Convirtiendo '{input_file}' a '{output_csv}'...")

    try:
        # El generador permite procesar el archivo sin cargarlo todo en RAM
        reader = pyreadstat.read_file_in_chunks(pyreadstat.read_sav, input_file, chunksize=chunk_size)

        for i, (df, meta) in enumerate(reader):
            # Escribe el encabezado solo en el primer fragmento
            modo = 'w' if i == 0 else 'a'
            header = True if i == 0 else False

            df.to_csv(output_csv, mode=modo, index=False, header=header, encoding='utf-8')
            print(f"Procesados {(i + 1) * chunk_size} registros...")
        
        print(f"Conversión finalizada. Archivo guardado como '{output_csv}'.")

    except PyreadstatError as e:
        print(f"Error: No se pudo leer el archivo '{input_file}'.")
        print("Puede que el archivo no sea un archivo SAV válido o esté corrupto.")
        print(f"Detalle del error: {e}")
        # Si el archivo de salida se creó, eliminarlo porque está incompleto/erróneo
        if os.path.exists(output_csv):
            os.remove(output_csv)
    except Exception as e:
        print(f"Ocurrió un error inesperado: {e}")
        if os.path.exists(output_csv):
            os.remove(output_csv)

if __name__ == "__main__":
    main()