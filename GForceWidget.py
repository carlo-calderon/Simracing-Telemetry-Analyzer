# -*- coding: utf-8 -*-
"""
File: GForceWidget.py
Created on 2025-07-07
@author: Carlo Calderón Becerra
@company: CarcaldeF1
"""

from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QRadialGradient
from PySide6.QtCore import Qt, QPointF

class GForceWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(150, 150) # Aseguramos un tamaño mínimo cuadrado
        
        self.lat_g = 0.0
        self.long_g = 0.0
        
        self.max_g = 5.0 # El máximo G que mostrarán los círculos

    def update_g_forces(self, lat_g: float, long_g: float):
        """ Actualiza los valores de G y solicita un redibujado. """
        #print(f"Updating G-Forces: Lat={lat_g}, Long={long_g}")
        self.lat_g = lat_g
        self.long_g = long_g
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
        point_x = center.x() + (self.lat_g / self.max_g) * max_radius
        point_y = center.y() - (self.long_g / self.max_g) * max_radius
        
        # Le damos un efecto de esfera con un gradiente radial
        point_radius = 6
        gradient = QRadialGradient(QPointF(point_x, point_y), point_radius)
        gradient.setColorAt(0, QColor(255, 100, 100)) # Rojo brillante en el centro
        gradient.setColorAt(1, QColor(150, 0, 0))    # Rojo oscuro en el borde
        
        painter.setPen(Qt.NoPen)
        painter.setBrush(gradient)
        painter.drawEllipse(QPointF(point_x, point_y), point_radius, point_radius)