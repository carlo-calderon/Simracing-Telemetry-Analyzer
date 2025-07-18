# -*- coding: utf-8 -*-
'''
File: TrackViewer.py
Created on 2025-07-02
@author: Carlo Calderón Becerra
@company: CarcaldeF1
'''

import sys
import numpy as np
import os
from PySide6.QtWidgets import (QApplication, QMainWindow, QFileDialog, QMenuBar, QToolBar, QComboBox, QLabel, QWidget)
from PySide6.QtWidgets import QProgressDialog
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtGui import QAction, QColor, QPainter, QPen, QPalette, QImage
from PySide6.QtCore import Qt, QSettings, Signal, QPoint, QRect
from OpenGL.GL import *
from matplotlib import cm 
from GLTFModel import GLTFModel

from TelemetrySession import TelemetrySession
from utils import resource_path

class TrackWidget(QOpenGLWidget):
    mouse_coord_changed = Signal(float, float)

    """
    Este widget es el lienzo de OpenGL donde dibujaremos la pista.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.vertices = None
        self.colors = None
        self.track_bbox = None
        self.map_bbox = None
        self.aspect_ratio = 1.0
        self.current_point_pos = None
        self.point_size_normal = 3.0
        self.point_size_lowlight = 1.0
        self.point_size_marker = 15.0

        # Variables para paneo y zoom
        self.pan_x = 0.0
        self.pan_y = 0.0
        self.zoom = 1.0
        self._last_mouse_pos = None

        self.map_texture_id = None
        self.map_image = None

        self.car_model = GLTFModel()        # Creamos una instancia de nuestra nueva clase
        self.current_car_pos = None     # Guardará (Lon, Lat, Alt)
        self.current_car_yaw = 0.0      # Guardará la orientación

    def reset_view(self):
        """Resetea el paneo a (0,0) y el zoom a 1.0. No provoca un redibujado."""
        self.pan_x = 0.0
        self.pan_y = 0.0
        self.zoom = 1.0

    def set_current_point(self, lon, lat, yaw):
        if lon is not None and lat is not None and yaw is not None:
            self.current_car_pos = (lon, lat)
            self.current_car_yaw = yaw
        else:
            self.current_car_pos = None
        self.update()

    def setData(self, vertices, colors, track_bbox, map_image, map_bbox):
        """
        Recibe los datos ya procesados (vértices, colores, bounding box) y los prepara para OpenGL.
        """
        self.vertices = vertices
        self.colors = colors
        self.track_bbox = track_bbox
        self.map_bbox = map_bbox     # El bbox REAL del mapa
        self.map_image = map_image

        if self.map_image:
            self.update_map_texture()

        #self.reset_view() # Reseteamos la vista al cargar nuevos datos
        self.update() # Le decimos al widget que necesita redibujarse

    def update_map_texture(self):
        """ Convierte la QImage en una textura de OpenGL. """
        if self.map_texture_id is not None:
            glDeleteTextures(1, [self.map_texture_id])
        
        self.map_texture_id = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, self.map_texture_id)

        # Convertimos la QImage a un formato que OpenGL entienda
        img = self.map_image.convertToFormat(QImage.Format.Format_RGBA8888)
        ptr = img.bits()
        
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, img.width(), img.height(), 0, GL_RGBA, GL_UNSIGNED_BYTE, ptr)
        
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glBindTexture(GL_TEXTURE_2D, 0)

    def initializeGL(self):
        """ Se llama una sola vez al crear el widget. Prepara el estado de OpenGL. """
        glClearColor(0.1, 0.1, 0.15, 1.0)  # Fondo gris oscuro
        glEnable(GL_POINT_SMOOTH)
        glPointSize(3.0)
        glEnable(GL_TEXTURE_2D)

        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        asset_filename = resource_path('./assets/formula_car.glb')
        #asset_filename = resource_path('./assets/scene.gltf')
        if self.car_model.load(asset_filename, rotation_xyz_degrees=(90, -90, 0), base_scale=0.0005):
            self.car_model.initGL()

    def resizeGL(self, w, h):
        """ Se llama cada vez que la ventana cambia de tamaño. Ajusta la cámara. """
        glViewport(0, 0, w, h)
        self.aspect_ratio = w / h if h > 0 else 1.0
        self.updateProjection()

    def get_world_limits(self):
        """
        Devuelve los límites (left, right, bottom, top) del mundo visible actual,
        considerando el bounding box, aspecto, zoom y paneo.
        """
        if self.track_bbox is None:
            return None

        bbox = self.track_bbox
        track_width = bbox['max_lon'] - bbox['min_lon']
        track_height = bbox['max_lat'] - bbox['min_lat']
        track_aspect = track_width / track_height if track_height > 0 else 1.0

        margin_x = track_width * 0.05
        margin_y = track_height * 0.05

        left, right = bbox['min_lon'] - margin_x, bbox['max_lon'] + margin_x
        bottom, top = bbox['min_lat'] - margin_y, bbox['max_lat'] + margin_y

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

        cx = (left + right) / 2 + self.pan_x
        cy = (bottom + top) / 2 + self.pan_y
        width = (right - left) / self.zoom
        height = (top - bottom) / self.zoom

        left = cx - width / 2
        right = cx + width / 2
        bottom = cy - height / 2
        top = cy + height / 2

        return left, right, bottom, top

    def updateProjection(self):
        """
        Calcula la proyección ortográfica para que la pista se vea a escala
        y encaje perfectamente en la ventana, aplicando paneo y zoom.
        """
        display_bbox = self.map_bbox if self.map_bbox else self.track_bbox
        if display_bbox is None:
            return

        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()

        left, right, bottom, top = self.get_world_limits()
        glOrtho(left, right, bottom, top, -1.0, 1.0)

    def paintGL(self):
        """ El corazón del dibujado. Se llama cada vez que hay que pintar. """
        glClear(GL_COLOR_BUFFER_BIT)
        
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        self.updateProjection() # Llamamos aquí para asegurar que el zoom/pan se aplique

        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()

        self.draw_background_map()

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

        if self.current_car_pos is not None:
            glDisable(GL_TEXTURE_2D)
            glPushMatrix()
            lon, lat = self.current_car_pos
            glTranslatef(lon, lat, 0.01) # Mover
            yaw_degrees = np.degrees(self.current_car_yaw)
            glRotatef(yaw_degrees, 0, 0, 1) # Girar (eje Z para vista cenital)
#            model_scale = 0.0001
#            glScalef(model_scale, model_scale, model_scale) # Escalar
            # Simplemente le pedimos al modelo que se dibuje a sí mismo
            self.car_model.draw()
            glPopMatrix()

    def draw_background_map(self):
        """ Dibuja un rectángulo con la textura del mapa. """
        if self.map_texture_id is None or self.map_bbox  is None:
            return

        glEnable(GL_TEXTURE_2D)
        glColor4f(1.0, 1.0, 1.0, 1.0) # Color blanco para no teñir la textura
        glBindTexture(GL_TEXTURE_2D, self.map_texture_id)
        
        bbox = self.map_bbox # Usamos el bbox REAL del mapa
        
        # Dibujamos un quad (rectángulo) usando las coordenadas del bounding box
        glBegin(GL_QUADS)
        glTexCoord2f(0, 1); glVertex2f(bbox['min_lon'], bbox['min_lat']) # Abajo-Izquierda
        glTexCoord2f(1, 1); glVertex2f(bbox['max_lon'], bbox['min_lat']) # Abajo-Derecha
        glTexCoord2f(1, 0); glVertex2f(bbox['max_lon'], bbox['max_lat']) # Arriba-Derecha
        glTexCoord2f(0, 0); glVertex2f(bbox['min_lon'], bbox['max_lat']) # Arriba-Izquierda
        glEnd()

        glBindTexture(GL_TEXTURE_2D, 0)
        glDisable(GL_TEXTURE_2D)

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

        # Calcular lon/lat bajo el mouse SIEMPRE que se mueve el mouse
        if self.track_bbox:
            left, right, bottom, top = self.get_world_limits()
            mx = event.x() / self.width()
            my = 1.0 - event.y() / self.height()
            lon = left + mx * (right - left)
            lat = bottom + my * (top - bottom)
            self.mouse_coord_changed.emit(lon, lat)

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

    def set_background_image(self, image):
        """
        Recibe una nueva imagen de fondo y fuerza la actualización de la textura de OpenGL.
        """
        self.map_image = image

        if self.map_image:
            # Si recibimos una imagen válida, le decimos a OpenGL que la procese.
            self.update_map_texture()
        else:
            # Si recibimos None (para ocultar el mapa), borramos la textura existente.
            if self.map_texture_id is not None:
                glDeleteTextures(1, [self.map_texture_id])
                self.map_texture_id = None

    def get_view_state(self):
        return self.pan_x, self.pan_y, self.zoom

    def set_view_state(self, pan_x, pan_y, zoom):
        self.pan_x = pan_x
        self.pan_y = pan_y
        self.zoom = zoom