"""
Tests for data block parsing and S-parameter conversion
"""

import pytest
import numpy as np
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.model import MeasurementTrace, SParameter, MeasurementFormat


class TestSParameterConversion:
    """Test S-parameter data conversion functions"""
    
    def test_magnitude_db_conversion(self):
        """Test magnitude dB conversion from complex data"""
        # Create test data: complex S-parameters
        frequencies = np.linspace(1e9, 2e9, 101)
        real_parts = np.linspace(0.9, 0.1, 101)  # Decreasing reflection
        imag_parts = np.linspace(0.0, 0.1, 101)  # Small imaginary component
        complex_data = real_parts + 1j * imag_parts
        
        # Create trace with complex data
        trace = MeasurementTrace(
            name="S11_test",
            sparam=SParameter.S11,
            format=MeasurementFormat.REAL,  # Will be converted to magnitude
            frequency_axis=frequencies,
            data=complex_data,
            timestamp=0.0
        )
        
        # Get magnitude in dB
        mag_db = trace.magnitude_db
        
        # Verify conversion
        expected_mag_db = 20 * np.log10(np.abs(complex_data))
        np.testing.assert_array_almost_equal(mag_db, expected_mag_db, decimal=6)
    
    def test_phase_deg_conversion(self):
        """Test phase degree conversion from complex data"""
        # Create test data with known phase
        frequencies = np.linspace(1e9, 2e9, 101)
        phases_rad = np.linspace(0, np.pi, 101)
        magnitudes = np.ones(101) * 0.5
        complex_data = magnitudes * np.exp(1j * phases_rad)
        
        # Create trace
        trace = MeasurementTrace(
            name="S21_test",
            sparam=SParameter.S21,
            format=MeasurementFormat.IMAGINARY,  # Will be converted to phase
            frequency_axis=frequencies,
            data=complex_data,
            timestamp=0.0
        )
        
        # Get phase in degrees
        phase_deg = trace.phase_deg
        
        # Verify conversion
        expected_phase_deg = np.angle(complex_data, deg=True)
        np.testing.assert_array_almost_equal(phase_deg, expected_phase_deg, decimal=6)
    
    def test_format_preservation(self):
        """Test that existing formats are preserved correctly"""
        frequencies = np.linspace(1e9, 2e9, 101)
        
        # Test magnitude dB format (should return data as-is)
        mag_data = np.linspace(-20, -40, 101)
        mag_trace = MeasurementTrace(
            name="S11_mag",
            sparam=SParameter.S11,
            format=MeasurementFormat.MAGNITUDE_DB,
            frequency_axis=frequencies,
            data=mag_data,
            timestamp=0.0
        )
        
        np.testing.assert_array_equal(mag_trace.magnitude_db, mag_data)
        
        # Test phase format (should return data as-is)
        phase_data = np.linspace(-180, 180, 101)
        phase_trace = MeasurementTrace(
            name="S21_phase",
            sparam=SParameter.S21,
            format=MeasurementFormat.PHASE,
            frequency_axis=frequencies,
            data=phase_data,
            timestamp=0.0
        )
        
        np.testing.assert_array_equal(phase_trace.phase_deg, phase_data)


class TestBlockDataParsing:
    """Test parsing of SCPI data blocks"""
    
    def test_fdata_parsing(self):
        """Test parsing of FDATA (formatted data) from SCPI response"""
        # Simulate SCPI response string
        test_data = np.array([-20.5, -21.2, -22.1, -23.0, -24.5])
        scpi_response = ",".join([f"{val:.6f}" for val in test_data])
        
        # Parse the data (simulate what driver does)
        parsed_data = np.fromstring(scpi_response, sep=',', dtype=np.float64)
        
        # Verify parsing
        np.testing.assert_array_almost_equal(parsed_data, test_data, decimal=6)
    
    def test_sdata_parsing(self):
        """Test parsing of SDATA (S-parameter real/imaginary pairs)"""
        # Create test S-parameter data (real, imag pairs)
        real_parts = np.array([0.9, 0.8, 0.7, 0.6, 0.5])
        imag_parts = np.array([0.1, 0.15, 0.2, 0.25, 0.3])
        
        # Create interleaved array as SCPI would return
        interleaved = np.empty(len(real_parts) * 2)
        interleaved[0::2] = real_parts
        interleaved[1::2] = imag_parts
        
        scpi_response = ",".join([f"{val:.6f}" for val in interleaved])
        
        # Parse and reshape (simulate what driver does)
        parsed_data = np.fromstring(scpi_response, sep=',', dtype=np.float64)
        ri_pairs = parsed_data.reshape(-1, 2)
        
        # Verify parsing
        np.testing.assert_array_almost_equal(ri_pairs[:, 0], real_parts, decimal=6)
        np.testing.assert_array_almost_equal(ri_pairs[:, 1], imag_parts, decimal=6)
    
    def test_complex_reconstruction(self):
        """Test reconstruction of complex numbers from real/imaginary pairs"""
        # Create test data
        real_parts = np.array([0.9, 0.8, 0.7])
        imag_parts = np.array([0.1, 0.15, 0.2])
        expected_complex = real_parts + 1j * imag_parts
        
        # Simulate parsing from SCPI
        ri_pairs = np.column_stack([real_parts, imag_parts])
        reconstructed_complex = ri_pairs[:, 0] + 1j * ri_pairs[:, 1]
        
        # Verify reconstruction
        np.testing.assert_array_almost_equal(reconstructed_complex, expected_complex, decimal=6)


class TestPhaseUnwrapping:
    """Test phase unwrapping functionality"""
    
    def test_phase_unwrap(self):
        """Test phase unwrapping for continuous phase data"""
        # Create wrapped phase data with discontinuities
        frequencies = np.linspace(1e9, 2e9, 101)
        
        # Create phase that wraps around
        continuous_phase = np.linspace(0, 4*np.pi, 101)  # 0 to 720 degrees
        wrapped_phase = np.angle(np.exp(1j * continuous_phase), deg=True)  # Wrapped to [-180, 180]
        
        # Unwrap the phase
        unwrapped_phase = np.unwrap(np.deg2rad(wrapped_phase), period=2*np.pi)
        unwrapped_phase_deg = np.rad2deg(unwrapped_phase)
        
        # The unwrapped phase should be close to the original continuous phase
        # (within a constant offset due to wrapping)
        phase_diff = unwrapped_phase_deg - np.rad2deg(continuous_phase)
        phase_diff_normalized = phase_diff - phase_diff[0]  # Remove constant offset
        
        # All differences should be small (< 1 degree)
        assert np.max(np.abs(phase_diff_normalized)) < 1.0
    
    def test_magnitude_preservation(self):
        """Test that magnitude is preserved during complex operations"""
        # Create test complex data
        magnitudes = np.array([0.9, 0.8, 0.7, 0.6, 0.5])
        phases = np.array([30, 60, 90, 120, 150]) * np.pi / 180  # Convert to radians
        
        complex_data = magnitudes * np.exp(1j * phases)
        
        # Extract magnitude and verify
        extracted_magnitudes = np.abs(complex_data)
        
        np.testing.assert_array_almost_equal(extracted_magnitudes, magnitudes, decimal=6)


if __name__ == "__main__":
    pytest.main([__file__])
