import os
import numpy as np
from PySide6.QtWidgets import (QApplication, QMainWindow, QFileDialog, QToolBar, QComboBox, QLabel, QProgressDialog, QStatusBar)
from PySide6.QtGui import QAction, QIcon
from PySide6.QtCore import Qt, QSettings
from matplotlib import cm
import requests
from PySide6.QtGui import QImage, QPixmap, QPainter
import math

from TelemetrySession import TelemetrySession
from RangeSlider import QRangeSlider
from TrackViewer import TrackWidget  # Asegúrate de que TrackWidget esté en TrackViewer.py

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Visor de Telemetría iRacing")
        self.setGeometry(100, 100, 1200, 900)
        self.dataframe = None # MainWindow es la dueña del dataframe
        self.ZOOM = 18  # Zoom por defecto para las teselas del mapa

        # Creamos nuestro widget de OpenGL y lo ponemos como widget central
        self.track_widget = TrackWidget(self)
        self.setCentralWidget(self.track_widget)

        # Barra de herramientas
        self.toolbar = QToolBar("Herramientas", self)
        self.addToolBar(self.toolbar)

        # ComboBox para seleccionar la columna de color
        self.color_combo = QComboBox(self)
        self.color_combo.setToolTip("Columna para colorear los puntos")
        self.color_combo.currentTextChanged.connect(self.on_color_column_changed)
        self.toolbar.addWidget(self.color_combo)

        # Controles para el rango de colores
        self.toolbar.addSeparator()
        self.min_value_label = QLabel("Min: N/A")
        self.range_slider = QRangeSlider(self)
        self.max_value_label = QLabel("Max: N/A")
        self.toolbar.addWidget(self.min_value_label)
        self.toolbar.addWidget(self.range_slider)
        self.toolbar.addWidget(self.max_value_label)
        self.range_slider.rangeChanged.connect(self.on_range_changed)

        # Configuración para archivos recientes
        self.settings = QSettings("MiEmpresa", "SimracingTelemetryAnalyzer")
        self.recent_file_actions = []
        self.max_recent_files = 5

        # Creamos una barra de menú
        menu_bar = self.menuBar()
        self.file_menu = menu_bar.addMenu("&Archivo")

        # Creamos una acción para abrir archivos
        open_action = QAction("&Abrir archivo .ibt...", self)
        open_action.triggered.connect(self.open_file_dialog)
        self.file_menu.addAction(open_action)

        # Separador y espacio para archivos recientes
        self.file_menu.addSeparator()
        for i in range(self.max_recent_files):
            action = QAction(self)
            action.setVisible(False)
            action.triggered.connect(self.open_recent_file)
            self.recent_file_actions.append(action)
            self.file_menu.addAction(action)

        # Botón toggle para mostrar/ocultar fondo de mapa
        self.show_map_action = QAction(QIcon("google_maps.png"), "Cargar fondo", self)
        self.show_map_action.setCheckable(True)
        self.show_map_action.setChecked(False)
        self.show_map_action.toggled.connect(self.on_toggle_map_background)
        self.toolbar.addAction(self.show_map_action)

        self.Maps_API_KEY = "AIzaSyBwn0dzu6ae97g4W3ArNRAHLr-cqOvlrUQ"  # Reemplaza con tu clave de API de Google Maps
        
        self.map_image_cache = None  # Para guardar la imagen descargada
        self.map_bbox_cache = None   # Para saber si el bbox cambió

        # Status bar para mostrar coordenadas
        self.statusbar = QStatusBar(self)
        self.setStatusBar(self.statusbar)
        self.coord_label = QLabel("Lon: -, Lat: -")
        self.statusbar.addPermanentWidget(self.coord_label)

        self.track_widget.mouse_coord_changed.connect(self.update_statusbar_coords)

        self.update_recent_files_menu()
    
    def open_file_dialog(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Abrir archivo de Telemetría", "", "iRacing Telemetry Files (*.ibt)")
        if file_name:
            self.load_file(file_name)

    def load_file(self, file_name):
        print(f"Abriendo archivo: {file_name}")

        progress_dialog = QProgressDialog("Cargando telemetría...", "Cancelar", 0, 0, self)
        progress_dialog.setWindowModality(Qt.WindowModal)
        progress_dialog.setMinimumDuration(0)
        progress_dialog.setValue(0)
        progress_dialog.show()

        QApplication.processEvents()

        try:
            session = TelemetrySession(file_name)
            if not session.dataframe.empty:
                session.filter_driving_columns()
                self.dataframe = session.dataframe

                # Llenar el combo con columnas numéricas
                numeric_cols = self.dataframe.select_dtypes(include=[np.number]).columns.tolist()
                self.color_combo.clear()
                self.color_combo.addItems(numeric_cols)

                # Seleccionar 'Speed' si existe
                if 'Speed' in numeric_cols:
                    self.color_combo.setCurrentText('Speed')
                self.add_to_recent_files(file_name)
            else:
                print("Error: No se cargaron datos de telemetría.")
        except Exception as e:
            print(f"Error durante la carga: {e}")
        finally:
            progress_dialog.cancel()
            del progress_dialog

    def add_to_recent_files(self, file_name):
        files = self.settings.value("recentFiles", [], type=list)
        try:
            files.remove(file_name)
        except ValueError:
            pass
        files.insert(0, file_name)
        del files[self.max_recent_files:]
        self.settings.setValue("recentFiles", files)
        self.update_recent_files_menu()

    def update_recent_files_menu(self):
        files = self.settings.value("recentFiles", [], type=list)
        num_recent_files = min(len(files), self.max_recent_files)
        for i in range(num_recent_files):
            text = f"&{i + 1} {os.path.basename(files[i])}"
            self.recent_file_actions[i].setText(text)
            self.recent_file_actions[i].setData(files[i])
            self.recent_file_actions[i].setVisible(True)
        for i in range(num_recent_files, self.max_recent_files):
            self.recent_file_actions[i].setVisible(False)

    def open_recent_file(self):
        action = self.sender()
        if action:
            self.load_file(action.data())

    def on_color_column_changed(self, column_name):
        """Callback cuando el usuario cambia la columna de color."""
        if column_name and self.dataframe is not None:
            self.update_color_controls()

    def on_range_changed(self, low, high):
        """Callback cuando el usuario mueve el QRangeSlider."""
        if self.dataframe is not None:
            self.min_value_label.setText(f"Min: {low:.2f}")
            self.max_value_label.setText(f"Max: {high:.2f}")
            self.process_and_update_track()

    def update_color_controls(self):
        """Actualiza el slider y las etiquetas para la columna de color actual."""
        df = self.dataframe
        column_name = self.color_combo.currentText()
        if df is not None and column_name in df.columns:
            min_val = df[column_name].min()
            max_val = df[column_name].max()

            self.range_slider.blockSignals(True)
            self.range_slider.setRange(min_val, max_val)
            self.range_slider.setValues(min_val, max_val)
            self.range_slider.blockSignals(False)

            # Llama a on_range_changed para actualizar las etiquetas y dibujar la pista por primera vez
            self.on_range_changed(min_val, max_val)

    def on_toggle_map_background(self, checked):
        """Muestra u oculta el fondo de mapa satelital."""
        if checked:
            # Solo descarga si no está en caché o el bbox cambió
            if self.map_image_cache is None or self.map_bbox_cache != self.current_bbox():
                bbox = self.current_bbox()
                if bbox is not None:
                    self.map_image_cache = self.fetch_map_tiles_and_stitch(bbox, self.ZOOM)
                    self.map_bbox_cache = bbox
            # Actualiza el fondo en el widget
            self.track_widget.set_background_image(self.map_image_cache)
        else:
            self.track_widget.set_background_image(None)
        self.track_widget.update()

    def current_bbox(self):
        """Devuelve el bounding box actual de la pista."""
        if self.dataframe is not None and not self.dataframe.empty:
            lon = self.dataframe['Lon'].to_numpy()
            lat = self.dataframe['Lat'].to_numpy()
            return {'min_lon': lon.min(), 'max_lon': lon.max(), 'min_lat': lat.min(), 'max_lat': lat.max()}
        return None

    def process_and_update_track(self):
        """
        Procesa el dataframe actual basado en los controles de la UI y envía los datos al TrackWidget.
        """
        df = self.dataframe
        column_name = self.color_combo.currentText()
        if df is None or df.empty or not column_name:
            self.track_widget.setData(None, None, None)
            return

        # Obtener el rango del slider
        vmin = self.range_slider._low_val
        vmax = self.range_slider._high_val

        # Guardar zoom y paneo actuales
        pan_x = self.track_widget.pan_x
        pan_y = self.track_widget.pan_y
        zoom = self.track_widget.zoom

        # 1. Preparar vértices y bounding box
        lon = df['Lon'].to_numpy()
        lat = df['Lat'].to_numpy()
        vertices = np.vstack((lon, lat)).T.flatten()
        track_bbox = {'min_lon': lon.min(), 'max_lon': lon.max(), 'min_lat': lat.min(), 'max_lat': lat.max()}

        # 2. Preparar colores
        values = df[column_name].to_numpy()
        norm_values = (values - vmin) / (vmax - vmin) if vmax > vmin else np.zeros_like(values)
        norm_values = np.clip(norm_values, 0, 1)
        colors = cm.RdYlGn(norm_values)

        # 3. No descargues el fondo aquí, solo pásalo si está activo
        map_image = self.map_image_cache if self.show_map_action.isChecked() else None
        self.track_widget.setData(vertices, colors, track_bbox, map_image)

        # Restaurar zoom y paneo
        self.track_widget.pan_x = pan_x
        self.track_widget.pan_y = pan_y
        self.track_widget.zoom = zoom
        self.track_widget.update()

    def deg2num(self, lat_deg, lon_deg, zoom):
        """ Convierte coordenadas geográficas a coordenadas de tesela de Google. """
        lat_rad = math.radians(lat_deg)
        n = 2.0 ** zoom
        xtile = int((lon_deg + 180.0) / 360.0 * n)
        ytile = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
        return (xtile, ytile)
    
   
    def fetch_map_tiles_and_stitch(self, bbox, zoom):
        """
        Calcula las teselas necesarias, las descarga y las une en una sola imagen.
        """
        if not self.Maps_API_KEY or self.Maps_API_KEY == "TU_CLAVE_DE_API_AQUI":
            print("ADVERTENCIA: No se ha configurado una clave de API de Google Maps.")
            return None

        # 1. Calcular el rango de teselas necesarias
        top_left_x, top_left_y = self.deg2num(bbox['max_lat'], bbox['min_lon'], zoom)
        bottom_right_x, bottom_right_y = self.deg2num(bbox['min_lat'], bbox['max_lon'], zoom)
        
        # El rango de teselas a descargar
        x_min, x_max = top_left_x, bottom_right_x
        y_min, y_max = top_left_y, bottom_right_y
        
        num_tiles_x = (x_max - x_min) + 1
        num_tiles_y = (y_max - y_min) + 1
        
        print(f"INFO: Se descargarán {num_tiles_x * num_tiles_y} teselas ({num_tiles_x}x{num_tiles_y}) para el zoom {zoom}.")

        # 2. Crear el lienzo final para unir las imágenes
        tile_size = 256  # Google usa teselas de 256x256
        stitched_image = QImage(num_tiles_x * tile_size, num_tiles_y * tile_size, QImage.Format_RGB888)
        painter = QPainter(stitched_image)

        # Barra de progreso para la descarga
        progress = QProgressDialog("Descargando teselas del mapa...", "Cancelar", 0, num_tiles_x * num_tiles_y, self)
        progress.setWindowModality(Qt.WindowModal)
        progress.setValue(0)
        
        # 3. Descargar y pegar cada tesela
        count = 0
        for x in range(x_min, x_max + 1):
            for y in range(y_min, y_max + 1):
                if progress.wasCanceled():
                    painter.end()
                    return None

                progress.setValue(count)
                QApplication.processEvents() # Actualizar la UI
                
                # URL de la API de Teselas de Google
                tile_url = f"https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={zoom}&key={self.Maps_API_KEY}"
                
                try:
                    response = requests.get(tile_url, stream=True)
                    response.raise_for_status()
                    tile_image = QImage()
                    tile_image.loadFromData(response.content)
                    
                    # Pegamos la tesela en su posición en el lienzo grande
                    px = (x - x_min) * tile_size
                    py = (y - y_min) * tile_size
                    painter.drawImage(px, py, tile_image)
                    
                except requests.exceptions.RequestException as e:
                    print(f"ERROR: No se pudo descargar la tesela ({x},{y}): {e}")

                count += 1
        
        painter.end()
        progress.setValue(num_tiles_x * num_tiles_y)
        print("INFO: Mosaico del mapa completado.")
        return stitched_image
    
    def update_statusbar_coords(self, lon, lat):
        """
        Este es el 'slot' que recibe las coordenadas del TrackWidget y actualiza la etiqueta.
        """
        self.coord_label.setText(f"Lon: {lon:.6f}, Lat: {lat:.6f}")