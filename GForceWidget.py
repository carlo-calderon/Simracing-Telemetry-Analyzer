# -*- coding: utf-8 -*-
"""
File: GForceWidget.py
Created on 2025-07-07
@author: Carlo Calderón Becerra
@company: CarcaldeF1
"""

from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QRadialGradient, QFont
from PySide6.QtCore import Qt, QPointF, QRectF
import numpy as np
import math

class GForceWidget(QWidget):
    def __init__(self, parent=None, max_g=5.0):
        super().__init__(parent)
        self.setMinimumSize(150, 150) # Aseguramos un tamaño mínimo cuadrado
        
        self.lat_g = 0.0
        self.long_g = 0.0
        self.x_g = 0.0
        self.y_g = 0.0
        
        self.max_g = max_g # El máximo G que mostrarán los círculos

    def set_max_g(self, g_value: float):
        """ Permite cambiar el G máximo del diagrama dinámicamente. """
        self.max_g = g_value if g_value > 0 else 1.0
        self.update()
        
    def update_g_forces(self, lat_g: float, long_g: float, yaw_radians: float):
        """ Actualiza los valores de G y solicita un redibujado. """
        #print(f"Updating G-Forces: Lat={lat_g}, Long={long_g}")
        self.lat_g = lat_g
        self.long_g = long_g

        cos_yaw = np.cos(yaw_radians-math.pi/2)
        sin_yaw = np.sin(yaw_radians-math.pi/2)
        self.x_g = lat_g * cos_yaw - long_g * sin_yaw
        self.y_g = lat_g * sin_yaw + long_g * cos_yaw
        
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # --- Geometría del Widget ---
        w = self.width()
        h = self.height()
        center = QPointF(w / 2, h / 2)
        # El radio máximo es la mitad del lado más corto del widget
        max_radius = min(w, h) / 2.0 - 10 # -10 para un pequeño margen

        # --- Dibujar Fondo y Ejes ---
        painter.setBrush(QColor(30, 30, 45)) # Fondo oscuro
        painter.drawRect(self.rect())
        
        axis_pen = QPen(QColor(100, 100, 120), 1, Qt.DashLine)
        painter.setPen(axis_pen)
        painter.drawLine(QPointF(center.x(), 5), QPointF(center.x(), h - 5)) # Eje Vertical
        painter.drawLine(QPointF(5, center.y()), QPointF(w - 5, center.y())) # Eje Horizontal

        # --- Dibujar Círculos Concéntricos ---
        circle_pen = QPen(QColor(70, 70, 90), 1, Qt.SolidLine)
        painter.setPen(circle_pen)
        painter.setBrush(Qt.NoBrush) # Sin relleno
        
        for g_force in range(1, int(self.max_g) + 1):
            radius = (g_force / self.max_g) * max_radius
            painter.drawEllipse(center, radius, radius)

        # --- Dibujar el Punto de G Actual ---
        # Mapeamos los valores de G al espacio de píxeles del widget
        # Long G (Adelante/Atrás) -> Eje Y (invertido, porque Y crece hacia abajo)
        # Lat G (Izquierda/Derecha) -> Eje X
        point_radius = 8
        painter.setPen(Qt.NoPen)

        point_x = center.x() + (self.lat_g / self.max_g) * max_radius
        point_y = center.y() - (self.long_g / self.max_g) * max_radius
        gradient = QRadialGradient(QPointF(point_x, point_y), point_radius)
        gradient.setColorAt(0, QColor(255, 100, 100)) # Rojo brillante en el centro
        gradient.setColorAt(1, QColor(150, 0, 0))    # Rojo oscuro en el borde
        painter.setBrush(gradient)
        painter.drawEllipse(QPointF(point_x, point_y), point_radius, point_radius)

        point_x = center.x() + (self.x_g / self.max_g) * max_radius
        point_y = center.y() - (self.y_g / self.max_g) * max_radius
        rel_gradient = QRadialGradient(QPointF(point_x, point_y), point_radius)
        rel_gradient.setColorAt(0, QColor(100, 255, 255))
        rel_gradient.setColorAt(1, QColor(0, 150, 150))
        painter.setBrush(rel_gradient)
        painter.drawEllipse(QPointF(point_x, point_y), point_radius, point_radius)

        font = QFont("Arial", 7)
        font.setBold(True)
        painter.setFont(font)
        metrics = painter.fontMetrics()

        # 1. Etiqueta para LongAccel (Arriba)
        long_text = f"{self.long_g:.2f} G"
        long_rect = metrics.boundingRect(long_text)
        long_label_rect = QRectF(center.x() - long_rect.width()/2 - 5, 5, long_rect.width() + 10, long_rect.height() + 4)
        painter.setBrush(QColor(150, 0, 0))
        painter.setPen(QColor(255, 255, 255))
        painter.drawRoundedRect(long_label_rect, 4, 4)
        painter.drawText(long_label_rect, Qt.AlignCenter, long_text)

        # 2. Etiqueta para LatAccel (Derecha)
        lat_text = f"{self.lat_g:.2f} G"
        lat_rect = metrics.boundingRect(lat_text)
        lat_label_rect = QRectF(w - lat_rect.width() - 15, center.y() - lat_rect.height()/2 - 2, lat_rect.width() + 10, lat_rect.height() + 4)
        painter.setBrush(QColor(150, 0, 0))
        painter.drawRoundedRect(lat_label_rect, 4, 4)
        painter.drawText(lat_label_rect, Qt.AlignCenter, lat_text)
        
        # 3. Etiqueta para Aceleración Total (Abajo-Izquierda)
        total_g = np.sqrt(self.x_g**2 + self.y_g**2)
        total_text = f"{total_g:.2f} G"
        total_rect = metrics.boundingRect(total_text)
        total_label_rect = QRectF(w - lat_rect.width() - 15, 5, total_rect.width() + 10, total_rect.height() + 4)
        painter.setBrush(QColor(0, 150, 150))
        painter.drawRoundedRect(total_label_rect, 4, 4)
        painter.drawText(total_label_rect, Qt.AlignCenter, total_text)