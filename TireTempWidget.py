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
        self.setMinimumHeight(100) # Le damos una altura mínima

        # Carga la imagen del coche que te proporcioné
        self.car_pixmap = QPixmap("./icons/formula_icon.jpeg") 

        # Diccionario para guardar los colores calculados para cada neumático
        default_color = QColor(Qt.gray)
        default_color.setAlphaF(0.7)
        self.tire_colors = {
            'LF': [default_color, default_color, default_color],
            'RF': [default_color, default_color, default_color],
            'LR': [default_color, default_color, default_color],
            'RR': [default_color, default_color, default_color]
        }
        
        # Mapa de colores para la temperatura (Azul=frío, Rojo=caliente)
        self.colormap = cm.get_cmap('coolwarm')

        # --- Coordenadas y tamaño de los rectángulos para cada neumático ---
        # Estos valores son porcentajes del ancho/alto total del widget.
        # Puede que necesites ajustarlos ligeramente para que coincidan con tu imagen.
        self.tire_rects_pct = {
            #               (x_pct, y_pct, w_pct, h_pct)
            'LF': QRectF(12/600.0, 222/1640.0, 95/600.0, 190/1640.0),
            'RF': QRectF(485/600.0, 222/1640.0, 100/600.0, 190/1640.0),
            'LR': QRectF(12/600.0, 1292/1640.0, 135/600.0, 190/1640.0),
            'RR': QRectF(455/600.0, 1292/1640.0, 135/600.0, 190/1640.)
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

        # 1. Escalar la imagen del coche manteniendo la proporción
        #    Qt.KeepAspectRatio asegura que no se deforme.
        scaled_pixmap = self.car_pixmap.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)

        # 2. Calcular la posición para centrar la imagen escalada en el widget
        x = (self.width() - scaled_pixmap.width()) / 2
        y = (self.height() - scaled_pixmap.height()) / 2
        image_rect = QRectF(x, y, scaled_pixmap.width(), scaled_pixmap.height())

        # 3. Dibujar la imagen del coche ya escalada y centrada
        painter.drawPixmap(image_rect.toRect(), scaled_pixmap)
        
        # 4. Dibujar los rectángulos de temperatura sobre la imagen escalada
        painter.setPen(Qt.NoPen)
        for tire_code, rect_pct in self.tire_rects_pct.items():
            # Convertimos los porcentajes a coordenadas relativas A LA IMAGEN, no al widget
            tire_x = image_rect.x() + rect_pct.x() * image_rect.width()
            tire_y = image_rect.y() + rect_pct.y() * image_rect.height()
            tire_w = rect_pct.width() * image_rect.width()
            tire_h = rect_pct.height() * image_rect.height()
            
            final_rect = QRectF(tire_x, tire_y, tire_w, tire_h)
            
            # Lógica para dibujar las 3 franjas de temperatura
            sub_rect_width = tire_w / 3
            colors = self.tire_colors[tire_code]

            painter.setBrush(colors[0]) # Interna
            painter.drawRect(QRectF(tire_x, tire_y, sub_rect_width, tire_h))
            
            painter.setBrush(colors[1]) # Media
            painter.drawRect(QRectF(tire_x + sub_rect_width, tire_y, sub_rect_width, tire_h))
            
            painter.setBrush(colors[2]) # Externa
            painter.drawRect(QRectF(tire_x + 2 * sub_rect_width, tire_y, sub_rect_width, tire_h))