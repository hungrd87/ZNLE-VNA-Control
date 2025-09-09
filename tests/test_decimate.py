"""
Tests for data decimation algorithms
"""

import pytest
import numpy as np
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.decimate import LTTBDecimator, StrideDecimator, AdaptiveDecimator, DecimationManager


class TestStrideDecimator:
    """Test simple stride decimation"""
    
    def test_stride_decimation(self):
        """Test basic stride decimation functionality"""
        # Create test data
        x_data = np.arange(100)
        y_data = np.sin(x_data * 0.1)
        
        # Apply stride decimation with factor 2
        x_dec, y_dec = StrideDecimator.decimate(x_data, y_data, factor=2)
        
        # Check results
        expected_x = x_data[::2]
        expected_y = y_data[::2]
        
        np.testing.assert_array_equal(x_dec, expected_x)
        np.testing.assert_array_equal(y_dec, expected_y)
    
    def test_stride_no_decimation(self):
        """Test that factor=1 returns original data"""
        x_data = np.arange(10)
        y_data = np.sin(x_data)
        
        x_dec, y_dec = StrideDecimator.decimate(x_data, y_data, factor=1)
        
        np.testing.assert_array_equal(x_dec, x_data)
        np.testing.assert_array_equal(y_dec, y_data)
    
    def test_stride_large_factor(self):
        """Test stride decimation with large factor"""
        x_data = np.arange(100)
        y_data = np.ones(100)
        
        x_dec, y_dec = StrideDecimator.decimate(x_data, y_data, factor=10)
        
        assert len(x_dec) == 10
        np.testing.assert_array_equal(x_dec, x_data[::10])


class TestLTTBDecimator:
    """Test Largest Triangle Three Buckets decimation"""
    
    def test_lttb_basic(self):
        """Test basic LTTB functionality"""
        # Create test data with clear features
        x_data = np.linspace(0, 10, 1000)
        y_data = np.sin(x_data) + 0.1 * np.sin(10 * x_data)  # Signal with detail
        
        # Decimate to 100 points
        x_dec, y_dec = LTTBDecimator.decimate(x_data, y_data, target_points=100)
        
        # Check that we got approximately the right number of points
        assert len(x_dec) <= 102  # Allow for small variations
        assert len(y_dec) <= 102
        assert len(x_dec) >= 98
        
        # Check that first and last points are preserved
        assert x_dec[0] == x_data[0]
        assert x_dec[-1] == x_data[-1]
        assert y_dec[0] == y_data[0]
        assert y_dec[-1] == y_data[-1]
    
    def test_lttb_preserves_extremes(self):
        """Test that LTTB preserves important features"""
        # Create data with clear peak
        x_data = np.linspace(0, 10, 1000)
        y_data = np.exp(-(x_data - 5)**2)  # Gaussian peak at x=5
        
        x_dec, y_dec = LTTBDecimator.decimate(x_data, y_data, target_points=50)
        
        # The maximum should be preserved reasonably well
        original_max = np.max(y_data)
        decimated_max = np.max(y_dec)
        
        # Should preserve at least 90% of the peak height
        assert decimated_max >= 0.9 * original_max
    
    def test_lttb_small_target(self):
        """Test LTTB with very small target points"""
        x_data = np.arange(100)
        y_data = np.sin(x_data * 0.1)
        
        # Test with target < 3 (should fall back to stride)
        x_dec, y_dec = LTTBDecimator.decimate(x_data, y_data, target_points=2)
        
        assert len(x_dec) <= 3  # Should handle gracefully
    
    def test_lttb_no_decimation_needed(self):
        """Test LTTB when target >= original length"""
        x_data = np.arange(10)
        y_data = np.sin(x_data)
        
        x_dec, y_dec = LTTBDecimator.decimate(x_data, y_data, target_points=20)
        
        # Should return original data
        np.testing.assert_array_equal(x_dec, x_data)
        np.testing.assert_array_equal(y_dec, y_data)


class TestAdaptiveDecimator:
    """Test adaptive decimation that preserves peaks"""
    
    def test_adaptive_preserves_peaks(self):
        """Test that adaptive decimation preserves local maxima and minima"""
        # Create data with clear peaks and valleys
        x_data = np.linspace(0, 20, 1000)
        y_data = np.sin(x_data) + 0.5 * np.sin(3 * x_data)
        
        x_dec, y_dec = AdaptiveDecimator.decimate(x_data, y_data, target_points=100, 
                                                 preserve_peaks=True)
        
        # Find peaks in original data
        original_peaks = []
        for i in range(1, len(y_data) - 1):
            if y_data[i] > y_data[i-1] and y_data[i] > y_data[i+1]:
                original_peaks.append(y_data[i])
        
        # Check that some significant peaks are preserved
        if original_peaks:
            max_original_peak = max(original_peaks)
            max_decimated = np.max(y_dec)
            
            # Should preserve the highest peak
            assert max_decimated >= 0.95 * max_original_peak
    
    def test_adaptive_endpoints_preserved(self):
        """Test that adaptive decimation always preserves endpoints"""
        x_data = np.arange(100)
        y_data = np.random.random(100)
        
        x_dec, y_dec = AdaptiveDecimator.decimate(x_data, y_data, target_points=20)
        
        assert x_dec[0] == x_data[0]
        assert x_dec[-1] == x_data[-1]
        assert y_dec[0] == y_data[0]
        assert y_dec[-1] == y_data[-1]
    
    def test_adaptive_no_preserve_peaks(self):
        """Test adaptive decimation without peak preservation"""
        x_data = np.arange(100)
        y_data = np.sin(x_data * 0.1)
        
        x_dec, y_dec = AdaptiveDecimator.decimate(x_data, y_data, target_points=20,
                                                 preserve_peaks=False)
        
        assert len(x_dec) <= 22  # Allow some tolerance
        assert len(x_dec) >= 18


class TestDecimationManager:
    """Test the decimation manager class"""
    
    def test_manager_strategy_selection(self):
        """Test that manager correctly uses different strategies"""
        x_data = np.arange(100)
        y_data = np.sin(x_data * 0.1)
        
        # Test LTTB strategy
        manager_lttb = DecimationManager("lttb")
        x_lttb, y_lttb = manager_lttb.decimate(x_data, y_data, target_points=20)
        
        # Test stride strategy
        manager_stride = DecimationManager("stride")
        x_stride, y_stride = manager_stride.decimate(x_data, y_data, factor=5)
        
        # Test adaptive strategy
        manager_adaptive = DecimationManager("adaptive")
        x_adaptive, y_adaptive = manager_adaptive.decimate(x_data, y_data, target_points=20)
        
        # All should produce different results (except possibly by coincidence)
        # Just check that they all work and produce reasonable output
        assert len(x_lttb) <= 22
        assert len(x_stride) == 20  # 100/5 = 20
        assert len(x_adaptive) <= 22
    
    def test_manager_invalid_strategy(self):
        """Test that manager raises error for invalid strategy"""
        with pytest.raises(ValueError):
            DecimationManager("invalid_strategy")
    
    def test_manager_strategy_change(self):
        """Test changing strategy on existing manager"""
        manager = DecimationManager("stride")
        assert manager.strategy == "stride"
        
        manager.set_strategy("lttb")
        assert manager.strategy == "lttb"
        
        with pytest.raises(ValueError):
            manager.set_strategy("invalid")
    
    def test_recommended_target_points(self):
        """Test recommended target points calculation"""
        manager = DecimationManager("lttb")
        
        # Test with different data lengths and display widths
        rec1 = manager.get_recommended_target_points(1000, 1920)
        rec2 = manager.get_recommended_target_points(10000, 1920)
        rec3 = manager.get_recommended_target_points(100, 1920)
        
        # Recommendations should be reasonable
        assert 100 <= rec1 <= 4000  # Between min and reasonable max
        assert rec2 <= 10000  # Not exceed original length
        assert rec3 == 100  # Should be at least minimum


class TestDecimationQuality:
    """Test decimation quality and performance characteristics"""
    
    def test_sine_wave_preservation(self):
        """Test that decimation preserves sine wave characteristics"""
        # Create clean sine wave
        x_data = np.linspace(0, 4*np.pi, 1000)
        y_data = np.sin(x_data)
        
        # Test different decimation methods
        methods = [
            ("lttb", {"target_points": 50}),
            ("stride", {"factor": 20}),
            ("adaptive", {"target_points": 50})
        ]
        
        for method, kwargs in methods:
            manager = DecimationManager(method)
            
            if method == "stride":
                x_dec, y_dec = manager.decimate(x_data, y_data, **kwargs)
            else:
                x_dec, y_dec = manager.decimate(x_data, y_data, **kwargs)
            
            # Check that the general shape is preserved
            # The decimated data should still oscillate around zero
            assert np.mean(y_dec) < 0.1  # Mean should be close to zero
            assert np.max(y_dec) > 0.8   # Should preserve peaks
            assert np.min(y_dec) < -0.8  # Should preserve valleys
    
    def test_noise_handling(self):
        """Test decimation behavior with noisy data"""
        # Create signal with noise
        x_data = np.linspace(0, 10, 1000)
        clean_signal = np.sin(x_data)
        noise = 0.1 * np.random.random(1000)
        y_data = clean_signal + noise
        
        # LTTB should handle noise better than simple stride
        x_lttb, y_lttb = LTTBDecimator.decimate(x_data, y_data, target_points=50)
        x_stride, y_stride = StrideDecimator.decimate(x_data, y_data, factor=20)
        
        # Both should work without errors
        assert len(x_lttb) <= 52
        assert len(x_stride) == 50
    
    def test_empty_data_handling(self):
        """Test decimation with empty or minimal data"""
        # Empty data
        x_empty = np.array([])
        y_empty = np.array([])
        
        manager = DecimationManager("lttb")
        x_dec, y_dec = manager.decimate(x_empty, y_empty, target_points=10)
        
        assert len(x_dec) == 0
        assert len(y_dec) == 0
        
        # Single point
        x_single = np.array([1.0])
        y_single = np.array([2.0])
        
        x_dec, y_dec = manager.decimate(x_single, y_single, target_points=10)
        
        np.testing.assert_array_equal(x_dec, x_single)
        np.testing.assert_array_equal(y_dec, y_single)


if __name__ == "__main__":
    pytest.main([__file__])
