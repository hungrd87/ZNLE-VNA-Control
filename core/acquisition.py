"""
Data acquisition thread for continuous measurement
"""

import time
import logging
from typing import Optional, Dict, Any
import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal, QMutex, QMutexLocker

from .driver_znle import ZNLE, ZNLEError
from .model import InstrumentState, MeasurementTrace, RingBuffer, SParameter, MeasurementFormat

logger = logging.getLogger(__name__)


class AcquisitionWorker(QThread):
    """Worker thread for continuous data acquisition"""
    
    # Signals
    measurement_ready = pyqtSignal(str, np.ndarray, np.ndarray, float)  # name, freq, data, timestamp
    error_occurred = pyqtSignal(str)  # error message
    status_changed = pyqtSignal(dict)  # status info
    acquisition_started = pyqtSignal()
    acquisition_stopped = pyqtSignal()
    
    def __init__(self, instrument: ZNLE, state: InstrumentState):
        super().__init__()
        self.instrument = instrument
        self.state = state
        self.running = False
        self.mutex = QMutex()
        self.ring_buffers: Dict[str, RingBuffer] = {}
        
        # Initialize ring buffers for each measurement
        for name in self.state.measurements:
            self.ring_buffers[name] = RingBuffer(self.state.acquisition_config.ring_buffer_size)
    
    def start_acquisition(self) -> None:
        """Start continuous acquisition"""
        with QMutexLocker(self.mutex):
            if not self.running:
                self.running = True
                self.start()
                logger.info("Acquisition started")
    
    def stop_acquisition(self) -> None:
        """Stop continuous acquisition"""
        with QMutexLocker(self.mutex):
            if self.running:
                self.running = False
                logger.info("Acquisition stop requested")
    
    def wait_for_stop(self, timeout_ms: int = 5000) -> bool:
        """Wait for acquisition to stop"""
        return self.wait(timeout_ms)
    
    def add_measurement(self, name: str, sparam: SParameter, 
                       format: MeasurementFormat = MeasurementFormat.MAGNITUDE_DB) -> None:
        """Add a new measurement to acquire"""
        with QMutexLocker(self.mutex):
            self.state.add_measurement(name, sparam, format)
            self.ring_buffers[name] = RingBuffer(self.state.acquisition_config.ring_buffer_size)
            logger.info(f"Added measurement: {name} ({sparam.value})")
    
    def remove_measurement(self, name: str) -> None:
        """Remove a measurement"""
        with QMutexLocker(self.mutex):
            if name in self.state.measurements:
                del self.state.measurements[name]
            if name in self.ring_buffers:
                del self.ring_buffers[name]
            logger.info(f"Removed measurement: {name}")
    
    def run(self) -> None:
        """Main acquisition loop"""
        try:
            self.acquisition_started.emit()
            
            # Configure instrument for continuous mode
            self._setup_continuous_acquisition()
            
            # Main acquisition loop
            loop_count = 0
            last_status_time = time.time()
            
            while self.running:
                try:
                    loop_start = time.time()
                    
                    # Acquire data for each active measurement
                    self._acquire_all_measurements()
                    
                    # Emit status periodically
                    if time.time() - last_status_time > 1.0:  # Every second
                        self._emit_status()
                        last_status_time = time.time()
                    
                    # Calculate sleep time to maintain target rate
                    loop_time = time.time() - loop_start
                    target_interval = 1.0 / self.state.acquisition_config.update_rate_hz
                    sleep_time = max(0, target_interval - loop_time)
                    
                    if sleep_time > 0:
                        self.msleep(int(sleep_time * 1000))
                    
                    loop_count += 1
                    
                except ZNLEError as e:
                    logger.error(f"ZNLE error in acquisition: {e}")
                    self.error_occurred.emit(str(e))
                    break
                except Exception as e:
                    logger.error(f"Unexpected error in acquisition: {e}")
                    self.error_occurred.emit(f"Acquisition error: {e}")
                    break
        
        finally:
            self.running = False
            self.acquisition_stopped.emit()
            logger.info("Acquisition stopped")
    
    def _setup_continuous_acquisition(self) -> None:
        """Configure instrument for continuous acquisition"""
        try:
            # Apply sweep configuration
            config = self.state.sweep_config
            
            self.instrument.set_freq_range(
                config.frequency.start_hz, 
                config.frequency.stop_hz
            )
            self.instrument.set_points(config.points)
            self.instrument.set_ifbw(config.if_bandwidth_hz)
            self.instrument.set_power(config.power_dbm)
            
            # Set up measurements on instrument
            for name, trace in self.state.measurements.items():
                if trace.active:
                    self.instrument.define_measure(name, trace.sparam.value)
            
            # Enable continuous mode
            self.instrument.set_continuous(config.continuous)
            
            logger.info("Instrument configured for continuous acquisition")
            
        except Exception as e:
            logger.error(f"Failed to setup acquisition: {e}")
            raise
    
    def _acquire_all_measurements(self) -> None:
        """Acquire data for all active measurements"""
        timestamp = time.time()
        frequency_axis = self.instrument.get_trace_freq_axis()
        
        for name, trace in self.state.measurements.items():
            if not trace.active:
                continue
            
            try:
                # Select measurement on instrument
                self.instrument.select_measure(name)
                self.instrument.set_format(trace.format.value)
                
                # Fetch data based on format
                if trace.format in [MeasurementFormat.REAL, MeasurementFormat.IMAGINARY]:
                    # Get complex S-parameter data
                    sdata = self.instrument.fetch_sdata()
                    if trace.format == MeasurementFormat.REAL:
                        data = sdata[:, 0]  # Real part
                    else:
                        data = sdata[:, 1]  # Imaginary part
                else:
                    # Get formatted data (magnitude, phase, etc.)
                    data = self.instrument.fetch_fdata()
                
                # Apply decimation if configured
                if self.state.acquisition_config.decimation_factor > 1:
                    data, frequency_axis = self._decimate_data(
                        data, frequency_axis, 
                        self.state.acquisition_config.decimation_factor
                    )
                
                # Update state
                self.state.update_measurement_data(name, frequency_axis, data, timestamp)
                
                # Store in ring buffer
                trace_copy = MeasurementTrace(
                    name=name,
                    sparam=trace.sparam,
                    format=trace.format,
                    frequency_axis=frequency_axis.copy(),
                    data=data.copy(),
                    timestamp=timestamp
                )
                self.ring_buffers[name].push(trace_copy)
                
                # Emit signal for UI update
                self.measurement_ready.emit(name, frequency_axis, data, timestamp)
                
            except Exception as e:
                logger.error(f"Failed to acquire {name}: {e}")
                # Continue with other measurements
                continue
    
    def _decimate_data(self, data: np.ndarray, freq: np.ndarray, factor: int) -> tuple[np.ndarray, np.ndarray]:
        """Simple decimation by factor"""
        if factor <= 1:
            return data, freq
        
        # Simple stride decimation - could be improved with LTTB algorithm
        decimated_data = data[::factor]
        decimated_freq = freq[::factor]
        
        return decimated_data, decimated_freq
    
    def _emit_status(self) -> None:
        """Emit current status information"""
        try:
            status = self.instrument.get_status()
            status.update({
                'acquisition_running': self.running,
                'measurements_count': len([t for t in self.state.measurements.values() if t.active]),
                'buffer_sizes': {name: buf.size for name, buf in self.ring_buffers.items()}
            })
            self.status_changed.emit(status)
        except Exception as e:
            logger.error(f"Failed to emit status: {e}")
    
    def get_measurement_history(self, name: str, count: int = 1) -> list[MeasurementTrace]:
        """Get measurement history from ring buffer"""
        if name in self.ring_buffers:
            return self.ring_buffers[name].get_latest(count)
        return []
    
    def clear_history(self, name: Optional[str] = None) -> None:
        """Clear measurement history"""
        if name:
            if name in self.ring_buffers:
                self.ring_buffers[name].clear()
        else:
            for buf in self.ring_buffers.values():
                buf.clear()


class SingleShotAcquisition:
    """Helper class for single-shot measurements"""
    
    def __init__(self, instrument: ZNLE):
        self.instrument = instrument
    
    def measure(self, measurement_name: str, sparam: SParameter, 
               format: MeasurementFormat = MeasurementFormat.MAGNITUDE_DB) -> MeasurementTrace:
        """Perform single measurement"""
        try:
            # Set up measurement
            self.instrument.define_measure(measurement_name, sparam.value)
            self.instrument.select_measure(measurement_name)
            self.instrument.set_format(format.value)
            
            # Trigger single sweep
            self.instrument.set_continuous(False)
            self.instrument.trigger_single()
            
            # Get data
            frequency_axis = self.instrument.get_trace_freq_axis()
            
            if format in [MeasurementFormat.REAL, MeasurementFormat.IMAGINARY]:
                sdata = self.instrument.fetch_sdata()
                if format == MeasurementFormat.REAL:
                    data = sdata[:, 0]
                else:
                    data = sdata[:, 1]
            else:
                data = self.instrument.fetch_fdata()
            
            return MeasurementTrace(
                name=measurement_name,
                sparam=sparam,
                format=format,
                frequency_axis=frequency_axis,
                data=data,
                timestamp=time.time()
            )
            
        except Exception as e:
            logger.error(f"Single shot measurement failed: {e}")
            raise ZNLEError(f"Single shot measurement failed: {e}")
