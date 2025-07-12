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
        fixed_ranges = {
            'Throttle': (0.0, 1.05),
            'Brake': (0.0, 1.05),
            'Speed': (0.0, 100.0),
        }

        linked_x_plot = None
        max_dist = 1.0

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
                if lap_name == 'Teórica':
                    pen = pg.mkPen(color='#FFFFFF', width=2, style=Qt.DashLine)
                else:
                    pen = pg.mkPen(color=colors[j % len(colors)], width=2)
                
                if 'LapDist' in lap_df and var_name in lap_df:
                    plot_item.plot(lap_df['LapDist'].to_numpy(), lap_df[var_name].to_numpy(), pen=pen, name=lap_name)
                    print(f"Graficando {var_name} para {lap_name} con {len(lap_df)} puntos.")
                    print(f"Rango de {var_name}: {lap_df[var_name].min()} a {lap_df[var_name].max()}, LapDist: {lap_df['LapDist'].min()} a {lap_df['LapDist'].max()}")
                    max_dist = max(max_dist, lap_df['LapDist'].max())

            if var_name in fixed_ranges:
                # Si la variable está en nuestro diccionario, fijamos el rango Y
                min_y, max_y = fixed_ranges[var_name]
                plot_item.setYRange(min_y, max_y, padding=0)
                plot_item.setXRange(0, max_dist, padding=0)
                plot_item.getViewBox().disableAutoRange()
            else:
                # Si no, usamos el ciclo de auto-range controlado que ya teníamos
                plot_item.getViewBox().enableAutoRange(axis=pg.ViewBox.YAxis)
                plot_item.getViewBox().disableAutoRange()

            linked_x_plot = plot_item
