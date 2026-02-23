# HTMS (Hybrid Toll Management System)

## Project Structure

This project follows a clean architecture with a single modern frontend located in the `/frontend` directory.

### Directory Structure
```
HTMS_Project/
├── index.html                    # Root redirect to modern frontend
├── _legacy_ui_backup/           # Backup of legacy UI (archived)
├── frontend/                    # Modern UI (current active frontend)
│   ├── css/
│   │   └── style.css            # Modern CSS with white theme
│   ├── js/
│   │   ├── app.js               # Main application logic (no auto-refresh)
│   │   ├── common.js            # Shared utilities
│   │   ├── readers.js           # Reader management
│   │   ├── decisions.js         # Decision telemetry
│   │   └── blockchain.js        # Blockchain audit
│   ├── index.html               # Modern dashboard
│   ├── readers.html             # Reader trust monitor
│   ├── decisions.html           # Decision telemetry
│   ├── blockchain.html          # Blockchain audit
│   ├── reader-management.html   # Reader management
│   ├── manual-entry.html        # Manual entry interface
│   └── toll-processing.html     # Toll processing
├── backend/                     # Backend services
└── ...
```

## Key Features

- **Modern UI**: Clean white theme with sidebar navigation
- **No Auto-Refresh**: Stable interface without automatic page refreshes
- **Hardware Integration**: Designed for real hardware data input
- **Manual Entry**: Interface for manual transaction entry
- **Responsive Design**: Works on various screen sizes

## Development

- Local development: Access via `http://127.0.0.1:5500/` (redirects to modern UI)
- GitHub Pages: Serves the modern UI from `/frontend` directory
- Backend API: Connects to `http://127.0.0.1:8000` by default

## Production Mode

The system operates in production mode with:
- Real hardware data input only
- Manual data entry capability
- No simulated data generation
- Stable, non-refreshing interface