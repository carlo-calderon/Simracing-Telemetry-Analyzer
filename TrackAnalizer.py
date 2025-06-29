import os
import numpy as np
from PySide6.QtWidgets import (QApplication, QMainWindow, QFileDialog, QToolBar, QComboBox, QLabel, QProgressDialog)
from PySide6.QtGui import QAction
from PySide6.QtCore import Qt, QSettings
from matplotlib import cm

from TelemetrySession import TelemetrySession
from RangeSlider import QRangeSlider
from TrackViewer import TrackWidget  # Asegúrate de que TrackWidget esté en TrackViewer.py

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Visor de Telemetría iRacing")
        self.setGeometry(100, 100, 1200, 900)
        self.dataframe = None # MainWindow es la dueña del dataframe

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

        # 3. Enviar datos al widget para que se dibuje
        self.track_widget.setData(vertices, colors, track_bbox)

        # Restaurar zoom y paneo
        self.track_widget.pan_x = pan_x
        self.track_widget.pan_y = pan_y
        self.track_widget.zoom = zoom
        self.track_widget.update()