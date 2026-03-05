from __future__ import annotations

import json
import os
import sys
import uuid
import winreg
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List

APP_NAME = "StickyNotes"
REGISTRY_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"

COLORS = {
    "yellow": "#fff9c4",
    "pink": "#f8bbd0",
    "blue": "#bbdefb",
    "green": "#c8e6c9",
    "purple": "#e1bee7",
    "orange": "#ffe0b2",
}

DEFAULT_COLOR = "yellow"
DEFAULT_WIDTH = 350
DEFAULT_HEIGHT = 350
DEFAULT_COLLECTION = "Default"


@dataclass
class NoteData:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    text: str = ""
    color: str = DEFAULT_COLOR
    x: int = 200
    y: int = 200
    width: int = DEFAULT_WIDTH
    height: int = DEFAULT_HEIGHT
    font_family: str = "Segoe UI"
    font_size: int = 11
    font_color: str = "#000000"
    collection: str = DEFAULT_COLLECTION


class NoteManager:
    def __init__(self) -> None:
        self._data_dir = Path(os.environ.get("APPDATA", ".")) / APP_NAME
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._data_file = self._data_dir / "notes.json"
        self._collections_file = self._data_dir / "collections.json"
        self._notes: Dict[str, NoteData] = {}
        self._collections: List[str] = [DEFAULT_COLLECTION]

    # ---- notes persistence ----

    def load(self) -> List[NoteData]:
        if self._data_file.exists():
            try:
                raw = json.loads(self._data_file.read_text(encoding="utf-8"))
                for item in raw:
                    note = NoteData(**{k: v for k, v in item.items() if k in NoteData.__dataclass_fields__})
                    self._notes[note.id] = note
            except (json.JSONDecodeError, TypeError, KeyError):
                pass
        self._load_collections()
        return list(self._notes.values())

    def save(self) -> None:
        payload = [asdict(n) for n in self._notes.values()]
        self._data_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def add(self, note: NoteData) -> None:
        self._notes[note.id] = note
        self.save()

    def update(self, note: NoteData) -> None:
        self._notes[note.id] = note
        self.save()

    def delete(self, note_id: str) -> None:
        self._notes.pop(note_id, None)
        self.save()

    def get_all_notes(self) -> List[NoteData]:
        return list(self._notes.values())

    # ---- collections persistence ----

    def _load_collections(self) -> None:
        if self._collections_file.exists():
            try:
                self._collections = json.loads(self._collections_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, TypeError):
                self._collections = [DEFAULT_COLLECTION]
        if DEFAULT_COLLECTION not in self._collections:
            self._collections.insert(0, DEFAULT_COLLECTION)
        for note in self._notes.values():
            if note.collection not in self._collections:
                self._collections.append(note.collection)

    def _save_collections(self) -> None:
        self._collections_file.write_text(json.dumps(self._collections, indent=2), encoding="utf-8")

    def get_collections(self) -> List[str]:
        return list(self._collections)

    def add_collection(self, name: str) -> bool:
        if name and name not in self._collections:
            self._collections.append(name)
            self._save_collections()
            return True
        return False

    def rename_collection(self, old_name: str, new_name: str) -> bool:
        if old_name == DEFAULT_COLLECTION or not new_name or new_name in self._collections:
            return False
        if old_name in self._collections:
            idx = self._collections.index(old_name)
            self._collections[idx] = new_name
            for note in self._notes.values():
                if note.collection == old_name:
                    note.collection = new_name
            self._save_collections()
            self.save()
            return True
        return False

    def delete_collection(self, name: str) -> bool:
        if name == DEFAULT_COLLECTION or name not in self._collections:
            return False
        self._collections.remove(name)
        for note in self._notes.values():
            if note.collection == name:
                note.collection = DEFAULT_COLLECTION
        self._save_collections()
        self.save()
        return True

    # ---- auto-start helpers ----

    @staticmethod
    def _exe_path() -> str:
        if getattr(sys, "frozen", False):
            return sys.executable
        return f'"{sys.executable}" "{os.path.abspath("main.py")}"'

    @staticmethod
    def is_autostart_enabled() -> bool:
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_KEY, 0, winreg.KEY_READ)
            winreg.QueryValueEx(key, APP_NAME)
            winreg.CloseKey(key)
            return True
        except FileNotFoundError:
            return False
        except OSError:
            return False

    @classmethod
    def set_autostart(cls, enabled: bool) -> None:
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_KEY, 0, winreg.KEY_SET_VALUE)
            if enabled:
                winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, cls._exe_path())
            else:
                try:
                    winreg.DeleteValue(key, APP_NAME)
                except FileNotFoundError:
                    pass
            winreg.CloseKey(key)
        except OSError:
            pass
