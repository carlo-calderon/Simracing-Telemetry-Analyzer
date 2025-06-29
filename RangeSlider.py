from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QColor, QPalette, QImage
from PySide6.QtCore import Qt, Signal, QPoint, QRect
import numpy as np

class QRangeSlider(QWidget):
    """
    Un widget de slider con dos manejadores para seleccionar un rango.
    Ahora puede mostrar una paleta de colores como fondo.
    """
    rangeChanged = Signal(float, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(200, 25)
        self._min_val, self._max_val = 0.0, 1.0
        self._low_val, self._high_val = 0.0, 1.0

        self._dragged_handle = None  # 'low', 'high', or None
        self.handle_width = 10

        self.colormap = None  # Debe ser una función: float [0,1] -> (r,g,b)
        self._colormap_cache = None  # Para cachear el gradiente pintado

    def setColormap(self, colormap):
        """
        colormap: función que recibe float [0,1] y devuelve (r,g,b) en [0,1] o [0,255]
        Ejemplo: matplotlib.cm.get_cmap('RdYlGn')
        """
        self.colormap = colormap
        self._colormap_cache = None
        self.update()

    def setRange(self, min_val, max_val):
        self._min_val = min_val
        self._max_val = max_val if max_val > min_val else min_val + 1
        self.update()

    def setValues(self, low, high):
        self._low_val = low
        self._high_val = high
        self.update()

    def _pos_to_val(self, pos):
        return self._min_val + (pos / self.width()) * (self._max_val - self._min_val)

    def _val_to_pos(self, val):
        return self.width() * (val - self._min_val) / (self._max_val - self._min_val)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        bar_rect = QRect(0, self.height() // 2 - 6, self.width(), 12)
        low_pos = self._val_to_pos(self._low_val)
        high_pos = self._val_to_pos(self._high_val)

        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(80, 80, 90))
        painter.drawRect(bar_rect)
        
        # --- Fondo con paleta de colores ---
        if self.colormap:
            # Primero, definimos el rectángulo del área seleccionada.
            clip_rect = QRect(int(low_pos), bar_rect.y(), int(high_pos - low_pos), bar_rect.height())

            # Guardamos el estado actual del painter
            painter.save()

            # ¡La Magia! Establecemos un área de recorte. 
            # A partir de ahora, el painter solo dibujará dentro de este rectángulo.
            painter.setClipRect(clip_rect)

            # Ahora dibujamos la imagen completa del gradiente de color.
            # Gracias al recorte, solo se verá la parte que está dentro de la selección.
            if self._colormap_cache is None or self._colormap_cache.width() != self.width():
                arr = np.linspace(0, 1, self.width())
                colors = (self.colormap(arr)[:, :3] * 255).astype(np.uint8)
                img_data = np.zeros((bar_rect.height(), self.width(), 3), dtype=np.uint8)
                img_data[:] = colors[np.newaxis, :, :]
                qimg = QImage(img_data.data, self.width(), bar_rect.height(), 3 * self.width(), QImage.Format_RGB888)
                self._colormap_cache = qimg
            
            painter.drawImage(bar_rect, self._colormap_cache)

            # Restauramos el painter a su estado original, eliminando el recorte.
            painter.restore()

        # Draw handles
        painter.setBrush(self.palette().light())
        painter.setPen(self.palette().color(QPalette.Shadow))
        painter.drawEllipse(QPoint(int(low_pos), bar_rect.center().y()), self.handle_width, self.handle_width)
        painter.drawEllipse(QPoint(int(high_pos), bar_rect.center().y()), self.handle_width, self.handle_width)

    def mousePressEvent(self, event):
        low_pos = self._val_to_pos(self._low_val)
        high_pos = self._val_to_pos(self._high_val)
        if abs(event.x() - low_pos) < self.handle_width:
            self._dragged_handle = 'low'
        elif abs(event.x() - high_pos) < self.handle_width:
            self._dragged_handle = 'high'
        self.update()

    def mouseMoveEvent(self, event):
        if self._dragged_handle:
            new_val = self._pos_to_val(event.x())
            if self._dragged_handle == 'low':
                self._low_val = max(self._min_val, min(new_val, self._high_val))
            elif self._dragged_handle == 'high':
                self._high_val = min(self._max_val, max(new_val, self._low_val))
            self.rangeChanged.emit(self._low_val, self._high_val)
            self.update()
        # Tooltip con valor bajo el mouse
        val = self._pos_to_val(event.x())
        self.setToolTip(f"{val:.3f}")

    def mouseReleaseEvent(self, event):
        self._dragged_handle = None
        self.update()

    def enterEvent(self, event):
        self.setMouseTracking(True)

    def leaveEvent(self, event):
        self.setMouseTracking(False)
        self.setToolTip("")