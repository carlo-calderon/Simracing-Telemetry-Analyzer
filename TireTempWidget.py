# -*- coding: utf-8 -*-
"""
File: TireTempWidget.py
Created on 2025-07-05
@author: Carlo Calderón Becerra
@company: CarcaldeF1
"""

from PySide6.QtWidgets import QWidget, QHBoxLayout
from PySide6.QtGui import QPainter, QPixmap, QColor
from PySide6.QtCore import Qt, QRectF
from matplotlib import cm
import numpy as np
import pandas as pd
from RangeSlider import QRangeSlider

class _CarCanvas(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.car_pixmap = QPixmap("./icons/formula_icon.jpeg")
        if self.car_pixmap.isNull():
            print("ADVERTENCIA: No se pudo cargar la imagen del coche en './icons/formula_icon.jpeg'. Revisa la ruta.")
        
        default_color = QColor(Qt.gray)
        default_color.setAlphaF(0.6)
        self.tire_colors = {
            'LF': [default_color] * 3, 'RF': [default_color] * 3,
            'LR': [default_color] * 3, 'RR': [default_color] * 3
        }
        self.tire_rects_pct = {
            'LF': QRectF(12/600.0, 222/1640.0, 95/600.0, 190/1640.0),
            'RF': QRectF(485/600.0, 222/1640.0, 100/600.0, 190/1640.0),
            'LR': QRectF(12/600.0, 1292/1640.0, 135/600.0, 190/1640.0),
            'RR': QRectF(460/600.0, 1292/1640.0, 135/600.0, 190/1640.)
        }

    def update_colors(self, colors: dict):
        self.tire_colors = colors
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if self.car_pixmap.isNull():
            return

        # 1. Escalar la imagen manteniendo proporciones y centrarla en este widget
        scaled_pixmap = self.car_pixmap.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        x = (self.width() - scaled_pixmap.width()) / 2
        y = (self.height() - scaled_pixmap.height()) / 2
        image_rect = QRectF(x, y, scaled_pixmap.width(), scaled_pixmap.height())
        painter.drawPixmap(image_rect.toRect(), scaled_pixmap)

        # 2. Dibujar los rectángulos de temperatura sobre la imagen escalada
        painter.setPen(Qt.NoPen)
        for tire_code, rect_pct in self.tire_rects_pct.items():
            tire_x = image_rect.x() + rect_pct.x() * image_rect.width()
            tire_y = image_rect.y() + rect_pct.y() * image_rect.height()
            tire_w = rect_pct.width() * image_rect.width()
            tire_h = rect_pct.height() * image_rect.height()
            
            sub_rect_width = tire_w / 3
            colors = self.tire_colors.get(tire_code, [QColor(Qt.gray)] * 3)

            painter.setBrush(colors[0])
            painter.drawRect(QRectF(tire_x, tire_y, sub_rect_width, tire_h))
            painter.setBrush(colors[1])
            painter.drawRect(QRectF(tire_x + sub_rect_width, tire_y, sub_rect_width, tire_h))
            painter.setBrush(colors[2])
            painter.drawRect(QRectF(tire_x + 2 * sub_rect_width, tire_y, sub_rect_width, tire_h))

class TireTempWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(150)
        
        # Guardamos los valores min/max para la normalización
        self._min_temp = 70.0
        self._max_temp = 120.0

        # --- Creación de los Widgets ---
        self.temp_slider = QRangeSlider(self, labels_visible=False, orientation=Qt.Vertical)
        self.temp_slider.setColormap(cm.get_cmap('CMRmap')) # Usamos CMRmap para temp
        self.temp_slider.setFixedWidth(25) # Un ancho fijo para el slider vertical
        
        # Nuestro lienzo de dibujado personalizado
        self.car_canvas = _CarCanvas(self)

        # --- Layout Principal Horizontal ---
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # Añadimos el slider a la izquierda y el lienzo del coche a la derecha
        layout.addWidget(self.temp_slider)
        layout.addWidget(self.car_canvas, 1) # El '1' le da más espacio para estirarse

    def set_temp_range_from_dataframe(self, df):
        temp_cols = [col for col in df.columns if 'temp' in col.lower() and col.endswith(('L', 'M', 'R'))]
        if not temp_cols:
            min_temp, max_temp = 70.0, 120.0
        else:
            min_temp = df[temp_cols].min().min()
            max_temp = df[temp_cols].max().max()
        
        if pd.isna(min_temp) or pd.isna(max_temp) or min_temp == max_temp:
            min_temp, max_temp = 70.0, 120.0

        self._min_temp = min_temp
        self._max_temp = max_temp
        self.temp_slider.setRange(min_temp, max_temp)
        self.temp_slider.setValues(min_temp, max_temp)

    def update_temperatures(self, temps: dict):
        temp_range = self._max_temp - self._min_temp if self._max_temp > self._min_temp else 1.0
        colormap = self.temp_slider.colormap
        
        tire_colors = {}
        for tire_code in ['LF', 'RF', 'LR', 'RR']:
            temp_colors_list = []
            for position in ['L', 'M', 'R']:
                temp_key = f"{tire_code}temp{position}"
                if temp_key in temps and not pd.isna(temps[temp_key]):
                    temp = temps[temp_key]
                    norm_temp = (temp - self._min_temp) / temp_range
                    rgba = colormap(np.clip(norm_temp, 0, 1))
                    temp_colors_list.append(QColor.fromRgbF(*rgba))
                else:
                    temp_colors_list.append(QColor(Qt.gray))
            tire_colors[tire_code] = temp_colors_list
        
        self.car_canvas.update_colors(tire_colors)
