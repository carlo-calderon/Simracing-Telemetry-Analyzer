# TrackViewer.py
import sys
import numpy as np
import os
from PySide6.QtWidgets import (QApplication, QMainWindow, QFileDialog, QMenuBar, QToolBar, QComboBox, QLabel, QWidget)
from PySide6.QtWidgets import QProgressDialog
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtGui import QAction, QColor, QPainter, QPen, QPalette
from PySide6.QtCore import Qt, QSettings, Signal, QPoint, QRect
from OpenGL.GL import *
from matplotlib import cm  # Usaremos matplotlib para los mapas de colores

from TelemetrySession import TelemetrySession

class TrackWidget(QOpenGLWidget):
    """
    Este widget es el lienzo de OpenGL donde dibujaremos la pista.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.vertices = None
        self.colors = None
        self.track_bbox = None
        self.aspect_ratio = 1.0

        # Variables para paneo y zoom
        self.pan_x = 0.0
        self.pan_y = 0.0
        self.zoom = 1.0
        self._last_mouse_pos = None

    def setData(self, vertices, colors, track_bbox):
        """
        Recibe los datos ya procesados (vértices, colores, bounding box) y los prepara para OpenGL.
        """
        self.vertices = vertices
        self.colors = colors
        self.track_bbox = track_bbox
        # Reseteamos la vista al cargar nuevos datos
        self.pan_x = 0.0
        self.pan_y = 0.0
        self.zoom = 1.0
        self.update() # Le decimos al widget que necesita redibujarse

    def initializeGL(self):
        """ Se llama una sola vez al crear el widget. Prepara el estado de OpenGL. """
        glClearColor(0.1, 0.1, 0.15, 1.0)  # Fondo gris oscuro
        glEnable(GL_POINT_SMOOTH)
        glPointSize(3.0)

    def resizeGL(self, w, h):
        """ Se llama cada vez que la ventana cambia de tamaño. Ajusta la cámara. """
        glViewport(0, 0, w, h)
        self.aspect_ratio = w / h if h > 0 else 1.0
        self.updateProjection()

    def updateProjection(self):
        """
        Calcula la proyección ortográfica para que la pista se vea a escala
        y encaje perfectamente en la ventana, aplicando paneo y zoom.
        """
        if self.track_bbox is None:
            return

        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()

        bbox = self.track_bbox
        track_width = bbox['max_lon'] - bbox['min_lon']
        track_height = bbox['max_lat'] - bbox['min_lat']
        track_aspect = track_width / track_height if track_height > 0 else 1.0

        # Agregamos un pequeño margen
        margin_x = track_width * 0.05
        margin_y = track_height * 0.05

        left, right = bbox['min_lon'] - margin_x, bbox['max_lon'] + margin_x
        bottom, top = bbox['min_lat'] - margin_y, bbox['max_lat'] + margin_y

        # --- Lógica para mantener la escala correcta (evitar que la pista se estire) ---
        if self.aspect_ratio > track_aspect:
            # La ventana es más ancha que la pista, ajustamos el ancho
            center_x = (left + right) / 2
            new_width = (top - bottom) * self.aspect_ratio
            left = center_x - new_width / 2
            right = center_x + new_width / 2
        else:
            # La ventana es más alta que la pista, ajustamos el alto
            center_y = (bottom + top) / 2
            new_height = (right - left) / self.aspect_ratio
            bottom = center_y - new_height / 2
            top = center_y + new_height / 2

        # Aplicar zoom (centrado en el centro de la vista)
        cx = (left + right) / 2 + self.pan_x
        cy = (bottom + top) / 2 + self.pan_y
        width = (right - left) / self.zoom
        height = (top - bottom) / self.zoom

        left = cx - width / 2
        right = cx + width / 2
        bottom = cy - height / 2
        top = cy + height / 2

        glOrtho(left, right, bottom, top, -1.0, 1.0)

    def paintGL(self):
        """ El corazón del dibujado. Se llama cada vez que hay que pintar. """
        glClear(GL_COLOR_BUFFER_BIT)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        
        self.updateProjection() # Recalculamos la proyección por si los datos cambiaron

        if self.vertices is not None and self.colors is not None:
            glEnableClientState(GL_VERTEX_ARRAY)
            glEnableClientState(GL_COLOR_ARRAY)

            # Apuntamos a nuestros arrays de datos
            glVertexPointer(2, GL_DOUBLE, 0, self.vertices)
            glColorPointer(4, GL_FLOAT, 0, self.colors)
            
            # Dibujamos todos los puntos de una sola vez (muy eficiente)
            glDrawArrays(GL_POINTS, 0, len(self.vertices) // 2)

            glDisableClientState(GL_COLOR_ARRAY)
            glDisableClientState(GL_VERTEX_ARRAY)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._last_mouse_pos = event.pos()

    def mouseMoveEvent(self, event):
        if self._last_mouse_pos is not None and event.buttons() & Qt.LeftButton:
            dx = event.x() - self._last_mouse_pos.x()
            dy = event.y() - self._last_mouse_pos.y()

            # Convertir desplazamiento de píxeles a unidades del mundo
            if self.track_bbox:
                bbox = self.track_bbox
                track_width = bbox['max_lon'] - bbox['min_lon']
                track_height = bbox['max_lat'] - bbox['min_lat']
                track_aspect = track_width / track_height if track_height > 0 else 1.0
                margin_x = track_width * 0.05
                margin_y = track_height * 0.05

                left, right = bbox['min_lon'] - margin_x, bbox['max_lon'] + margin_x
                bottom, top = bbox['min_lat'] - margin_y, bbox['max_lat'] + margin_y

                # Mantener la escala correcta (igual que en updateProjection)
                if self.aspect_ratio > track_aspect:
                    center_x = (left + right) / 2
                    new_width = (top - bottom) * self.aspect_ratio
                    left = center_x - new_width / 2
                    right = center_x + new_width / 2
                else:
                    center_y = (bottom + top) / 2
                    new_height = (right - left) / self.aspect_ratio
                    bottom = center_y - new_height / 2
                    top = center_y + new_height / 2

                width = (right - left) / self.zoom
                height = (top - bottom) / self.zoom

                self.pan_x -= dx * width / self.width()
                self.pan_y += dy * height / self.height()

            self._last_mouse_pos = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._last_mouse_pos = None

    def wheelEvent(self, event):
        # Zoom centrado en el cursor
        delta = event.angleDelta().y()
        factor = 1.15 if delta > 0 else 1/1.15
        old_zoom = self.zoom
        self.zoom *= factor
        self.zoom = max(0.1, min(self.zoom, 100))

        # Opcional: mantener el punto bajo el cursor fijo al hacer zoom
        if self.track_bbox and self._last_mouse_pos is not None:
            bbox = self.track_bbox
            width = (bbox['max_lon'] - bbox['min_lon']) * 1.1 / old_zoom
            height = (bbox['max_lat'] - bbox['min_lat']) * 1.1 / old_zoom
            mx = self._last_mouse_pos.x() / self.width()
            my = 1.0 - self._last_mouse_pos.y() / self.height()
            world_x = (bbox['min_lon'] - width * 0.05) + mx * width + self.pan_x
            world_y = (bbox['min_lat'] - height * 0.05) + my * height + self.pan_y

            width_new = width * old_zoom / self.zoom
            height_new = height * old_zoom / self.zoom
            new_world_x = (bbox['min_lon'] - width_new * 0.05) + mx * width_new + self.pan_x
            new_world_y = (bbox['min_lat'] - height_new * 0.05) + my * height_new + self.pan_y

            self.pan_x += world_x - new_world_x
            self.pan_y += world_y - new_world_y

        self.update()
