"""
ZNLE4 VNA Driver using RsInstrument for VISA/SCPI communication
"""

import numpy as np
import time
import logging
from typing import Literal, Optional, List
from RsInstrument import RsInstrument

logger = logging.getLogger(__name__)


class ZNLEError(Exception):
    """Custom exception for ZNLE driver errors"""
    pass


class ZNLE:
    """Driver class for R&S ZNLE4 Vector Network Analyzer"""
    
    def __init__(self, resource: str, visa_select: Literal["rs", "ni", "keysight"] = "rs"):
        """
        Initialize ZNLE driver
        
        Args:
            resource: VISA resource string (e.g., 'TCPIP::192.168.1.100::hislip0::INSTR')
            visa_select: VISA backend selection
        """
        self.resource = resource
        self.visa_select = visa_select
        self.instrument: Optional[RsInstrument] = None
        self.connected = False
        
    def connect(self, id_query: bool = True, reset: bool = False) -> None:
        """
        Connect to the instrument
        
        Args:
            id_query: Perform identification query on connection
            reset: Reset instrument on connection
        """
        try:
            options = f'SelectVisa={self.visa_select},SessionLock=True'
            self.instrument = RsInstrument(
                self.resource, 
                id_query=id_query, 
                reset=reset,
                options=options
            )
            self.connected = True
            logger.info(f"Connected to ZNLE at {self.resource}")
            
            # Clear any pending errors
            self._clear_errors()
            
        except Exception as e:
            logger.error(f"Failed to connect to ZNLE: {e}")
            raise ZNLEError(f"Connection failed: {e}")
    
    def close(self) -> None:
        """Close connection to instrument"""
        if self.instrument:
            try:
                self.instrument.close()
                self.connected = False
                logger.info("ZNLE connection closed")
            except Exception as e:
                logger.error(f"Error closing connection: {e}")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    def _check_connection(self) -> None:
        """Check if instrument is connected"""
        if not self.connected or not self.instrument:
            raise ZNLEError("Instrument not connected")
    
    def _write_command(self, command: str, timeout: float = 5.0) -> None:
        """Write SCPI command with error checking"""
        self._check_connection()
        try:
            self.instrument.write(command)
            self._check_errors()
        except Exception as e:
            logger.error(f"Command '{command}' failed: {e}")
            raise ZNLEError(f"Command failed: {e}")
    
    def _query_command(self, command: str, timeout: float = 5.0) -> str:
        """Query SCPI command with error checking"""
        self._check_connection()
        try:
            result = self.instrument.query_str(command)
            self._check_errors()
            return result
        except Exception as e:
            logger.error(f"Query '{command}' failed: {e}")
            raise ZNLEError(f"Query failed: {e}")
    
    def _check_errors(self) -> None:
        """Check instrument error queue"""
        errors = self.get_errors()
        if errors:
            error_msg = "; ".join(errors)
            logger.error(f"Instrument errors: {error_msg}")
            raise ZNLEError(f"Instrument errors: {error_msg}")
    
    def _clear_errors(self) -> None:
        """Clear all errors from instrument error queue"""
        while True:
            try:
                error = self.instrument.query_str('SYST:ERR?')
                if '0,"No error"' in error or '0,No error' in error:
                    break
            except:
                break
    
    def idn(self) -> str:
        """Get instrument identification string"""
        return self._query_command('*IDN?')
    
    def opc(self) -> None:
        """Wait for operation complete"""
        self._query_command('*OPC?')
    
    def get_errors(self) -> List[str]:
        """Get all errors from instrument error queue"""
        errors = []
        try:
            while True:
                error = self.instrument.query_str('SYST:ERR?')
                if '0,"No error"' in error or '0,No error' in error:
                    break
                errors.append(error.strip())
                if len(errors) > 10:  # Prevent infinite loop
                    break
        except:
            pass
        return errors
    
    # Sweep and Channel Configuration
    def set_freq_range(self, f_start_hz: float, f_stop_hz: float) -> None:
        """Set frequency sweep range"""
        self._write_command(f'SENS:FREQ:STAR {f_start_hz}')
        self._write_command(f'SENS:FREQ:STOP {f_stop_hz}')
        logger.info(f"Frequency range set: {f_start_hz/1e6:.3f} - {f_stop_hz/1e6:.3f} MHz")
    
    def get_freq_range(self) -> tuple[float, float]:
        """Get current frequency sweep range"""
        f_start = float(self._query_command('SENS:FREQ:STAR?'))
        f_stop = float(self._query_command('SENS:FREQ:STOP?'))
        return f_start, f_stop
    
    def set_points(self, n: int) -> None:
        """Set number of sweep points"""
        self._write_command(f'SENS:SWE:POIN {n}')
        logger.info(f"Sweep points set: {n}")
    
    def get_points(self) -> int:
        """Get current number of sweep points"""
        return int(self._query_command('SENS:SWE:POIN?'))
    
    def set_ifbw(self, hz: float) -> None:
        """Set IF bandwidth"""
        self._write_command(f'SENS:BAND {hz}')
        logger.info(f"IF bandwidth set: {hz} Hz")
    
    def get_ifbw(self) -> float:
        """Get current IF bandwidth"""
        return float(self._query_command('SENS:BAND?'))
    
    def set_power(self, dbm: float) -> None:
        """Set source power level"""
        self._write_command(f'SOUR:POW:LEV {dbm}')
        logger.info(f"Power level set: {dbm} dBm")
    
    def get_power(self) -> float:
        """Get current source power level"""
        return float(self._query_command('SOUR:POW:LEV?'))
    
    def set_continuous(self, on: bool) -> None:
        """Set continuous sweep mode"""
        state = "ON" if on else "OFF"
        self._write_command(f'INIT:CONT {state}')
        logger.info(f"Continuous sweep: {state}")
    
    def trigger_single(self) -> None:
        """Trigger single sweep and wait for completion"""
        self._write_command('INIT:IMM')
        self.opc()
    
    # Measurement Configuration
    def define_measure(self, name: str, sparam: str) -> None:
        """Define a measurement parameter"""
        self._write_command(f"CALC:PAR:DEF '{name}','{sparam}'")
        logger.info(f"Measurement defined: {name} = {sparam}")
    
    def select_measure(self, name: str) -> None:
        """Select active measurement"""
        self._write_command(f"CALC:PAR:SEL '{name}'")
    
    def set_format(self, fmt: str = "MLOG") -> None:
        """Set measurement format (MLOG, PHAS, REAL, IMAG, SMIT, etc.)"""
        self._write_command(f'CALC:FORM {fmt}')
        logger.info(f"Format set: {fmt}")
    
    def get_format(self) -> str:
        """Get current measurement format"""
        return self._query_command('CALC:FORM?').strip()
    
    # Data Acquisition
    def fetch_fdata(self) -> np.ndarray:
        """Fetch formatted measurement data"""
        data_str = self._query_command('CALC:DATA? FDATA')
        return np.fromstring(data_str, sep=',', dtype=np.float64)
    
    def fetch_sdata(self) -> np.ndarray:
        """Fetch S-parameter data as real/imaginary pairs"""
        data_str = self._query_command('CALC:DATA? SDATA')
        ri_data = np.fromstring(data_str, sep=',', dtype=np.float64)
        return ri_data.reshape(-1, 2)  # Reshape to [N, 2] for real/imag pairs
    
    def get_trace_freq_axis(self) -> np.ndarray:
        """Get frequency axis for current sweep"""
        f_start, f_stop = self.get_freq_range()
        n_points = self.get_points()
        return np.linspace(f_start, f_stop, n_points, dtype=np.float64)
    
    def get_sweep_time(self) -> float:
        """Get estimated sweep time"""
        try:
            return float(self._query_command('SENS:SWE:TIME?'))
        except:
            # Fallback calculation if command not supported
            points = self.get_points()
            ifbw = self.get_ifbw()
            # Rough estimation: time per point ≈ 1/(IF BW) + overhead
            return points * (1.0 / ifbw + 0.001)
    
    # File Operations (Optional)
    def save_snp(self, filepath: str, ports: str = "1,2") -> None:
        """Save S-parameters to SnP file on instrument"""
        try:
            # This command may vary depending on ZNLE firmware
            self._write_command(f"MMEM:STOR:TRAC:FORM:SNP DB")
            self._write_command(f"CALC:DATA:SNP:PORTs:SAVE '{ports}','{filepath}'")
            logger.info(f"SnP file saved: {filepath}")
        except Exception as e:
            logger.warning(f"SnP save failed (may not be supported): {e}")
    
    # Utility Methods
    def preset(self) -> None:
        """Preset instrument to default state"""
        self._write_command('SYST:PRES')
        self.opc()
        logger.info("Instrument preset completed")
    
    def get_status(self) -> dict:
        """Get instrument status information"""
        try:
            f_start, f_stop = self.get_freq_range()
            points = self.get_points()
            ifbw = self.get_ifbw()
            power = self.get_power()
            sweep_time = self.get_sweep_time()
            
            return {
                'frequency_start': f_start,
                'frequency_stop': f_stop,
                'points': points,
                'if_bandwidth': ifbw,
                'power': power,
                'sweep_time': sweep_time,
                'connected': self.connected
            }
        except Exception as e:
            logger.error(f"Failed to get status: {e}")
            return {'connected': self.connected, 'error': str(e)}
