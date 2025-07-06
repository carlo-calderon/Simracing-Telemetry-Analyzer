# -*- coding: utf-8 -*-
"""
File: TireTempWidget.py
Created on 2025-07-05
@author: Carlo Calderón Becerra
@company: CarcaldeF1
"""

from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QPixmap, QColor
from PySide6.QtCore import Qt, QRectF
from matplotlib import cm
import numpy as np
import pandas as pd
from RangeSlider import QRangeSlider

class TireTempWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(120)  # Un poco más alto para el slider

        # Carga la imagen del coche que te proporcioné
        self.car_pixmap = QPixmap("./icons/formula_icon.jpeg") 

        # Diccionario para guardar los colores calculados para cada neumático
        default_color = QColor(Qt.gray)
        default_color.setAlphaF(0.6)
        self.tire_colors = {
            'LF': [default_color, default_color, default_color],
            'RF': [default_color, default_color, default_color],
            'LR': [default_color, default_color, default_color],
            'RR': [default_color, default_color, default_color]
        }
        
        # Mapa de colores para la temperatura (Azul=frío, Rojo=caliente)
        self.colormap = cm.get_cmap('CMRmap')

        # --- Coordenadas y tamaño de los rectángulos para cada neumático ---
        # Estos valores son porcentajes del ancho/alto total del widget.
        # Puede que necesites ajustarlos ligeramente para que coincidan con tu imagen.
        self.tire_rects_pct = {
            #               (x_pct, y_pct, w_pct, h_pct)
            'LF': QRectF(12/600.0, 222/1640.0, 95/600.0, 190/1640.0),
            'RF': QRectF(485/600.0, 222/1640.0, 100/600.0, 190/1640.0),
            'LR': QRectF(12/600.0, 1292/1640.0, 135/600.0, 190/1640.0),
            'RR': QRectF(460/600.0, 1292/1640.0, 135/600.0, 190/1640.)
        }

        # --- Slider de temperatura ---
        self.temp_slider = QRangeSlider(self, labels_visible=False)
        self.temp_slider.setColormap(self.colormap)
        self.temp_slider.setRange(70.0, 120.0)
        self.temp_slider.setValues(70.0, 120.0)
        self.temp_slider.setFixedHeight(22)
        self.temp_slider.setToolTip("Rango de temperatura (°C)")
        self.temp_slider.setEnabled(True)  # Solo visual

        # Colores de los extremos (usando la paleta)
        min_color = QColor.fromRgbF(*self.colormap(0.0))
        max_color = QColor.fromRgbF(*self.colormap(1.0))
        self.temp_slider._min_edge_color = min_color
        self.temp_slider._max_edge_color = max_color

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Posiciona el slider debajo de la imagen del auto
        slider_margin = 8
        slider_height = self.temp_slider.height()
        self.temp_slider.setGeometry(
            0,
            self.height() - slider_height - slider_margin,
            self.width(),
            slider_height
        )

    def set_temp_range_from_dataframe(self, df):
        """
        Ajusta el rango de temperaturas del slider y la normalización de colores
        según los valores mínimos y máximos de las columnas de temperatura del DataFrame.
        """
        temp_cols = [col for col in df.columns if 'temp' in col]
        if not temp_cols:
            return
        min_temp = df[temp_cols].min().min()
        max_temp = df[temp_cols].max().max()
        if pd.isna(min_temp) or pd.isna(max_temp) or min_temp == max_temp:
            min_temp, max_temp = 70.0, 120.0  # Valores por defecto si hay problema

        self.temp_slider.setRange(min_temp, max_temp)
        self.temp_slider.setValues(min_temp, max_temp)
        self._min_temp = min_temp
        self._max_temp = max_temp

    def update_temperatures(self, temps: dict):
        """
        Recibe un diccionario con las temperaturas y actualiza los colores.
        """
        # Usa los valores actuales de min/max si existen, si no, usa por defecto
        min_temp = getattr(self, '_min_temp', 70.0)
        max_temp = getattr(self, '_max_temp', 120.0)
        temp_range = max_temp - min_temp if max_temp > min_temp else 1.0

        for tire_code in ['LF', 'RF', 'LR', 'RR']:
            temp_colors = []
            for position in ['L', 'M', 'R']: # Interna, Media, Externa
                temp_key = f"{tire_code}temp{position}"
                if temp_key in temps and temps[temp_key] is not np.nan:
                    temp = temps[temp_key]
                    norm_temp = (temp - min_temp) / temp_range
                    rgba = self.colormap(np.clip(norm_temp, 0, 1))
                    temp_colors.append(QColor.fromRgbF(*rgba))
                else:
                    temp_colors.append(QColor(Qt.gray))
            self.tire_colors[tire_code] = temp_colors

        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 1. Escalar la imagen del coche manteniendo la proporción
        #    Qt.KeepAspectRatio asegura que no se deforme.
        scaled_pixmap = self.car_pixmap.scaled(self.size().width(), self.size().height() - self.temp_slider.height() - 12, Qt.KeepAspectRatio, Qt.SmoothTransformation)

        # 2. Calcular la posición para centrar la imagen escalada en el widget
        x = (self.width() - scaled_pixmap.width()) / 2
        y = (self.height() - self.temp_slider.height() - scaled_pixmap.height()) / 2
        image_rect = QRectF(x, y, scaled_pixmap.width(), scaled_pixmap.height())

        # 3. Dibujar la imagen del coche ya escalada y centrada
        painter.drawPixmap(image_rect.toRect(), scaled_pixmap)
        
        # 4. Dibujar los rectángulos de temperatura sobre la imagen escalada
        painter.setPen(Qt.NoPen)
        for tire_code, rect_pct in self.tire_rects_pct.items():
            tire_x = image_rect.x() + rect_pct.x() * image_rect.width()
            tire_y = image_rect.y() + rect_pct.y() * image_rect.height()
            tire_w = rect_pct.width() * image_rect.width()
            tire_h = rect_pct.height() * image_rect.height()
            
            final_rect = QRectF(tire_x, tire_y, tire_w, tire_h)
            sub_rect_width = tire_w / 3
            colors = self.tire_colors[tire_code]

            painter.setBrush(colors[0]) # Interna
            painter.drawRect(QRectF(tire_x, tire_y, sub_rect_width, tire_h))
            
            painter.setBrush(colors[1]) # Media
            painter.drawRect(QRectF(tire_x + sub_rect_width, tire_y, sub_rect_width, tire_h))
            
            painter.setBrush(colors[2]) # Externa
            painter.drawRect(QRectF(tire_x + 2 * sub_rect_width, tire_y, sub_rect_width, tire_h))