from __future__ import annotations

from typing import Optional

import os

from PySide6.QtCore import Qt, QPoint, Signal, QTimer, QSize
from PySide6.QtGui import QFont, QMouseEvent, QColor, QIcon
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTextEdit,
    QPushButton,
    QSizeGrip,
    QGraphicsDropShadowEffect,
    QFontComboBox,
    QLabel,
    QColorDialog,
)

_RES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources")

from note_manager import NoteData, COLORS, DEFAULT_COLOR

TITLE_BAR_HEIGHT = 32
COLOR_DOT_SIZE = 16

_TITLE_BTN_STYLE = """
    QPushButton {
        background: transparent;
        border: none;
        font-size: 14px;
        font-weight: bold;
        color: rgba(0,0,0,0.45);
    }
    QPushButton:hover { color: rgba(0,0,0,0.8); }
"""

_ICON_BTN_STYLE = """
    QPushButton {
        background: transparent;
        border: none;
        border-radius: 4px;
    }
    QPushButton:hover { background: rgba(0,0,0,0.08); }
"""

_ICON_BTN_STYLE_RED = """
    QPushButton {
        background: transparent;
        border: none;
        border-radius: 4px;
    }
    QPushButton:hover { background: rgba(200,0,0,0.12); }
"""


class ColorDot(QPushButton):
    """Small circular button representing a note color."""

    def __init__(self, color_name: str, hex_color: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.color_name = color_name
        self.setFixedSize(COLOR_DOT_SIZE, COLOR_DOT_SIZE)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {hex_color};
                border: 1px solid rgba(0,0,0,0.25);
                border-radius: {COLOR_DOT_SIZE // 2}px;
                min-width: {COLOR_DOT_SIZE}px;
                min-height: {COLOR_DOT_SIZE}px;
                max-width: {COLOR_DOT_SIZE}px;
                max-height: {COLOR_DOT_SIZE}px;
            }}
            QPushButton:hover {{ border: 2px solid rgba(0,0,0,0.5); }}
            """
        )


class NoteWidget(QWidget):
    closed = Signal(str)
    changed = Signal(object)
    hidden_to_back = Signal(str)

    def __init__(self, data: NoteData, parent: QWidget | None = None):
        super().__init__(parent)
        self.data = data
        self._drag_pos: Optional[QPoint] = None
        self._is_on_top = True
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(400)
        self._save_timer.timeout.connect(self._emit_changed)

        self._setup_window()
        self._build_ui()
        self._apply_color()
        self._apply_font()

    # ---- window setup ----

    def _setup_window(self) -> None:
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMinimumSize(200, 140)
        self.resize(self.data.width, self.data.height)
        self.move(self.data.x, self.data.y)

    # ---- UI construction ----

    def _build_ui(self) -> None:
        self._container = QWidget(self)
        shadow = QGraphicsDropShadowEffect(self._container)
        shadow.setBlurRadius(18)
        shadow.setOffset(0, 2)
        shadow.setColor(QColor(0, 0, 0, 60))
        self._container.setGraphicsEffect(shadow)

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.addWidget(self._container)

        inner = QVBoxLayout(self._container)
        inner.setContentsMargins(0, 0, 0, 0)
        inner.setSpacing(0)

        # -- title label (centered) --
        self._title_label = QLabel(self._get_title())
        self._title_label.setFixedHeight(22)
        self._title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._title_label.setStyleSheet(
            "QLabel { background: transparent; border: none;"
            " font-size: 11px; font-weight: bold; color: rgba(0,0,0,0.55); }"
        )
        inner.addWidget(self._title_label)

        # -- title bar --
        self._title_bar = QWidget()
        self._title_bar.setFixedHeight(TITLE_BAR_HEIGHT)
        self._title_bar.setCursor(Qt.CursorShape.SizeAllCursor)
        tb = QHBoxLayout(self._title_bar)
        tb.setContentsMargins(8, 4, 4, 4)
        tb.setSpacing(4)

        for name, hex_c in COLORS.items():
            dot = ColorDot(name, hex_c, self._title_bar)
            dot.clicked.connect(lambda checked=False, n=name: self._set_color(n))
            tb.addWidget(dot)

        tb.addStretch()

        hide_btn = QPushButton("hide")
        hide_btn.setToolTip("Send to back")
        hide_btn.setFixedSize(32, 22)
        hide_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        hide_btn.setStyleSheet(_TITLE_BTN_STYLE)
        hide_btn.clicked.connect(self._send_to_back)
        tb.addWidget(hide_btn)

        save_btn = QPushButton()
        save_btn.setToolTip("Save now")
        save_btn.setFixedSize(22, 22)
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.setIcon(QIcon(os.path.join(_RES_DIR, "save.svg")))
        save_btn.setIconSize(QSize(14, 14))
        save_btn.setStyleSheet(_ICON_BTN_STYLE)
        save_btn.clicked.connect(self._force_save)
        tb.addWidget(save_btn)

        trash_btn = QPushButton()
        trash_btn.setToolTip("Delete note")
        trash_btn.setFixedSize(22, 22)
        trash_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        trash_btn.setIcon(QIcon(os.path.join(_RES_DIR, "trash.svg")))
        trash_btn.setIconSize(QSize(14, 14))
        trash_btn.setStyleSheet(_ICON_BTN_STYLE_RED)
        trash_btn.clicked.connect(self._on_close)
        tb.addWidget(trash_btn)

        close_btn = QPushButton("✕")
        close_btn.setToolTip("Hide note")
        close_btn.setFixedSize(22, 22)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet(_TITLE_BTN_STYLE)
        close_btn.clicked.connect(self._hide_note)
        tb.addWidget(close_btn)

        inner.addWidget(self._title_bar)

        # -- formatting toolbar --
        self._fmt_bar = QWidget()
        self._fmt_bar.setFixedHeight(34)
        fmt_layout = QHBoxLayout(self._fmt_bar)
        fmt_layout.setContentsMargins(8, 2, 8, 2)
        fmt_layout.setSpacing(4)

        self._font_combo = QFontComboBox()
        self._font_combo.setCurrentFont(QFont(self.data.font_family))
        self._font_combo.setFixedHeight(26)
        self._font_combo.setMaximumWidth(120)
        self._font_combo.currentFontChanged.connect(self._on_font_family_changed)
        self._font_combo.setStyleSheet(
            "QFontComboBox { background: rgba(255,255,255,0.6); border: 1px solid rgba(0,0,0,0.15); border-radius: 3px; font-size: 10px; color: black; }"
            " QFontComboBox QAbstractItemView { color: black; background: white; }"
        )
        fmt_layout.addWidget(self._font_combo)

        size_minus = QPushButton("−")
        size_minus.setFixedSize(26, 26)
        size_minus.setCursor(Qt.CursorShape.PointingHandCursor)
        size_minus.setStyleSheet(
            "QPushButton { background: rgba(255,255,255,0.6); border: 1px solid rgba(0,0,0,0.15); border-radius: 3px; font-size: 14px; color: black; }"
            " QPushButton:hover { background: rgba(255,255,255,0.9); }"
        )
        size_minus.clicked.connect(lambda: self._change_font_size(-1))
        fmt_layout.addWidget(size_minus)

        self._size_label = QLabel(f"{self.data.font_size}pt")
        self._size_label.setFixedWidth(32)
        self._size_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._size_label.setStyleSheet("font-size: 10px; color: black; background: transparent; border: none;")
        fmt_layout.addWidget(self._size_label)

        size_plus = QPushButton("+")
        size_plus.setFixedSize(26, 26)
        size_plus.setCursor(Qt.CursorShape.PointingHandCursor)
        size_plus.setStyleSheet(
            "QPushButton { background: rgba(255,255,255,0.6); border: 1px solid rgba(0,0,0,0.15); border-radius: 3px; font-size: 14px; color: black; }"
            " QPushButton:hover { background: rgba(255,255,255,0.9); }"
        )
        size_plus.clicked.connect(lambda: self._change_font_size(1))
        fmt_layout.addWidget(size_plus)

        self._color_btn = QPushButton()
        self._color_btn.setFixedSize(24, 24)
        self._color_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._color_btn.setToolTip("Text color")
        self._update_color_btn_style()
        self._color_btn.clicked.connect(self._pick_font_color)
        fmt_layout.addWidget(self._color_btn)

        fmt_layout.addStretch()
        inner.addWidget(self._fmt_bar)

        # -- text editor --
        self._editor = QTextEdit()
        self._editor.setPlaceholderText("Type your note here…")
        self._editor.setAcceptRichText(False)
        self._editor.setText(self.data.text)
        self._editor.textChanged.connect(self._on_text_changed)
        inner.addWidget(self._editor)

        # -- resize grip --
        grip_bar = QHBoxLayout()
        grip_bar.setContentsMargins(0, 0, 2, 2)
        grip_bar.addStretch()
        self._grip = QSizeGrip(self._container)
        self._grip.setFixedSize(16, 16)
        self._grip.setStyleSheet("background: transparent;")
        grip_bar.addWidget(self._grip)
        inner.addLayout(grip_bar)

    # ---- formatting ----

    def _apply_font(self) -> None:
        self._editor.setFont(QFont(self.data.font_family, self.data.font_size))
        self._editor.setStyleSheet(
            f"""
            QTextEdit {{
                background: transparent;
                border: none;
                padding: 8px;
                color: {self.data.font_color};
                selection-background-color: rgba(0,0,0,0.15);
            }}
            """
        )

    def _on_font_family_changed(self, font: QFont) -> None:
        self.data.font_family = font.family()
        self._apply_font()
        self._schedule_save()

    def _change_font_size(self, delta: int) -> None:
        new_size = max(8, min(48, self.data.font_size + delta))
        if new_size != self.data.font_size:
            self.data.font_size = new_size
            self._size_label.setText(f"{new_size}pt")
            self._apply_font()
            self._schedule_save()

    def _pick_font_color(self) -> None:
        color = QColorDialog.getColor(QColor(self.data.font_color), self, "Text Color")
        if color.isValid():
            self.data.font_color = color.name()
            self._update_color_btn_style()
            self._apply_font()
            self._schedule_save()

    def _update_color_btn_style(self) -> None:
        self._color_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {self.data.font_color};
                border: 1px solid rgba(0,0,0,0.3);
                border-radius: 4px;
            }}
            QPushButton:hover {{ border: 2px solid rgba(0,0,0,0.6); }}
            """
        )

    # ---- color ----

    def _apply_color(self) -> None:
        bg = COLORS.get(self.data.color, COLORS[DEFAULT_COLOR])
        self._container.setStyleSheet(
            f"QWidget {{ background-color: {bg}; border-radius: 10px; }}"
        )
        self._title_bar.setStyleSheet(
            f"""
            QWidget {{
                background-color: {self._darken(bg, 15)};
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
                border-bottom-left-radius: 0px;
                border-bottom-right-radius: 0px;
            }}
            """
        )

    @staticmethod
    def _darken(hex_color: str, amount: int) -> str:
        c = QColor(hex_color)
        return QColor(
            max(c.red() - amount, 0),
            max(c.green() - amount, 0),
            max(c.blue() - amount, 0),
        ).name()

    def _set_color(self, name: str) -> None:
        self.data.color = name
        self._apply_color()
        self._schedule_save()

    # ---- hide / bring to front ----

    def _send_to_back(self) -> None:
        self._is_on_top = False
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
        )
        self.show()
        self.lower()
        self.hidden_to_back.emit(self.data.id)

    def bring_to_front(self) -> None:
        self._is_on_top = True
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.show()
        self.raise_()
        self.activateWindow()

    # ---- dragging ----

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._in_title_bar(event.position().toPoint()):
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._drag_pos is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self._drag_pos is not None:
            self._drag_pos = None
            self._sync_geometry()
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def _in_title_bar(self, local_pos: QPoint) -> bool:
        return local_pos.y() <= TITLE_BAR_HEIGHT + 10

    # ---- resize tracking ----

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._sync_geometry()

    def moveEvent(self, event) -> None:
        super().moveEvent(event)
        self._sync_geometry()

    def _sync_geometry(self) -> None:
        pos = self.pos()
        size = self.size()
        self.data.x = pos.x()
        self.data.y = pos.y()
        self.data.width = size.width()
        self.data.height = size.height()
        self._schedule_save()

    # ---- persistence helpers ----

    def _get_title(self) -> str:
        first_line = self.data.text.split("\n", 1)[0].strip()
        if not first_line:
            return "Untitled"
        return first_line[:40] + ("…" if len(first_line) > 40 else "")

    def _on_text_changed(self) -> None:
        self.data.text = self._editor.toPlainText()
        self._title_label.setText(self._get_title())
        self._schedule_save()

    def _force_save(self) -> None:
        self._save_timer.stop()
        self._emit_changed()

    def _schedule_save(self) -> None:
        self._save_timer.start()

    def _emit_changed(self) -> None:
        self.changed.emit(self.data)

    def _hide_note(self) -> None:
        self.hide()
        self.hidden_to_back.emit(self.data.id)

    def _on_close(self) -> None:
        self.closed.emit(self.data.id)
        self.close()
