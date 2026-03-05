from __future__ import annotations

from functools import partial

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QLineEdit,
    QPushButton,
    QLabel,
    QScrollArea,
    QFrame,
    QInputDialog,
    QMessageBox,
    QSplitter,
)

from note_manager import NoteManager, NoteData, COLORS, DEFAULT_COLOR, DEFAULT_COLLECTION

_CARD_STYLE = """
    QFrame {{
        background-color: {bg};
        border-radius: 8px;
        border: 1px solid rgba(0,0,0,0.1);
        color: black;
    }}
    QFrame:hover {{
        border: 1px solid rgba(0,0,0,0.3);
    }}
"""

_BTN_STYLE = """
    QPushButton {
        background: rgba(0,0,0,0.06);
        border: 1px solid rgba(0,0,0,0.12);
        border-radius: 4px;
        padding: 4px 10px;
        font-size: 11px;
        color: black;
    }
    QPushButton:hover {
        background: rgba(0,0,0,0.12);
    }
"""

_SIDEBAR_BTN_STYLE = """
    QPushButton {
        background: rgba(0,0,0,0.05);
        border: 1px solid rgba(0,0,0,0.1);
        border-radius: 4px;
        padding: 3px 8px;
        font-size: 11px;
        color: black;
    }
    QPushButton:hover { background: rgba(0,0,0,0.12); }
"""

_DELETE_BTN_STYLE = """
    QPushButton {
        background: rgba(200,0,0,0.08);
        border: 1px solid rgba(200,0,0,0.2);
        border-radius: 4px;
        padding: 4px 10px;
        font-size: 11px;
        color: #b00;
    }
    QPushButton:hover { background: rgba(200,0,0,0.18); }
"""


class CollectionWindow(QMainWindow):
    request_new_note = Signal(str)       # collection name
    request_show_note = Signal(str)      # note id
    request_hide_note = Signal(str)      # note id
    request_delete_note = Signal(str)    # note id

    def __init__(self, manager: NoteManager, parent: QWidget | None = None):
        super().__init__(parent)
        self._manager = manager
        self._current_collection: str | None = None
        self._search_text = ""

        self.setWindowTitle("Sticky Notes Manager")
        self.setMinimumSize(700, 480)
        self.resize(820, 540)

        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # -- top search bar --
        search_bar = QWidget()
        search_bar.setStyleSheet("QWidget { background: #f5f5f5; color: black; }")
        search_bar.setFixedHeight(44)
        sb_layout = QHBoxLayout(search_bar)
        sb_layout.setContentsMargins(12, 8, 12, 8)

        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Search notes…")
        self._search_input.setClearButtonEnabled(True)
        self._search_input.textChanged.connect(self._on_search)
        self._search_input.setStyleSheet(
            "QLineEdit { background: white; border: 1px solid #ddd; border-radius: 4px; padding: 4px 8px; font-size: 12px; color: black; }"
        )
        sb_layout.addWidget(self._search_input)
        main_layout.addWidget(search_bar)

        # -- splitter: sidebar | cards --
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)

        # sidebar
        sidebar = QWidget()
        sidebar.setFixedWidth(180)
        sidebar.setStyleSheet("QWidget { background: #fafafa; color: black; }")
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(8, 8, 8, 8)
        side_layout.setSpacing(4)

        side_label = QLabel("Collections")
        side_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        side_layout.addWidget(side_label)

        self._coll_list = QListWidget()
        self._coll_list.setStyleSheet(
            """
            QListWidget { background: transparent; border: none; font-size: 12px; color: black; }
            QListWidget::item { padding: 4px 6px; border-radius: 4px; color: black; }
            QListWidget::item:selected { background: rgba(0,0,0,0.1); color: black; }
            QListWidget::item:hover { background: rgba(0,0,0,0.05); }
            """
        )
        self._coll_list.currentItemChanged.connect(self._on_collection_selected)
        side_layout.addWidget(self._coll_list)

        coll_btns = QHBoxLayout()
        coll_btns.setSpacing(4)
        for text, slot in [("Add", self._add_collection), ("Rename", self._rename_collection), ("Del", self._delete_collection)]:
            btn = QPushButton(text)
            btn.setStyleSheet(_SIDEBAR_BTN_STYLE)
            btn.clicked.connect(slot)
            coll_btns.addWidget(btn)
        side_layout.addLayout(coll_btns)

        splitter.addWidget(sidebar)

        # right panel: scrollable card grid
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: white; }")
        self._cards_container = QWidget()
        self._cards_layout = QVBoxLayout(self._cards_container)
        self._cards_layout.setContentsMargins(12, 12, 12, 12)
        self._cards_layout.setSpacing(8)
        self._cards_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll.setWidget(self._cards_container)
        right_layout.addWidget(scroll)

        splitter.addWidget(right)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        main_layout.addWidget(splitter, 1)

        # -- bottom bar --
        bottom = QWidget()
        bottom.setFixedHeight(40)
        bottom.setStyleSheet("QWidget { background: #f5f5f5; border-top: 1px solid #e0e0e0; color: black; }")
        bot_layout = QHBoxLayout(bottom)
        bot_layout.setContentsMargins(12, 4, 12, 4)

        new_btn = QPushButton("+ New Note")
        new_btn.setStyleSheet(_BTN_STYLE)
        new_btn.clicked.connect(self._on_new_note)
        bot_layout.addWidget(new_btn)

        bot_layout.addStretch()
        self._count_label = QLabel()
        self._count_label.setStyleSheet("font-size: 11px; color: #555;")
        bot_layout.addWidget(self._count_label)

        main_layout.addWidget(bottom)

    # ---- refresh ----

    def refresh(self) -> None:
        self._refresh_collections()
        self._refresh_cards()

    def _refresh_collections(self) -> None:
        self._coll_list.blockSignals(True)
        self._coll_list.clear()

        all_item = QListWidgetItem("All Notes")
        all_item.setData(Qt.ItemDataRole.UserRole, None)
        self._coll_list.addItem(all_item)

        for name in self._manager.get_collections():
            item = QListWidgetItem(name)
            item.setData(Qt.ItemDataRole.UserRole, name)
            self._coll_list.addItem(item)

        # restore selection
        for i in range(self._coll_list.count()):
            it = self._coll_list.item(i)
            if it.data(Qt.ItemDataRole.UserRole) == self._current_collection:
                self._coll_list.setCurrentItem(it)
                break
        else:
            self._coll_list.setCurrentRow(0)

        self._coll_list.blockSignals(False)

    def _refresh_cards(self) -> None:
        while self._cards_layout.count():
            child = self._cards_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        notes = self._manager.get_all_notes()

        if self._current_collection is not None:
            notes = [n for n in notes if n.collection == self._current_collection]
        if self._search_text:
            q = self._search_text.lower()
            notes = [n for n in notes if q in n.text.lower()]

        for note in notes:
            card = self._make_card(note)
            self._cards_layout.addWidget(card)

        self._count_label.setText(f"{len(notes)} note{'s' if len(notes) != 1 else ''}")

    @staticmethod
    def _note_title(note: NoteData) -> str:
        first_line = note.text.split("\n", 1)[0].strip()
        return first_line[:50] if first_line else "Untitled"

    def _make_card(self, note: NoteData) -> QFrame:
        bg = COLORS.get(note.color, COLORS[DEFAULT_COLOR])
        card = QFrame()
        card.setFixedHeight(40)
        card.setStyleSheet(_CARD_STYLE.format(bg=bg))

        layout = QHBoxLayout(card)
        layout.setContentsMargins(12, 4, 8, 4)
        layout.setSpacing(8)

        title = QLabel(self._note_title(note))
        title.setStyleSheet("font-size: 12px; font-weight: bold; background: transparent; border: none; color: black;")
        layout.addWidget(title, 1)

        show_btn = QPushButton("Show")
        show_btn.setStyleSheet(_BTN_STYLE)
        show_btn.setFixedSize(50, 26)
        show_btn.clicked.connect(partial(self.request_show_note.emit, note.id))
        layout.addWidget(show_btn)

        hide_btn = QPushButton("Hide")
        hide_btn.setStyleSheet(_BTN_STYLE)
        hide_btn.setFixedSize(50, 26)
        hide_btn.clicked.connect(partial(self.request_hide_note.emit, note.id))
        layout.addWidget(hide_btn)

        del_btn = QPushButton("Del")
        del_btn.setStyleSheet(_DELETE_BTN_STYLE)
        del_btn.setFixedSize(40, 26)
        del_btn.clicked.connect(partial(self.request_delete_note.emit, note.id))
        layout.addWidget(del_btn)

        return card

    # ---- slots ----

    def _on_collection_selected(self, current: QListWidgetItem | None, _prev: QListWidgetItem | None) -> None:
        if current is None:
            return
        self._current_collection = current.data(Qt.ItemDataRole.UserRole)
        self._refresh_cards()

    def _on_search(self, text: str) -> None:
        self._search_text = text.strip()
        self._refresh_cards()

    def _on_new_note(self) -> None:
        coll = self._current_collection or DEFAULT_COLLECTION
        self.request_new_note.emit(coll)

    # ---- collection CRUD ----

    def _add_collection(self) -> None:
        name, ok = QInputDialog.getText(self, "New Collection", "Collection name:")
        if ok and name.strip():
            if self._manager.add_collection(name.strip()):
                self.refresh()
            else:
                QMessageBox.warning(self, "Error", "Collection already exists.")

    def _rename_collection(self) -> None:
        item = self._coll_list.currentItem()
        if not item:
            return
        old = item.data(Qt.ItemDataRole.UserRole)
        if old is None or old == DEFAULT_COLLECTION:
            QMessageBox.information(self, "Info", "Cannot rename this collection.")
            return
        new, ok = QInputDialog.getText(self, "Rename Collection", "New name:", text=old)
        if ok and new.strip():
            if self._manager.rename_collection(old, new.strip()):
                self._current_collection = new.strip()
                self.refresh()
            else:
                QMessageBox.warning(self, "Error", "Name already in use or invalid.")

    def _delete_collection(self) -> None:
        item = self._coll_list.currentItem()
        if not item:
            return
        name = item.data(Qt.ItemDataRole.UserRole)
        if name is None or name == DEFAULT_COLLECTION:
            QMessageBox.information(self, "Info", "Cannot delete this collection.")
            return
        reply = QMessageBox.question(
            self, "Delete Collection",
            f'Delete "{name}"? Notes will be moved to Default.',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._manager.delete_collection(name)
            self._current_collection = None
            self.refresh()
