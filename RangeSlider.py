# RangeSlider.py
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QColor, QPalette, QImage
from PySide6.QtCore import Qt, Signal, QPoint, QRect
import numpy as np

class QRangeSlider(QWidget):
    rangeChanged = Signal(float, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(200, 25)
        self.setMouseTracking(True)
        self._min_val, self._max_val = 0.0, 1.0
        self._low_val, self._high_val = 0.0, 1.0
        self._dragged_handle = None
        self.handle_width = 10
        self.colormap = None
        self._colormap_cache = None

    def setColormap(self, colormap):
        self.colormap = colormap
        self._colormap_cache = None
        self.update()

    def setRange(self, min_val, max_val):
        self._min_val = min_val
        self._max_val = max_val if max_val > min_val else min_val + 1.0
        self._colormap_cache = None
        self.update()

    def setValues(self, low, high):
        self._low_val = low
        self._high_val = high
        self.update() # No invalidamos el caché aquí

    def _pos_to_val(self, pos):
        full_range = self._max_val - self._min_val
        if self.width() <= 0 or full_range <= 0:
            return self._min_val
        return self._min_val + (pos / self.width()) * full_range

    def _val_to_pos(self, val):
        full_range = self._max_val - self._min_val
        if full_range <= 0:
            return 0 if val <= self._min_val else self.width()
        
        clamped_val = max(self._min_val, min(val, self._max_val))
        return self.width() * (clamped_val - self._min_val) / full_range

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        bar_rect = QRect(0, self.height() // 2 - 6, self.width(), 12)
        low_pos = self._val_to_pos(self._low_val)
        high_pos = self._val_to_pos(self._high_val)
        print(f"Low: {self._low_val} at {low_pos}, High: {self._high_val} at {high_pos}")

        # 1. Dibuja toda la barra de fondo en un color neutro.
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(80, 80, 90))
        painter.drawRect(bar_rect)

        # 2. Si tenemos un mapa de colores, generamos y dibujamos el gradiente dinámico.
        if self.colormap:
            selection_width = int(high_pos - low_pos)

            if selection_width > 0:
                # a. Creamos un gradiente que siempre va de 0 a 1 (rojo a verde),
                #    pero con un número de puntos igual al ancho en píxeles de la selección.
                arr = np.linspace(0, 1, selection_width)
                colors = (self.colormap(arr)[:, :3] * 255).astype(np.uint8)

                # b. Creamos una imagen pequeña, solo del tamaño de la selección.
                img_data = np.zeros((bar_rect.height(), selection_width, 3), dtype=np.uint8)
                img_data[:] = colors[np.newaxis, :, :]
                qimg = QImage(img_data.data, selection_width, bar_rect.height(), 3 * selection_width, QImage.Format_RGB888)

                # c. Dibujamos esta pequeña imagen de gradiente directamente en su posición.
                painter.drawImage(QPoint(int(low_pos), bar_rect.y()), qimg)

        # 3. Dibuja los manejadores al final.
        painter.setBrush(self.palette().light())
        painter.setPen(self.palette().color(QPalette.Shadow))
        painter.drawEllipse(QPoint(int(low_pos), bar_rect.center().y()), self.handle_width, self.handle_width)
        painter.drawEllipse(QPoint(int(high_pos), bar_rect.center().y()), self.handle_width, self.handle_width)

    def mousePressEvent(self, event):
        low_pos = self._val_to_pos(self._low_val)
        high_pos = self._val_to_pos(self._high_val)
        
        if abs(event.pos().x() - low_pos) < abs(event.pos().x() - high_pos):
            if abs(event.pos().x() - low_pos) < self.handle_width:
                self._dragged_handle = 'low'
        else:
            if abs(event.pos().x() - high_pos) < self.handle_width:
                self._dragged_handle = 'high'
        self.update()

    def mouseMoveEvent(self, event):
        val = self._pos_to_val(event.pos().x())
        self.setToolTip(f"{val:.3f}")

        if self._dragged_handle:
            new_val = self._pos_to_val(event.pos().x())
            if self._dragged_handle == 'low':
                self._low_val = max(self._min_val, min(new_val, self._high_val))
            elif self._dragged_handle == 'high':
                self._high_val = min(self._max_val, max(new_val, self._low_val))
            
            self.rangeChanged.emit(self._low_val, self._high_val)
            self.update()

    def mouseReleaseEvent(self, event):
        self._dragged_handle = None
        self.update()

    def leaveEvent(self, event):
        self.setToolTip("")