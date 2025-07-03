# -*- coding: utf-8 -*-
'''
File: TrackAnalizer.py
Created on 2025-06-29
@author: Carlo Calderón Becerra
@company: CarcaldeF1
'''

import os
import numpy as np
from PySide6.QtWidgets import (QApplication, QMainWindow, QFileDialog, QToolBar, QComboBox, QLabel,
                               QProgressDialog, QStatusBar, QStyle, QDockWidget, QWidget, QVBoxLayout)
from PySide6.QtGui import QAction, QIcon, QColor
from PySide6.QtCore import Qt, QSettings
from matplotlib import cm
import requests
from PySide6.QtGui import QImage, QPixmap, QPainter
import math

from TelemetrySession import TelemetrySession
from RangeSlider import QRangeSlider
from TrackViewer import TrackWidget
from LapsTimeTable import LapsTimeTable

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Simracing Telemetry Analizer")
        self.setGeometry(100, 100, 1200, 900)
        self.session = None  # Inicializamos la sesión de telemetría
        self.ZOOM = 18  # Zoom por defecto para las teselas del mapa

        self.show_low_range = True
        self.show_high_range = True

        # Creamos nuestro widget de OpenGL y lo ponemos como widget central
        self.track_widget = TrackWidget(self)
        self.setCentralWidget(self.track_widget)

        # Barra de herramientas
        self.toolbar = QToolBar("Herramientas", self)
        self.addToolBar(self.toolbar)
        self.color_combo = QComboBox(self)
        self.color_combo.setToolTip("Columna para colorear los puntos")
        self.color_combo.currentTextChanged.connect(self.on_color_column_changed)
        self.toolbar.addWidget(self.color_combo)

        self.toolbar.addSeparator()
        self.color_range_slider  = QRangeSlider(self, labels_visible=True)
        self.toolbar.addWidget(self.color_range_slider )

        self.color_range_slider .rangeChanged.connect(self.on_range_changed)
        self.color_range_slider .left_bar_clicked.connect(self.toggle_low_range_visibility)
        self.color_range_slider .right_bar_clicked.connect(self.toggle_high_range_visibility)

        # Configuración para archivos recientes
        self.settings = QSettings("CarcaldeF1", "SimracingTelemetryAnalyzer")
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
        self.show_map_action = QAction(QIcon("./icons/google_maps.png"), "Cargar fondo", self)
        self.show_map_action.setCheckable(True)
        self.show_map_action.setChecked(False)
        self.show_map_action.toggled.connect(self.on_toggle_map_background)
        self.toolbar.addAction(self.show_map_action)

        # Botón para resetear la vista del mapa
        self.toolbar.addSeparator()
        reset_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload)
        self.reset_view_action = QAction(reset_icon, "Resetear Vista", self)
        self.reset_view_action.setToolTip("Reinicia el zoom y la posición del mapa")
        self.reset_view_action.triggered.connect(self.on_reset_view)
        self.toolbar.addAction(self.reset_view_action)

        # Acción Guardar como
        self.save_as_action = QAction(QIcon("./icons/save.ico"), "Guardar como CSV", self)
        self.save_as_action.setToolTip("Guardar como CSV")
        self.save_as_action.triggered.connect(self.save_as_csv)
        self.toolbar.addAction(self.save_as_action)

        self.Maps_API_KEY = "AIzaSyBwn0dzu6ae97g4W3ArNRAHLr-cqOvlrUQ"  # Reemplaza con tu clave de API de Google Maps
        
        self.map_image_cache = None  # Para guardar la imagen descargada
        self.map_bbox_cache = None   # Para saber si el bbox cambió

        # Status bar para mostrar coordenadas
        self.statusbar = QStatusBar(self)
        self.setStatusBar(self.statusbar)
        self.coord_label = QLabel("Lon: -, Lat: -")
        self.statusbar.addPermanentWidget(self.coord_label)

        self.track_widget.mouse_coord_changed.connect(self.update_statusbar_coords)

        # --- DOCK WIDGET DERECHO (PARA TIEMPOS Y DISTANCIA) ---
        self.distance_slider = QRangeSlider(self, labels_visible=False)
        self.distance_slider.setToolTip("Filtra los puntos visibles por distancia en la vuelta")
        self.distance_slider.setFixedHeight(30)
        self.distance_slider.rangeChanged.connect(self.process_and_update_track) # Conectar directamente al procesado

        self.laps_table_widget = LapsTimeTable(self)

        dock_container_widget = QWidget()
        dock_layout = QVBoxLayout(dock_container_widget)
#        dock_layout.addWidget(QLabel("Filtro por Distancia (m):")) # Etiqueta para el nuevo slider
        dock_layout.addWidget(self.distance_slider)
        dock_layout.addWidget(self.laps_table_widget)

        laps_dock_widget = QDockWidget("Tiempos por Vuelta", self)
        laps_dock_widget.setWidget(dock_container_widget)
        laps_dock_widget.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.addDockWidget(Qt.RightDockWidgetArea, laps_dock_widget)

        self.update_recent_files_menu()

        self.laps_table_widget.sector_percents = [0.25, 0.5, 0.75]  # O la lista real usada
        self.laps_table_widget.on_sector_selected = self.set_distance_slider_range

    def toggle_low_range_visibility(self):
        self.show_low_range = not self.show_low_range
        print(f"INFO: Visibilidad del rango bajo establecida a {self.show_low_range}")
        self.process_and_update_track()

    def toggle_high_range_visibility(self):
        self.show_high_range = not self.show_high_range
        print(f"INFO: Visibilidad del rango alto establecida a {self.show_high_range}")
        self.process_and_update_track()

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
            self.session = TelemetrySession(file_name)
            print(f"INFO: Cargando datos de telemetría... {self.session}")
            if not self.session.dataframe.empty:
                self.session.filter_driving_columns()
                self.session.remove_problematic_rows()
                self.dataframe = self.session.dataframe

                # Llenar el combo con columnas numéricas
                numeric_cols = self.dataframe.select_dtypes(include=[np.number]).columns.tolist()
                self.color_combo.clear()
                self.color_combo.addItems(numeric_cols)

                # Seleccionar 'Speed' si existe
                if 'Speed' in numeric_cols:
                    self.color_combo.setCurrentText('Speed')
                self.update_color_controls()

                # Actualizar la tabla de tiempos por vuelta
                if self.session.laps_df is not None:
                    self.laps_table_widget.update_data(self.session.laps_df)

                if 'LapDistPct' in self.dataframe.columns:
                    pct_min = self.dataframe['LapDistPct'].min()
                    pct_max = self.dataframe['LapDistPct'].max()
                    self.distance_slider.setRange(pct_min, pct_max)
                    self.distance_slider.setValues(pct_min, pct_max)

                self.track_widget.reset_view()
                self.add_to_recent_files(file_name)
            else:
                print("Error: No se cargaron datos de telemetría.")
        except Exception as e:
            print(f"Error durante la carga: {e}")
        finally:
            progress_dialog.cancel()
            del progress_dialog

    def save_as_csv(self):
        if hasattr(self, "session") and self.session is not None:
            file_name, _ = QFileDialog.getSaveFileName(self, "Guardar como CSV", "", "CSV Files (*.csv)")
            if file_name:
                self.session.save_to_csv(file_name)
                self.session.resumen()
        else:
            print("No hay sesión de telemetría cargada.")

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
            # self.min_value_label.setText(f"Min: {low:.2f}")
            # self.max_value_label.setText(f"Max: {high:.2f}")
            self.process_and_update_track()

    def on_reset_view(self):
        """Slot para manejar la acción de resetear la vista."""
        self.track_widget.reset_view()
        self.track_widget.update()

    def update_color_controls(self):
        """Actualiza el slider y las etiquetas para la columna de color actual."""
        df = self.dataframe
        column_name = self.color_combo.currentText()
        if df is not None and column_name in df.columns:
            min_val = df[column_name].min()
            max_val = df[column_name].max()

            # Puedes elegir la paleta según la columna si lo deseas
            colormap = cm.get_cmap('RdYlGn')  # O cualquier otra lógica
            self.color_range_slider .setColormap(colormap)

            self.color_range_slider .blockSignals(True)
            self.color_range_slider .setRange(min_val, max_val)
            self.color_range_slider .setValues(min_val, max_val)
            self.color_range_slider .blockSignals(False)

            self.on_range_changed(min_val, max_val)

    def on_toggle_map_background(self, checked):
        """Muestra u oculta el fondo de mapa satelital."""
        if checked:
            current_track_bbox = self.current_bbox()
            if current_track_bbox is not None:
                # Obtenemos la imagen Y el bbox real del mapa
                self.map_image_cache, self.map_bbox_cache = self.fetch_map_tiles_and_stitch(current_track_bbox, self.ZOOM)
                self.process_and_update_track() # Volvemos a procesar todo con el nuevo mapa
        else:
            self.map_image_cache = None
            self.map_bbox_cache = None
            self.process_and_update_track()

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
            self.track_widget.setData(None, None, None, None) 
            return

        vmin = self.color_range_slider._low_val
        vmax = self.color_range_slider._high_val
        dist_min = self.distance_slider._low_val
        dist_max = self.distance_slider._high_val

        pan_x, pan_y, zoom = self.track_widget.get_view_state()
        # 1. Preparar vértices y bounding box (esto está bien)
        lon = df['Lon'].to_numpy()
        lat = df['Lat'].to_numpy()
        vertices = np.vstack((lon, lat)).T.flatten()
        track_bbox = {'min_lon': lon.min(), 'max_lon': lon.max(), 'min_lat': lat.min(), 'max_lat': lat.max()}

        # 2. --- LÓGICA DE COLORES DINÁMICA (VERSIÓN CORREGIDA) ---
        values = df[column_name].to_numpy()
        colormap = self.color_range_slider .colormap

        # a. Normalizar los valores que están DENTRO del rango para aplicar el gradiente
        range_width = vmax - vmin if vmax > vmin else 1.0
        norm_values = (values - vmin) / range_width
        
        # b. Aplicamos el colormap a TODOS los valores normalizados. Los que están fuera del
        #    rango [0, 1] serán "fijados" a los colores de los extremos por ahora.
        colors = colormap(np.clip(norm_values, 0, 1))

        # c. Calculamos los colores atenuados para los extremos (la lógica que faltaba)
        min_palette_color = np.array(colormap(0.0))  # Color para el valor mínimo (rojo)
        max_palette_color = np.array(colormap(1.0))  # Color para el valor máximo (verde)
        black_color = np.array([0.0, 0.0, 0.0, 1.0]) # RGBA para el color negro

        # Fórmula: (2 * negro + color_paleta) / 3
        dark_min_color = (2 * black_color + min_palette_color) / 3
        dark_max_color = (2 * black_color + max_palette_color) / 3
        
        # d. Usamos "máscaras" para encontrar los puntos fuera de rango y aplicarles el color oscuro
        low_mask = values < vmin
        high_mask = values > vmax
        
        if self.show_low_range:
            colors[low_mask] = dark_min_color
            min_edge_qcolor = QColor.fromRgbF(*dark_min_color)
        else:
            colors[low_mask] = [0,0,0,0] # Hacemos los puntos transparentes
            min_edge_qcolor = QColor(80, 80, 90) # Color gris neutro para el slider
 
        if self.show_high_range:
            colors[high_mask] = dark_max_color
            max_edge_qcolor = QColor.fromRgbF(*dark_max_color)
        else:
            colors[high_mask] = [0,0,0,0] # Hacemos los puntos transparentes
            max_edge_qcolor = QColor(80, 80, 90) # Color gris neutro para el slider
        # --- FIN DE LA LÓGICA DE COLORES ---

        # 3. Actualizar el fondo del Range Slider
        self.color_range_slider .set_edge_colors(min_edge_qcolor, max_edge_qcolor)

        # Filtro de distancia en la vuelta
        if 'LapDistPct' in df.columns:
            lap_pct_values = df['LapDistPct'].to_numpy()
            distance_mask_out = (lap_pct_values < dist_min) | (lap_pct_values > dist_max)
            colors[distance_mask_out, 3] = 0

        # 4. Enviar datos al TrackWidget
        map_image = None
        map_bbox = None # Inicializamos el bbox del mapa
        if self.show_map_action.isChecked() and self.map_image_cache is not None:
             map_image = self.map_image_cache
             map_bbox = self.map_bbox_cache # Usamos el bbox del mapa cacheado

        #map_image = self.map_image_cache if self.show_map_action.isChecked() else None
        self.track_widget.setData(vertices, colors, track_bbox, map_image, map_bbox)

        # 5. Restaurar vista
        self.track_widget.set_view_state(pan_x, pan_y, zoom)
        self.track_widget.update() # Forzar un redibujado explícito

    def deg2num(self, lat_deg, lon_deg, zoom):
        """ Convierte coordenadas geográficas a coordenadas de tesela de Google. """
        lat_rad = math.radians(lat_deg)
        n = 2.0 ** zoom
        xtile = int((lon_deg + 180.0) / 360.0 * n)
        ytile = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
        return (xtile, ytile)

    def num2deg(self, xtile, ytile, zoom):
        """ Convierte coordenadas de tesela de Google a coordenadas geográficas. """
        n = 2.0 ** zoom
        lon_deg = xtile / n * 360.0 - 180.0
        lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * ytile / n)))
        lat_deg = math.degrees(lat_rad)
        return (lon_deg, lat_deg)    
   
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

        map_min_lon, map_max_lat = self.num2deg(x_min, y_min, zoom)
        map_max_lon, map_min_lat = self.num2deg(x_max + 1, y_max + 1, zoom)
        
        map_bbox = {
            'min_lon': map_min_lon, 'max_lon': map_max_lon,
            'min_lat': map_min_lat, 'max_lat': map_max_lat
        }

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
        return stitched_image, map_bbox
    
    def update_statusbar_coords(self, lon, lat):
        """
        Este es el 'slot' que recibe las coordenadas del TrackWidget y actualiza la etiqueta.
        """
        self.coord_label.setText(f"Lon: {lon:.6f}, Lat: {lat:.6f}")

    def set_distance_slider_range(self, start_pct, end_pct):
        self.distance_slider.setValues(start_pct, end_pct)
        self.process_and_update_track()
