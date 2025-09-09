# ZNLE VNA Control & Real-time S-Parameter Viewer

A professional Python-based control application for the R&S ZNLE Vector Network Analyzer with modern PyQt6 interface and real-time S-parameter visualization.

## Features

### Core Functionality
- **VNA Control**: Complete control of R&S ZNLE via VISA (HiSLIP/VXI-11/USB-TMC)
- **Real-time Plotting**: Interactive S-parameter visualization with pyqtgraph
- **Data Acquisition**: Continuous and single-shot measurement modes
- **Multi-format Export**: CSV, NumPy, S1P, S2P file formats
- **Marker Analysis**: Interactive frequency markers with precise readouts

### Modern UI Design
- **Professional Theme System**: Light and Dark themes with runtime switching
- **Compact Layout**: Optimized interface for efficient space utilization
- **Tabbed Interface**: Organized controls (Parameters, Measurements, Markers)
- **Status Integration**: Real-time instrument status within parameter tab
- **Logging Dialog**: Non-modal logging interface with save/clear functionality

### Recent Improvements (v1.2.0)
- ✅ **Status Group Integration**: Moved from separate dock to Parameters tab
- ✅ **Compact UI Optimization**: Reduced control sizes while maintaining readability
- ✅ **Enhanced Plot Area**: Maximized plotting space with minimal margins
- ✅ **Improved Logging**: Dialog-based logging system replacing dock widget
- ✅ **Font Optimization**: Balanced font sizes for compact yet readable interface

## Tech Stack

- Python 3.11+
- PyQt6 for GUI
- pyqtgraph for real-time plotting
- NumPy for numerical operations
- RsInstrument for VISA communication
- pytest for testing

## Project Structure

```
ZNLE/
├── app.py                   # Main application entry point
├── requirements.txt         # Dependencies
├── core/
│   ├── __init__.py
│   ├── driver_znle.py      # SCPI driver for ZNLE4
│   ├── acquisition.py      # Data acquisition thread
│   ├── model.py            # Data models and configuration
│   ├── storage.py          # Data storage and export
│   ├── decimate.py         # Data decimation for performance
│   └── logging_cfg.py      # Logging configuration
├── ui/
│   ├── __init__.py
│   ├── main_window.py      # Main application window
│   └── widgets.py          # Custom GUI widgets
├── reusable_theme_system/  # Professional theme system
│   ├── __init__.py
│   ├── theme_manager.py    # Theme management
│   ├── theme_constants.py  # Color schemes and constants
│   └── example_usage.py    # Theme system examples
└── tests/
    ├── __init__.py
    ├── test_block_parse.py
    └── test_decimate.py
```

## Installation

1. Create a virtual environment:
```bash
python -m venv .venv
.venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

Run the application:
```bash
python app.py
```

### Application Interface

- **Parameters Tab**: 
  - Sweep configuration (frequency range, points, power, IF bandwidth)
  - Real-time instrument status (connection, sweep time, acquisition state)
- **Measurements Tab**: S-parameter selection and measurement formats
- **Markers Tab**: Interactive marker management and analysis
- **Plot Area**: High-performance real-time S-parameter visualization
- **Menu System**: File operations, tools, view options, and help

### Theme Switching

The application includes a professional theme system:
- **Light Theme**: Clean, professional interface for normal lighting
- **Dark Theme**: Modern dark interface for low-light environments  
- **Runtime Switching**: Instant theme changes via View → Theme menu
- **Consistent Design**: Professional styling with optimized spacing and colors

To change themes:
1. Go to **View** menu → **Theme**
2. Select **Light Theme** or **Dark Theme**
3. Theme applies instantly without restart

### Basic Operation

1. **Launch Application**: 
   ```bash
   python app.py
   ```

2. **Connect to Instrument**:
   - Go to **Tools** → **Connection...**
   - Enter instrument IP (e.g., `TCPIP::192.168.1.100::hislip0::INSTR`)
   - Select VISA backend (recommended: `rs`)
   - Click **Connect**

3. **Configure Measurements**:
   - **Sweep Tab**: Set frequency range, points, IF bandwidth
   - **Measurements Tab**: Add S-parameters (S11, S12, S21, S22)
   - **Markers Tab**: Add frequency markers for analysis

4. **Start Measurement**:
   - Click **Start** for continuous acquisition
   - Click **Single** for one-time measurement
   - View real-time plots with interactive markers

5. **Export Data**:
   - **File** → **Export** → Choose format (CSV, NumPy, S1P/S2P)

## Configuration

- Default connection: HiSLIP protocol
- Resource string format: `TCPIP::<ip>::hislip0::INSTR`
- Alternative VXI-11: `TCPIP::<ip>::inst0::INSTR`

## Development

- Follow PEP8 coding standards
- Use type hints
- All SCPI operations include timeout and error checking
- Non-blocking UI thread design
- Comprehensive logging

## Testing

Run tests:
```bash
pytest tests/
```

## License

This project is for educational and research purposes.
