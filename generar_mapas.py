#!/usr/bin/env python3
"""
Genera todos los mapas interactivos de análisis de cobertura.

Uso:
    python generar_mapas.py              # Genera todos los mapas
    python generar_mapas.py --output-dir ./mapas  # En directorio específico
"""

import os
import subprocess
import argparse
from datetime import datetime

def generate_all_maps(output_dir="."):
    """Genera todos los mapas disponibles"""

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    
    metrics = [
        {
            "name": "cobertura",
            "description": "Porcentaje de cobertura de beneficiarios",
            "color": "🟢"
        },
        {
            "name": "gap",
            "description": "Brecha absoluta (personas sin cobertura)",
            "color": "🔴"
        },
        {
            "name": "pobreza_general",
            "description": "Porcentaje de pobreza general",
            "color": "🔵"
        },
        {
            "name": "pobreza_extrema",
            "description": "Porcentaje de pobreza extrema",
            "color": "⚫"
        },
    ]

    print("╔════════════════════════════════════════════════════════════╗")
    print("║        Generando Mapas Interactivos de Análisis            ║")
    print("╚════════════════════════════════════════════════════════════╝\n")

    generated_files = []

    for metric_config in metrics:
        metric = metric_config["name"]
        output_file = f"mapa_{metric}_{timestamp}.html"
        output_path = os.path.join(output_dir, output_file)

        print(f"{metric_config['color']} Generando: {metric_config['description']}")
        print(f"   → {output_file}")

        try:
            result = subprocess.run(
                [
                    "python",
                    "choropleth_cobertura.py",
                    "--metric",
                    metric,
                    "--output",
                    output_path,
                ],
                capture_output=True,
                text=True,
                timeout=120,
            )

            if result.returncode == 0:
                file_size = os.path.getsize(output_path) / 1024 / 1024
                print(f"   ✓ Guardado ({file_size:.2f} MB)\n")
                generated_files.append((metric, output_path))
            else:
                print(f"   ❌ Error: {result.stderr}\n")

        except Exception as e:
            print(f"   ❌ Error: {e}\n")

    print("╔════════════════════════════════════════════════════════════╗")
    print("║                    Resumen de Mapas                        ║")
    print("╚════════════════════════════════════════════════════════════╝\n")

    if generated_files:
        print(f"✓ Generados {len(generated_files)} mapas:\n")
        for metric, path in generated_files:
            abs_path = os.path.abspath(path)
            print(f"  • {metric:20} → {abs_path}")

        print(f"\n📂 Directorio: {os.path.abspath(output_dir)}")
        print(f"\nPara abrir en navegador:")
        print(f"  open {os.path.abspath(generated_files[0][1])}")

    else:
        print("❌ No se generaron mapas")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Genera todos los mapas interactivos")
    parser.add_argument(
        "--output-dir",
        default="./mapas",
        help="Directorio de salida (default: ./mapas)",
    )

    args = parser.parse_args()
    generate_all_maps(output_dir=args.output_dir)
