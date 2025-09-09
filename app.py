"""
ZNLE VNA Control Application
Main entry point for the ZNLE4 Vector Network Analyzer control software
"""

import sys
import os
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.logging_cfg import setup_logging
from ui.main_window import MainWindow
from reusable_theme_system import get_theme_stylesheet


def main():
    """Main application entry point"""
    
    # Setup logging
    log_dir = project_root / "logs"
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / "znle_control.log"
    
    setup_logging(
        log_level="INFO",
        log_file=str(log_file),
        console_output=True
    )
    
    # Create Qt application
    app = QApplication(sys.argv)
    app.setApplicationName("ZNLE VNA Control")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("VNA Control")
    
    # Set application attributes
    app.setAttribute(Qt.ApplicationAttribute.AA_DontShowIconsInMenus, False)
    
    # Set application style to Fusion for best theme compatibility
    app.setStyle('Fusion')
    
    # Apply professional theme - default to light theme
    theme_stylesheet = get_theme_stylesheet("light")
    app.setStyleSheet(theme_stylesheet)
    
    # Create and show main window
    main_window = MainWindow()
    main_window.show()
    
    # Start event loop
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
