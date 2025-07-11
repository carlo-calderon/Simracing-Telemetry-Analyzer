# -*- coding: utf-8 -*-
"""
File: SteeringInputWidget.py
Created on 2025-07-06
@author: Carlo Calderón Becerra
@company: CarcaldeF1
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QProgressBar, QLabel
from PySide6.QtGui import QPixmap, QTransform, QPainter
from PySide6.QtCore import Qt

from utils import resource_path

# --- NUEVO WIDGET INTERNO SOLO PARA DIBUJAR EL VOLANTE ---
class _SteeringWheelCanvas(QWidget):
    def __init__(self, pixmap, parent=None):
        super().__init__(parent)
        self.original_pixmap = pixmap
        self.current_angle = 0.0

    def set_angle(self, angle_degrees: float):
        """ Actualiza el ángulo y solicita un redibujado. """
        self.current_angle = angle_degrees
        self.update()

    def paintEvent(self, event):
        """ Dibuja el volante rotado y escalado correctamente. """
        if self.original_pixmap.isNull():
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        # 1. Calcular el tamaño máximo manteniendo la proporción
        #    Esto nos da un rectángulo centrado donde siempre dibujaremos.
        scaled_pixmap = self.original_pixmap.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        
        center_x = self.width() / 2
        center_y = self.height() / 2
        
        # 2. Guardamos el estado del painter, nos movemos al centro y rotamos
        painter.save()
        painter.translate(center_x, center_y)
        painter.rotate(self.current_angle)
        
        # 3. Dibujamos el pixmap centrado en el nuevo origen rotado
        draw_x = -scaled_pixmap.width() / 2
        draw_y = -scaled_pixmap.height() / 2
        painter.drawPixmap(int(draw_x), int(draw_y), scaled_pixmap)
        
        # 4. Restauramos el estado del painter
        painter.restore()


class SteeringInputWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # --- Cargar la imagen original del volante ---
        original_steering_wheel_pixmap = QPixmap(resource_path('./icons/steering_wheel.png'))
        
        # --- Crear los widgets ---
        self.brake_bar = self._create_pedal_bar(is_brake=True)
        self.throttle_bar = self._create_pedal_bar(is_brake=False)
        # Usamos nuestro nuevo lienzo en lugar de un QLabel
        self.steering_canvas = _SteeringWheelCanvas(original_steering_wheel_pixmap, self)
        
        # --- Layout Principal ---
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)
        
        main_layout.addWidget(self.brake_bar)
        main_layout.addWidget(self.steering_canvas, 1) # El '1' le da más espacio para estirarse
        main_layout.addWidget(self.throttle_bar)
        
        # Inicializar el estado visual
        self.update_inputs(0, 0, 0)

    def _create_pedal_bar(self, is_brake: bool) -> QProgressBar:
        bar = QProgressBar()
        bar.setRange(0, 100)
        bar.setValue(0)
        bar.setTextVisible(False)
        bar.setOrientation(Qt.Vertical)
        bar.setFixedWidth(20)
        
        color = "#c92d39" if is_brake else "#2dc9b8"
        background_color = "#2a2a3a"
        bar.setStyleSheet(f"""
            QProgressBar {{ border: 1px solid {background_color}; border-radius: 4px; background-color: {background_color}; }}
            QProgressBar::chunk {{ background-color: {color}; border-radius: 3px; margin: 2px; }}
        """)
        return bar

    def update_inputs(self, brake: float, throttle: float, steer_angle: float):
        """
        Punto de entrada público para actualizar todos los controles.
        El ángulo del volante debe estar en grados.
        """
        self.brake_bar.setValue(int(brake * 100))
        self.throttle_bar.setValue(int(throttle * 100))
        
        # Le pasamos el ángulo a nuestro lienzo para que se redibuje
        self.steering_canvas.set_angle(steer_angle)