<p align="left">
  <img src="../imgs/docker_icon.png" alt="Docker Icon" width="64" height="64">
</p>

# DockMon

DockMon 是一款簡潔易用的 Docker 容器監控與管理桌面應用程式，採用 Python Tkinter 開發。它可即時顯示容器狀態、資源使用情形，並能快速執行啟動、停止、重啟、重建及查看日誌等操作。也支援容器資源即時圖表（需管理員/Root 權限）與自動語言偵測。

> 如需英文版說明，請參閱 [../README.md](../README.md)。

## 主要功能

- **即時監控**：自動刷新所有 Docker 容器的運行狀態與資源消耗。
- **啟動/停止/重啟/重建容器**：選取容器後一鍵操作。
- **查看日誌**：一鍵取得最新 50 行容器日誌。
- **Uptime 顯示**：精確呈現運行時長（天/時/分/秒）。
- **資源圖表**：CPU、記憶體、網路 I/O 即時圖表（需管理員/Root 權限）。
- **介面多語言**：自動偵測系統語言（英文/繁體中文）。
- **跨平台支援**：自動判斷 Windows、Linux、MacOS，智能選用 docker compose 或 docker-compose 指令。

## 技術特點

- 使用 Python 3 及 Tkinter GUI 框架。
- 透過 `docker` Python SDK 連接本地 Docker 服務。
- 多執行緒背景刷新，介面流暢不卡頓。
- 圖表模組化（見 `lib/DockMod.py`，採用 matplotlib）。
- 主程式單一檔案，易於部署與維護。

## 安裝與啟動

1. **安裝依賴**（需有 Python 3、Docker 及 Docker Compose）：
   ```bash
   pip install docker matplotlib
   ```

2. **下載專案**：
   ```bash
   git clone https://github.com/Shiroko253/DockMon.git
   cd DockMon
   ```

3. **啟動 DockMon**：
   ```bash
   python main.py
   ```

## 截圖

![DockMon Screenshot](../imgs/screenshot.png)

## 授權

本專案採用 MIT License 授權。

---

歡迎提出 Issue 或 Pull Request，一起讓 DockMon 更完善！
