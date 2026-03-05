import sys

from PySide6.QtWidgets import QApplication

from tray import SystemTrayApp


def main() -> None:
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    tray_app = SystemTrayApp()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
