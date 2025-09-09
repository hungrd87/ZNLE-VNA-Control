"""
Data storage and export functionality
"""

import csv
import json
import logging
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from .model import MeasurementTrace, InstrumentState, SParameter, MeasurementFormat

logger = logging.getLogger(__name__)


class DataExporter:
    """Handle data export in various formats"""
    
    @staticmethod
    def export_csv(traces: List[MeasurementTrace], filepath: str, 
                   include_metadata: bool = True) -> None:
        """Export measurement traces to CSV format"""
        try:
            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                
                # Write metadata header
                if include_metadata and traces:
                    writer.writerow(['# ZNLE VNA Measurement Data'])
                    writer.writerow([f'# Export Date: {datetime.now().isoformat()}'])
                    writer.writerow([f'# Number of Traces: {len(traces)}'])
                    writer.writerow([''])
                
                # Determine all unique frequencies
                all_frequencies = set()
                for trace in traces:
                    all_frequencies.update(trace.frequency_axis)
                freq_axis = np.array(sorted(all_frequencies))
                
                # Create header
                header = ['Frequency_Hz']
                for trace in traces:
                    header.append(f'{trace.name}_{trace.sparam.value}_{trace.format.value}')
                writer.writerow(header)
                
                # Interpolate all traces to common frequency axis
                for i, freq in enumerate(freq_axis):
                    row = [freq]
                    for trace in traces:
                        # Interpolate trace data to common frequency
                        if len(trace.frequency_axis) > 0 and len(trace.data) > 0:
                            interpolated_value = np.interp(freq, trace.frequency_axis, trace.data)
                            row.append(interpolated_value)
                        else:
                            row.append('')
                    writer.writerow(row)
                
                logger.info(f"Data exported to CSV: {filepath}")
                
        except Exception as e:
            logger.error(f"CSV export failed: {e}")
            raise
    
    @staticmethod
    def export_numpy(traces: List[MeasurementTrace], filepath: str) -> None:
        """Export measurement traces to NumPy format"""
        try:
            # Prepare data dictionary
            data_dict = {}
            
            for i, trace in enumerate(traces):
                prefix = f'trace_{i}_{trace.name}'
                data_dict[f'{prefix}_frequency'] = trace.frequency_axis
                data_dict[f'{prefix}_data'] = trace.data
                data_dict[f'{prefix}_sparam'] = trace.sparam.value
                data_dict[f'{prefix}_format'] = trace.format.value
                data_dict[f'{prefix}_timestamp'] = trace.timestamp
            
            # Add metadata
            data_dict['export_timestamp'] = datetime.now().timestamp()
            data_dict['num_traces'] = len(traces)
            
            np.savez_compressed(filepath, **data_dict)
            logger.info(f"Data exported to NumPy: {filepath}")
            
        except Exception as e:
            logger.error(f"NumPy export failed: {e}")
            raise
    
    @staticmethod
    def export_json_metadata(state: InstrumentState, filepath: str) -> None:
        """Export instrument state and configuration to JSON"""
        try:
            metadata = {
                'export_timestamp': datetime.now().isoformat(),
                'instrument_id': state.identification,
                'sweep_config': {
                    'frequency_start_hz': state.sweep_config.frequency.start_hz,
                    'frequency_stop_hz': state.sweep_config.frequency.stop_hz,
                    'points': state.sweep_config.points,
                    'if_bandwidth_hz': state.sweep_config.if_bandwidth_hz,
                    'power_dbm': state.sweep_config.power_dbm,
                    'continuous': state.sweep_config.continuous,
                    'averaging': state.sweep_config.averaging
                },
                'measurements': {},
                'markers': {},
                'connection': {
                    'resource_string': state.connection_config.resource_string,
                    'visa_backend': state.connection_config.visa_backend
                }
            }
            
            # Add measurement configurations
            for name, trace in state.measurements.items():
                metadata['measurements'][name] = {
                    'sparam': trace.sparam.value,
                    'format': trace.format.value,
                    'active': trace.active,
                    'data_points': len(trace.data) if hasattr(trace.data, '__len__') else 0
                }
            
            # Add markers
            for marker_id, marker in state.markers.items():
                metadata['markers'][str(marker_id)] = {
                    'frequency_hz': marker.frequency_hz,
                    'enabled': marker.enabled
                }
            
            with open(filepath, 'w', encoding='utf-8') as jsonfile:
                json.dump(metadata, jsonfile, indent=2)
            
            logger.info(f"Metadata exported to JSON: {filepath}")
            
        except Exception as e:
            logger.error(f"JSON metadata export failed: {e}")
            raise


class TouchstoneExporter:
    """Export S-parameter data to Touchstone format"""
    
    @staticmethod
    def export_s1p(trace: MeasurementTrace, filepath: str, 
                   reference_impedance: float = 50.0) -> None:
        """Export single-port S-parameter to S1P format"""
        if trace.sparam not in [SParameter.S11, SParameter.S22]:
            raise ValueError("S1P export requires S11 or S22 parameter")
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                # Write header
                f.write(f"! Touchstone file exported from ZNLE VNA Control\n")
                f.write(f"! Date: {datetime.now().isoformat()}\n")
                f.write(f"! Measurement: {trace.name} ({trace.sparam.value})\n")
                f.write(f"! Format: {trace.format.value}\n")
                f.write(f"# Hz S MA R {reference_impedance}\n")
                
                # Convert data to magnitude/angle if needed
                if trace.format.value == "MLOG":
                    # Data is already in dB magnitude
                    mag_db = trace.data
                    phase_deg = np.zeros_like(mag_db)  # Assume zero phase
                else:
                    # Try to extract magnitude and phase
                    mag_db = 20 * np.log10(np.abs(trace.data) + 1e-15)
                    phase_deg = np.angle(trace.data, deg=True)
                
                # Write data points
                for i, freq in enumerate(trace.frequency_axis):
                    f.write(f"{freq:.6e} {mag_db[i]:.6f} {phase_deg[i]:.6f}\n")
            
            logger.info(f"S1P file exported: {filepath}")
            
        except Exception as e:
            logger.error(f"S1P export failed: {e}")
            raise
    
    @staticmethod
    def export_s2p(traces: Dict[str, MeasurementTrace], filepath: str,
                   reference_impedance: float = 50.0) -> None:
        """Export two-port S-parameters to S2P format"""
        required_params = [SParameter.S11, SParameter.S12, SParameter.S21, SParameter.S22]
        
        # Find traces for each S-parameter
        param_traces = {}
        for trace in traces.values():
            if trace.sparam in required_params:
                param_traces[trace.sparam] = trace
        
        # Check if we have all required parameters
        missing_params = [p for p in required_params if p not in param_traces]
        if missing_params:
            logger.warning(f"Missing S-parameters for S2P export: {missing_params}")
            # Continue with available parameters, fill missing with zeros
        
        try:
            # Use frequency axis from first available trace
            freq_axis = None
            for trace in param_traces.values():
                if len(trace.frequency_axis) > 0:
                    freq_axis = trace.frequency_axis
                    break
            
            if freq_axis is None:
                raise ValueError("No frequency data available")
            
            with open(filepath, 'w', encoding='utf-8') as f:
                # Write header
                f.write(f"! Touchstone file exported from ZNLE VNA Control\n")
                f.write(f"! Date: {datetime.now().isoformat()}\n")
                f.write(f"! Available parameters: {list(param_traces.keys())}\n")
                f.write(f"# Hz S MA R {reference_impedance}\n")
                
                # Write data points
                for i, freq in enumerate(freq_axis):
                    line_parts = [f"{freq:.6e}"]
                    
                    for param in required_params:
                        if param in param_traces:
                            trace = param_traces[param]
                            if i < len(trace.data):
                                if trace.format.value == "MLOG":
                                    mag_db = trace.data[i]
                                    phase_deg = 0.0
                                else:
                                    mag_db = 20 * np.log10(abs(trace.data[i]) + 1e-15)
                                    phase_deg = np.angle(trace.data[i], deg=True)
                                
                                line_parts.extend([f"{mag_db:.6f}", f"{phase_deg:.6f}"])
                            else:
                                line_parts.extend(["-999.0", "0.0"])  # Missing data
                        else:
                            line_parts.extend(["-999.0", "0.0"])  # Missing parameter
                    
                    f.write(" ".join(line_parts) + "\n")
            
            logger.info(f"S2P file exported: {filepath}")
            
        except Exception as e:
            logger.error(f"S2P export failed: {e}")
            raise


class DataLoader:
    """Load previously saved measurement data"""
    
    @staticmethod
    def load_numpy(filepath: str) -> List[MeasurementTrace]:
        """Load measurement traces from NumPy file"""
        try:
            data = np.load(filepath)
            traces = []
            
            # Get number of traces
            num_traces = int(data.get('num_traces', 0))
            
            for i in range(num_traces):
                prefix = f'trace_{i}'
                
                # Find the trace name (extract from keys)
                name_key = None
                for key in data.keys():
                    if key.startswith(prefix) and not key.endswith(('_frequency', '_data', '_sparam', '_format', '_timestamp')):
                        name_key = key
                        break
                
                if name_key:
                    name = name_key.replace(f'{prefix}_', '')
                else:
                    name = f'trace_{i}'
                
                # Extract trace data
                freq_key = f'{prefix}_{name}_frequency'
                data_key = f'{prefix}_{name}_data'
                sparam_key = f'{prefix}_{name}_sparam'
                format_key = f'{prefix}_{name}_format'
                timestamp_key = f'{prefix}_{name}_timestamp'
                
                if all(key in data for key in [freq_key, data_key, sparam_key, format_key]):
                    frequency_axis = data[freq_key]
                    trace_data = data[data_key]
                    sparam = SParameter(data[sparam_key].item())
                    format_val = data[format_key].item()
                    timestamp = data.get(timestamp_key, 0.0).item()
                    
                    # Find matching format enum
                    trace_format = None
                    for fmt in MeasurementFormat:
                        if fmt.value == format_val:
                            trace_format = fmt
                            break
                    
                    if trace_format:
                        trace = MeasurementTrace(
                            name=name,
                            sparam=sparam,
                            format=trace_format,
                            frequency_axis=frequency_axis,
                            data=trace_data,
                            timestamp=timestamp
                        )
                        traces.append(trace)
            
            logger.info(f"Loaded {len(traces)} traces from NumPy file: {filepath}")
            return traces
            
        except Exception as e:
            logger.error(f"NumPy load failed: {e}")
            raise
    
    @staticmethod
    def load_csv(filepath: str) -> List[MeasurementTrace]:
        """Load measurement traces from CSV file"""
        try:
            traces = []
            
            with open(filepath, 'r', encoding='utf-8') as csvfile:
                # Skip comment lines
                lines = []
                for line in csvfile:
                    if not line.strip().startswith('#'):
                        lines.append(line)
                
                if not lines:
                    return traces
                
                reader = csv.reader(lines)
                header = next(reader)
                
                # Parse header to identify columns
                freq_col = 0  # Assume first column is frequency
                trace_cols = []
                
                for i, col_name in enumerate(header[1:], 1):
                    # Parse column name format: name_sparam_format
                    parts = col_name.split('_')
                    if len(parts) >= 3:
                        name = '_'.join(parts[:-2])
                        sparam_str = parts[-2]
                        format_str = parts[-1]
                        
                        try:
                            sparam = SParameter(sparam_str)
                            trace_format = None
                            for fmt in MeasurementFormat:
                                if fmt.value == format_str:
                                    trace_format = fmt
                                    break
                            
                            if trace_format:
                                trace_cols.append((i, name, sparam, trace_format))
                        except:
                            continue
                
                # Read data
                frequencies = []
                trace_data = {i: [] for i, _, _, _ in trace_cols}
                
                for row in reader:
                    if len(row) > freq_col:
                        try:
                            freq = float(row[freq_col])
                            frequencies.append(freq)
                            
                            for col_idx, _, _, _ in trace_cols:
                                if col_idx < len(row) and row[col_idx]:
                                    trace_data[col_idx].append(float(row[col_idx]))
                                else:
                                    trace_data[col_idx].append(np.nan)
                        except:
                            continue
                
                # Create trace objects
                freq_array = np.array(frequencies)
                for col_idx, name, sparam, trace_format in trace_cols:
                    data_array = np.array(trace_data[col_idx])
                    
                    trace = MeasurementTrace(
                        name=name,
                        sparam=sparam,
                        format=trace_format,
                        frequency_axis=freq_array,
                        data=data_array,
                        timestamp=0.0
                    )
                    traces.append(trace)
            
            logger.info(f"Loaded {len(traces)} traces from CSV file: {filepath}")
            return traces
            
        except Exception as e:
            logger.error(f"CSV load failed: {e}")
            raise
