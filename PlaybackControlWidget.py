# -*- coding: utf-8 -*-
"""
File: PlaybackControlWidget.py
Created on 2025-07-05
@author: Carlo Calderón Becerra
@company: CarcaldeF1
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QSlider, QStyle
from PySide6.QtCore import Qt, QTimer, Signal
import pandas as pd

from TireTempWidget import TireTempWidget

class PlaybackControlWidget(QWidget):
    # Señal que emitirá el índice del frame/tick actual cada vez que cambie
    tick_changed = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        
        # --- Estado Interno ---
        self.dataframe = None
        self._is_playing = False
        self._current_tick = 0
        self._total_ticks = 0

        # --- Temporizador para la reproducción ---
        self.timer = QTimer(self)
        self.timer.setInterval(16) # ~60 FPS (1000ms / 60 = 16.6)
        self.timer.timeout.connect(self._advance_tick)

        # --- Creación de Widgets ---
        self.tire_temp_widget = TireTempWidget(self)
        
        self.play_pause_button = QPushButton()
        self.play_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay)
        self.pause_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPause)
        self.play_pause_button.setIcon(self.play_icon)
        
        self.stop_button = QPushButton()
        self.stop_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaStop))

        self.playback_slider = QSlider(Qt.Horizontal)

        # --- Layout ---
        main_layout = QVBoxLayout(self)
        controls_layout = QHBoxLayout()

        controls_layout.addWidget(self.play_pause_button)
        controls_layout.addWidget(self.stop_button)
        controls_layout.addWidget(self.playback_slider)
        
        main_layout.addWidget(self.tire_temp_widget)
        main_layout.addLayout(controls_layout)

        # --- Conexiones de Señales ---
        self.play_pause_button.clicked.connect(self.toggle_playback)
        self.stop_button.clicked.connect(self.stop_playback)
        self.playback_slider.valueChanged.connect(self.scrub_to_tick)

    def set_data(self, df: pd.DataFrame):
        """ Recibe el dataframe completo para la reproducción. """
        self.stop_playback() # Detiene cualquier reproducción anterior
        self.dataframe = df
        if self.dataframe is not None and not self.dataframe.empty:
            self._total_ticks = len(self.dataframe) - 1
            self.playback_slider.setRange(0, self._total_ticks)
            self.tire_temp_widget.set_temp_range_from_dataframe(df)  # <-- Aquí está el cambio
        else:
            self._total_ticks = 0
            self.playback_slider.setRange(0, 0)

    def toggle_playback(self):
        """ Inicia o pausa la reproducción. """
        if self._is_playing:
            self.timer.stop()
            self.play_pause_button.setIcon(self.play_icon)
        else:
            self.timer.start()
            self.play_pause_button.setIcon(self.pause_icon)
        self._is_playing = not self._is_playing

    def stop_playback(self):
        """ Detiene la reproducción y vuelve al inicio. """
        if self.timer.isActive():
            self.timer.stop()
        self._is_playing = False
        self._current_tick = 0
        self.play_pause_button.setIcon(self.play_icon)
        self.playback_slider.setValue(0)
        self._update_display(0)

    def _advance_tick(self):
        """ Avanza un tick en la línea de tiempo. """
        if self._current_tick < self._total_ticks:
            self._current_tick += 1
            # Actualizamos el slider sin emitir su propia señal para evitar un bucle
            self.playback_slider.blockSignals(True)
            self.playback_slider.setValue(self._current_tick)
            self.playback_slider.blockSignals(False)
            self._update_display(self._current_tick)
        else:
            self.stop_playback()

    def scrub_to_tick(self, tick):
        """ Se activa cuando el usuario arrastra el slider. """
        if not self.timer.isActive(): # Solo permite arrastrar si está en pausa
            self._current_tick = tick
            self._update_display(tick)

    def _update_display(self, tick):
        """
        Actualiza los widgets visuales (TireTemp) con los datos del tick actual.
        """
        if self.dataframe is not None and 0 <= tick < len(self.dataframe):
            current_data_row = self.dataframe.iloc[tick]
            
            temp_cols = [
                'LFtempL', 'LFtempM', 'LFtempR', 'RFtempL', 'RFtempM', 'RFtempR',
                'LRtempL', 'LRtempM', 'LRtempR', 'RRtempL', 'RRtempM', 'RRtempR'
            ]
            temps_dict = {col: current_data_row[col] for col in temp_cols if col in current_data_row}
            
            if temps_dict:
                self.tire_temp_widget.update_temperatures(temps_dict)
            
            # Emitimos la señal para que otros widgets (como el mapa) puedan reaccionar
            self.tick_changed.emit(tick)