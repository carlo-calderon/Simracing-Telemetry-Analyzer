# -*- coding: utf-8 -*-
'''
File: LapsTimeTable.py
Created on 2025-06-29
@author: Carlo Calderón Becerra
@company: CarcaldeF1
'''

from PySide6.QtWidgets import QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView
from PySide6.QtCore import Qt
import pandas as pd
from PySide6.QtGui import QColor

class LapsTimeTable(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0) # Sin márgenes

        self.table = QTableWidget()
        self.layout.addWidget(self.table)
        
        self._setup_ui()

    def _setup_ui(self):
        """ Configura la apariencia inicial y el estilo de la tabla. """
        self.table.setColumnCount(1) # Empezamos con 1, se ajustará con los datos
        self.table.setHorizontalHeaderLabels(["Vuelta"])
        
        # --- ESTILO PROFESIONAL ---
        self.table.setShowGrid(False)
        self.table.verticalHeader().setVisible(False) # Ocultar la cabecera vertical (números de fila)
        self.table.setAlternatingRowColors(True) # Habilitar colores de fila alternos

        # Estiramos la última columna para que ocupe el espacio sobrante
        self.table.horizontalHeader().setStretchLastSection(True)
        
        # Usamos CSS de Qt para lograr el aspecto oscuro
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #2E2E2E; /* Fondo oscuro */
                color: #FFFFFF; /* Texto blanco */
                border: none;
                gridline-color: #444444;
            }
            QTableWidget::item {
                border-bottom: 1px solid #444444; /* Línea separadora sutil */
                padding: 5px;
            }
            QHeaderView::section {
                background-color: #3A3A3A; /* Fondo de la cabecera */
                color: #CCCCCC;
                padding: 4px;
                border: 1px solid #555555;
            }
            QTableWidget::item:selected {
                background-color: #555555; /* Color al seleccionar una celda */
            }
            QTableWidget QTableCornerButton::section {
                background-color: #3A3A3A;
            }
        """)

        self.table.horizontalHeader().sectionClicked.connect(self.on_header_clicked)

    def format_time(self, total_seconds, remove_leading_zero=False):
        """ Formatea segundos a MM:SS.ss o SS.ss si es menor a un minuto. 
            Si remove_leading_zero=True, elimina el 0 inicial en minutos.
        """
        if pd.isna(total_seconds):
            return "N/A"
        minutes, seconds = divmod(total_seconds, 60)
        if minutes >= 1:
            if remove_leading_zero and int(minutes) == 0:
                return f"{seconds:06.3f}"
            return f"{int(minutes):02d}:{seconds:06.3f}"
        else:
            return f"{seconds:05.3f}"

    def update_data(self, laps_df: pd.DataFrame):
        """ Limpia la tabla y la llena con los datos del nuevo DataFrame. """
        if laps_df is None or laps_df.empty:
            self.table.setRowCount(0)
            return

        self.table.setRowCount(laps_df.shape[0])
        self.table.setColumnCount(len(laps_df.columns))
        self.table.setHorizontalHeaderLabels(laps_df.columns)

        # Identificar vueltas válidas (todos los sectores > 0)
        sector_cols = [col for col in laps_df.columns if col.startswith('S')]
        valid_mask = laps_df[sector_cols].gt(0).all(axis=1)
        valid_laps = laps_df[valid_mask]

        # Mejor vuelta válida (menor tiempo total)
        best_lap_idx = None
        if not valid_laps.empty:
            best_lap_idx = valid_laps['Time'].idxmin()

        # Mejor sector por columna (solo entre vueltas válidas)
        best_sector_idx = {}
        for col in sector_cols:
            if not valid_laps.empty:
                best_idx = valid_laps[col].idxmin()
                best_sector_idx[col] = best_idx

        for row_idx, row_data in laps_df.iterrows():
            is_valid = valid_mask.iloc[row_idx] if row_idx in valid_mask.index else False
            for col_idx, col_name in enumerate(laps_df.columns):
                value = row_data[col_name]

                # Formatear el valor dependiendo de la columna
                if col_name == 'Lap':
                    display_text = str(int(value))
                elif col_name == 'Time':
                    display_text = self.format_time(value, remove_leading_zero=True)
                elif col_name.startswith('S'):
                    display_text = self.format_time(value)
                else:
                    display_text = str(value)

                item = QTableWidgetItem(display_text)
                item.setTextAlignment(Qt.AlignCenter)

                # Marcar mejor vuelta (Lap y Time) en magenta y negrita
                if is_valid and row_idx == best_lap_idx and col_name in ['Lap', 'Time']:
                    item.setForeground(QColor('magenta'))
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)

                # Marcar mejor sector en magenta y negrita
                if is_valid and col_name in best_sector_idx and row_idx == best_sector_idx[col_name]:
                    item.setForeground(QColor('magenta'))
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)

                self.table.setItem(row_idx, col_idx, item)

        # --- Agregar fila de mejor tiempo teórico ---
        if not valid_laps.empty and sector_cols:
            theoretical_row_idx = self.table.rowCount()
            self.table.insertRow(theoretical_row_idx)

            # Lap vacío
            lap_item = QTableWidgetItem("")
            self.table.setItem(theoretical_row_idx, 0, lap_item)

            # Calcular mejor tiempo teórico sumando los mejores sectores válidos
            best_sectors = [valid_laps[col].min() for col in sector_cols]
            theoretical_time = sum(best_sectors)

            for col_idx, col_name in enumerate(laps_df.columns):
                if col_name == 'Lap':
                    continue
                elif col_name == 'Time':
                    display_text = self.format_time(theoretical_time, remove_leading_zero=True)
                elif col_name in sector_cols:
                    display_text = self.format_time(valid_laps[col_name].min())
                else:
                    display_text = ""

                item = QTableWidgetItem(display_text)
                item.setTextAlignment(Qt.AlignCenter)
                font = item.font()
                font.setBold(True)
                item.setFont(font)
                item.setForeground(QColor('lightblue'))
                self.table.setItem(theoretical_row_idx, col_idx, item)

        # Ajustar el tamaño de las columnas al contenido
        self.table.resizeColumnsToContents()
        self.table.horizontalHeader().setStretchLastSection(True)

    def on_header_clicked(self, logicalIndex):
        # Solo sectores (columna 2 en adelante, es decir, S1, S2, ...)
        if logicalIndex < 2:
            return

        col_name = self.table.horizontalHeaderItem(logicalIndex).text()
        if not col_name.startswith('S'):
            return

        # Obtener los porcentajes de inicio y fin del sector
        sector_num = int(col_name[1:])  # S1 -> 1, S2 -> 2, ...
        # Supón que tienes acceso a la lista de porcentajes (debes pasarla o guardarla)
        # Ejemplo: self.sector_percents = [0.25, 0.5, 0.75]
        if not hasattr(self, 'sector_percents'):
            return

        if sector_num == 1:
            start_pct = 0.0
        else:
            start_pct = self.sector_percents[sector_num - 2]
        if sector_num - 1 < len(self.sector_percents):
            end_pct = self.sector_percents[sector_num - 1]
        else:
            end_pct = 1.0

        # Emitir señal o llamar callback para ajustar el slider
        if hasattr(self, 'on_sector_selected'):
            self.on_sector_selected(start_pct, end_pct)