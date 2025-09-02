import tkinter as tk
from tkinter import ttk, messagebox
import docker
import subprocess
import threading
import platform
import time
from datetime import datetime, timezone

client = docker.from_env()

# 判斷系統使用 docker compose 的命令
def get_compose_cmd():
    system = platform.system().lower()
    if system == "windows":
        return ["docker", "compose"]
    else:
        try:
            subprocess.run(["docker-compose", "--version"], check=True, capture_output=True)
            return ["docker-compose"]
        except (subprocess.CalledProcessError, FileNotFoundError):
            return ["docker", "compose"]

COMPOSE_CMD = get_compose_cmd()

# uptime 格式化
def format_uptime(delta):
    days = delta.days
    hours, remainder = divmod(delta.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if days > 0:
        return f"{days}d {hours}h {minutes}m"
    elif hours > 0:
        return f"{hours}h {minutes}m {seconds}s"
    elif minutes > 0:
        return f"{minutes}m {seconds}s"
    else:
        return f"{seconds}s"


class DockMonApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("DockMon - Docker Monitor")
        self.geometry("1100x500")

        # 加載圖示
        try:
            self.iconphoto(True, tk.PhotoImage(file="imgs/docker_icon.png"))
        except Exception:
            pass

        columns = ("Name", "Status", "CPU %", "Mem Usage", "Net I/O", "Uptime")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=15)
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=160, anchor="center")
        self.tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        btn_frame = tk.Frame(self)
        btn_frame.pack(fill=tk.X, pady=5)

        tk.Button(btn_frame, text="Start", command=self.start_container).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Stop", command=self.stop_container).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Restart", command=self.restart_container).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Rebuild & Relaunch", command=self.rebuild_container).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Logs", command=self.show_logs).pack(side=tk.LEFT, padx=5)

        # 背景刷新用
        self.refreshing = False
        self.refresh_thread = None

        # 容器資料快取
        self.container_data = []

        # 啟動自動更新
        self.auto_refresh()

    def auto_refresh(self):
        if not self.refreshing:
            self.refreshing = True
            self.refresh_thread = threading.Thread(target=self.refresh_loop, daemon=True)
            self.refresh_thread.start()
        self.after(1000, self.update_table)  # 每秒刷新 UI

    def refresh_loop(self):
        """背景執行緒：每 30 秒抓一次容器統計資料"""
        while True:
            self.update_container_data()
            time.sleep(30)

    def update_container_data(self):
        """更新容器資料（CPU / Mem / Net I/O / Status）"""
        new_data = []
        try:
            for c in client.containers.list(all=True):
                stats = self.get_stats(c) if c.status == "running" else ("-", "-", "-")
                uptime = self.get_uptime(c) if c.status == "running" else "-"
                new_data.append((c.name, c.status, stats[0], stats[1], stats[2], uptime))
        except Exception:
            pass
        self.container_data = new_data

    def update_table(self):
        """更新 Tkinter UI 表格（每秒跑一次，只更新 Uptime 其他數據保留）"""
        if self.container_data:
            for row in self.tree.get_children():
                self.tree.delete(row)
            for entry in self.container_data:
                name, status, cpu, mem, net, uptime = entry
                if status == "running":
                    uptime = self.get_uptime(client.containers.get(name))
                self.tree.insert("", tk.END, values=(name, status, cpu, mem, net, uptime))
        self.after(1000, self.update_table)

    def get_stats(self, container):
        try:
            s = container.stats(stream=False)

            # CPU %
            cpu_delta = s["cpu_stats"]["cpu_usage"]["total_usage"] - s["precpu_stats"]["cpu_usage"]["total_usage"]
            system_delta = s["cpu_stats"]["system_cpu_usage"] - s["precpu_stats"]["system_cpu_usage"]
            cpu_percent = 0.0
            if system_delta > 0.0 and cpu_delta > 0.0:
                cpu_percent = (cpu_delta / system_delta) * len(s["cpu_stats"]["cpu_usage"].get("percpu_usage", [])) * 100.0

            # Memory
            mem_usage = s["memory_stats"]["usage"] / (1024 * 1024)
            mem_limit = s["memory_stats"]["limit"] / (1024 * 1024)
            mem_str = f"{mem_usage:.0f}MB / {mem_limit:.0f}MB"

            # Net I/O
            net_rx = net_tx = 0
            if "networks" in s:
                for iface in s["networks"].values():
                    net_rx += iface.get("rx_bytes", 0)
                    net_tx += iface.get("tx_bytes", 0)
            net_str = f"{net_rx//1024}kB / {net_tx//1024}kB"

            return (f"{cpu_percent:.1f}%", mem_str, net_str)
        except Exception:
            return ("-", "-", "-")

    def get_uptime(self, container):
        try:
            started_at = container.attrs["State"]["StartedAt"]
            started_time = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
            uptime = datetime.now(timezone.utc) - started_time
            return format_uptime(uptime)
        except Exception:
            return "-"

    def get_selected_container(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "請選擇一個容器")
            return None
        return self.tree.item(selected[0], "values")[0]

    def start_container(self):
        name = self.get_selected_container()
        if name:
            client.containers.get(name).start()

    def stop_container(self):
        name = self.get_selected_container()
        if name:
            client.containers.get(name).stop()

    def restart_container(self):
        name = self.get_selected_container()
        if name:
            client.containers.get(name).restart()

    def rebuild_container(self):
        name = self.get_selected_container()
        if name:
            try:
                subprocess.run(COMPOSE_CMD + ["build", name], check=True)
                subprocess.run(COMPOSE_CMD + ["up", "-d", name], check=True)
            except Exception as e:
                messagebox.showerror("Error", f"Rebuild failed: {e}")

    def show_logs(self):
        name = self.get_selected_container()
        if name:
            container = client.containers.get(name)
            logs = container.logs(tail=50).decode()
            log_win = tk.Toplevel(self)
            log_win.title(f"Logs - {name}")
            text = tk.Text(log_win, wrap="word")
            text.insert("1.0", logs)
            text.pack(fill=tk.BOTH, expand=True)


if __name__ == "__main__":
    app = DockMonApp()
    app.mainloop()
