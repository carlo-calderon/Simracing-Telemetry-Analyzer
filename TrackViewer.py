# TrackViewer.py
import sys
import numpy as np
from PySide6.QtWidgets import (QApplication, QMainWindow, QFileDialog, QMenuBar)
from PySide6.QtWidgets import QProgressDialog
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtGui import QAction, QColor
from PySide6.QtCore import Qt
from OpenGL.GL import *
from matplotlib import cm  # Usaremos matplotlib para los mapas de colores

from TelemetrySession import TelemetrySession

class TrackWidget(QOpenGLWidget):
    """
    Este widget es el lienzo de OpenGL donde dibujaremos la pista.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.dataframe = None
        self.vertices = None
        self.colors = None
        self.track_bbox = None
        self.aspect_ratio = 1.0

        # Variables para paneo y zoom
        self.pan_x = 0.0
        self.pan_y = 0.0
        self.zoom = 1.0
        self._last_mouse_pos = None

    def setData(self, dataframe):
        """
        Recibe el DataFrame, lo procesa y prepara los datos para OpenGL.
        """
        if dataframe is None or dataframe.empty or 'Lon' not in dataframe.columns or 'Lat' not in dataframe.columns:
            return

        self.dataframe = dataframe

        # 1. Extraer coordenadas y calcular el bounding box (caja contenedora) de la pista
        lon = self.dataframe['Lon'].to_numpy()
        lat = self.dataframe['Lat'].to_numpy()
        self.track_bbox = {
            'min_lon': lon.min(), 'max_lon': lon.max(),
            'min_lat': lat.min(), 'max_lat': lat.max()
        }

        # 2. Preparar los vértices para OpenGL (array de puntos [x1, y1, x2, y2, ...])
        # Usamos Lon para X y Lat para Y.
        self.vertices = np.vstack((lon, lat)).T.flatten()

        # 3. Mapear la velocidad a un color
        speed = self.dataframe['Speed'].to_numpy()
        # Normalizamos la velocidad (0.0 a 1.0) para poder aplicarle un mapa de color
        norm_speed = (speed - speed.min()) / (speed.max() - speed.min())
        
        # Usamos el mapa de colores "plasma" de matplotlib. Azul=lento, Amarillo=rápido.
        # Obtenemos un array de colores RGBA (Rojo, Verde, Azul, Alpha)
        self.colors = cm.plasma(norm_speed)

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
            glDrawArrays(GL_POINTS, 0, len(self.dataframe))

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


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Visor de Telemetría iRacing")
        self.setGeometry(100, 100, 1200, 900)

        # Creamos nuestro widget de OpenGL y lo ponemos como widget central
        self.track_widget = TrackWidget(self)
        self.setCentralWidget(self.track_widget)

        # Creamos una barra de menú
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("&Archivo")

        # Creamos una acción para abrir archivos
        open_action = QAction("&Abrir archivo .ibt...", self)
        open_action.triggered.connect(self.open_file_dialog)
        file_menu.addAction(open_action)
    
    def open_file_dialog(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Abrir archivo de Telemetría", "", "iRacing Telemetry Files (*.ibt)")
        if file_name:
            print(f"Abriendo archivo: {file_name}")

            # Creamos un diálogo de progreso bloqueante
            progress_dialog = QProgressDialog("Cargando telemetría...", "Cancelar", 0, 0, self)  # 0, 0 indica rango indefinido
            progress_dialog.setWindowModality(Qt.WindowModal)  # Hace el diálogo bloqueante
            progress_dialog.setMinimumDuration(0)  # Muestra el diálogo inmediatamente
            progress_dialog.setValue(0) # Inicializa el valor
            progress_dialog.show()

            QApplication.processEvents()  # Asegura que el diálogo se muestre antes de cargar

            try:
                session = TelemetrySession(file_name)
                if not session.dataframe.empty:
                    # Pasamos el dataframe filtrado a nuestro widget
                    session.filter_driving_columns()
                    self.track_widget.setData(session.dataframe)
                else:
                    print("Error: No se cargaron datos de telemetría.")
            except Exception as e:
                print(f"Error durante la carga: {e}")
            finally:
                progress_dialog.cancel()  # Cierra el diálogo al finalizar, incluso si hubo un error
                del progress_dialog # Limpia la memoria