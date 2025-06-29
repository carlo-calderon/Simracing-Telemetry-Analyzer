from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QColor, QPalette
from PySide6.QtCore import Qt, Signal, QPoint, QRect

class QRangeSlider(QWidget):
    """
    Un widget de slider con dos manejadores para seleccionar un rango.
    """
    rangeChanged = Signal(float, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(200, 25)
        self._min_val, self._max_val = 0.0, 1.0
        self._low_val, self._high_val = 0.0, 1.0

        self._dragged_handle = None  # 'low', 'high', or None
        self.handle_width = 10

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
        
        bar_rect = QRect(0, self.height() // 2 - 2, self.width(), 4)
        low_pos = self._val_to_pos(self._low_val)
        high_pos = self._val_to_pos(self._high_val)

        # Draw background bar
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(80, 80, 90))
        painter.drawRect(bar_rect)

        # Draw selected range bar
        painter.setBrush(QColor(0, 120, 215))
        painter.drawRect(QRect(int(low_pos), bar_rect.y(), int(high_pos - low_pos), bar_rect.height()))

        # Draw handles
        painter.setBrush(self.palette().light())
        painter.setPen(self.palette().color(QPalette.Shadow))
        painter.drawEllipse(QPoint(int(low_pos), bar_rect.center().y() + 1), self.handle_width, self.handle_width)
        painter.drawEllipse(QPoint(int(high_pos), bar_rect.center().y() + 1), self.handle_width, self.handle_width)

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

    def mouseReleaseEvent(self, event):
        self._dragged_handle = None
        self.update()