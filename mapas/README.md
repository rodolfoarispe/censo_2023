# Mapas interactivos

Este directorio contiene los mapas HTML generados por `choropleth_cobertura.py`
y `generar_mapas.py`. Los archivos incluyen un timestamp en el nombre.

## Mapas disponibles

- `mapa_cobertura_YYYYMMDD_HHMM.html`
  - Muestra el porcentaje de cobertura de beneficiarios sobre la poblacion
    en pobreza (pobres_total).
  - Interpretacion: verde = mayor cobertura, rojo = menor cobertura.

- `mapa_gap_YYYYMMDD_HHMM.html`
  - Muestra la brecha absoluta: pobres_total - beneficiarios_total.
  - Interpretacion: valores altos indican mas personas sin cobertura.

- `mapa_pobreza_general_YYYYMMDD_HHMM.html`
  - Porcentaje de pobreza general sobre la poblacion total.
  - Interpretacion: valores altos indican mayor incidencia de pobreza.

- `mapa_pobreza_extrema_YYYYMMDD_HHMM.html`
  - Porcentaje de pobreza extrema sobre la poblacion total.
  - Interpretacion: valores altos indican mayor severidad de pobreza.

- `mapa_cobertura_menores_YYYYMMDD_HHMM.html`
  - Cobertura de menores de 18 anos: menores_18_beneficiarios / menores_18_censo.
  - Interpretacion: verde = mayor cobertura de menores, rojo = menor cobertura.

## Panel de busqueda

- Selecciona Provincia -> Distrito -> Corregimiento.
- `Ir a Ubicacion`: hace zoom y resalta el borde del corregimiento.
- `Limpiar`: reinicia los dropdowns y quita el resaltado.

## Notas de interpretacion

- Pobreza general y pobreza extrema son porcentajes (tasas).
- Gap es un numero absoluto de personas sin cobertura.
- Cobertura de menores usa:
  - `menores_18_censo`: menores de 18 segun el censo.
  - `menores_18_beneficiarios`: menores de 18 en hogares de beneficiarios
    segun planilla.
- Si un corregimiento no tiene menores en censo, la cobertura de menores
  se muestra como 0.
