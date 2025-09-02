import tkinter as tk
from tkinter import ttk, messagebox
import docker, subprocess, threading, platform, time, os, json
from datetime import datetime
from lib import DockMod

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

# 判斷管理員權限
def is_admin():
    if platform.system().lower() == "windows":
        try:
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except:
            return False
    else:
        return os.geteuid() == 0

# 載入語言
def load_language():
    try:
        sys_lang = platform.locale.getlocale()[0]
    except:
        sys_lang = "en_US"
    lang_file = "language/en-us.json"
    if sys_lang and "zh" in str(sys_lang).lower():
        lang_file = "language/zh-tw.json"
    if os.path.exists(lang_file):
        with open(lang_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}
LANG = load_language()


class DockMonApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(LANG.get("title", "DockMon - Docker Monitor"))
        self.geometry("1100x600")
        self.has_admin = is_admin()
        self.container_data = []

        self.init_ui()

        self.refresh_thread = threading.Thread(target=self.refresh_loop, daemon=True)
        self.refresh_thread.start()

        self.update_ui_loop()

    def init_ui(self):
        # 表格
        columns = ("Name", "Status", "CPU %", "Mem Usage", "Net I/O", "Uptime")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=15)
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=160, anchor="center")
        self.tree.pack(fill=tk.BOTH, expand=False, padx=10, pady=10)

        # 按鈕
        btn_frame = tk.Frame(self)
        btn_frame.pack(fill=tk.X, pady=5)
        tk.Button(btn_frame, text=LANG.get("start","Start"), command=self.start_container).pack(side=tk.LEFT,padx=5)
        tk.Button(btn_frame, text=LANG.get("stop","Stop"), command=self.stop_container).pack(side=tk.LEFT,padx=5)
        tk.Button(btn_frame, text=LANG.get("restart","Restart"), command=self.restart_container).pack(side=tk.LEFT,padx=5)
        tk.Button(btn_frame, text=LANG.get("rebuild","Rebuild & Relaunch"), command=self.rebuild_container).pack(side=tk.LEFT,padx=5)
        tk.Button(btn_frame, text=LANG.get("logs","Logs"), command=self.show_logs).pack(side=tk.LEFT,padx=5)

        # 圖表
        if self.has_admin:
            self.canvas, self.ax_dict, self.history = DockMod.init_chart(self)
        else:
            print(LANG.get("chart_permission_warning","Resource charts require admin/root privileges."))

    def refresh_loop(self):
        """背景執行緒：每 60 秒抓一次容器資料"""
        while True:
            try:
                data = []
                for c in client.containers.list(all=True):
                    stats = self.get_stats(c) if c.status == "running" else ("-", "-", "-")
                    uptime = self.get_uptime(c) if c.status == "running" else "-"
                    data.append((c.name, c.status, stats[0], stats[1], stats[2], uptime))
                self.container_data = data
            except:
                pass
            time.sleep(60)

    def update_ui_loop(self):
        # 更新表格
        for row in self.tree.get_children():
            self.tree.delete(row)
        for entry in self.container_data:
            self.tree.insert("", tk.END, values=entry)

        # 更新圖表
        if self.has_admin:
            DockMod.update_chart(self.canvas, self.ax_dict, self.history, self.container_data)

        self.after(1000, self.update_ui_loop)

    def get_stats(self, container):
        try:
            s = container.stats(stream=False)
            cpu_delta = s["cpu_stats"]["cpu_usage"]["total_usage"] - s["precpu_stats"]["cpu_usage"]["total_usage"]
            system_delta = s["cpu_stats"]["system_cpu_usage"] - s["precpu_stats"]["system_cpu_usage"]
            cpu_percent = 0.0
            if system_delta > 0.0 and cpu_delta > 0.0:
                cpu_percent = (cpu_delta / system_delta) * len(s["cpu_stats"]["cpu_usage"].get("percpu_usage",[])) * 100.0

            mem_usage = s["memory_stats"]["usage"] / (1024*1024)
            mem_limit = s["memory_stats"]["limit"] / (1024*1024)
            mem_str = f"{mem_usage:.0f}MB / {mem_limit:.0f}MB"

            net_rx = net_tx = 0
            if "networks" in s:
                for iface in s["networks"].values():
                    net_rx += iface.get("rx_bytes",0)
                    net_tx += iface.get("tx_bytes",0)
            net_str = f"{net_rx//1024}kB / {net_tx//1024}kB"

            return (f"{cpu_percent:.1f}%", mem_str, net_str)
        except:
            return ("-", "-", "-")

    def get_uptime(self, container):
        try:
            started_at = container.attrs["State"]["StartedAt"]
            started_time = datetime.fromisoformat(started_at.replace("Z","+00:00"))
            uptime = datetime.utcnow() - started_time.replace(tzinfo=None)
            return str(uptime).split(".")[0]
        except:
            return "-"

    def get_selected_container(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning(LANG.get("select_container_warning","Please select a container"))
            return None
        return self.tree.item(selected[0],"values")[0]

    def start_container(self):
        name = self.get_selected_container()
        if name:
            container = client.containers.get(name)
            container.start()

    def stop_container(self):
        name = self.get_selected_container()
        if name:
            container = client.containers.get(name)
            container.stop()

    def restart_container(self):
        name = self.get_selected_container()
        if name:
            container = client.containers.get(name)
            container.restart()

    def rebuild_container(self):
        name = self.get_selected_container()
        if name:
            try:
                subprocess.run(COMPOSE_CMD + ["build", name], check=True)
                subprocess.run(COMPOSE_CMD + ["up","-d", name], check=True)
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
