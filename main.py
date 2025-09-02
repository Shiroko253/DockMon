import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import docker
import subprocess
import datetime

client = docker.from_env()

class DockMonApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("DockMon")
        self.geometry("1100x500")

        columns = ("Name", "Status", "CPU %", "Mem Usage", "Net I/O", "Uptime")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=15)
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=160, anchor="center")
        self.tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        btn_frame = tk.Frame(self)
        btn_frame.pack(fill=tk.X, pady=5)

        tk.Button(btn_frame, text="Refresh", command=self.refresh).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Start", command=self.start_container).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Stop", command=self.stop_container).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Restart", command=self.restart_container).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Rebuild & Relaunch", command=self.rebuild_container).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Logs", command=self.show_logs).pack(side=tk.LEFT, padx=5)

        self.refresh()

    def get_selected_container(self):
        """取得目前選中的容器名稱"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("No selection", "請先選擇一個容器")
            return None
        return self.tree.item(selected[0])["values"][0]

    def refresh(self):
        for row in self.tree.get_children():
            self.tree.delete(row)

        for c in client.containers.list(all=True):
            stats = self.get_stats(c) if c.status == "running" else ("-", "-", "-")
            uptime = self.get_uptime(c) if c.status == "running" else "-"
            self.tree.insert("", tk.END, values=(
                c.name,
                c.status,
                stats[0],
                stats[1],
                stats[2],
                uptime
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

    def get_uptime(self, container):
        try:
            started_at = container.attrs["State"]["StartedAt"]
            start_time = datetime.datetime.fromisoformat(started_at.replace("Z", "+00:00"))
            delta = datetime.datetime.now(datetime.timezone.utc) - start_time
            return str(delta).split(".")[0]  # 去掉毫秒
        except Exception:
            return "-"

    def start_container(self):
        name = self.get_selected_container()
        if name:
            try:
                c = client.containers.get(name)
                c.start()
                messagebox.showinfo("Started", f"容器 {name} 已啟動")
                self.refresh()
            except Exception as e:
                messagebox.showerror("Error", str(e))

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
                subprocess.run(["docker-compose", "build", name], check=True)
                subprocess.run(["docker-compose", "up", "-d", name], check=True)
                messagebox.showinfo("Rebuilt", f"容器 {name} 已重新 build 並啟動")
                self.refresh()
            except Exception as e:
                messagebox.showerror("Error", str(e))

    def show_logs(self):
        name = self.get_selected_container()
        if name:
            try:
                c = client.containers.get(name)
                logs = c.logs(tail=100).decode("utf-8")

                log_window = tk.Toplevel(self)
                log_window.title(f"Logs - {name}")
                log_window.geometry("800x400")

                text_area = scrolledtext.ScrolledText(log_window, wrap=tk.WORD)
                text_area.pack(expand=True, fill="both")
                text_area.insert(tk.END, logs)
                text_area.config(state="disabled")

            except Exception as e:
                messagebox.showerror("Error", str(e))

if __name__ == "__main__":
    app = DockMonApp()
    app.mainloop()
