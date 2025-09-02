<p align="left">
  <img src="imgs/docker_icon.png" alt="Docker Icon" width="64" height="64">
</p>

# DockMon

DockMon is a simple, cross-platform desktop application for monitoring and managing Docker containers, built with Python Tkinter. It provides a real-time overview of container status, resource usage, and convenient management operations—all in one place.

> For Traditional Chinese, please refer to [doc/README-ch_tw.md](doc/README-ch_tw.md).

## Features

- **Live Monitoring:** Auto-refresh display of all Docker containers, including status and resource consumption.
- **Start/Stop/Restart/Rebuild Containers:** Easily control containers with single-click operations.
- **View Logs:** One-click access to the latest 50 lines of container logs.
- **Uptime Display:** Accurate running time shown in days/hours/minutes/seconds.
- **Resource Charts:** Real-time charts for CPU, memory, and network I/O (requires admin/root privileges).
- **Multi-language UI:** Automatically detects system language (English/Traditional Chinese).
- **Cross-platform:** Supports Windows, Linux, and MacOS. Automatically selects `docker compose` or `docker-compose` command.

## Technical Highlights

- Built with Python 3 and Tkinter GUI framework.
- Uses `docker` Python SDK to connect to local Docker service.
- Background threads for smooth UI and real-time updates.
- Modular chart logic with matplotlib (see `lib/DockMod.py`).
- Single-file main program; easy to deploy and maintain.

## Installation & Usage

1. **Install dependencies**  
   Requires Python 3, Docker, and Docker Compose:
   ```bash
   pip install docker matplotlib
   ```

2. **Clone the repository**
   ```bash
   git clone https://github.com/Shiroko253/DockMon.git
   cd DockMon
   ```

3. **Run DockMon**
   ```bash
   python main.py
   ```

## License

This project is licensed under the MIT License.

---

Feel free to submit issues or pull requests to help improve DockMon!
