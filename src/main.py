import time
from threading import Thread, Event, Lock

import tkinter as tk
from tkinter import filedialog
from tkinter import messagebox
from tkinter import ttk
from ttkthemes import ThemedTk

import numpy as np
from matplotlib.animation import FuncAnimation
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure

from msgspec import Struct
from msgspec.json import decode

from pathlib import Path

assets_path = Path(__file__).parent.parent / "assets"
data_path = Path(__file__).parent.parent / "data"


class Schema(Struct):
    x_coord: list[float]
    y_coord: list[float]
    rp_y: list[float]
    noiserp_y: list[float]
    doppz: list[list[int]]


class ReadDataThread(Thread):
    def __init__(self, file_path):
        super().__init__()
        self.daemon = True

        self.paused = Event()
        self._stop_event = Event()

        try:
            self.file = open(file_path, "rb")
        except Exception as e:
            print(f"An error occurred: {e}")

        self.lock = Lock()
        self.x_coord = []
        self.y_coord = []
        self.rp_y = []
        self.noiserp_y = []
        self.doppz = [[]]

    def run(self):
        while not self._stop_event.is_set():
            if not self.paused.is_set():
                data = decode(self.file.readline(), type=Schema)
                with self.lock:
                    self.x_coord[:] = data.x_coord
                    self.y_coord[:] = data.y_coord
                    self.rp_y[:] = data.rp_y
                    self.noiserp_y[:] = data.noiserp_y
                    self.doppz[:] = data.doppz
            self._stop_event.wait(timeout=0.4)
        self._close_file()

    def _close_file(self):
        if self.file:
            self.file.close()
            self.file = None

    def change_file_path(self, file_path):
        self.paused.set()
        self._close_file()
        try:
            self.file = open(file_path, "rb")
        except Exception as e:
            print(f"An error occurred: {e}")
            self.stop()

    def stop(self):
        self._stop_event.set()
        self.join()
        self._close_file()


class ConfigureFrame(ttk.Frame):
    def __init__(self, container):
        super().__init__(container)

        self.columnconfigure(0, weight=1)

        setup = ttk.LabelFrame(self, text="Setup Details")
        setup.grid(column=0, row=0, padx=10, pady=10, sticky=tk.NSEW)

        scene = ttk.LabelFrame(self, text="Scene selection")
        scene.grid(column=0, row=1, padx=10, pady=10, sticky=tk.NSEW)

        plot = ttk.LabelFrame(self, text="Plot selection")
        plot.grid(column=0, row=2, padx=10, pady=10, sticky=tk.NSEW)

        buttons = ttk.LabelFrame(self, text="File selection, or run through USB")
        buttons.grid(column=0, row=3, padx=10, pady=10, sticky=tk.NSEW)

        setup.columnconfigure(0, weight=1)
        setup.columnconfigure(1, weight=2)

        ttk.Label(setup, text="Platform").grid(row=0, column=0, sticky=tk.W)
        self._platform = tk.StringVar(value="xWR16xx")
        ttk.Combobox(
            setup,
            textvariable=self._platform,
            values=("xWR14xx", "xWR16xx"),
            state="readonly",
        ).grid(row=0, column=1, sticky=tk.EW)

        ttk.Label(setup, text="SDK Version").grid(row=1, column=0, sticky=tk.W)
        self._sdk_version = tk.DoubleVar(value=2.1)
        ttk.Combobox(
            setup,
            textvariable=self._sdk_version,
            values=(1.2, 2.0, 2.1),
            state="readonly",
        ).grid(row=1, column=1, sticky=tk.EW)

        ttk.Label(setup, text="Antenna Config (Azimuth Res-deg)").grid(
            row=2, column=0, sticky=tk.W
        )
        self._antenna_conf = tk.StringVar(value="4Rx,2Tx(15 deg)")
        ttk.Combobox(
            setup,
            textvariable=self._antenna_conf,
            values=(
                "4Rx,3Tx(15 deg + Elevation)",
                "4Rx,2Tx(15 deg)",
                "4Rx,1Tx(30 deg)",
                "2Rx,1Tx(60 deg)",
                "1Rx,1Tx(None)",
            ),
            state="readonly",
        ).grid(row=2, column=1, sticky=tk.EW)

        ttk.Label(setup, text="Desirable Configuration").grid(
            row=3, column=0, sticky=tk.W
        )
        self._subprofile_type = tk.StringVar(value="Best Range Resolution")
        ttk.Combobox(
            setup,
            textvariable=self._subprofile_type,
            values=("Best Range Resolution", "Best Velocity Resolution", "Best Range"),
            state="readonly",
        ).grid(row=3, column=1, sticky=tk.EW)

        ttk.Label(setup, text="Frequency Band (GHz)").grid(row=4, column=0, sticky=tk.W)
        self._freq_band = tk.StringVar(value="77-81")
        ttk.Combobox(
            setup,
            textvariable=self._freq_band,
            values=("76-77", "77-81"),
            state="readonly",
        ).grid(row=4, column=1, sticky=tk.EW)

        for widget in setup.winfo_children():
            widget.grid(padx=5, pady=5)

        scene.columnconfigure(0, weight=1)
        scene.columnconfigure(1, weight=2)
        scene.columnconfigure(2, weight=1)

        ttk.Label(scene, text="Frame Rate (fps)").grid(row=0, column=0, sticky=tk.W)
        self._frame_rate = tk.IntVar(value=10)
        _cur_fps_val = ttk.Label(scene, text=f"{self._frame_rate.get():02}")
        _cur_fps_val.grid(row=0, column=2)
        ttk.Scale(
            scene,
            from_=1,
            to=30,
            variable=self._frame_rate,
            command=lambda _: _cur_fps_val.configure(
                text=f"{self._frame_rate.get():02}"
            ),
        ).grid(row=0, column=1, sticky=tk.EW)

        ttk.Label(scene, text="Range resolution (m)").grid(row=1, column=0, sticky=tk.W)
        self._range_res = tk.DoubleVar(value=0.044)
        _cur_range_res = ttk.Label(scene, text=f"{self._range_res.get():.3f}")
        _cur_range_res.grid(row=1, column=2)
        ttk.Scale(
            scene,
            from_=0.039,
            to=0.047,
            variable=self._range_res,
            command=lambda _: _cur_range_res.configure(
                text=f"{self._range_res.get():.3f}"
            ),
        ).grid(row=1, column=1, sticky=tk.EW)

        ttk.Label(scene, text="Maximum Unambiguous Range (m)").grid(
            row=2, column=0, sticky=tk.W
        )
        self._max_range = tk.DoubleVar(value=9.02)
        _cur_max_range = ttk.Label(scene, text=f"{self._max_range.get():.2f}")
        _cur_max_range.grid(row=2, column=2)
        ttk.Scale(
            scene,
            from_=3.95,
            to=10.8,
            variable=self._max_range,
            command=lambda _: _cur_max_range.configure(
                text=f"{self._max_range.get():.2f}"
            ),
        ).grid(row=2, column=1, sticky=tk.EW)

        ttk.Label(scene, text="Maximum Radial Velocity (m/s)").grid(
            row=3, column=0, sticky=tk.W
        )
        self._max_rad_vel = tk.DoubleVar(value=1)
        _cur_max_rad_vel = ttk.Label(scene, text=f"{self._max_rad_vel.get():.2f}")
        _cur_max_rad_vel.grid(row=3, column=2)
        ttk.Scale(
            scene,
            from_=0.32,
            to=7.59,
            variable=self._max_rad_vel,
            command=lambda _: _cur_max_rad_vel.configure(
                text=f"{self._max_rad_vel.get():.2f}"
            ),
        ).grid(row=3, column=1, sticky=tk.EW)

        ttk.Label(scene, text="Radial Velocity Resolution (m/s)").grid(
            row=4, column=0, sticky=tk.W
        )
        self._rad_vel_res = tk.DoubleVar(value=0.13)
        _sel_rad_vel = ttk.Label(scene, text=self._rad_vel_res.get())
        _sel_rad_vel.grid(row=4, column=2)
        _rad_vel_cb = ttk.Combobox(
            scene,
            textvariable=self._rad_vel_res,
            values=(0.07, 0.13),
            state="readonly",
        )
        _rad_vel_cb.bind(
            "<<ComboboxSelected>>",
            lambda _: _sel_rad_vel.configure(text=self._rad_vel_res.get()),
        )
        _rad_vel_cb.grid(row=4, column=1, sticky=tk.EW)

        for widget in scene.winfo_children():
            widget.grid(padx=5, pady=5)

        # Start of the Plot Selection Section
        plot.columnconfigure(0, weight=1)
        plot.columnconfigure(1, weight=1)

        self._scatter_plot = tk.BooleanVar(value=True)
        ttk.Checkbutton(plot, text="Scatter Plot", variable=self._scatter_plot).grid(
            row=0, column=0, sticky=tk.W
        )
        self._range_profile = tk.BooleanVar(value=True)
        ttk.Checkbutton(plot, text="Range Profile", variable=self._range_profile).grid(
            row=1, column=0, sticky=tk.W
        )
        self._noise_profile = tk.BooleanVar()
        ttk.Checkbutton(plot, text="Noise Profile", variable=self._noise_profile).grid(
            row=2, column=0, sticky=tk.W
        )
        self._range_azimuth_heat_map = tk.BooleanVar()
        ttk.Checkbutton(
            plot, text="Range Azimuth Heat Map", variable=self._range_azimuth_heat_map
        ).grid(row=0, column=1, sticky=tk.W)
        self._range_doppler_heat_map = tk.BooleanVar()
        ttk.Checkbutton(
            plot, text="Range Doppler Heat Map", variable=self._range_doppler_heat_map
        ).grid(row=1, column=1, sticky=tk.W)
        self._statistics = tk.BooleanVar(value=True)
        ttk.Checkbutton(plot, text="Statistics", variable=self._statistics).grid(
            row=2, column=1, sticky=tk.W
        )

        for widget in plot.winfo_children():
            widget.grid(padx=5, pady=5)

        buttons.columnconfigure(0, weight=1)
        buttons.columnconfigure(1, weight=1)
        usefile_btn = ttk.Button(
            buttons, text="RERUN PRELOADED ITERATION", command=self.read_and_graph_file
        )
        usefile_btn.grid(column=0, row=0, padx=10, pady=10, sticky=tk.E)
        send_btn = ttk.Button(
            buttons, text="SEND CONFIG TO MMWAVE DEVICE", command=self.send_config
        )
        send_btn.grid(column=1, row=0, padx=10, pady=10, sticky=tk.E)

        for widget in buttons.winfo_children():
            widget.grid(padx=5, pady=5)

    def read_and_graph_file(self):
        global read_data
        read_data.paused.set()
        file_path = filedialog.askopenfilename()
        if file_path:
            read_data.change_file_path(file_path)
            read_data.paused.clear()
        else:
            messagebox.showerror("Error", "Select A File")

    def send_config(self):
        global read_data
        read_data.paused.set()
        time.sleep(2)
        read_data.paused.clear()


class PlotFrame(ttk.Frame):
    def __init__(self, container):
        super().__init__(container)

        self.rowconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)

        canvas_pos = FigureCanvasTkAgg(fig_pos, self)
        canvas_pos.draw()
        toolbar_pos = NavigationToolbar2Tk(canvas_pos, self, pack_toolbar=False)
        toolbar_pos.update()

        toolbar_pos.grid(row=1, column=0, sticky=tk.EW)
        canvas_pos.get_tk_widget().grid(row=0, column=0, sticky=tk.NSEW)

        canvas_noise = FigureCanvasTkAgg(fig_noise, self)
        canvas_noise.draw()
        toolbar_noise = NavigationToolbar2Tk(canvas_noise, self, pack_toolbar=False)
        toolbar_noise.update()

        toolbar_noise.grid(row=1, column=1, sticky=tk.EW)
        canvas_noise.get_tk_widget().grid(row=0, column=1, sticky=tk.NSEW)

        canvas_dop = FigureCanvasTkAgg(fig_dop, self)
        canvas_dop.draw()
        toolbar_dop = NavigationToolbar2Tk(canvas_dop, self, pack_toolbar=False)
        toolbar_dop.update()

        toolbar_dop.grid(
            row=3,
            column=0,
            columnspan=2,
            sticky=tk.EW,
            padx=self.winfo_screenwidth() // 4,
        )
        canvas_dop.get_tk_widget().grid(
            row=2,
            column=0,
            columnspan=2,
            sticky=tk.NSEW,
            padx=self.winfo_screenwidth() // 4,
        )


class App(ThemedTk):
    def __init__(self):
        super().__init__()

        self.title("mmWave Visualizer")
        icon = tk.PhotoImage(file=f"{assets_path}/ubinetlogo.png", master=self)
        self.iconphoto(False, icon)
        width = self.winfo_screenwidth()
        height = self.winfo_screenheight()

        self.geometry(f"{width}x{height}")
        self.set_theme("arc")

        style = ttk.Style()
        style.configure(
            "TNotebook.Tab", font=("Noto Sans Mono", 15, "bold"), padding=[10, 10]
        )
        style.configure("TLabelframe.Label", font=("Noto Sans Mono", 12, "bold"))

        notebook = ttk.Notebook(self, width=width, height=height)
        notebook.pack(padx=5, pady=10, expand=True)

        frameconf = ConfigureFrame(notebook)
        frameplt = PlotFrame(notebook)

        frameconf.pack(fill="both", expand=True)
        frameplt.pack(fill="both", expand=True)

        notebook.add(frameconf, text="Configure")
        notebook.add(frameplt, text="Plots")


read_data = ReadDataThread("../data/CCW_A_1.json")
read_data.start()
read_data.paused.set()

# Graph for position
fig_pos = Figure(figsize=(5, 5))
ax_pos = fig_pos.add_subplot(111, xlim=(-11, 11), ylim=(-1, 21))
ax_pos.set_title("Position")
ax_pos.set_xlabel("X-Axis")
ax_pos.set_ylabel("Y-Axis")
(obj_pos,) = ax_pos.plot([], [], "o", lw=3)


def animate_pos(_):
    if not read_data.paused.is_set():
        obj_pos.set_data(read_data.x_coord, read_data.y_coord)
    return (obj_pos,)


# Graph for doppler
fig_dop = Figure(figsize=(8, 6))
ax_dop = fig_dop.add_subplot(111)
im = ax_dop.imshow(
    np.zeros((16, 256), np.int32),
    aspect="auto",
    interpolation="gaussian",
    cmap="viridis",
    animated=True,
)
ax_dop.tick_params(left=False, bottom=False, labelleft=False, labelbottom=False)


def animate_dop(_):
    if not read_data.paused.is_set():
        heatmap = read_data.doppz
        # HACK: This hack is to set min max colors. This will slow down the
        # function though.
        im.set_clim(np.amin(heatmap), np.amax(heatmap))
        im.set_data(heatmap)
    return (im,)


# Graph for noise profile
fig_noise = Figure(figsize=(8, 6))
ax_noise = fig_noise.add_subplot(111, xlim=(1, 256), ylim=(0, 150))
ax_noise.set_title("Noise")
ax_noise.set_xlabel("X-Axis")
ax_noise.set_ylabel("dB")
(obj_rp,) = ax_noise.plot([], [])
(obj_noiserp,) = ax_noise.plot([], [])
ax_noise.legend([obj_rp, obj_noiserp], ["rp_y", "noiserp_y"])
noise_xaxis = np.arange(256) + 1


def animate_noise(_):
    if not read_data.paused.is_set():
        obj_rp.set_data(noise_xaxis, read_data.rp_y)
        obj_noiserp.set_data(noise_xaxis, read_data.noiserp_y)
    return (obj_rp, obj_noiserp)


app = App()

anim_pos = FuncAnimation(
    fig_pos, animate_pos, interval=400, blit=True, cache_frame_data=False
)
anim_dop = FuncAnimation(
    fig_dop,
    animate_dop,
    interval=400,
    blit=True,
    cache_frame_data=False,
)
anim_noise = FuncAnimation(
    fig_noise, animate_noise, interval=400, blit=True, cache_frame_data=False
)

app.mainloop()
