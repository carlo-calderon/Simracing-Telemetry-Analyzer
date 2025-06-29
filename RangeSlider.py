# RangeSlider.py
from PySide6.QtWidgets import QWidget, QToolTip
from PySide6.QtGui import QPainter, QColor, QPalette, QImage, QFont, QPen, QRadialGradient
from PySide6.QtCore import Qt, Signal, QPoint, QRect, QPointF
import numpy as np

class QRangeSlider(QWidget):
    rangeChanged = Signal(float, float)
    left_bar_clicked = Signal()
    right_bar_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(250, 60)
        self.setMouseTracking(True)
        self._min_val, self._max_val = 0.0, 1.0
        self._low_val, self._high_val = 0.0, 1.0
        self._dragged_handle = None
        self.handle_diameter = 16
        self.margin = self.handle_diameter // 2
        self.colormap = None
        
        # Nuevos atributos para los colores de los extremos
        self._min_edge_color = QColor(80, 80, 90)
        self._max_edge_color = QColor(80, 80, 90)

    def setColormap(self, colormap):
        self.colormap = colormap
        self.update()

    def setRange(self, min_val, max_val):
        self._min_val = min_val
        self._max_val = max_val if max_val > min_val else min_val + 1.0
        self.update()

    def setValues(self, low, high):
        self._low_val = low
        self._high_val = high
        self.update()
        
    def set_edge_colors(self, min_color: QColor, max_color: QColor):
        """ Recibe los colores para pintar los extremos fuera de rango. """
        self._min_edge_color = min_color
        self._max_edge_color = max_color
        self.update()

    def _pos_to_val(self, pos):
        effective_width = self.width() - 2 * self.margin
        if effective_width <= 0: return self._min_val
        clamped_pos = max(self.margin, min(pos, self.width() - self.margin))
        pos_fraction = (clamped_pos - self.margin) / effective_width
        return self._min_val + pos_fraction * (self._max_val - self._min_val)

    def _val_to_pos(self, val):
        full_range = self._max_val - self._min_val
        if full_range <= 0:
            return self.margin if val <= self._min_val else self.width() - self.margin
        
        effective_width = self.width() - 2 * self.margin
        clamped_val = max(self._min_val, min(val, self._max_val))
        val_fraction = (clamped_val - self._min_val) / full_range
        return self.margin + val_fraction * effective_width

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        bar_height = 8
        bar_y = self.height() // 2 - bar_height // 2
        
        low_pos = self._val_to_pos(self._low_val)
        high_pos = self._val_to_pos(self._high_val)

        if not self.colormap:
            bar_rect = QRect(self.margin, bar_y, self.width() - 2 * self.margin, bar_height)
            painter.setBrush(QColor(80, 80, 90))
            painter.drawRect(bar_rect)
        else:
            # 1. Dibuja la parte izquierda (fuera de rango) con su color atenuado
            left_rect = QRect(self.margin, bar_y, int(low_pos) - self.margin, bar_height)
            painter.setPen(Qt.NoPen)
            painter.setBrush(self._min_edge_color)
            painter.drawRect(left_rect)
            
            # 2. Dibuja la parte derecha (fuera de rango) con su color atenuado
            right_rect = QRect(int(high_pos), bar_y, self.width() - self.margin - int(high_pos), bar_height)
            painter.setBrush(self._max_edge_color)
            painter.drawRect(right_rect)

            # 3. Dibuja el gradiente dinámico en la sección seleccionada
            if self.colormap:
                selection_width = int(high_pos - low_pos)
                if selection_width > 0:
                    arr = np.linspace(0, 1, selection_width)
                    colors = (self.colormap(arr)[:, :3] * 255).astype(np.uint8)
                    qimg = QImage(colors.data, selection_width, 1, 3 * selection_width, QImage.Format_RGB888)
                    dest_rect = QRect(int(low_pos), bar_y, selection_width, bar_height)
                    painter.drawImage(dest_rect, qimg.scaled(selection_width, bar_height, Qt.IgnoreAspectRatio, Qt.SmoothTransformation))
        
        handle_radius = self.handle_diameter / 2
        for pos in [low_pos, high_pos]:
            gradient = QRadialGradient(QPointF(pos, self.height() // 2), handle_radius)
            gradient.setColorAt(0, QColor(255, 255, 255))
            gradient.setColorAt(1, QColor(200, 200, 210))
            painter.setBrush(gradient)
            painter.setPen(QPen(QColor(50,50,50), 1))
            painter.drawEllipse(QPointF(pos, self.height() // 2), handle_radius, handle_radius)

        font = self.font()
        font.setPointSize(8)
        font.setBold(True)
        painter.setFont(font)
        
        for val, pos in [(self._low_val, low_pos), (self._high_val, high_pos)]:
            text = f"{val:.2f}"
            metrics = painter.fontMetrics()
            text_rect = metrics.boundingRect(text)
            
            bubble_w = text_rect.width() + 6
            bubble_h = text_rect.height() + 2
            bubble_x = pos - bubble_w / 2
            bubble_y = bar_y - bubble_h - 5

            bubble_x = max(0, min(bubble_x, self.width() - bubble_w))
            bubble_rect = QRect(int(bubble_x), int(bubble_y), bubble_w, bubble_h)
            
            if self.colormap:
                full_range = self._max_val - self._min_val
                norm_val = (val - self._min_val) / full_range if full_range > 0 else 0
                color_val = QColor.fromRgbF(*self.colormap(norm_val))
                text_color = color_val.darker(150)
            else:
                text_color = self.palette().color(QPalette.Text)
            
            painter.setBrush(QColor(240, 240, 240))
            painter.setPen(QPen(QColor(150,150,150), 1))
            painter.drawRoundedRect(bubble_rect, 5, 5)
            painter.setPen(text_color)
            painter.drawText(bubble_rect, Qt.AlignCenter, text)

        font.setPointSize(8)
        font.setBold(False)
        painter.setFont(font)
        metrics = painter.fontMetrics()
        painter.setBrush(QColor(240, 240, 240))
        painter.setPen(QPen(QColor(150,150,150), 1))

        min_text = f"{self._min_val:.2f}"
        min_text_rect = metrics.boundingRect(min_text)
        min_bubble_w = min_text_rect.width() + 8
        min_bubble_h = min_text_rect.height() + 4
        min_bubble_rect = QRect(0, self.height() - min_bubble_h, min_bubble_w, min_bubble_h)
        painter.drawRoundedRect(min_bubble_rect, 4, 4)

        max_text = f"{self._max_val:.2f}"
        max_text_rect = metrics.boundingRect(max_text)
        max_bubble_w = max_text_rect.width() + 8
        max_bubble_h = max_text_rect.height() + 4
        max_bubble_rect = QRect(self.width() - max_bubble_w, self.height() - max_bubble_h, max_bubble_w, max_bubble_h)
        painter.drawRoundedRect(max_bubble_rect, 4, 4)

        painter.setPen(self.palette().color(QPalette.Text))
        painter.drawText(min_bubble_rect, Qt.AlignCenter, min_text)
        painter.drawText(max_bubble_rect, Qt.AlignCenter, max_text)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            low_pos = self._val_to_pos(self._low_val)
            high_pos = self._val_to_pos(self._high_val)
            
            # Lógica existente para arrastrar los manejadores
            if abs(event.pos().x() - low_pos) < abs(event.pos().x() - high_pos):
                if abs(event.pos().x() - low_pos) < self.handle_diameter / 2:
                    self._dragged_handle = 'low'
            else:
                if abs(event.pos().x() - high_pos) < self.handle_diameter / 2:
                    self._dragged_handle = 'high'

            # Comprobar si el clic fue en las barras de los extremos
            if event.pos().x() < low_pos and not self._dragged_handle == 'low':
                self.left_bar_clicked.emit()
                return # Detenemos el procesamiento aquí
            
            if event.pos().x() > high_pos and not self._dragged_handle == 'high':
                self.right_bar_clicked.emit()
                return # Detenemos el procesamiento aquí


            self.update()

    def mouseMoveEvent(self, event):
        if self._dragged_handle:
            new_val = self._pos_to_val(event.pos().x())
            if self._dragged_handle == 'low':
                self._low_val = max(self._min_val, min(new_val, self._high_val))
            elif self._dragged_handle == 'high':
                self._high_val = min(self._max_val, max(new_val, self._low_val))
            self.rangeChanged.emit(self._low_val, self._high_val)
            self.update()
        
        val = self._pos_to_val(event.pos().x())
        QToolTip.showText(event.globalPos(), f"{val:.2f}", self)

    def mouseReleaseEvent(self, event):
        self._dragged_handle = None
        self.update()

    def leaveEvent(self, event):
        QToolTip.hideText()