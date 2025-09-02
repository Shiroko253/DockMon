import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import collections

def init_chart(master):
    """
    初始化資源圖表
    返回: canvas, ax_dict, history_dict
    """
    fig = Figure(figsize=(10, 3), dpi=100)
    ax_cpu = fig.add_subplot(311)
    ax_mem = fig.add_subplot(312)
    ax_net = fig.add_subplot(313)

    history = {
        "cpu": collections.deque([0]*60, maxlen=60),
        "mem": collections.deque([0]*60, maxlen=60),
        "net": collections.deque([0]*60, maxlen=60)
    }

    canvas = FigureCanvasTkAgg(fig, master=master)
    canvas.get_tk_widget().pack(fill="both", expand=True)

    ax_dict = {
        "cpu": ax_cpu,
        "mem": ax_mem,
        "net": ax_net,
        "fig": fig
    }

    return canvas, ax_dict, history

def update_chart(canvas, ax_dict, history, container_data):
    """
    更新圖表數據，每秒刷新一次
    container_data: [(name, status, cpu_str, mem_str, net_str, uptime), ...]
    """
    if container_data:
        total_cpu = total_mem = total_net = 0
        for c in container_data:
            cpu_str, mem_str, net_str = c[2], c[3], c[4]
            try:
                total_cpu += float(cpu_str.strip("%")) if cpu_str != "-" else 0
                total_mem += float(mem_str.split("/")[0].replace("MB","")) if mem_str != "-" else 0
                rx, tx = net_str.split("/")
                total_net += int(rx.strip("kB")) + int(tx.strip("kB")) if net_str != "-" else 0
            except:
                pass

        history["cpu"].append(total_cpu)
        history["mem"].append(total_mem)
        history["net"].append(total_net)

        ax_dict["cpu"].clear()
        ax_dict["cpu"].plot(history["cpu"], color='r')
        ax_dict["cpu"].set_ylabel("CPU %")

        ax_dict["mem"].clear()
        ax_dict["mem"].plot(history["mem"], color='g')
        ax_dict["mem"].set_ylabel("Mem MB")

        ax_dict["net"].clear()
        ax_dict["net"].plot(history["net"], color='b')
        ax_dict["net"].set_ylabel("Net kB")
        ax_dict["net"].set_xlabel("Last 60s")

        canvas.draw()
