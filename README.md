# Sticky Notes

A lightweight desktop sticky notes app for Windows 11 built with Python and PySide6.

## Features

- **Draggable frameless notes** — place anywhere on your desktop
- **Always-on-top** — notes float above other windows
- **Multiple colors** — Yellow, Pink, Blue, Green, Purple, Orange
- **Text formatting** — per-note font family, size, and text color
- **Hide / Send to back** — tuck notes behind windows, bring them back anytime
- **Persistence** — notes auto-save to `%APPDATA%/StickyNotes/notes.json`
- **Collections** — organize notes into named groups via the Manager window
- **System tray** — lives in the tray with quick access to create, show all, or manage notes
- **Auto-start** — optional "Start with Windows" toggle

## Requirements

- Python 3.11+
- Windows 10/11

## Setup

```bash
# Install uv if you don't have it
pip install uv

# Install dependencies
uv sync

# Run
uv run python main.py
```

## Usage

- **New note**: double-click the tray icon or right-click → New Note
- **Drag**: grab the color-dot bar to move a note
- **Resize**: drag the bottom-right corner grip
- **Change color**: click a color dot in the title bar
- **Format text**: use the font/size/color controls below the title bar
- **Hide note**: click ✕ to hide, or "hide" to send behind windows
- **Delete note**: click the trash icon on the note, or use the Manager
- **Manage notes**: right-click tray → Manage Notes (search, collections, show/hide/delete)
- **Auto-start**: right-click tray → Start with Windows
