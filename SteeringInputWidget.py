# -*- coding: utf-8 -*-
"""
File: SteeringInputWidget.py
Created on 2025-07-06
@author: Carlo Calderón Becerra
@company: CarcaldeF1
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QProgressBar, QLabel
from PySide6.QtGui import QPixmap, QTransform
from PySide6.QtCore import Qt

class SteeringInputWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # --- Cargar la imagen original del volante ---
        self.original_steering_wheel_pixmap = QPixmap('./icons/steering_wheel.png')
        self.steering_wheel_label = QLabel()
        self.steering_wheel_label.setAlignment(Qt.AlignCenter)
        
        # --- Crear y configurar las barras de progreso para los pedales ---
        self.brake_bar = self._create_pedal_bar(is_brake=True)
        self.brake_bar.setMaximumWidth(20)  # Ajusta aquí el ancho máximo
        self.throttle_bar = self._create_pedal_bar(is_brake=False)
        self.throttle_bar.setMaximumWidth(20)  # Ajusta aquí el ancho máximo
        
        # --- Layout Principal ---
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(2)
        
        main_layout.addWidget(self.brake_bar)
        main_layout.addWidget(self.steering_wheel_label, 1) # El '1' le da más espacio al volante
        main_layout.addWidget(self.throttle_bar)
        
        # Inicializar el estado visual
        self.update_inputs(0, 0, 0)

    def _create_pedal_bar(self, is_brake: bool) -> QProgressBar:
        """Helper para crear y estilizar una barra de pedal."""
        bar = QProgressBar()
        bar.setRange(0, 100)
        bar.setValue(0)
        bar.setTextVisible(False)
        bar.setOrientation(Qt.Vertical)
        
        # Estilo CSS para las barras
        color = "#c92d39" if is_brake else "#2dc9b8" # Rojo para freno, verde-azulado para acelerador
        background_color = "#2a2a3a"
        
        bar.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid {background_color};
                border-radius: 4px;
                background-color: {background_color};
            }}
            QProgressBar::chunk {{
                background-color: {color};
                border-radius: 3px;
            }}
        """)
        return bar

    def _update_steering_wheel(self, angle_degrees: float):
        """Gira la imagen del volante según el ángulo."""
        # Creamos una transformación de rotación
        transform = QTransform().rotate(angle_degrees)
        
        # Aplicamos la transformación al pixmap original
        # Qt.SmoothTransformation asegura que la imagen se vea bien al rotar
        rotated_pixmap = self.original_steering_wheel_pixmap.transformed(transform, Qt.SmoothTransformation)
        
        # Redimensionamos el pixmap para que encaje en el label sin cambiar su tamaño
        scaled_pixmap = rotated_pixmap.scaled(self.steering_wheel_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)

        self.steering_wheel_label.setPixmap(scaled_pixmap)

    def update_inputs(self, brake: float, throttle: float, steer_angle: float):
        """
        Punto de entrada público para actualizar todos los controles.
        Los valores de freno y acelerador deben estar entre 0.0 y 1.0.
        El ángulo del volante es en grados.
        """
        self.brake_bar.setValue(int(brake * 100))
        self.throttle_bar.setValue(int(throttle * 100))
        self._update_steering_wheel(steer_angle)
        
    def resizeEvent(self, event):
        """Se asegura de que el volante se redibuje al cambiar el tamaño de la ventana."""
        super().resizeEvent(event)
        # Forzamos una actualización del volante para que se reescale correctamente
        self._update_steering_wheel(0) # Aquí podrías guardar el último ángulo si lo prefieres