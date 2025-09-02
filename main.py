import tkinter as tk
from tkinter import ttk, messagebox
import docker
import subprocess

client = docker.from_env()

class DockMonApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("DockMon")
        self.geometry("950x450")

        # 表格欄位
        columns = ("Name", "Status", "CPU %", "Mem Usage", "Net I/O")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=15)
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=160, anchor="center")
        self.tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 控制按鈕
        btn_frame = tk.Frame(self)
        btn_frame.pack(fill=tk.X, pady=5)

        refresh_btn = tk.Button(btn_frame, text="Refresh", command=self.refresh)
        refresh_btn.pack(side=tk.LEFT, padx=5)

        stop_btn = tk.Button(btn_frame, text="Stop", command=self.stop_container)
        stop_btn.pack(side=tk.LEFT, padx=5)

        restart_btn = tk.Button(btn_frame, text="Restart", command=self.restart_container)
        restart_btn.pack(side=tk.LEFT, padx=5)

        rebuild_btn = tk.Button(btn_frame, text="Rebuild & Relaunch", command=self.rebuild_container)
        rebuild_btn.pack(side=tk.LEFT, padx=5)

        self.refresh()

    def get_selected_container(self):
        """取得目前選中的容器名稱"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("No selection", "請先選擇一個容器")
            return None
        name = self.tree.item(selected[0])["values"][0]
        return name

    def refresh(self):
        # 清空表格
        for row in self.tree.get_children():
            self.tree.delete(row)

        # 加載容器資訊
        for c in client.containers.list(all=True):
            stats = self.get_stats(c) if c.status == "running" else ("-", "-", "-")
            self.tree.insert("", tk.END, values=(
                c.name,
                c.status,
                stats[0],   # CPU
                stats[1],   # Memory
                stats[2]    # Net I/O
            ))

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

    def stop_container(self):
        name = self.get_selected_container()
        if name:
            try:
                c = client.containers.get(name)
                c.stop()
                messagebox.showinfo("Stopped", f"容器 {name} 已停止")
                self.refresh()
            except Exception as e:
                messagebox.showerror("Error", str(e))

    def restart_container(self):
        name = self.get_selected_container()
        if name:
            try:
                c = client.containers.get(name)
                c.restart()
                messagebox.showinfo("Restarted", f"容器 {name} 已重啟")
                self.refresh()
            except Exception as e:
                messagebox.showerror("Error", str(e))

    def rebuild_container(self):
        name = self.get_selected_container()
        if name:
            try:
                # 這裡假設 Docker Compose 定義了這個容器
                subprocess.run(["docker-compose", "build", name], check=True)
                subprocess.run(["docker-compose", "up", "-d", name], check=True)
                messagebox.showinfo("Rebuilt", f"容器 {name} 已重新 build 並啟動")
                self.refresh()
            except Exception as e:
                messagebox.showerror("Error", str(e))

if __name__ == "__main__":
    app = DockMonApp()
    app.mainloop()
