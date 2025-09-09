"""
Data decimation for performance optimization
"""

import numpy as np
from typing import Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class LTTBDecimator:
    """
    Largest Triangle Three Buckets (LTTB) algorithm for time series decimation.
    Preserves important features while reducing data points.
    """
    
    @staticmethod
    def decimate(x_data: np.ndarray, y_data: np.ndarray, 
                target_points: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Apply LTTB decimation algorithm
        
        Args:
            x_data: X-axis data (frequency)
            y_data: Y-axis data (measurement values)
            target_points: Target number of points after decimation
            
        Returns:
            Tuple of (decimated_x, decimated_y)
        """
        if len(x_data) != len(y_data):
            raise ValueError("X and Y data must have same length")
        
        if len(x_data) <= target_points:
            return x_data, y_data
        
        if target_points < 3:
            # For very small target sizes, use simple stride
            stride = len(x_data) // target_points
            return x_data[::stride], y_data[::stride]
        
        # LTTB algorithm
        bucket_size = (len(x_data) - 2) / (target_points - 2)
        
        # Always include first point
        sampled_x = [x_data[0]]
        sampled_y = [y_data[0]]
        
        a = 0  # Initially a is the first point in the triangle
        
        for i in range(target_points - 2):
            # Calculate point average for next bucket (for triangle peak)
            avg_range_start = int((i + 1) * bucket_size) + 1
            avg_range_end = int((i + 2) * bucket_size) + 1
            avg_range_end = min(avg_range_end, len(x_data))
            
            if avg_range_start >= avg_range_end:
                break
                
            avg_x = np.mean(x_data[avg_range_start:avg_range_end])
            avg_y = np.mean(y_data[avg_range_start:avg_range_end])
            
            # Get the range for this bucket
            range_start = int(i * bucket_size) + 1
            range_end = int((i + 1) * bucket_size) + 1
            range_end = min(range_end, len(x_data))
            
            if range_start >= range_end:
                break
            
            # Point a is already selected
            point_a_x = x_data[a]
            point_a_y = y_data[a]
            
            max_area = -1
            next_a = range_start
            
            for j in range(range_start, range_end):
                # Calculate triangle area
                area = abs((point_a_x - avg_x) * (y_data[j] - point_a_y) - 
                          (point_a_x - x_data[j]) * (avg_y - point_a_y))
                
                if area > max_area:
                    max_area = area
                    next_a = j
            
            sampled_x.append(x_data[next_a])
            sampled_y.append(y_data[next_a])
            a = next_a
        
        # Always include last point
        sampled_x.append(x_data[-1])
        sampled_y.append(y_data[-1])
        
        return np.array(sampled_x), np.array(sampled_y)


class StrideDecimator:
    """Simple stride-based decimation"""
    
    @staticmethod
    def decimate(x_data: np.ndarray, y_data: np.ndarray, 
                factor: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Apply stride decimation
        
        Args:
            x_data: X-axis data
            y_data: Y-axis data
            factor: Decimation factor (take every Nth point)
            
        Returns:
            Tuple of (decimated_x, decimated_y)
        """
        if factor <= 1:
            return x_data, y_data
        
        return x_data[::factor], y_data[::factor]


class AdaptiveDecimator:
    """
    Adaptive decimation that preserves peaks and important features
    """
    
    @staticmethod
    def decimate(x_data: np.ndarray, y_data: np.ndarray, 
                target_points: int, preserve_peaks: bool = True) -> Tuple[np.ndarray, np.ndarray]:
        """
        Apply adaptive decimation
        
        Args:
            x_data: X-axis data
            y_data: Y-axis data
            target_points: Target number of points
            preserve_peaks: Whether to preserve local maxima/minima
            
        Returns:
            Tuple of (decimated_x, decimated_y)
        """
        if len(x_data) <= target_points:
            return x_data, y_data
        
        # Find important points to preserve
        important_indices = set()
        
        # Always preserve first and last points
        important_indices.add(0)
        important_indices.add(len(x_data) - 1)
        
        if preserve_peaks and len(y_data) > 2:
            # Find local maxima and minima
            for i in range(1, len(y_data) - 1):
                if (y_data[i] > y_data[i-1] and y_data[i] > y_data[i+1]) or \
                   (y_data[i] < y_data[i-1] and y_data[i] < y_data[i+1]):
                    important_indices.add(i)
        
        # If we have too many important points, select the most significant ones
        if len(important_indices) > target_points:
            # Calculate significance based on local variance
            significance_scores = []
            for idx in important_indices:
                if idx == 0 or idx == len(y_data) - 1:
                    significance_scores.append((float('inf'), idx))  # Always keep endpoints
                else:
                    # Calculate local variance around this point
                    start = max(0, idx - 2)
                    end = min(len(y_data), idx + 3)
                    local_var = np.var(y_data[start:end])
                    significance_scores.append((local_var, idx))
            
            # Sort by significance and keep top points
            significance_scores.sort(reverse=True)
            important_indices = set(idx for _, idx in significance_scores[:target_points])
        
        # Fill remaining slots with evenly spaced points
        remaining_slots = target_points - len(important_indices)
        if remaining_slots > 0:
            # Create mask for available indices
            available_indices = []
            for i in range(len(x_data)):
                if i not in important_indices:
                    available_indices.append(i)
            
            if available_indices:
                # Select evenly spaced points from available indices
                if remaining_slots >= len(available_indices):
                    important_indices.update(available_indices)
                else:
                    step = len(available_indices) / remaining_slots
                    for i in range(remaining_slots):
                        idx = available_indices[int(i * step)]
                        important_indices.add(idx)
        
        # Sort indices and extract data
        selected_indices = sorted(important_indices)
        
        return x_data[selected_indices], y_data[selected_indices]


class DecimationManager:
    """
    Manager class for handling different decimation strategies
    """
    
    def __init__(self, strategy: str = "lttb"):
        """
        Initialize decimation manager
        
        Args:
            strategy: Decimation strategy ("lttb", "stride", "adaptive")
        """
        self.strategy = strategy
        self.decimators = {
            "lttb": LTTBDecimator(),
            "stride": StrideDecimator(),
            "adaptive": AdaptiveDecimator()
        }
        
        if strategy not in self.decimators:
            raise ValueError(f"Unknown decimation strategy: {strategy}")
    
    def decimate(self, x_data: np.ndarray, y_data: np.ndarray, 
                target_points: Optional[int] = None, 
                factor: Optional[int] = None) -> Tuple[np.ndarray, np.ndarray]:
        """
        Apply decimation using configured strategy
        
        Args:
            x_data: X-axis data
            y_data: Y-axis data
            target_points: Target number of points (for LTTB and adaptive)
            factor: Decimation factor (for stride)
            
        Returns:
            Tuple of (decimated_x, decimated_y)
        """
        if len(x_data) == 0 or len(y_data) == 0:
            return x_data, y_data
        
        try:
            if self.strategy == "stride":
                if factor is None:
                    factor = 2
                return self.decimators[self.strategy].decimate(x_data, y_data, factor)
            else:
                if target_points is None:
                    target_points = len(x_data) // 2
                return self.decimators[self.strategy].decimate(x_data, y_data, target_points)
        
        except Exception as e:
            logger.error(f"Decimation failed: {e}")
            # Fallback to simple stride decimation
            factor = max(1, len(x_data) // (target_points or len(x_data) // 2))
            return x_data[::factor], y_data[::factor]
    
    def set_strategy(self, strategy: str) -> None:
        """Change decimation strategy"""
        if strategy not in self.decimators:
            raise ValueError(f"Unknown decimation strategy: {strategy}")
        self.strategy = strategy
    
    def get_recommended_target_points(self, data_length: int, 
                                    display_width_pixels: int = 1920) -> int:
        """
        Get recommended target points based on data length and display resolution
        
        Args:
            data_length: Original data length
            display_width_pixels: Display width in pixels
            
        Returns:
            Recommended target points
        """
        # Rule of thumb: 2-4 points per pixel for smooth curves
        points_per_pixel = 2
        recommended = display_width_pixels * points_per_pixel
        
        # Don't exceed original data length
        recommended = min(recommended, data_length)
        
        # Ensure minimum reasonable number of points
        recommended = max(recommended, 100)
        
        return recommended
