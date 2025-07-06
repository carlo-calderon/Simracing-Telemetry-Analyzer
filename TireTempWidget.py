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

class TireTempWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(150) # Le damos una altura mínima

        # Carga la imagen del coche que te proporcioné
        self.car_pixmap = QPixmap("./icons/formula_icon.jpeg") 

        # Diccionario para guardar los colores calculados para cada neumático
        self.tire_colors = {
            'LF': QColor(Qt.gray), 'RF': QColor(Qt.gray),
            'LR': QColor(Qt.gray), 'RR': QColor(Qt.gray)
        }
        
        # Mapa de colores para la temperatura (Azul=frío, Rojo=caliente)
        self.colormap = cm.get_cmap('coolwarm')

        # --- Coordenadas y tamaño de los rectángulos para cada neumático ---
        # Estos valores son porcentajes del ancho/alto total del widget.
        # Puede que necesites ajustarlos ligeramente para que coincidan con tu imagen.
        self.tire_rects_pct = {
            #               (x_pct, y_pct, w_pct, h_pct)
            'LF': QRectF(0.23, 0.10, 0.14, 0.20),
            'RF': QRectF(0.63, 0.10, 0.14, 0.20),
            'LR': QRectF(0.23, 0.70, 0.14, 0.20),
            'RR': QRectF(0.63, 0.70, 0.14, 0.20)
        }

    def update_temperatures(self, temps: dict):
        """
        Recibe un diccionario con las temperaturas y actualiza los colores.
        Ejemplo: {'LFtempM': 85.0, 'RFtempM': 90.0, ...}
        """
        # Rango de temperaturas esperado (ej. 70°C a 120°C).
        # Lo usamos para normalizar el valor y aplicarle un color.
        min_temp, max_temp = 70.0, 120.0
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

        # 1. Dibuja la imagen del coche, escalada para ajustarse al widget
        painter.drawPixmap(self.rect(), self.car_pixmap)
        
        # 2. Dibuja un rectángulo de color sobre cada neumático
        widget_width = self.width()
        widget_height = self.height()

        for tire_code, rect_pct in self.tire_rects_pct.items():
            # Convertimos los porcentajes a coordenadas de píxeles reales
            x = rect_pct.x() * widget_width
            y = rect_pct.y() * widget_height
            w = rect_pct.width() * widget_width
            h = rect_pct.height() * widget_height
            
            # Ancho de cada una de las 3 franjas de temperatura
            sub_rect_width = w / 3
            
            # Obtenemos los 3 colores para este neumático
            colors = self.tire_colors[tire_code]

            # Dibujamos las 3 franjas (Interna, Media, Externa)
            # Franja Izquierda (Interna)
            painter.setBrush(colors[0])
            painter.drawRect(QRectF(x, y, sub_rect_width, h))

            # Franja Central (Media)
            painter.setBrush(colors[1])
            painter.drawRect(QRectF(x + sub_rect_width, y, sub_rect_width, h))

            # Franja Derecha (Externa)
            painter.setBrush(colors[2])
            painter.drawRect(QRectF(x + 2 * sub_rect_width, y, sub_rect_width, h))