import os
import tkinter as tk
from tkinter import ttk, messagebox, StringVar
import docker, subprocess, threading, platform, time, json
from datetime import datetime, timezone
from lib import DockMod
from lib.help import get_help_text

# sv-ttk 主題支援（需 pip install sv-ttk）
try:
    import sv_ttk
    SV_TTK_AVAILABLE = True
except ImportError:
    sv_ttk = None
    SV_TTK_AVAILABLE = False

client = docker.from_env()

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

def is_admin():
    if platform.system().lower() == "windows":
        try:
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except:
            return False
    else:
        return os.geteuid() == 0

def get_language_options():
    options = {}
    lang_dir = "language"
    if not os.path.isdir(lang_dir):
        return {"English": "en-us"}
    for fname in os.listdir(lang_dir):
        if fname.endswith(".json"):
            code = fname.replace(".json", "")
            try:
                with open(os.path.join(lang_dir, fname), encoding="utf-8") as f:
                    title = json.load(f).get("title", code)
                    if "zh" in code:
                        display = "简体中文" if "cn" in code else "繁體中文"
                    elif "ja" in code:
                        display = "日本語"
                    elif "ko" in code:
                        display = "한국어"
                    elif "en" in code:
                        display = "English"
                    elif "es" in code:
                        display = "Español"
                    elif "de" in code:
                        display = "Deutsch"
                    elif "fr" in code:
                        display = "Français"
                    else:
                        display = title
                    options[display] = code
            except:
                options[code] = code
    return options

def load_language(lang_code=None):
    lang_dir = "language"
    if not lang_code:
        lang_code = "en-us"
    lang_file = os.path.join(lang_dir, f"{lang_code}.json")
    if os.path.exists(lang_file):
        with open(lang_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

class DockMonApp(tk.Tk):
    def __init__(self):
        super().__init__()
        # 主題設定（只亮/暗）
        self.theme_options = {
            "Light": "light",
            "Dark": "dark"
        }
        self.theme_var = StringVar(value="Light")  # 默認亮色

        try:
            self.iconphoto(False, tk.PhotoImage(file="imgs/docker_icon.png"))
        except Exception as e:
            print(f"Icon load failed: {e}")

        # 語言（預設英文）
        self.language_options = get_language_options()
        self.lang_var = StringVar(value=[k for k, v in self.language_options.items() if v == "en-us"][0])
        self.LANG = load_language(self.language_options[self.lang_var.get()])

        self.title(self.LANG.get("title", "DockMon - Docker Monitor"))
        self.geometry("1100x700")
        self.has_admin = is_admin()
        self.container_data = []
        self.error_msg_var = StringVar(value="")
        self._selected_container_name = None
        self.chart_loaded = False

        try:
            self.init_ui()
        except Exception as e:
            messagebox.showerror("UI Init Failed", f"UI 初始化失敗: {e}")
            raise
        self.set_theme(self.theme_var.get())  # 初始化主題
        self.refresh_thread = threading.Thread(target=self.refresh_loop, daemon=True)
        self.refresh_thread.start()
        self.update_ui_loop()

    def init_ui(self):
        top_frame = tk.Frame(self)
        top_frame.pack(fill=tk.X, padx=10, pady=5, anchor='ne')

        # 主題選單
        theme_label = tk.Label(top_frame, text="Theme:")
        theme_label.pack(side=tk.LEFT)
        theme_combo = ttk.Combobox(top_frame, textvariable=self.theme_var, values=list(self.theme_options.keys()), state="readonly", width=10)
        theme_combo.pack(side=tk.LEFT)
        theme_combo.bind("<<ComboboxSelected>>", self.change_theme)

        # 語言選單
        lang_label = tk.Label(top_frame, text="Language:")
        lang_label.pack(side=tk.LEFT, padx=(20,0))
        lang_combo = ttk.Combobox(top_frame, textvariable=self.lang_var, values=list(self.language_options.keys()), state="readonly", width=12)
        lang_combo.pack(side=tk.LEFT)
        lang_combo.bind("<<ComboboxSelected>>", self.change_language)

        refresh_btn = tk.Button(top_frame, text=self.LANG.get("refresh", "Refresh"), command=self.manual_refresh)
        refresh_btn.pack(side=tk.LEFT, padx=15)

        # 幫助按鈕
        help_btn = tk.Button(top_frame, text="Help", command=self.show_help)
        help_btn.pack(side=tk.RIGHT, padx=5)

        columns = ("Name", "Status", "CPU %", "Mem Usage", "Net I/O", "Uptime")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=15)
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=160, anchor="center")
        self.tree.pack(fill=tk.BOTH, expand=False, padx=10, pady=10)
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)

        btn_frame = tk.Frame(self)
        btn_frame.pack(fill=tk.X, pady=5)
        self.btn_keys = ["start", "stop", "restart", "rebuild", "logs", "remove"]
        self.btn_funcs = [self.start_container, self.stop_container, self.restart_container, self.rebuild_container, self.show_logs, self.remove_container]
        self.btns = []
        for key, func in zip(self.btn_keys, self.btn_funcs):
            btn = tk.Button(btn_frame, text=self.LANG.get(key, key.title()), command=func, width=16)
            btn.pack(side=tk.LEFT, padx=5)
            self.btns.append(btn)

        msg_frame = tk.Frame(self)
        msg_frame.pack(fill=tk.X, padx=10, pady=2)
        self.error_label = tk.Label(msg_frame, textvariable=self.error_msg_var, fg="red")
        self.error_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        clear_btn = tk.Button(msg_frame, text=self.LANG.get("clear_msg", "Clear Message"), command=lambda: self.error_msg_var.set(""))
        clear_btn.pack(side=tk.RIGHT, padx=5)

        if self.has_admin:
            self.chart_btn = tk.Button(self, text=self.LANG.get("show_chart", "Show Resource Charts"), command=self.show_chart)
            self.chart_btn.pack(pady=5)
        else:
            tk.Label(self, text=self.LANG.get("chart_permission_warning", "Resource charts require admin/root privileges."), fg="orange").pack(pady=5)

        self.chart_area = None

    def set_theme(self, mode):
        if SV_TTK_AVAILABLE:
            if mode == "Light":
                sv_ttk.set_theme("light")
            elif mode == "Dark":
                sv_ttk.set_theme("dark")
        else:
            style = ttk.Style()
            if mode == "Dark":
                style.theme_use("alt")
            else:
                style.theme_use("default")

    def change_theme(self, event=None):
        self.set_theme(self.theme_var.get())

    def change_language(self, event=None):
        lang_code = self.language_options[self.lang_var.get()]
        self.LANG = load_language(lang_code)
        self.title(self.LANG.get("title", "DockMon - Docker Monitor"))
        for i, btn in enumerate(self.btns):
            btn.config(text=self.LANG.get(self.btn_keys[i], self.btns[i].cget("text")))
        for child in self.pack_slaves():
            if isinstance(child, tk.Button) and child.cget("text") in ("Clear Message", "Clear", "警告"):
                child.config(text=self.LANG.get("clear_msg", "Clear Message"))
            if isinstance(child, tk.Button) and child.cget("text") in ("Refresh", "刷新"):
                child.config(text=self.LANG.get("refresh", "Refresh"))
        if hasattr(self, "chart_btn"):
            self.chart_btn.config(text=self.LANG.get("show_chart", "Show Resource Charts"))
        columns = ("Name", "Status", "CPU %", "Mem Usage", "Net I/O", "Uptime")
        for col in columns:
            self.tree.heading(col, text=col)

    def manual_refresh(self):
        threading.Thread(target=self.refresh_once, daemon=True).start()

    def refresh_once(self):
        try:
            data = []
            for c in client.containers.list(all=True):
                stats = self.get_stats(c) if c.status == "running" else ("-", "-", "-")
                uptime = self.get_uptime(c) if c.status == "running" else "-"
                data.append((c.name, c.status, stats[0], stats[1], stats[2], uptime))
            self.container_data = data
        except Exception as e:
            self.error_msg_var.set(str(e))

    def refresh_loop(self):
        while True:
            self.refresh_once()
            time.sleep(60)

    def update_ui_loop(self):
        selected_name = self._selected_container_name
        self.tree.delete(*self.tree.get_children())
        for entry in self.container_data:
            self.tree.insert("", tk.END, values=entry)
        if selected_name:
            for iid in self.tree.get_children():
                if self.tree.item(iid, "values")[0] == selected_name:
                    self.tree.selection_set(iid)
                    self.tree.see(iid)
                    break
        if self.has_admin and self.chart_loaded and self.chart_area:
            DockMod.update_chart(self.canvas, self.ax_dict, self.history, self.container_data)
        self.after(1000, self.update_ui_loop)

    def show_chart(self):
        if not self.chart_loaded:
            self.chart_area = tk.Frame(self)
            self.chart_area.pack(fill=tk.BOTH, expand=True)
            self.canvas, self.ax_dict, self.history = DockMod.init_chart(self.chart_area)
            self.chart_loaded = True
            self.chart_btn.config(state=tk.DISABLED)

    def on_tree_select(self, event):
        selected = self.tree.selection()
        if selected:
            self._selected_container_name = self.tree.item(selected[0], "values")[0]
        else:
            self._selected_container_name = None

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
        except Exception as e:
            self.error_msg_var.set(str(e))
            return ("-", "-", "-")

    def get_uptime(self, container):
        try:
            started_at = container.attrs["State"]["StartedAt"]
            started_time = datetime.fromisoformat(started_at.replace("Z","+00:00"))
            uptime = datetime.now(timezone.utc) - started_time.astimezone(timezone.utc)
            return str(uptime).split(".")[0]
        except Exception as e:
            self.error_msg_var.set(str(e))
            return "-"

    def get_selected_container(self):
        name = self._selected_container_name
        if not name:
            self.error_msg_var.set(self.LANG.get("select_container", "Please select a container"))
            return None
        return name

    def start_container(self):
        name = self.get_selected_container()
        if name:
            try:
                container = client.containers.get(name)
                container.start()
                self.error_msg_var.set("")
            except Exception as e:
                self.error_msg_var.set(f"{self.LANG.get('error', 'Error')}: {e}")

    def stop_container(self):
        name = self.get_selected_container()
        if name:
            try:
                container = client.containers.get(name)
                container.stop()
                self.error_msg_var.set("")
            except Exception as e:
                self.error_msg_var.set(f"{self.LANG.get('error', 'Error')}: {e}")

    def restart_container(self):
        name = self.get_selected_container()
        if name:
            try:
                container = client.containers.get(name)
                container.restart()
                self.error_msg_var.set("")
            except Exception as e:
                self.error_msg_var.set(f"{self.LANG.get('error', 'Error')}: {e}")

    def rebuild_container(self):
        name = self.get_selected_container()
        if name:
            try:
                subprocess.run(COMPOSE_CMD + ["build", name], check=True)
                subprocess.run(COMPOSE_CMD + ["up","-d", name], check=True)
                self.error_msg_var.set("")
            except Exception as e:
                self.error_msg_var.set(f"{self.LANG.get('rebuild_failed', 'Rebuild failed')}: {e}")

    def show_logs(self):
        name = self.get_selected_container()
        if name:
            try:
                container = client.containers.get(name)
                logs = container.logs(tail=50).decode()
                log_win = tk.Toplevel(self)
                log_win.title(f"Logs - {name}")
                text = tk.Text(log_win, wrap="word")
                text.insert("1.0", logs)
                text.pack(fill=tk.BOTH, expand=True)
                self.error_msg_var.set("")
            except Exception as e:
                self.error_msg_var.set(f"{self.LANG.get('error', 'Error')}: {e}")

    def remove_container(self):
        name = self.get_selected_container()
        if name:
            confirm = messagebox.askyesno(
                self.LANG.get("remove_confirm_title", "Confirm Remove"),
                f"{self.LANG.get('remove_confirm_msg', 'Are you sure to REMOVE container')} '{name}'?\n"
                f"{self.LANG.get('remove_warning', 'This action cannot be undone!')}"
            )
            if confirm:
                try:
                    container = client.containers.get(name)
                    container.remove(force=True)
                    self.error_msg_var.set(self.LANG.get("remove_success", "Container removed successfully"))
                    self.manual_refresh()
                except Exception as e:
                    self.error_msg_var.set(f"{self.LANG.get('remove_failed', 'Remove failed')}: {e}")

    def show_help(self):
        lang_code = self.language_options[self.lang_var.get()]
        help_text = get_help_text(lang_code)
        help_win = tk.Toplevel(self)
        help_win.title("Help")
        text = tk.Text(help_win, wrap="word", height=30, width=80)
        text.insert("1.0", help_text)
        text.config(state=tk.DISABLED)
        text.pack(fill=tk.BOTH, expand=True)

if __name__ == "__main__":
    try:
        app = DockMonApp()
        app.mainloop()
    except Exception as e:
        print(f"DockMon 啓動失敗: {e}")
