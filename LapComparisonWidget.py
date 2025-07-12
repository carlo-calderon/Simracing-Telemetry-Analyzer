# -*- coding: utf-8 -*-
'''
File: LapComparisonWidget.py
Created on 2025-07-12
@author: Carlo Calderón Becerra
@company: CarcaldeF1
'''

from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QListWidget, QListWidgetItem
from PySide6.QtCore import Qt, Signal
import pyqtgraph as pg
import pandas as pd
import numpy as np

class LapComparisonWidget(QWidget):
    # Señal que emite la lista de variables a graficar
    plotted_variables_changed = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        
        # --- Configuración del Layout Principal ---
        main_layout = QHBoxLayout(self)
        
        # 1. Panel de selección de variables (izquierda)
        self.variable_list_widget = QListWidget()
        self.variable_list_widget.setFixedWidth(150)
        self.variable_list_widget.itemChanged.connect(self._on_variable_selection_changed)
        
        # 2. Área de gráficos (derecha)
        self.graphics_layout_widget = pg.GraphicsLayoutWidget()
        self.graphics_layout_widget.setBackground('#1f1f2e')

        main_layout.addWidget(self.variable_list_widget)
        main_layout.addWidget(self.graphics_layout_widget, 1) # El '1' le da más espacio

    def populate_variables(self, columns):
        """ Llena la lista de variables seleccionables. """
        self.variable_list_widget.blockSignals(True)

        self.variable_list_widget.clear()
        defaults = ['Speed', 'Throttle', 'Brake']
        for col in columns:
            item = QListWidgetItem(col, self.variable_list_widget)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            # Marcar los gráficos por defecto
            if col in defaults:
                item.setCheckState(Qt.Checked)
            else:
                item.setCheckState(Qt.Unchecked)

        self.variable_list_widget.blockSignals(False)
        self._on_variable_selection_changed(None)  # Emitir la señal inicial con los valores por defecto

    def _on_variable_selection_changed(self, item):
        """ Se activa cuando el usuario marca/desmarca una variable. """
        checked_vars = []
        for i in range(self.variable_list_widget.count()):
            item = self.variable_list_widget.item(i)
            if item.checkState() == Qt.Checked:
                checked_vars.append(item.text())
        self.plotted_variables_changed.emit(checked_vars)
        
    def update_plots(self, laps_data: dict, variables_to_plot: list):
        """
        Dibuja los gráficos.
        laps_data: {'Vuelta 5': df_vuelta_5, 'Vuelta 7': df_vuelta_7}
        variables_to_plot: ['Speed', 'Throttle']
        """
        print(f"Actualizando gráficos con {len(laps_data)} vueltas y {variables_to_plot} variables.")

        self.graphics_layout_widget.clear()

        # Generar una paleta de colores para las diferentes vueltas
        colors = ['#FF5733', '#33FF57', '#3357FF', '#FF33A1', '#A133FF', '#33FFA1']
        fixed_y_ranges = {
            'Throttle': (0.0, 1.05),
            'Brake': (0.0, 1.05),
            'Speed': (0.0, 100.0),
        }

        linked_x_plot = None
        max_dist = 0.0
        y_ranges = {}
        if laps_data:
            # Encontrar la distancia máxima en todas las vueltas a graficar
            for lap_df in laps_data.values():
                if 'LapDist' in lap_df and not lap_df.empty:
                    max_dist = max(max_dist, lap_df['LapDist'].max())
            
            # Calcular los rangos Y para cada variable que no tenga un rango fijo
            for var_name in variables_to_plot:
                if var_name not in fixed_y_ranges:
                    min_val, max_val = np.inf, -np.inf
                    for lap_df in laps_data.values():
                        if var_name in lap_df and not lap_df.empty:
                            min_val = min(min_val, lap_df[var_name].min())
                            max_val = max(max_val, lap_df[var_name].max())
                    
                    # Añadir un pequeño padding para que no quede pegado
                    padding = (max_val - min_val) * 0.05 if max_val > min_val else 1
                    y_ranges[var_name] = (min_val - padding, max_val + padding)

        for i, var_name in enumerate(variables_to_plot):
            plot_item = self.graphics_layout_widget.addPlot(row=i, col=0)

            plot_item.setLabel('left', var_name)
            if i == len(variables_to_plot) - 1:
                plot_item.setLabel('bottom', 'Distancia (m)')
            plot_item.showGrid(x=True, y=True, alpha=0.3)
            legend = plot_item.addLegend()
            
            if linked_x_plot:
                plot_item.setXLink(linked_x_plot)
            
            for j, (lap_name, lap_df) in enumerate(laps_data.items()):
                pen_style = Qt.DashLine if lap_name == 'Teórica' else Qt.SolidLine
                pen_color = '#FFFFFF' if lap_name == 'Teórica' else colors[j % len(colors)]
                pen = pg.mkPen(color=pen_color, width=2, style=pen_style)
                
                if 'LapDist' in lap_df and var_name in lap_df:
                    # Elimina NaN y ordena por LapDist
                    plot_df = lap_df[['LapDist', var_name]].dropna().sort_values('LapDist')
                    if not plot_df.empty:
                        plot_item.plot(
                            x=plot_df['LapDist'].to_numpy(), 
                            y=plot_df[var_name].to_numpy(), 
                            pen=pen,
                            name=lap_name
                            )

                        print(f"Graficando {var_name} para {lap_name} con {len(lap_df)} puntos.")
                        print(f"Rango de {var_name}: {lap_df[var_name].min()} a {lap_df[var_name].max()}, LapDist: {lap_df['LapDist'].min()} a {lap_df['LapDist'].max()}")
                        print(f"Datos: {plot_df['LapDist'].to_numpy()[:5]}... {plot_df[var_name].to_numpy()[:5]}")
                        max_dist = max(max_dist, lap_df['LapDist'].max())

            plot_item.setXRange(0, max_dist, padding=0.01)

            if var_name in fixed_y_ranges:
                min_y, max_y = fixed_y_ranges[var_name]
                plot_item.setYRange(min_y, max_y, padding=0)
            elif var_name in y_ranges:
                min_y, max_y = y_ranges[var_name]
                plot_item.setYRange(min_y, max_y, padding=0)

            linked_x_plot = plot_item
