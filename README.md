# Container Log Viewer 🐳📋

A web-based log viewer for Docker, Kubernetes, and system logs built with Python and Flask.

![Screenshot](screenshot.png) *(Replace with actual screenshot)*

## Features ✨

- **Docker Logs**: View real-time logs from running containers
- **Kubernetes Support**: Access pod logs across namespaces
- **System Logs**: Monitor `/var/log/syslog`, Nginx access/error logs
- **Auto-Refresh**: Configurable refresh intervals (5s, 10s, 30s, 1m)
- **User-Friendly UI**:
  - Dark mode log display
  - One-click scroll to top/bottom
  - Download logs as text files
- **Error Handling**: Visual alerts for logging driver issues

## Installation 🛠️

### Prerequisites
- Python 3.7+
- Docker Engine (for Docker logs)
- kubectl configured (for Kubernetes logs)

### Steps
1. Clone the repository:
   git clone https://github.com/yourusername/container-log-viewer.git
   cd container-log-viewer
   
Install dependencies:


pip install flask

Configure (optional):

Edit KUBECONFIG_PATH in app.py if your kubeconfig is elsewhere

Add custom log paths in the NGINX_* variables

Run:

python app.py

Access at: http://localhost:5000

Usage 🖥️
Docker Tab:

Select container from dropdown

Set number of lines to display (default: 500)

Kubernetes Tab:

Choose namespace → pod

Tail logs with auto-refresh

System Tab:

Select from predefined logs or enter custom path

Supports Nginx access/error logs


Key Functions
get_docker_logs(): Handles both direct log API and file-based fallback

read_file_tail(): Efficiently reads last N lines of large files

AJAX endpoints for dynamic pod listing and log refreshing

Troubleshooting 🐞
Docker Logs Error?

The app automatically falls back to reading log files when Docker's logging driver doesn't support direct reading

Kubernetes Access Issues?

Verify your kubeconfig path in app.py

Ensure kubectl has proper permissions

Contributing 🤝
Pull requests welcome! Especially for:

Additional log source integrations

UI improvements

Security enhancements
