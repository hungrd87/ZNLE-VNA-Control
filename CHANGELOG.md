# Changelog

All notable changes to the ZNLE VNA Control application will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.0] - 2025-09-09

### Added
- Non-modal logging dialog accessible via View → Logging menu
- Status group integration within Parameters tab for better organization
- Compact UI optimization for efficient space utilization
- Enhanced plot area with minimal margins for maximum visualization space
- Comprehensive git repository setup with .gitignore and documentation

### Changed
- Renamed "Sweep" tab to "Parameters" for better semantic meaning
- Moved Status group from separate dock widget to Parameters tab
- Optimized font sizes for better readability while maintaining compact design
- Reduced control heights and spacing for more efficient layout
- Window size optimized to 1200x900 for optimal plot visibility

### Improved
- Status information now logically grouped with sweep parameters
- Plot area maximized by removing unnecessary margins and spacing
- UI responsiveness with compact controls maintaining functionality
- Theme consistency across light and dark modes

### Technical
- Refactored status label management to use widget-based approach
- Removed redundant dock widget code for cleaner architecture
- Enhanced SweepConfigWidget with integrated status display
- Improved main window layout with optimized space distribution

## [1.1.0] - 2025-09-08

### Added
- Professional theme system with light and dark themes
- Runtime theme switching capability
- Reusable theme management system
- Enhanced UI styling with professional appearance
- Theme constants for consistent design elements

### Changed
- Upgraded UI to use professional theme system
- Improved visual consistency across all widgets
- Enhanced button and control styling

### Improved
- Professional desktop-standard appearance
- Consistent color schemes and spacing
- Better user experience with modern styling

## [1.0.0] - 2025-09-07

### Added
- Initial release of ZNLE VNA Control application
- Core VNA control functionality via VISA/SCPI
- Real-time S-parameter plotting with pyqtgraph
- Sweep configuration with frequency range, points, and power settings
- S-parameter measurement configuration (S11, S12, S21, S22)
- Interactive marker functionality for frequency analysis
- Multiple data export formats (CSV, NumPy, S1P, S2P)
- PyQt6-based modern GUI interface
- Comprehensive logging system
- Unit tests for core functionality

### Core Features
- ZNLE instrument driver with SCPI command interface
- Data acquisition system with continuous and single-shot modes
- Real-time plotting with interactive crosshairs and legends
- Measurement configuration for multiple S-parameters
- Marker system for precise frequency analysis
- Professional menu system with keyboard shortcuts
- Status bar for real-time instrument feedback

### Technical Foundation
- Modular architecture with separate core, UI, and test components
- Type-hinted Python codebase for better maintainability
- Error handling and timeout management for instrument communication
- Non-blocking UI design with proper threading
- Comprehensive test suite with pytest
- Logging configuration for debugging and monitoring

---

## Development Guidelines

### Version Numbering
- **Major** (X.0.0): Breaking changes, major feature additions
- **Minor** (1.X.0): New features, significant improvements
- **Patch** (1.1.X): Bug fixes, minor improvements

### Changelog Categories
- **Added**: New features
- **Changed**: Changes in existing functionality  
- **Deprecated**: Soon-to-be removed features
- **Removed**: Removed features
- **Fixed**: Bug fixes
- **Security**: Vulnerability fixes
- **Improved**: Enhancements to existing features
- **Technical**: Internal/architectural changes
