"""
Data models and configuration for ZNLE VNA Control
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
import numpy as np
from enum import Enum


class SParameter(Enum):
    """S-Parameter types"""
    S11 = "S11"
    S12 = "S12"
    S21 = "S21"
    S22 = "S22"


class MeasurementFormat(Enum):
    """Measurement format types"""
    MAGNITUDE_DB = "MLOG"
    PHASE = "PHAS"
    REAL = "REAL"
    IMAGINARY = "IMAG"
    SMITH = "SMIT"
    POLAR = "POL"
    SWR = "SWR"


@dataclass
class FrequencyRange:
    """Frequency range configuration"""
    start_hz: float = 1e9  # 1 GHz
    stop_hz: float = 2e9   # 2 GHz
    
    @property
    def center_hz(self) -> float:
        return (self.start_hz + self.stop_hz) / 2
    
    @property
    def span_hz(self) -> float:
        return self.stop_hz - self.start_hz
    
    def to_axis(self, points: int) -> np.ndarray:
        """Generate frequency axis array"""
        return np.linspace(self.start_hz, self.stop_hz, points)


@dataclass
class SweepConfig:
    """Sweep configuration parameters"""
    frequency: FrequencyRange = field(default_factory=FrequencyRange)
    points: int = 801
    if_bandwidth_hz: float = 3e3  # 3 kHz
    power_dbm: float = -10.0
    continuous: bool = True
    averaging: int = 1


@dataclass
class Marker:
    """Frequency marker configuration"""
    id: int
    frequency_hz: float
    enabled: bool = True
    value: Optional[complex] = None
    
    def __post_init__(self):
        if self.id < 1 or self.id > 10:
            raise ValueError("Marker ID must be between 1 and 10")


@dataclass
class LimitLine:
    """Limit line for pass/fail testing"""
    name: str
    frequencies: np.ndarray
    upper_limits: np.ndarray
    lower_limits: Optional[np.ndarray] = None
    enabled: bool = True


@dataclass
class MeasurementTrace:
    """Single measurement trace data"""
    name: str
    sparam: SParameter
    format: MeasurementFormat
    frequency_axis: np.ndarray
    data: np.ndarray
    timestamp: float
    active: bool = True
    
    @property
    def magnitude_db(self) -> np.ndarray:
        """Get magnitude in dB (convert if necessary)"""
        if self.format == MeasurementFormat.MAGNITUDE_DB:
            return self.data
        elif self.format in [MeasurementFormat.REAL, MeasurementFormat.IMAGINARY]:
            # Assume data is complex
            return 20 * np.log10(np.abs(self.data) + 1e-15)
        else:
            # For other formats, return as-is
            return self.data
    
    @property
    def phase_deg(self) -> np.ndarray:
        """Get phase in degrees (convert if necessary)"""
        if self.format == MeasurementFormat.PHASE:
            return self.data
        elif self.format in [MeasurementFormat.REAL, MeasurementFormat.IMAGINARY]:
            # Assume data is complex
            return np.angle(self.data, deg=True)
        else:
            return np.zeros_like(self.data)


@dataclass
class ConnectionConfig:
    """Instrument connection configuration"""
    resource_string: str = "TCPIP::192.168.1.100::hislip0::INSTR"
    visa_backend: str = "rs"  # "rs", "ni", "keysight"
    timeout_ms: int = 5000
    id_query: bool = True
    reset_on_connect: bool = False


@dataclass
class AcquisitionConfig:
    """Data acquisition configuration"""
    update_rate_hz: float = 10.0  # Target update rate
    ring_buffer_size: int = 1000   # Number of traces to keep in memory
    auto_scale: bool = True
    decimation_factor: int = 1     # For performance optimization
    
    @property
    def update_interval_ms(self) -> int:
        """Update interval in milliseconds"""
        return int(1000 / self.update_rate_hz)


class InstrumentState:
    """Current state of the instrument"""
    
    def __init__(self):
        self.connected = False
        self.measuring = False
        self.identification = ""
        self.last_error = ""
        self.sweep_config = SweepConfig()
        self.measurements: Dict[str, MeasurementTrace] = {}
        self.markers: Dict[int, Marker] = {}
        self.limit_lines: Dict[str, LimitLine] = {}
        self.connection_config = ConnectionConfig()
        self.acquisition_config = AcquisitionConfig()
    
    def add_measurement(self, name: str, sparam: SParameter, 
                       format: MeasurementFormat = MeasurementFormat.MAGNITUDE_DB) -> None:
        """Add a new measurement configuration"""
        # Initialize with empty arrays - will be filled during acquisition
        empty_freq = np.array([])
        empty_data = np.array([])
        
        trace = MeasurementTrace(
            name=name,
            sparam=sparam,
            format=format,
            frequency_axis=empty_freq,
            data=empty_data,
            timestamp=0.0
        )
        self.measurements[name] = trace
    
    def add_marker(self, marker_id: int, frequency_hz: float) -> None:
        """Add a frequency marker"""
        marker = Marker(id=marker_id, frequency_hz=frequency_hz)
        self.markers[marker_id] = marker
    
    def remove_marker(self, marker_id: int) -> None:
        """Remove a frequency marker"""
        if marker_id in self.markers:
            del self.markers[marker_id]
    
    def get_active_measurements(self) -> List[MeasurementTrace]:
        """Get list of active measurement traces"""
        return [trace for trace in self.measurements.values() if trace.active]
    
    def update_measurement_data(self, name: str, frequency_axis: np.ndarray, 
                              data: np.ndarray, timestamp: float) -> None:
        """Update measurement trace data"""
        if name in self.measurements:
            trace = self.measurements[name]
            trace.frequency_axis = frequency_axis
            trace.data = data
            trace.timestamp = timestamp


class RingBuffer:
    """Thread-safe ring buffer for measurement data"""
    
    def __init__(self, max_size: int):
        self.max_size = max_size
        self.buffer: List[MeasurementTrace] = []
        self.index = 0
    
    def push(self, trace: MeasurementTrace) -> None:
        """Add new trace to buffer"""
        if len(self.buffer) < self.max_size:
            self.buffer.append(trace)
        else:
            self.buffer[self.index] = trace
            self.index = (self.index + 1) % self.max_size
    
    def get_latest(self, count: int = 1) -> List[MeasurementTrace]:
        """Get the latest N traces"""
        if not self.buffer:
            return []
        
        if count >= len(self.buffer):
            return self.buffer.copy()
        
        # Get the last 'count' items considering ring buffer structure
        if len(self.buffer) < self.max_size:
            # Buffer not full yet
            return self.buffer[-count:]
        else:
            # Buffer is full, need to handle wrap-around
            start_idx = (self.index - count) % self.max_size
            if start_idx + count <= self.max_size:
                return self.buffer[start_idx:start_idx + count]
            else:
                # Wrap around
                return self.buffer[start_idx:] + self.buffer[:self.index]
    
    def clear(self) -> None:
        """Clear all data from buffer"""
        self.buffer.clear()
        self.index = 0
    
    @property
    def size(self) -> int:
        """Current number of items in buffer"""
        return len(self.buffer)
    
    @property
    def is_full(self) -> bool:
        """Check if buffer is full"""
        return len(self.buffer) >= self.max_size
