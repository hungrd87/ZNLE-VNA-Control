"""
Main window for ZNLE VNA Control application
"""

import sys
import logging
from pathlib import Path
from typing import Dict, Optional

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                            QMenuBar, QMenu, QStatusBar, QFileDialog, QMessageBox,
                            QDockWidget, QSplitter, QTabWidget, QToolBar, QLabel,
                            QGroupBox, QGridLayout)
from PyQt6.QtCore import Qt, QTimer, pyqtSlot
from PyQt6.QtGui import QAction, QIcon

from ui.widgets import (SParameterPlotWidget, ConnectionDialog, SweepConfigWidget,
                     MeasurementControlWidget, MarkerWidget, LoggingDialog)
from core.driver_znle import ZNLE, ZNLEError
from core.model import (InstrumentState, SParameter, MeasurementFormat, 
                         FrequencyRange, SweepConfig)
from core.acquisition import AcquisitionWorker
from core.storage import DataExporter, TouchstoneExporter
from core.logging_cfg import get_logger
from reusable_theme_system import get_theme_stylesheet, get_available_themes

logger = get_logger(__name__)


class MainWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        
        # Initialize components
        self.instrument: Optional[ZNLE] = None
        self.state = InstrumentState()
        self.acquisition_worker: Optional[AcquisitionWorker] = None
        self.current_theme = "light"  # Track current theme
        self.connection_dialog: Optional[ConnectionDialog] = None  # Connection dialog
        self.logging_dialog: Optional[LoggingDialog] = None  # Logging dialog
        
        # Setup UI
        self.setup_ui()
        self.setup_menus()
        self.setup_toolbars()
        self.setup_statusbar()
        
        # Connect signals
        self.connect_signals()
        
        # Initialize
        self.setWindowTitle("ZNLE VNA Control")
        self.resize(1400, 900)
        
        logger.info("Main window initialized")
    
    def setup_ui(self):
        """Setup the main user interface"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QHBoxLayout(central_widget)
        
        # Create splitter for resizable panes
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left panel - Controls
        left_panel = self.create_control_panel()
        splitter.addWidget(left_panel)
        
        # Right panel - Plot
        right_panel = self.create_plot_panel()
        splitter.addWidget(right_panel)
        
        # Set initial splitter sizes (30% controls, 70% plot)
        splitter.setSizes([400, 1000])
        
        main_layout.addWidget(splitter)
        
        # Don't create dock widgets by default anymore
        # LoggingDialog will be created on demand from View menu
    
    def create_control_panel(self) -> QWidget:
        """Create the left control panel"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Create tab widget for organized controls
        tab_widget = QTabWidget()
        
        # Sweep configuration tab
        self.sweep_widget = SweepConfigWidget()
        tab_widget.addTab(self.sweep_widget, "Sweep")
        
        # Measurement control tab
        self.measurement_widget = MeasurementControlWidget()
        tab_widget.addTab(self.measurement_widget, "Measurements")
        
        # Marker control tab
        self.marker_widget = MarkerWidget()
        tab_widget.addTab(self.marker_widget, "Markers")
        
        layout.addWidget(tab_widget)
        
        # Add Status group below tabs
        self.create_status_group(layout)
        
        return panel
    
    def create_status_group(self, parent_layout):
        """Create status group for control panel"""
        from PyQt6.QtGui import QFont
        
        # Status group
        status_group = QGroupBox("Status")
        status_layout = QGridLayout(status_group)
        
        # Status labels
        self.status_labels = {}
        status_items = [
            ("Connection", "Disconnected"),
            ("Sweep Time", "---"),
            ("Points", "---"),
            ("IF BW", "---"),
            ("Acquisition", "Stopped")
        ]
        
        for i, (name, default) in enumerate(status_items):
            status_layout.addWidget(QLabel(f"{name}:"), i, 0)
            label = QLabel(default)
            label.setProperty("class", "status-label")
            label.setFont(QFont("monospace", 9))
            status_layout.addWidget(label, i, 1)
            self.status_labels[name.lower().replace(' ', '_')] = label
        
        parent_layout.addWidget(status_group)
    
    def create_plot_panel(self) -> QWidget:
        """Create the right plot panel"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Plot widget
        self.plot_widget = SParameterPlotWidget()
        layout.addWidget(self.plot_widget)
        
        return panel
    
    def create_logging_dialog(self):
        """Create logging dialog on demand"""
        if self.logging_dialog is not None:
            return  # Already created
            
        # Create logging dialog
        self.logging_dialog = LoggingDialog(self)
        
        # Connect close event to update menu
        self.logging_dialog.finished.connect(self.on_logging_dialog_closed)
        
    def show_logging_dialog(self):
        """Show logging dialog"""
        if self.logging_dialog is None:
            # Create dialog if not exists
            self.create_logging_dialog()
        
        # Show dialog
        self.logging_dialog.show()
        self.logging_dialog.raise_()
        self.logging_dialog.activateWindow()
        self.logging_action.setChecked(True)
    
    def on_logging_dialog_closed(self, result: int):
        """Handle logging dialog close"""
        if hasattr(self, 'logging_action'):
            self.logging_action.setChecked(False)
    
    def log_message(self, message: str):
        """Log message to logging dialog if available"""
        if hasattr(self, 'logging_dialog') and self.logging_dialog is not None:
            self.logging_dialog.add_log_message(message)
    
    def update_status_labels(self, status_dict: dict):
        """Update status labels in control panel"""
        if hasattr(self, 'status_labels'):
            for key, value in status_dict.items():
                if key in self.status_labels:
                    self.status_labels[key].setText(str(value))
    
    def setup_menus(self):
        """Setup application menus"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("&File")
        
        # Export submenu
        export_menu = file_menu.addMenu("&Export")
        
        export_csv_action = QAction("Export &CSV...", self)
        export_csv_action.triggered.connect(self.export_csv)
        export_menu.addAction(export_csv_action)
        
        export_numpy_action = QAction("Export &NumPy...", self)
        export_numpy_action.triggered.connect(self.export_numpy)
        export_menu.addAction(export_numpy_action)
        
        export_s1p_action = QAction("Export &S1P...", self)
        export_s1p_action.triggered.connect(self.export_s1p)
        export_menu.addAction(export_s1p_action)
        
        export_s2p_action = QAction("Export &S2P...", self)
        export_s2p_action.triggered.connect(self.export_s2p)
        export_menu.addAction(export_s2p_action)
        
        file_menu.addSeparator()
        
        # Exit
        exit_action = QAction("E&xit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Tools menu
        tools_menu = menubar.addMenu("&Tools")
        
        # Connection dialog
        connection_action = QAction("&Connection...", self)
        connection_action.triggered.connect(self.show_connection_dialog)
        tools_menu.addAction(connection_action)
        
        tools_menu.addSeparator()
        
        preset_action = QAction("&Preset Instrument", self)
        preset_action.triggered.connect(self.preset_instrument)
        tools_menu.addAction(preset_action)
        
        clear_traces_action = QAction("&Clear Traces", self)
        clear_traces_action.triggered.connect(self.clear_traces)
        tools_menu.addAction(clear_traces_action)
        
        # View menu
        view_menu = menubar.addMenu("&View")
        
        # Theme submenu
        theme_menu = view_menu.addMenu("&Theme")
        
        light_theme_action = QAction("&Light Theme", self)
        light_theme_action.setCheckable(True)
        light_theme_action.setChecked(self.current_theme == "light")
        light_theme_action.triggered.connect(lambda: self.change_theme("light"))
        theme_menu.addAction(light_theme_action)
        
        dark_theme_action = QAction("&Dark Theme", self)
        dark_theme_action.setCheckable(True)
        dark_theme_action.setChecked(self.current_theme == "dark")
        dark_theme_action.triggered.connect(lambda: self.change_theme("dark"))
        theme_menu.addAction(dark_theme_action)
        
        # Store theme actions for mutual exclusivity
        self.theme_actions = {
            "light": light_theme_action,
            "dark": dark_theme_action
        }
        
        view_menu.addSeparator()
        
        # Logging dialog
        logging_action = QAction("&Logging", self)
        logging_action.setCheckable(True)
        logging_action.triggered.connect(self.show_logging_dialog)
        view_menu.addAction(logging_action)
        self.logging_action = logging_action
        
        # Help menu
        help_menu = menubar.addMenu("&Help")
        
        about_action = QAction("&About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def setup_toolbars(self):
        """Setup application toolbars"""
        # Main toolbar
        toolbar = QToolBar("Main")
        self.addToolBar(toolbar)
        
        # Quick connection
        self.quick_connect_label = QLabel("Quick Connect:")
        toolbar.addWidget(self.quick_connect_label)
        
        # Connection status indicator
        self.connection_indicator = QLabel("●")
        self.connection_indicator.setStyleSheet("color: red; font-size: 16px;")
        toolbar.addWidget(self.connection_indicator)
        
        toolbar.addSeparator()
        
        # Quick measurement controls
        self.start_action = QAction("Start", self)
        self.start_action.triggered.connect(self.start_acquisition)
        toolbar.addAction(self.start_action)
        
        self.stop_action = QAction("Stop", self)
        self.stop_action.triggered.connect(self.stop_acquisition)
        toolbar.addAction(self.stop_action)
        
        self.single_action = QAction("Single", self)
        self.single_action.triggered.connect(self.single_measurement)
        toolbar.addAction(self.single_action)
    
    def setup_statusbar(self):
        """Setup status bar"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # Add permanent widgets
        self.sweep_status_label = QLabel("Ready")
        self.status_bar.addPermanentWidget(self.sweep_status_label)
    
    def connect_signals(self):
        """Connect widget signals to slots"""
        # Sweep configuration widget
        self.sweep_widget.config_changed.connect(self.update_sweep_config)
        
        # Measurement control widget
        self.measurement_widget.measurement_added.connect(self.add_measurement)
        self.measurement_widget.measurement_removed.connect(self.remove_measurement)
        self.measurement_widget.start_requested.connect(self.start_acquisition)
        self.measurement_widget.stop_requested.connect(self.stop_acquisition)
        self.measurement_widget.single_requested.connect(self.single_measurement)
        
        # Marker widget
        self.marker_widget.marker_added.connect(self.add_marker)
        self.marker_widget.marker_removed.connect(self.remove_marker)
        
        # Plot widget
        self.plot_widget.marker_added.connect(self.on_plot_marker_added)
        self.plot_widget.marker_removed.connect(self.remove_marker)
    
    @pyqtSlot(str, str)
    def connect_instrument(self, resource: str, backend: str):
        """Connect to instrument"""
        try:
            self.status_bar.showMessage("Connecting to instrument...")
            
            # Create instrument instance
            self.instrument = ZNLE(resource, backend)
            self.instrument.connect()
            
            # Update state
            self.state.connected = True
            self.state.identification = self.instrument.idn()
            self.state.connection_config.resource_string = resource
            self.state.connection_config.visa_backend = backend
            
            # Update UI
            if self.connection_dialog:
                self.connection_dialog.set_connected(True, self.state.identification)
            self.connection_indicator.setStyleSheet("color: green; font-size: 16px;")
            
            # Create acquisition worker
            self.acquisition_worker = AcquisitionWorker(self.instrument, self.state)
            self.acquisition_worker.measurement_ready.connect(self.on_measurement_ready)
            self.acquisition_worker.error_occurred.connect(self.on_acquisition_error)
            self.acquisition_worker.status_changed.connect(self.update_status_labels)
            
            self.status_bar.showMessage(f"Connected: {self.state.identification}", 5000)
            self.log_message(f"Connected to {resource}")
            
            logger.info(f"Connected to instrument: {self.state.identification}")
            
        except Exception as e:
            error_msg = f"Connection failed: {e}"
            self.status_bar.showMessage(error_msg)
            self.log_message(error_msg)
            QMessageBox.critical(self, "Connection Error", error_msg)
            logger.error(error_msg)
    
    @pyqtSlot()
    def disconnect_instrument(self):
        """Disconnect from instrument"""
        try:
            # Stop acquisition first
            if self.acquisition_worker and self.acquisition_worker.running:
                self.stop_acquisition()
            
            # Close instrument connection
            if self.instrument:
                self.instrument.close()
                self.instrument = None
            
            # Update state
            self.state.connected = False
            self.state.identification = ""
            
            # Update UI
            if self.connection_dialog:
                self.connection_dialog.set_connected(False)
            self.connection_indicator.setStyleSheet("color: red; font-size: 16px;")
            
            self.status_bar.showMessage("Disconnected", 3000)
            self.log_message("Disconnected from instrument")
            
            logger.info("Disconnected from instrument")
            
        except Exception as e:
            error_msg = f"Disconnect error: {e}"
            self.log_message(error_msg)
            logger.error(error_msg)
    
    @pyqtSlot(dict)
    def update_sweep_config(self, config: dict):
        """Update sweep configuration"""
        try:
            if not self.instrument:
                return
            
            # Update state
            self.state.sweep_config.frequency.start_hz = config['start_freq']
            self.state.sweep_config.frequency.stop_hz = config['stop_freq']
            self.state.sweep_config.points = config['points']
            self.state.sweep_config.if_bandwidth_hz = config['if_bandwidth']
            self.state.sweep_config.power_dbm = config['power']
            self.state.sweep_config.continuous = config['continuous']
            
            # Apply to instrument
            self.instrument.set_freq_range(
                self.state.sweep_config.frequency.start_hz,
                self.state.sweep_config.frequency.stop_hz
            )
            self.instrument.set_points(self.state.sweep_config.points)
            self.instrument.set_ifbw(self.state.sweep_config.if_bandwidth_hz)
            self.instrument.set_power(self.state.sweep_config.power_dbm)
            
            self.log_message("Sweep configuration updated")
            logger.info("Sweep configuration updated")
            
        except Exception as e:
            error_msg = f"Sweep config error: {e}"
            self.log_message(error_msg)
            QMessageBox.warning(self, "Configuration Error", error_msg)
            logger.error(error_msg)
    
    @pyqtSlot(str, str, str)
    def add_measurement(self, name: str, sparam: str, format_str: str):
        """Add measurement configuration"""
        try:
            # Convert strings to enums
            s_param = SParameter(sparam)
            meas_format = MeasurementFormat(format_str)
            
            # Add to state
            self.state.add_measurement(name, s_param, meas_format)
            
            # Add to acquisition worker if it exists
            if self.acquisition_worker:
                self.acquisition_worker.add_measurement(name, s_param, meas_format)
            
            self.log_message(f"Added measurement: {name} ({sparam})")
            logger.info(f"Added measurement: {name} ({sparam}, {format_str})")
            
        except Exception as e:
            error_msg = f"Add measurement error: {e}"
            self.log_message(error_msg)
            logger.error(error_msg)
    
    @pyqtSlot(str)
    def remove_measurement(self, name: str):
        """Remove measurement configuration"""
        try:
            if name in self.state.measurements:
                del self.state.measurements[name]
            
            if self.acquisition_worker:
                self.acquisition_worker.remove_measurement(name)
            
            self.plot_widget.remove_trace(name)
            
            self.log_message(f"Removed measurement: {name}")
            logger.info(f"Removed measurement: {name}")
            
        except Exception as e:
            error_msg = f"Remove measurement error: {e}"
            self.log_message(error_msg)
            logger.error(error_msg)
    
    @pyqtSlot()
    def start_acquisition(self):
        """Start continuous acquisition"""
        try:
            if not self.instrument or not self.acquisition_worker:
                QMessageBox.warning(self, "Error", "Instrument not connected")
                return
            
            if not self.state.measurements:
                QMessageBox.warning(self, "Error", "No measurements configured")
                return
            
            self.acquisition_worker.start_acquisition()
            self.log_message("Acquisition started")
            logger.info("Acquisition started")
            
        except Exception as e:
            error_msg = f"Start acquisition error: {e}"
            self.log_message(error_msg)
            QMessageBox.critical(self, "Acquisition Error", error_msg)
            logger.error(error_msg)
    
    @pyqtSlot()
    def stop_acquisition(self):
        """Stop continuous acquisition"""
        try:
            if self.acquisition_worker:
                self.acquisition_worker.stop_acquisition()
                self.acquisition_worker.wait_for_stop()
            
            self.log_message("Acquisition stopped")
            logger.info("Acquisition stopped")
            
        except Exception as e:
            error_msg = f"Stop acquisition error: {e}"
            self.log_message(error_msg)
            logger.error(error_msg)
    
    @pyqtSlot()
    def single_measurement(self):
        """Perform single measurement"""
        try:
            if not self.instrument:
                QMessageBox.warning(self, "Error", "Instrument not connected")
                return
            
            if not self.state.measurements:
                QMessageBox.warning(self, "Error", "No measurements configured")
                return
            
            # Stop continuous mode temporarily
            was_continuous = self.state.sweep_config.continuous
            if was_continuous:
                self.instrument.set_continuous(False)
            
            # Trigger single sweep for each measurement
            for name, trace in self.state.measurements.items():
                if trace.active:
                    self.instrument.define_measure(name, trace.sparam.value)
                    self.instrument.select_measure(name)
                    self.instrument.set_format(trace.format.value)
                    self.instrument.trigger_single()
                    
                    # Get data
                    frequency_axis = self.instrument.get_trace_freq_axis()
                    data = self.instrument.fetch_fdata()
                    
                    # Update plot
                    self.plot_widget.add_trace(name, frequency_axis, data)
            
            # Restore continuous mode if it was enabled
            if was_continuous:
                self.instrument.set_continuous(True)
            
            self.log_message("Single measurement completed")
            logger.info("Single measurement completed")
            
        except Exception as e:
            error_msg = f"Single measurement error: {e}"
            self.log_message(error_msg)
            QMessageBox.critical(self, "Measurement Error", error_msg)
            logger.error(error_msg)
    
    @pyqtSlot(str, object, object, float)
    def on_measurement_ready(self, name: str, frequency: object, data: object, timestamp: float):
        """Handle new measurement data"""
        try:
            # Update plot
            self.plot_widget.add_trace(name, frequency, data)
            
            # Update sweep status
            points = len(data) if hasattr(data, '__len__') else 0
            self.sweep_status_label.setText(f"Points: {points}")
            
        except Exception as e:
            logger.error(f"Error handling measurement data: {e}")
    
    @pyqtSlot(str)
    def on_acquisition_error(self, error_msg: str):
        """Handle acquisition errors"""
        self.log_message(f"Acquisition error: {error_msg}")
        QMessageBox.critical(self, "Acquisition Error", error_msg)
    
    @pyqtSlot(int, float)
    def add_marker(self, marker_id: int, frequency: float):
        """Add frequency marker"""
        try:
            self.state.add_marker(marker_id, frequency)
            self.plot_widget.add_marker(marker_id, frequency)
            
            self.log_message(f"Added marker {marker_id} at {frequency:.0f} Hz")
            logger.info(f"Added marker {marker_id} at {frequency:.0f} Hz")
            
        except Exception as e:
            logger.error(f"Error adding marker: {e}")
    
    @pyqtSlot(int, float)
    def on_plot_marker_added(self, marker_id: int, frequency: float):
        """Handle marker added from plot (double-click)"""
        self.marker_widget.add_marker_to_table(marker_id, frequency)
        self.add_marker(marker_id, frequency)
    
    @pyqtSlot(int)
    def remove_marker(self, marker_id: int):
        """Remove frequency marker"""
        try:
            self.state.remove_marker(marker_id)
            self.plot_widget.remove_marker(marker_id)
            
            self.log_message(f"Removed marker {marker_id}")
            logger.info(f"Removed marker {marker_id}")
            
        except Exception as e:
            logger.error(f"Error removing marker: {e}")
    
    def export_csv(self):
        """Export measurement data to CSV"""
        try:
            filename, _ = QFileDialog.getSaveFileName(
                self, "Export CSV", "", "CSV Files (*.csv)"
            )
            if filename:
                traces = list(self.state.measurements.values())
                if traces:
                    DataExporter.export_csv(traces, filename)
                    self.log_message(f"Exported CSV: {filename}")
                else:
                    QMessageBox.warning(self, "Export Warning", "No measurement data to export")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", str(e))
    
    def export_numpy(self):
        """Export measurement data to NumPy format"""
        try:
            filename, _ = QFileDialog.getSaveFileName(
                self, "Export NumPy", "", "NumPy Files (*.npz)"
            )
            if filename:
                traces = list(self.state.measurements.values())
                if traces:
                    DataExporter.export_numpy(traces, filename)
                    self.log_message(f"Exported NumPy: {filename}")
                else:
                    QMessageBox.warning(self, "Export Warning", "No measurement data to export")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", str(e))
    
    def export_s1p(self):
        """Export S1P Touchstone file"""
        try:
            # Find S11 or S22 measurement
            s1p_trace = None
            for trace in self.state.measurements.values():
                if trace.sparam in [SParameter.S11, SParameter.S22]:
                    s1p_trace = trace
                    break
            
            if not s1p_trace:
                QMessageBox.warning(self, "Export Warning", "No S11 or S22 measurement available")
                return
            
            filename, _ = QFileDialog.getSaveFileName(
                self, "Export S1P", "", "Touchstone Files (*.s1p)"
            )
            if filename:
                TouchstoneExporter.export_s1p(s1p_trace, filename)
                self.log_message(f"Exported S1P: {filename}")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", str(e))
    
    def export_s2p(self):
        """Export S2P Touchstone file"""
        try:
            filename, _ = QFileDialog.getSaveFileName(
                self, "Export S2P", "", "Touchstone Files (*.s2p)"
            )
            if filename:
                TouchstoneExporter.export_s2p(self.state.measurements, filename)
                self.log_message(f"Exported S2P: {filename}")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", str(e))
    
    def preset_instrument(self):
        """Preset instrument to default state"""
        try:
            if self.instrument:
                self.instrument.preset()
                self.log_message("Instrument preset completed")
            else:
                QMessageBox.warning(self, "Error", "Instrument not connected")
        except Exception as e:
            QMessageBox.critical(self, "Preset Error", str(e))
    
    def clear_traces(self):
        """Clear all traces from plot"""
        self.plot_widget.clear_traces()
        self.log_message("Traces cleared")
    
    def show_connection_dialog(self):
        """Show connection dialog"""
        if self.connection_dialog is None:
            self.connection_dialog = ConnectionDialog(self)
            # Connect dialog signals
            self.connection_dialog.connect_requested.connect(self.connect_instrument)
            self.connection_dialog.disconnect_requested.connect(self.disconnect_instrument)
        
        # Update dialog status
        if self.instrument and self.instrument.connected:
            self.connection_dialog.set_connected(True, self.state.identification)
        else:
            self.connection_dialog.set_connected(False)
        
        # Show dialog
        self.connection_dialog.exec()
    
    def change_theme(self, theme_name: str):
        """Change application theme"""
        try:
            # Get new theme stylesheet
            stylesheet = get_theme_stylesheet(theme_name)
            
            # Apply to main window and all children
            self.setStyleSheet(stylesheet)
            
            # Update current theme
            self.current_theme = theme_name
            
            # Update theme action checkboxes
            for theme, action in self.theme_actions.items():
                action.setChecked(theme == theme_name)
            
            # Log theme change
            self.log_message(f"Theme changed to {theme_name}")
            logger.info(f"Theme changed to {theme_name}")
            
        except Exception as e:
            QMessageBox.critical(self, "Theme Error", f"Failed to change theme: {str(e)}")
            logger.error(f"Failed to change theme to {theme_name}: {e}")
    
    def show_about(self):
        """Show about dialog"""
        QMessageBox.about(
            self, "About ZNLE VNA Control",
            """
            <h3>ZNLE VNA Control</h3>
            <p>Real-time S-parameter measurement and visualization for R&S ZNLE4 VNA</p>
            <p><b>Features:</b></p>
            <ul>
            <li>VISA/SCPI communication</li>
            <li>Real-time plotting with pyqtgraph</li>
            <li>Data export (CSV, NumPy, Touchstone)</li>
            <li>Frequency markers</li>
            <li>Configurable sweep parameters</li>
            </ul>
            <p><b>Tech Stack:</b> Python, PyQt6, pyqtgraph, RsInstrument</p>
            """
        )
    
    def closeEvent(self, event):
        """Handle application close"""
        try:
            # Stop acquisition
            if self.acquisition_worker and self.acquisition_worker.running:
                self.stop_acquisition()
            
            # Disconnect instrument
            if self.instrument:
                self.disconnect_instrument()
            
            logger.info("Application closing")
            event.accept()
            
        except Exception as e:
            logger.error(f"Error during close: {e}")
            event.accept()  # Close anyway
