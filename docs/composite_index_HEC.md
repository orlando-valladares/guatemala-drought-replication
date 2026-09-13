# Índice descriptivo de exposición e impacto hídrico

Fecha de actualización: 2026-09-13.

Con los mismos insumos ya incluidos en los puntos de control derivados, la versión actual separa el peligro climático de la exposición estructural:

```text
H_i = max(-z_i, 0)
d_i = Pctl(A_i / T_i)
p_i = Pctl(A_i / ha_ag,i)
E_i = (d_i + p_i) / 2
C_i = H_i × E_i
```

- `z_i` es el z-score CHIRPS de precipitación mayo--agosto; `H_i` es cero para condiciones no secas.
- `A_i/T_i` mide dependencia laboral de agricultura usando el Cuadro A12.2 del INE (2018).
- `A_i/ha_ag,i` usa los polígonos MAGA 2025 de Nivel 1 `Territorios agrícolas`; la tabla muestra la escala equivalente `100 A_i/ha_ag,i`.
- `d_i` y `p_i` son percentiles empíricos de 0--100 calculados entre las unidades del mismo nivel geográfico. `E_i` da el mismo peso a ambos canales.
- `C_i` permite ordenar unidades por exposición a una sequía concreta. No es una predicción de pérdidas, productividad, tenencia de tierra o causalidad, y los valores de municipio y departamento no deben compararse directamente porque sus percentiles se calculan por separado.

La desagregación evita depender sólo de trabajadores por hectárea --que puede penalizar departamentos extensos del norte-- o sólo de la participación agrícola --que ignora el número de personas potencialmente expuestas.
