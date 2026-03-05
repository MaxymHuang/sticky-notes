from __future__ import annotations

from PySide6.QtCore import QSize
from PySide6.QtGui import QAction, QIcon, QPixmap, QPainter, QColor, QBrush, QPen
from PySide6.QtWidgets import QSystemTrayIcon, QMenu, QApplication

from note_manager import NoteManager, NoteData, DEFAULT_COLLECTION
from note_widget import NoteWidget
from collection_window import CollectionWindow


def _make_icon() -> QIcon:
    """Generate a simple sticky-note icon programmatically."""
    size = 64
    pm = QPixmap(QSize(size, size))
    pm.fill(QColor(0, 0, 0, 0))
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setBrush(QBrush(QColor("#fff176")))
    p.setPen(QPen(QColor("#f9a825"), 2))
    p.drawRoundedRect(4, 4, size - 8, size - 8, 8, 8)
    p.setPen(QPen(QColor("#bdbdbd"), 2))
    for y_off in (22, 34, 46):
        p.drawLine(14, y_off, size - 14, y_off)
    p.end()
    return QIcon(pm)


class SystemTrayApp:
    def __init__(self) -> None:
        self._manager = NoteManager()
        self._widgets: dict[str, NoteWidget] = {}
        self._collection_win: CollectionWindow | None = None

        self._icon = _make_icon()
        self._tray = QSystemTrayIcon(self._icon)
        self._tray.setToolTip("Sticky Notes")
        self._tray.activated.connect(self._on_tray_activated)

        self._build_menu()
        self._tray.show()
        self._load_existing()

    # ---- menu ----

    def _build_menu(self) -> None:
        menu = QMenu()

        new_action = QAction("New Note", menu)
        new_action.triggered.connect(lambda: self.create_note())
        menu.addAction(new_action)

        show_action = QAction("Show All", menu)
        show_action.triggered.connect(self._show_all)
        menu.addAction(show_action)

        manage_action = QAction("Manage Notes", menu)
        manage_action.triggered.connect(self._open_manager)
        menu.addAction(manage_action)

        menu.addSeparator()

        self._autostart_action = QAction("Start with Windows", menu)
        self._autostart_action.setCheckable(True)
        self._autostart_action.setChecked(NoteManager.is_autostart_enabled())
        self._autostart_action.toggled.connect(self._toggle_autostart)
        menu.addAction(self._autostart_action)

        menu.addSeparator()

        quit_action = QAction("Quit", menu)
        quit_action.triggered.connect(self._quit)
        menu.addAction(quit_action)

        self._tray.setContextMenu(menu)

    # ---- collection manager ----

    def _open_manager(self) -> None:
        if self._collection_win is None:
            self._collection_win = CollectionWindow(self._manager)
            self._collection_win.request_new_note.connect(self._on_manager_new_note)
            self._collection_win.request_show_note.connect(self._on_manager_show_note)
            self._collection_win.request_hide_note.connect(self._on_manager_hide_note)
            self._collection_win.request_delete_note.connect(self._on_manager_delete_note)
        self._collection_win.refresh()
        self._collection_win.show()
        self._collection_win.raise_()
        self._collection_win.activateWindow()

    def _on_manager_new_note(self, collection: str) -> None:
        self.create_note(collection)
        if self._collection_win:
            self._collection_win.refresh()

    def _on_manager_show_note(self, note_id: str) -> None:
        w = self._widgets.get(note_id)
        if w:
            w.bring_to_front()

    def _on_manager_hide_note(self, note_id: str) -> None:
        w = self._widgets.get(note_id)
        if w:
            w._send_to_back()

    def _on_manager_delete_note(self, note_id: str) -> None:
        w = self._widgets.pop(note_id, None)
        if w:
            w.close()
        self._manager.delete(note_id)
        if self._collection_win:
            self._collection_win.refresh()

    # ---- note lifecycle ----

    def _load_existing(self) -> None:
        notes = self._manager.load()
        if not notes:
            self.create_note()
        else:
            for data in notes:
                self._spawn_widget(data)

    def create_note(self, collection: str = DEFAULT_COLLECTION) -> None:
        data = NoteData(collection=collection)
        offset = len(self._widgets) * 30
        data.x += offset
        data.y += offset
        self._manager.add(data)
        self._spawn_widget(data)

    def _spawn_widget(self, data: NoteData) -> None:
        w = NoteWidget(data)
        w.changed.connect(self._on_note_changed)
        w.closed.connect(self._on_note_closed)
        w.hidden_to_back.connect(self._on_note_hidden)
        self._widgets[data.id] = w
        w.show()

    def _on_note_changed(self, data: NoteData) -> None:
        self._manager.update(data)

    def _on_note_closed(self, note_id: str) -> None:
        self._widgets.pop(note_id, None)
        self._manager.delete(note_id)
        if self._collection_win and self._collection_win.isVisible():
            self._collection_win.refresh()

    def _on_note_hidden(self, note_id: str) -> None:
        pass

    def _show_all(self) -> None:
        for w in self._widgets.values():
            w.bring_to_front()

    # ---- tray events ----

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.create_note()

    def _toggle_autostart(self, checked: bool) -> None:
        NoteManager.set_autostart(checked)

    def _quit(self) -> None:
        self._manager.save()
        if self._collection_win:
            self._collection_win.close()
        for w in list(self._widgets.values()):
            w.close()
        QApplication.quit()
