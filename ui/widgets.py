"""
Custom widgets for ZNLE VNA Control GUI
"""

import numpy as np
import pyqtgraph as pg
from typing import Dict, List, Optional, Tuple
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QLineEdit, QPushButton, QComboBox, QSpinBox,
                            QDoubleSpinBox, QGroupBox, QGridLayout, QCheckBox,
                            QTableWidget, QTableWidgetItem, QHeaderView,
                            QTextEdit, QSplitter, QTabWidget, QDialog)
from PyQt6.QtCore import pyqtSignal, Qt, QTimer
from PyQt6.QtGui import QFont

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from core.model import SParameter, MeasurementFormat, Marker


class SParameterPlotWidget(QWidget):
    """Widget for plotting S-parameter measurements"""
    
    marker_added = pyqtSignal(int, float)  # marker_id, frequency
    marker_removed = pyqtSignal(int)  # marker_id
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.traces = {}  # name -> plot_item
        self.markers = {}  # marker_id -> marker_item
        self.crosshair_enabled = True
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Create plot widget
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setLabel('left', 'Magnitude', 'dB')
        self.plot_widget.setLabel('bottom', 'Frequency', 'Hz')
        self.plot_widget.setTitle('S-Parameter Measurements')
        self.plot_widget.showGrid(x=True, y=True)
        self.plot_widget.addLegend()
        
        # Enable auto-range
        self.plot_widget.enableAutoRange()
        
        # Add crosshair
        self.crosshair_v = pg.InfiniteLine(angle=90, movable=False, pen='y')
        self.crosshair_h = pg.InfiniteLine(angle=0, movable=False, pen='y')
        self.plot_widget.addItem(self.crosshair_v, ignoreBounds=True)
        self.plot_widget.addItem(self.crosshair_h, ignoreBounds=True)
        
        # Connect mouse events
        self.plot_widget.scene().sigMouseMoved.connect(self.on_mouse_moved)
        self.plot_widget.scene().sigMouseClicked.connect(self.on_mouse_clicked)
        
        layout.addWidget(self.plot_widget)
    
    def add_trace(self, name: str, frequency: np.ndarray, data: np.ndarray, 
                 color: str = None, line_style: str = '-') -> None:
        """Add or update a measurement trace"""
        if name in self.traces:
            # Update existing trace
            self.traces[name].setData(frequency, data)
        else:
            # Create new trace
            pen = pg.mkPen(color=color, width=2, style=line_style)
            plot_item = self.plot_widget.plot(frequency, data, pen=pen, name=name)
            self.traces[name] = plot_item
    
    def remove_trace(self, name: str) -> None:
        """Remove a measurement trace"""
        if name in self.traces:
            self.plot_widget.removeItem(self.traces[name])
            del self.traces[name]
    
    def clear_traces(self) -> None:
        """Clear all measurement traces"""
        for trace in self.traces.values():
            self.plot_widget.removeItem(trace)
        self.traces.clear()
    
    def add_marker(self, marker_id: int, frequency: float, 
                  color: str = 'red') -> None:
        """Add a frequency marker"""
        if marker_id in self.markers:
            # Update existing marker
            self.markers[marker_id].setPos(frequency)
        else:
            # Create new marker
            marker_line = pg.InfiniteLine(
                pos=frequency, angle=90, movable=True,
                pen=pg.mkPen(color=color, width=2, style=Qt.PenStyle.DashLine),
                label=f'M{marker_id}'
            )
            marker_line.sigPositionChanged.connect(
                lambda: self.on_marker_moved(marker_id)
            )
            self.plot_widget.addItem(marker_line)
            self.markers[marker_id] = marker_line
    
    def remove_marker(self, marker_id: int) -> None:
        """Remove a frequency marker"""
        if marker_id in self.markers:
            self.plot_widget.removeItem(self.markers[marker_id])
            del self.markers[marker_id]
            self.marker_removed.emit(marker_id)
    
    def on_mouse_moved(self, evt):
        """Handle mouse movement for crosshair"""
        if self.crosshair_enabled:
            pos = evt
            if self.plot_widget.sceneBoundingRect().contains(pos):
                mouse_point = self.plot_widget.plotItem.vb.mapSceneToView(pos)
                self.crosshair_v.setPos(mouse_point.x())
                self.crosshair_h.setPos(mouse_point.y())
    
    def on_mouse_clicked(self, evt):
        """Handle mouse clicks for marker placement"""
        if evt.double():  # Double-click to add marker
            pos = evt.scenePos()
            if self.plot_widget.sceneBoundingRect().contains(pos):
                mouse_point = self.plot_widget.plotItem.vb.mapSceneToView(pos)
                frequency = mouse_point.x()
                
                # Find next available marker ID
                marker_id = 1
                while marker_id in self.markers:
                    marker_id += 1
                
                self.add_marker(marker_id, frequency)
                self.marker_added.emit(marker_id, frequency)
    
    def on_marker_moved(self, marker_id: int):
        """Handle marker movement"""
        if marker_id in self.markers:
            frequency = self.markers[marker_id].value()
            self.marker_added.emit(marker_id, frequency)  # Reuse signal for updates
    
    def set_crosshair_enabled(self, enabled: bool) -> None:
        """Enable/disable crosshair"""
        self.crosshair_enabled = enabled
        self.crosshair_v.setVisible(enabled)
        self.crosshair_h.setVisible(enabled)


class ConnectionWidget(QWidget):
    """Widget for instrument connection configuration"""
    
    connect_requested = pyqtSignal(str, str)  # resource_string, visa_backend
    disconnect_requested = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Connection group
        conn_group = QGroupBox("Instrument Connection")
        conn_layout = QGridLayout(conn_group)
        
        # Resource string
        conn_layout.addWidget(QLabel("Resource:"), 0, 0)
        self.resource_edit = QLineEdit("TCPIP::192.168.1.100::hislip0::INSTR")
        conn_layout.addWidget(self.resource_edit, 0, 1)
        
        # VISA backend
        conn_layout.addWidget(QLabel("VISA Backend:"), 1, 0)
        self.visa_combo = QComboBox()
        self.visa_combo.addItems(["rs", "ni", "keysight"])
        conn_layout.addWidget(self.visa_combo, 1, 1)
        
        # Connect/Disconnect buttons
        button_layout = QHBoxLayout()
        self.connect_btn = QPushButton("Connect")
        self.disconnect_btn = QPushButton("Disconnect")
        self.disconnect_btn.setEnabled(False)
        
        self.connect_btn.clicked.connect(self.on_connect_clicked)
        self.disconnect_btn.clicked.connect(self.on_disconnect_clicked)
        
        button_layout.addWidget(self.connect_btn)
        button_layout.addWidget(self.disconnect_btn)
        conn_layout.addLayout(button_layout, 2, 0, 1, 2)
        
        # Status label
        self.status_label = QLabel("Disconnected")
        self.status_label.setStyleSheet("color: red;")
        conn_layout.addWidget(self.status_label, 3, 0, 1, 2)
        
        layout.addWidget(conn_group)
    
    def on_connect_clicked(self):
        resource = self.resource_edit.text().strip()
        backend = self.visa_combo.currentText()
        if resource:
            self.connect_requested.emit(resource, backend)
    
    def on_disconnect_clicked(self):
        self.disconnect_requested.emit()
    
    def set_connected(self, connected: bool, status_text: str = ""):
        """Update connection status"""
        self.connect_btn.setEnabled(not connected)
        self.disconnect_btn.setEnabled(connected)
        
        if connected:
            self.status_label.setText(f"Connected: {status_text}")
            self.status_label.setStyleSheet("color: green;")
        else:
            self.status_label.setText(f"Disconnected: {status_text}")
            self.status_label.setStyleSheet("color: red;")


class SweepConfigWidget(QWidget):
    """Widget for sweep configuration"""
    
    config_changed = pyqtSignal(dict)  # Configuration dictionary
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Sweep configuration group
        sweep_group = QGroupBox("Sweep Configuration")
        sweep_layout = QGridLayout(sweep_group)
        
        # Frequency range
        sweep_layout.addWidget(QLabel("Start Freq (Hz):"), 0, 0)
        self.start_freq_edit = QDoubleSpinBox()
        self.start_freq_edit.setRange(1e3, 100e9)
        self.start_freq_edit.setValue(1e9)
        self.start_freq_edit.setDecimals(0)
        self.start_freq_edit.setSuffix(" Hz")
        sweep_layout.addWidget(self.start_freq_edit, 0, 1)
        
        sweep_layout.addWidget(QLabel("Stop Freq (Hz):"), 1, 0)
        self.stop_freq_edit = QDoubleSpinBox()
        self.stop_freq_edit.setRange(1e3, 100e9)
        self.stop_freq_edit.setValue(2e9)
        self.stop_freq_edit.setDecimals(0)
        self.stop_freq_edit.setSuffix(" Hz")
        sweep_layout.addWidget(self.stop_freq_edit, 1, 1)
        
        # Points
        sweep_layout.addWidget(QLabel("Points:"), 2, 0)
        self.points_spin = QSpinBox()
        self.points_spin.setRange(2, 100001)
        self.points_spin.setValue(801)
        sweep_layout.addWidget(self.points_spin, 2, 1)
        
        # IF Bandwidth
        sweep_layout.addWidget(QLabel("IF BW (Hz):"), 3, 0)
        self.ifbw_edit = QDoubleSpinBox()
        self.ifbw_edit.setRange(1, 1e6)
        self.ifbw_edit.setValue(3000)
        self.ifbw_edit.setDecimals(0)
        self.ifbw_edit.setSuffix(" Hz")
        sweep_layout.addWidget(self.ifbw_edit, 3, 1)
        
        # Power
        sweep_layout.addWidget(QLabel("Power (dBm):"), 4, 0)
        self.power_edit = QDoubleSpinBox()
        self.power_edit.setRange(-40, 20)
        self.power_edit.setValue(-10)
        self.power_edit.setDecimals(1)
        self.power_edit.setSuffix(" dBm")
        sweep_layout.addWidget(self.power_edit, 4, 1)
        
        # Continuous mode
        self.continuous_check = QCheckBox("Continuous Sweep")
        self.continuous_check.setChecked(True)
        sweep_layout.addWidget(self.continuous_check, 5, 0, 1, 2)
        
        # Apply button
        self.apply_btn = QPushButton("Apply Configuration")
        self.apply_btn.clicked.connect(self.on_apply_clicked)
        sweep_layout.addWidget(self.apply_btn, 6, 0, 1, 2)
        
        layout.addWidget(sweep_group)
        
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
        
        layout.addWidget(status_group)
        
        # Connect change signals
        self.start_freq_edit.valueChanged.connect(self.on_config_changed)
        self.stop_freq_edit.valueChanged.connect(self.on_config_changed)
        self.points_spin.valueChanged.connect(self.on_config_changed)
        self.ifbw_edit.valueChanged.connect(self.on_config_changed)
        self.power_edit.valueChanged.connect(self.on_config_changed)
        self.continuous_check.toggled.connect(self.on_config_changed)
    
    def on_apply_clicked(self):
        self.on_config_changed()
    
    def on_config_changed(self):
        config = {
            'start_freq': self.start_freq_edit.value(),
            'stop_freq': self.stop_freq_edit.value(),
            'points': self.points_spin.value(),
            'if_bandwidth': self.ifbw_edit.value(),
            'power': self.power_edit.value(),
            'continuous': self.continuous_check.isChecked()
        }
        self.config_changed.emit(config)
    
    def set_config(self, config: dict):
        """Update widget with configuration values"""
        self.start_freq_edit.setValue(config.get('start_freq', 1e9))
        self.stop_freq_edit.setValue(config.get('stop_freq', 2e9))
        self.points_spin.setValue(config.get('points', 801))
        self.ifbw_edit.setValue(config.get('if_bandwidth', 3000))
        self.power_edit.setValue(config.get('power', -10))
        self.continuous_check.setChecked(config.get('continuous', True))
    
    def update_status_labels(self, status_dict: dict):
        """Update status labels with new values"""
        for key, value in status_dict.items():
            if key in self.status_labels:
                self.status_labels[key].setText(str(value))


class MeasurementControlWidget(QWidget):
    """Widget for measurement control and configuration"""
    
    measurement_added = pyqtSignal(str, str, str)  # name, sparam, format
    measurement_removed = pyqtSignal(str)  # name
    start_requested = pyqtSignal()
    stop_requested = pyqtSignal()
    single_requested = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Measurement control group
        control_group = QGroupBox("Measurement Control")
        control_layout = QGridLayout(control_group)
        
        # Control buttons
        self.start_btn = QPushButton("Start")
        self.stop_btn = QPushButton("Stop")
        self.single_btn = QPushButton("Single")
        
        self.start_btn.clicked.connect(self.start_requested.emit)
        self.stop_btn.clicked.connect(self.stop_requested.emit)
        self.single_btn.clicked.connect(self.single_requested.emit)
        
        control_layout.addWidget(self.start_btn, 0, 0)
        control_layout.addWidget(self.stop_btn, 0, 1)
        control_layout.addWidget(self.single_btn, 0, 2)
        
        layout.addWidget(control_group)
        
        # Measurement setup group
        setup_group = QGroupBox("Add Measurement")
        setup_layout = QGridLayout(setup_group)
        
        # Measurement name
        setup_layout.addWidget(QLabel("Name:"), 0, 0)
        self.name_edit = QLineEdit("Meas1")
        setup_layout.addWidget(self.name_edit, 0, 1)
        
        # S-parameter
        setup_layout.addWidget(QLabel("Parameter:"), 1, 0)
        self.sparam_combo = QComboBox()
        self.sparam_combo.addItems(["S11", "S12", "S21", "S22"])
        setup_layout.addWidget(self.sparam_combo, 1, 1)
        
        # Format
        setup_layout.addWidget(QLabel("Format:"), 2, 0)
        self.format_combo = QComboBox()
        self.format_combo.addItems(["MLOG", "PHAS", "REAL", "IMAG", "SMIT"])
        setup_layout.addWidget(self.format_combo, 2, 1)
        
        # Add button
        self.add_btn = QPushButton("Add Measurement")
        self.add_btn.clicked.connect(self.on_add_measurement)
        setup_layout.addWidget(self.add_btn, 3, 0, 1, 2)
        
        layout.addWidget(setup_group)
        
        # Active measurements list
        measurements_group = QGroupBox("Active Measurements")
        measurements_layout = QVBoxLayout(measurements_group)
        
        self.measurements_table = QTableWidget()
        self.measurements_table.setColumnCount(4)
        self.measurements_table.setHorizontalHeaderLabels(["Name", "Parameter", "Format", "Action"])
        self.measurements_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        measurements_layout.addWidget(self.measurements_table)
        
        layout.addWidget(measurements_group)
    
    def on_add_measurement(self):
        name = self.name_edit.text().strip()
        sparam = self.sparam_combo.currentText()
        format_val = self.format_combo.currentText()
        
        if name:
            self.measurement_added.emit(name, sparam, format_val)
            self.add_measurement_to_table(name, sparam, format_val)
    
    def add_measurement_to_table(self, name: str, sparam: str, format_val: str):
        """Add measurement to the table"""
        row = self.measurements_table.rowCount()
        self.measurements_table.insertRow(row)
        
        self.measurements_table.setItem(row, 0, QTableWidgetItem(name))
        self.measurements_table.setItem(row, 1, QTableWidgetItem(sparam))
        self.measurements_table.setItem(row, 2, QTableWidgetItem(format_val))
        
        # Remove button
        remove_btn = QPushButton("Remove")
        remove_btn.clicked.connect(lambda: self.remove_measurement(name))
        self.measurements_table.setCellWidget(row, 3, remove_btn)
    
    def remove_measurement(self, name: str):
        """Remove measurement from table and emit signal"""
        for row in range(self.measurements_table.rowCount()):
            if self.measurements_table.item(row, 0).text() == name:
                self.measurements_table.removeRow(row)
                break
        self.measurement_removed.emit(name)


class MarkerWidget(QWidget):
    """Widget for marker control"""
    
    marker_added = pyqtSignal(int, float)  # marker_id, frequency
    marker_removed = pyqtSignal(int)  # marker_id
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Marker group
        marker_group = QGroupBox("Markers")
        marker_layout = QVBoxLayout(marker_group)
        
        # Add marker controls
        add_layout = QHBoxLayout()
        add_layout.addWidget(QLabel("Frequency (Hz):"))
        self.freq_edit = QDoubleSpinBox()
        self.freq_edit.setRange(1e3, 100e9)
        self.freq_edit.setValue(1.5e9)
        self.freq_edit.setDecimals(0)
        add_layout.addWidget(self.freq_edit)
        
        self.add_marker_btn = QPushButton("Add Marker")
        self.add_marker_btn.clicked.connect(self.on_add_marker)
        add_layout.addWidget(self.add_marker_btn)
        
        marker_layout.addLayout(add_layout)
        
        # Marker table
        self.marker_table = QTableWidget()
        self.marker_table.setColumnCount(3)
        self.marker_table.setHorizontalHeaderLabels(["ID", "Frequency (Hz)", "Action"])
        self.marker_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        marker_layout.addWidget(self.marker_table)
        
        layout.addWidget(marker_group)
    
    def on_add_marker(self):
        frequency = self.freq_edit.value()
        
        # Find next available marker ID
        marker_id = 1
        used_ids = set()
        for row in range(self.marker_table.rowCount()):
            used_ids.add(int(self.marker_table.item(row, 0).text()))
        
        while marker_id in used_ids:
            marker_id += 1
        
        self.marker_added.emit(marker_id, frequency)
        self.add_marker_to_table(marker_id, frequency)
    
    def add_marker_to_table(self, marker_id: int, frequency: float):
        """Add marker to the table"""
        row = self.marker_table.rowCount()
        self.marker_table.insertRow(row)
        
        self.marker_table.setItem(row, 0, QTableWidgetItem(str(marker_id)))
        self.marker_table.setItem(row, 1, QTableWidgetItem(f"{frequency:.0f}"))
        
        # Remove button
        remove_btn = QPushButton("Remove")
        remove_btn.clicked.connect(lambda: self.remove_marker(marker_id))
        self.marker_table.setCellWidget(row, 2, remove_btn)
    
    def remove_marker(self, marker_id: int):
        """Remove marker from table and emit signal"""
        for row in range(self.marker_table.rowCount()):
            if int(self.marker_table.item(row, 0).text()) == marker_id:
                self.marker_table.removeRow(row)
                break
        self.marker_removed.emit(marker_id)


class LoggingDialog(QDialog):
    """Dialog for displaying application logs"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Application Logging")
        self.setModal(False)  # Non-modal dialog
        self.resize(600, 400)
        self.setup_ui()
        
        # Update timer for auto-scroll
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_display)
        self.update_timer.start(1000)  # Update every second
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Log display group
        log_group = QGroupBox("Application Log Messages")
        log_layout = QVBoxLayout(log_group)
        
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setFont(QFont("monospace", 9))
        self.log_display.setPlaceholderText("Application logs will appear here...")
        log_layout.addWidget(self.log_display)
        
        # Log controls
        controls_layout = QHBoxLayout()
        
        self.clear_btn = QPushButton("Clear Log")
        self.clear_btn.clicked.connect(self.clear_log)
        controls_layout.addWidget(self.clear_btn)
        
        self.save_btn = QPushButton("Save Log...")
        self.save_btn.clicked.connect(self.save_log)
        controls_layout.addWidget(self.save_btn)
        
        controls_layout.addStretch()
        
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.close)
        controls_layout.addWidget(self.close_btn)
        
        log_layout.addLayout(controls_layout)
        layout.addWidget(log_group)
    
    def add_log_message(self, message: str):
        """Add message to log display"""
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        self.log_display.append(formatted_message)
        
        # Keep log size manageable
        document = self.log_display.document()
        if document and document.lineCount() > 500:
            cursor = self.log_display.textCursor()
            cursor.movePosition(cursor.MoveOperation.Start)
            cursor.movePosition(cursor.MoveOperation.Down, cursor.MoveMode.KeepAnchor, 50)
            cursor.removeSelectedText()
    
    def clear_log(self):
        """Clear log display"""
        self.log_display.clear()
        self.add_log_message("Log cleared")
    
    def save_log(self):
        """Save log to file"""
        from PyQt6.QtWidgets import QFileDialog
        from datetime import datetime
        
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Log File",
            f"znle_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            "Text Files (*.txt);;All Files (*)"
        )
        
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(self.log_display.toPlainText())
                self.add_log_message(f"Log saved to: {filename}")
            except Exception as e:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "Save Error", f"Failed to save log: {str(e)}")
    
    def update_display(self):
        """Periodic update of display elements"""
        # Auto-scroll log to bottom if at or near bottom
        scrollbar = self.log_display.verticalScrollBar()
        if scrollbar and scrollbar.value() >= scrollbar.maximum() - 10:
            scrollbar.setValue(scrollbar.maximum())


# Legacy StatusWidget for backward compatibility (only log functionality)
class StatusWidget(QWidget):
    """Simplified widget for log display only (for dock widget compatibility)"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Log display only
        log_group = QGroupBox("Log")
        log_layout = QVBoxLayout(log_group)
        
        self.log_display = QTextEdit()
        self.log_display.setMaximumHeight(150)
        self.log_display.setReadOnly(True)
        self.log_display.setFont(QFont("monospace", 9))
        log_layout.addWidget(self.log_display)
        
        layout.addWidget(log_group)
    
    def add_log_message(self, message: str):
        """Add message to log display"""
        self.log_display.append(message)
        # Keep log size manageable
        document = self.log_display.document()
        if document and document.lineCount() > 100:
            cursor = self.log_display.textCursor()
            cursor.movePosition(cursor.MoveOperation.Start)
            cursor.movePosition(cursor.MoveOperation.Down, cursor.MoveMode.KeepAnchor, 10)
            cursor.removeSelectedText()


class ConnectionDialog(QDialog):
    """Dialog for instrument connection configuration"""
    
    connect_requested = pyqtSignal(str, str)  # resource_string, visa_backend
    disconnect_requested = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Instrument Connection")
        self.setModal(True)
        self.setFixedSize(450, 300)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Connection group
        conn_group = QGroupBox("ZNLE4 Instrument Connection")
        conn_layout = QGridLayout(conn_group)
        
        # Resource string
        conn_layout.addWidget(QLabel("Resource String:"), 0, 0)
        self.resource_edit = QLineEdit("TCPIP::192.168.1.100::hislip0::INSTR")
        self.resource_edit.setToolTip("VISA resource string for the instrument")
        conn_layout.addWidget(self.resource_edit, 0, 1)
        
        # VISA backend
        conn_layout.addWidget(QLabel("VISA Backend:"), 1, 0)
        self.visa_combo = QComboBox()
        self.visa_combo.addItems(["rs", "ni", "keysight"])
        self.visa_combo.setToolTip("VISA implementation to use")
        conn_layout.addWidget(self.visa_combo, 1, 1)
        
        # Protocol info
        info_label = QLabel("""
        <b>Supported Protocols:</b><br>
        • HiSLIP: TCPIP::&lt;ip&gt;::hislip0::INSTR (Recommended)<br>
        • VXI-11: TCPIP::&lt;ip&gt;::inst0::INSTR<br>
        • USB-TMC: USB0::&lt;vendor&gt;::&lt;product&gt;::&lt;serial&gt;::INSTR
        """)
        info_label.setWordWrap(True)
        info_label.setStyleSheet("QLabel { background-color: #f0f0f0; padding: 10px; border-radius: 4px; }")
        conn_layout.addWidget(info_label, 2, 0, 1, 2)
        
        # Current status
        conn_layout.addWidget(QLabel("Status:"), 3, 0)
        self.status_label = QLabel("Disconnected")
        self.status_label.setProperty("class", "status-label")
        conn_layout.addWidget(self.status_label, 3, 1)
        
        layout.addWidget(conn_group)
        
        # Button layout
        button_layout = QHBoxLayout()
        
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.setDefault(True)
        self.disconnect_btn = QPushButton("Disconnect")
        self.disconnect_btn.setEnabled(False)
        
        self.test_btn = QPushButton("Test Connection")
        self.close_btn = QPushButton("Close")
        
        # Connect signals
        self.connect_btn.clicked.connect(self.on_connect_clicked)
        self.disconnect_btn.clicked.connect(self.on_disconnect_clicked)
        self.test_btn.clicked.connect(self.on_test_clicked)
        self.close_btn.clicked.connect(self.accept)
        
        button_layout.addWidget(self.connect_btn)
        button_layout.addWidget(self.disconnect_btn)
        button_layout.addWidget(self.test_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.close_btn)
        
        layout.addLayout(button_layout)
    
    def on_connect_clicked(self):
        """Handle connect button click"""
        resource = self.resource_edit.text().strip()
        backend = self.visa_combo.currentText()
        if resource:
            self.connect_requested.emit(resource, backend)
    
    def on_disconnect_clicked(self):
        """Handle disconnect button click"""
        self.disconnect_requested.emit()
    
    def on_test_clicked(self):
        """Handle test connection button click"""
        # For now, just trigger a connection attempt
        self.on_connect_clicked()
    
    def set_connected(self, connected: bool, status_text: str = ""):
        """Update connection status"""
        self.connect_btn.setEnabled(not connected)
        self.disconnect_btn.setEnabled(connected)
        self.test_btn.setEnabled(not connected)
        
        if connected:
            self.status_label.setText(f"Connected: {status_text}")
            self.status_label.setStyleSheet("color: green; font-weight: bold;")
        else:
            self.status_label.setText(f"Disconnected: {status_text}")
            self.status_label.setStyleSheet("color: red; font-weight: bold;")
    
    def get_connection_info(self) -> tuple:
        """Get current connection parameters"""
        return self.resource_edit.text().strip(), self.visa_combo.currentText()
