# -*- coding: utf-8 -*-
"""
File: SteeringInputWidget.py
Created on 2025-07-06
@author: Carlo Calderón Becerra
@company: CarcaldeF1
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QProgressBar, QLabel
from PySide6.QtGui import QPixmap, QTransform, QPainter, QColor, QFont
from PySide6.QtCore import Qt

from utils import resource_path

# --- NUEVO WIDGET INTERNO SOLO PARA DIBUJAR EL VOLANTE ---
class _SteeringWheelCanvas(QWidget):
    def __init__(self, pixmap, parent=None):
        super().__init__(parent)
        self.original_pixmap = pixmap
        self.current_angle = 0.0
        self.setMinimumSize(150, 150)  # Tamaño mínimo para el volante

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

class _RPMLedsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(30)
        self.rpm_percentage = 0.0

        # Definimos los colores y los umbrales para cada LED
        self.led_config = [
            # (Umbral_%, Color_Encendido)
            (0.60, QColor("#15b500")),  # Verde 1
            (0.65, QColor("#45d600")),  # Verde 2
            (0.70, QColor("#84f500")),  # Verde 3
            (0.75, QColor("#c3ff00")),  # Amarillo 1
            (0.80, QColor("#f7f500")),  # Amarillo 2
            (0.85, QColor("#f7b500")),  # Naranja
            (0.90, QColor("#e86100")),  # Rojo 1
            (0.95, QColor("#d90000")),  # Rojo 2
            (0.98, QColor("#9d00c2")),  # Morado
            (1.00, QColor("#0080ff"))   # Azul (luz de cambio)
        ]
        self.led_off_color = QColor(40, 40, 50)

    def update_rpm(self, rpm_pct: float):
        """ Actualiza el porcentaje de RPM y solicita un redibujado. """
        self.rpm_percentage = rpm_pct
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        num_leds = len(self.led_config)
        if num_leds == 0:
            return
            
        space_per_led = self.width() / num_leds
        led_diameter = min(space_per_led * 0.75, self.height() * 0.7)
        total_leds_width = num_leds * led_diameter
        total_spacing = self.width() - total_leds_width
        spacing = total_spacing / (num_leds + 1) if num_leds > 0 else 0

        led_y = (self.height() - led_diameter) / 2
        for i, (threshold, color) in enumerate(self.led_config):
            led_x = spacing + i * (led_diameter + spacing)            
            # Decidimos si el LED está encendido
            if self.rpm_percentage >= threshold:
                painter.setBrush(color)
            else:
                painter.setBrush(self.led_off_color)
            
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(int(led_x), int(led_y), int(led_diameter), int(led_diameter))


class SteeringInputWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # --- Cargar la imagen original del volante ---
        original_steering_wheel_pixmap = QPixmap(resource_path('./icons/steering_wheel.png'))
        
        # --- Crear los widgets ---
        self.brake_bar = self._create_pedal_bar(is_brake=True)
        self.throttle_bar = self._create_pedal_bar(is_brake=False)
        self.steering_canvas = _SteeringWheelCanvas(original_steering_wheel_pixmap, self)
        self.rpm_leds = _RPMLedsWidget(self)
        self.gear_label = self._create_gear_label()
        
        # --- Layout Principal ---
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)
        
        # Layout central para apilar LEDs y volante
        center_layout = QVBoxLayout()
        center_layout.addWidget(self.rpm_leds) # LEDs arriba
        center_layout.addWidget(self.steering_canvas) # Volante abajo
        center_layout.addWidget(self.gear_label) # Etiqueta de marcha al final
        
        main_layout.addWidget(self.brake_bar)
        main_layout.addLayout(center_layout, 1) # El '1' le da más espacio para estirarse
        main_layout.addWidget(self.throttle_bar)
        
        # Inicializar el estado visual
        self.update_inputs(0, 0, 0, 0, 0)

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

    def _create_gear_label(self) -> QLabel:
        """Helper para crear y estilizar la etiqueta de la marcha."""
        label = QLabel("N")
        font = QFont("Arial", 24, QFont.Bold)
        label.setFont(font)
        label.setAlignment(Qt.AlignCenter)
        label.setFixedHeight(40)
        label.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                background-color: #1E1E2F;
                border-radius: 5px;
                padding: 5px;
            }
        """)
        return label
    
    def update_inputs(self, brake: float, throttle: float, steer_angle: float, rpm_pct: float = 0.0, gear: int = 0):
        """
        Punto de entrada público para actualizar todos los controles.
        El ángulo del volante debe estar en grados.
        """
        self.brake_bar.setValue(int(brake * 100))
        self.throttle_bar.setValue(int(throttle * 100))
        
        self.steering_canvas.set_angle(steer_angle)
        self.rpm_leds.update_rpm(rpm_pct)

        gear_text = "N" if gear == 0 else "R" if gear == -1 else str(int(gear))
        self.gear_label.setText(gear_text)