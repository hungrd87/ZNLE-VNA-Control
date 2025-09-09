# QUICK START GUIDE - ZNLE VNA Control

## 🚀 Immediate Usage Instructions

### Prerequisites Verified ✅
- Python 3.13.7 installed and configured
- Virtual environment created: `.venv/`
- All dependencies installed successfully

### Start Application
```powershell
# Navigate to project directory
cd "d:\HUNG\Projects\Instruments_Projects\ZNLE"

# Run application
.\.venv\Scripts\python.exe app.py
```

### Expected Output
```
2025-09-07 09:40:25 - root - INFO - Logging configured successfully
2025-09-07 09:40:26 - ui.main_window - INFO - Main window initialized
```

## 🔧 Basic Operation

### 1. Connect to ZNLE4
- Open **Connection** tab
- Enter instrument IP: `TCPIP::192.168.1.100::hislip0::INSTR`
- Select VISA backend: `rs` (recommended)
- Click **Connect**

### 2. Configure Sweep
- Open **Sweep** tab
- Set frequency range (e.g., 1 GHz - 2 GHz)
- Set points (e.g., 801)
- Set IF bandwidth (e.g., 3 kHz)
- Click **Apply Configuration**

### 3. Add Measurements
- Open **Measurements** tab
- Enter measurement name (e.g., "S11_Reflection")
- Select parameter: S11, S12, S21, or S22
- Select format: MLOG (magnitude dB) or PHAS (phase)
- Click **Add Measurement**

### 4. Start Measurement
- Click **Start** for continuous acquisition
- OR click **Single** for one-time measurement
- View real-time data in plot panel

### 5. Add Markers
- Double-click on plot to add markers
- OR use **Markers** tab for precise frequency entry

### 6. Export Data
- **File** → **Export** → Choose format:
  - **CSV** for spreadsheet analysis
  - **NumPy** for Python processing
  - **S1P/S2P** for RF simulation tools

## 📁 Project Files Overview

### Core Application
- `app.py` - Main entry point
- `core/driver_znle.py` - SCPI communication
- `ui/main_window.py` - Main interface

### Configuration
- `requirements.txt` - Dependencies
- `core/model.py` - Settings and data structures
- `core/logging_cfg.py` - Logging setup

### Data Handling
- `core/acquisition.py` - Real-time measurement
- `core/storage.py` - Export functionality
- `core/decimate.py` - Performance optimization

## 🧪 Testing

### Run Tests
```powershell
.\.venv\Scripts\python.exe -m pytest tests/
```

### Test Coverage
- Data parsing and S-parameter conversion
- Decimation algorithm verification
- Format handling validation

## 🔍 Troubleshooting

### Common Issues
1. **"Python was not found"**
   - Use full path: `.\.venv\Scripts\python.exe`

2. **Import errors**
   - Ensure you're in the ZNLE directory
   - Check virtual environment activation

3. **Connection failed**
   - Verify instrument IP address
   - Check network connectivity
   - Try different VISA backend

4. **GUI doesn't appear**
   - Check PyQt6 installation
   - Verify display settings

### Log Files
- Application logs: `logs/znle_control.log`
- Console output for real-time debugging

## 📈 Performance Tips

### For Large Datasets
- Enable decimation in acquisition settings
- Adjust update rate (5-20 Hz recommended)
- Use LTTB algorithm for best quality

### For Real-time Display
- Reduce number of plot points
- Use appropriate IF bandwidth
- Monitor memory usage

## 🔧 Customization

### Modify Default Settings
Edit `core/model.py`:
- Default frequency ranges
- IF bandwidth values
- Update rates
- Buffer sizes

### Add New S-Parameters
Extend `SParameter` enum in `core/model.py`
Update driver commands in `core/driver_znle.py`

### Custom Export Formats
Add new exporters in `core/storage.py`
Register in main window menu

## 📞 Support

### Documentation
- `README.md` - Complete project overview
- `PROJECT_SUMMARY.md` - Technical details
- `SESSION_SUMMARY.md` - Development history

### Key Contacts
- SCPI Reference: R&S ZNLE Manual
- PyQt6 Documentation: Qt6 official docs
- RsInstrument: R&S Python ecosystem

---

**Application Status: ✅ READY FOR USE**  
**Last Tested: September 7, 2025**  
**Python Version: 3.13.7**  
**All Dependencies: Installed**
