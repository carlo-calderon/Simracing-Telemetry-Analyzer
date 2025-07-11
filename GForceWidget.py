# -*- coding: utf-8 -*-
"""
File: GForceWidget.py
Created on 2025-07-07
@author: Carlo Calderón Becerra
@company: CarcaldeF1
"""

from PySide6.QtWidgets import QWidget, QToolTip
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QRadialGradient, QFont, QCursor
from PySide6.QtCore import Qt, QPointF, QRectF
import numpy as np
import math

class GForceWidget(QWidget):
    def __init__(self, parent=None, max_g=5.0):
        super().__init__(parent)
        self.setMinimumSize(180, 180) # Aseguramos un tamaño mínimo cuadrado
        self.setMouseTracking(True) # Para detectar el movimiento del mouse
        
        self.lat_g = 0.0
        self.long_g = 0.0
        self.vert_g = 0.0
        self.x_g = 0.0
        self.y_g = 0.0
        
        self.max_g = max_g # El máximo G que mostrarán los círculos

        self._label_rects = {}

    def set_max_g(self, g_value: float):
        """ Permite cambiar el G máximo del diagrama dinámicamente. """
        self.max_g = g_value if g_value > 0 else 1.0
        self.update()
        
    def update_g_forces(self, lat_g: float, long_g: float, vert_g: float, yaw_radians: float):
        """ Actualiza los valores de G y solicita un redibujado. """
        #print(f"Updating G-Forces: Lat={lat_g}, Long={long_g}")
        self.lat_g = lat_g
        self.long_g = long_g
        self.vert_g = vert_g

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

        # --- DIBUJAR ETIQUETAS ---
        font = QFont("Arial", 7); font.setBold(True); painter.setFont(font)
        metrics = painter.fontMetrics()
        
        # Diccionario con la configuración de cada etiqueta
        labels_to_draw = {
            'Long': {'text': f"{self.long_g:.2f} G", 'color': QColor(150, 0, 0), 'pos': 'top_center'},
            'Lat':  {'text': f"{self.lat_g:.2f} G",  'color': QColor(150, 0, 0), 'pos': 'mid_right'},
            'Total':{'text': f"{np.sqrt(self.x_g**2 + self.y_g**2):.2f} G", 'color': QColor(0, 150, 150), 'pos': 'top_right'},
            'Vert': {'text': f"{self.vert_g:.2f} G",   'color': QColor(0, 120, 0),   'pos': 'bottom_left'} # NUEVA ETIQUETA
        }

        self._label_rects.clear() # Limpiamos los rectángulos anteriores
        painter.setPen(QColor(255, 255, 255))
        
        for name, data in labels_to_draw.items():
            text_rect = metrics.boundingRect(data['text'])
            bubble_rect = QRectF(0, 0, text_rect.width() + 10, text_rect.height() + 4)
            
            if data['pos'] == 'top_center':
                bubble_rect.moveCenter(QPointF(center.x(), 5 + bubble_rect.height()/2))
            elif data['pos'] == 'mid_right':
                bubble_rect.moveCenter(QPointF(w - 5 - bubble_rect.width()/2, center.y()))
            elif data['pos'] == 'bottom_left':
                bubble_rect.moveBottomLeft(QPointF(5, h - 5))
            elif data['pos'] == 'top_right':
                bubble_rect.moveTopRight(QPointF(w - 10, 10))

            painter.setBrush(data['color'])
            painter.drawRoundedRect(bubble_rect, 4, 4)
            painter.drawText(bubble_rect, Qt.AlignCenter, data['text'])
            self._label_rects[name] = bubble_rect # Guardamos el rectángulo para el tooltip
    
    def mouseMoveEvent(self, event):
        """ Se activa cuando el mouse se mueve sobre el widget. """
        tooltip_texts = {
            'Long': 'Aceleración Longitudinal (Frenada / Aceleración)',
            'Lat': 'Aceleración Lateral (Fuerzas en Curva)',
            'Total': 'Magnitud Total de la Aceleración Horizontal',
            'Vert': 'Aceleración Vertical (Baches, Compresión)'
        }
        
        for name, rect in self._label_rects.items():
            if rect.contains(event.pos()):
                QToolTip.showText(QCursor.pos(), tooltip_texts.get(name, ""), self)
                return
        
        QToolTip.hideText() # Ocultar si no está sobre ninguna etiqueta

    def leaveEvent(self, event):
        """ Se activa cuando el mouse abandona el widget. """
        QToolTip.hideText()