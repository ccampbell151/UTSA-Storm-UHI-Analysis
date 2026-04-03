import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling
import numpy as np
import geopandas as gpd
import contextily as cx
from shapely.geometry import Point
import pandas as pd
from PIL import Image
import io

# --- HEADLESS MODE: NO POPUP WINDOWS ---
import matplotlib
matplotlib.use('Agg') 
import matplotlib.pyplot as plt

class BalconesTopoFinalSuite:
    def __init__(self, root):
        self.root = root
        self.root.title("Rowdy's Radar - Topo-Intensity Suite")
        self.root.geometry("600x650")
        
        self.utsa_orange = "#f15a22"
        self.utsa_blue = "#0c2340"
        self.bg_color = "#ffffff"
        self.root.configure(bg=self.bg_color)
        
        # Center of Study Area (Latitude, Longitude)
        self.c_lat, self.c_lon = 29.75, -98.30 
        
        # Output Variables
        self.var_gif = tk.BooleanVar(value=True)
        self.var_poster = tk.BooleanVar(value=True)
        self.var_csv = tk.BooleanVar(value=True)
        
        self.setup_ui()

    def setup_ui(self):
        self.wrapper = ttk.Frame(self.root, padding="30")
        self.wrapper.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(self.wrapper, text="Elevation vs. Intensity Master", font=("Segoe UI Semibold", 18), foreground=self.utsa_blue).pack(pady=(0, 10))
        ttk.Label(self.wrapper, text="REGIONAL TOPOGRAPHIC ANALYSIS", font=("Segoe UI", 8, "bold"), foreground="#6a737d").pack(pady=(0, 15))
        
        # Path Selector
        path_container = tk.Frame(self.wrapper, bg="#f5f7fa", bd=1, relief="solid")
        path_container.pack(fill='x', pady=10)
        self.folder_path = tk.StringVar()
        self.entry_path = tk.Entry(path_container, textvariable=self.folder_path, bg="#f5f7fa", relief="flat", font=("Segoe UI", 10))
        self.entry_path.pack(side=tk.LEFT, fill='x', expand=True, padx=10, ipady=8)
        ttk.Button(path_container, text="BROWSE", command=self.browse).pack(side=tk.RIGHT, padx=5, pady=5)
        
        # Output Configuration (Checkboxes)
        opts_frame = tk.LabelFrame(self.wrapper, text=" Output Configuration ", bg=self.bg_color, font=("Segoe UI", 10, "bold"), pady=10, padx=10)
        opts_frame.pack(fill='x', pady=10)
        
        ttk.Checkbutton(opts_frame, text="Generate Animated GIF (.gif)", variable=self.var_gif).pack(anchor='w', pady=2)
        ttk.Checkbutton(opts_frame, text="Export Poster Series (6 Images)", variable=self.var_poster).pack(anchor='w', pady=2)
        ttk.Checkbutton(opts_frame, text="Generate CSV Telemetry (.csv)", variable=self.var_csv).pack(anchor='w', pady=2)

        # Execution
        self.btn_run = tk.Button(self.wrapper, text="EXECUTE SPATIAL MODEL", command=self.run_logic, 
                             bg=self.utsa_blue, fg="white", font=("Segoe UI", 11, "bold"), relief="flat")
        self.btn_run.pack(fill='x', pady=20, ipady=15)

        self.status = ttk.Label(self.wrapper, text="Ready", foreground="#6a737d")
        self.status.pack()
        self.progress = ttk.Progressbar(self.wrapper, orient=tk.HORIZONTAL, mode='determinate')
        self.progress.pack(fill='x', pady=10)

    def browse(self):
        folder = filedialog.askdirectory()
        if folder: self.folder_path.set(folder)

    def run_logic(self):
        path = self.folder_path.get()
        if not path: return
        files = sorted([f for f in os.listdir(path) if f.lower().endswith(('.tif', '.tiff'))])
        if not files: return

        # Pre-scan for Static Scaling
        self.status.config(text="Scanning for static scale...")
        self.root.update()
        global_intensities = []
        for f in files:
            with rasterio.open(os.path.join(path, f)) as src:
                data = src.read(1).astype(np.float32)
                data[data < 15] = np.nan
                if not np.all(np.isnan(data)):
                    global_intensities.append(np.nanmean(data))
        
        if not global_intensities: return
        static_ylim = [max(0, min(global_intensities) - 3), max(global_intensities) + 3]

        poster_indices = np.linspace(0, len(files) - 1, 6).astype(int) if self.var_poster.get() else []
        all_stats = []
        gif_frames = []

        center_gs = gpd.GeoSeries([Point(self.c_lon, self.c_lat)], crs="EPSG:4326").to_crs("EPSG:3857")
        bx_x, bx_y = center_gs[0].x, center_gs[0].y
        view_r = 100000 
        xlim, ylim = [bx_x - view_r, bx_x + view_r], [bx_y - view_r, bx_y + view_r]

        for i, filename in enumerate(files):
            with rasterio.open(os.path.join(path, filename)) as src:
                transform, width, height = calculate_default_transform(src.crs, 'EPSG:3857', src.width, src.height, *src.bounds)
                data = np.zeros((height, width), dtype=np.float32)
                reproject(source=rasterio.band(src, 1), destination=data, src_transform=src.transform, 
                          src_crs=src.crs, dst_transform=transform, dst_crs='EPSG:3857', resampling=Resampling.nearest)
                
                data[data < 15] = np.nan
                mean_int = np.nanmean(data) if not np.all(np.isnan(data)) else 0
                all_stats.append({"Frame": i, "Intensity": mean_int})

                # Create Figure
                fig = plt.figure(figsize=(14, 10))
                gs = fig.add_gridspec(2, 1, height_ratios=[2.5, 1], hspace=0.15)
                ax_map = fig.add_subplot(gs[0]); ax_line = fig.add_subplot(gs[1])

                # Map logic
                left, bottom, right, top = rasterio.transform.array_bounds(height, width, transform)
                im = ax_map.imshow(data, extent=[left, right, bottom, top], cmap='turbo', vmin=15, vmax=65, alpha=0.7, zorder=5)
                try: cx.add_basemap(ax_map, crs="EPSG:3857", source=cx.providers.OpenTopoMap, zoom=9, zorder=1)
                except: pass
                
                ax_map.set_xlim(xlim); ax_map.set_ylim(ylim)
                ax_map.set_title(f"Topo-Intensity Lifecycle | Frame {i}", fontsize=16, fontweight='bold')

                # Lat/Long Ticks
                xticks = np.linspace(xlim[0], xlim[1], 5)
                yticks = np.linspace(ylim[0], ylim[1], 5)
                pts_lon = gpd.GeoSeries([Point(x, bx_y) for x in xticks], crs="EPSG:3857").to_crs("EPSG:4326")
                pts_lat = gpd.GeoSeries([Point(bx_x, y) for y in yticks], crs="EPSG:3857").to_crs("EPSG:4326")
                ax_map.set_xticks(xticks); ax_map.set_xticklabels([f"{abs(p.x):.2f}°W" for p in pts_lon])
                ax_map.set_yticks(yticks); ax_map.set_yticklabels([f"{p.y:.2f}°N" for p in pts_lat])

                # Line Panel
                df_plot = pd.DataFrame(all_stats)
                ax_line.plot(df_plot.index, df_plot['Intensity'], color=self.utsa_orange, lw=4, label='Mean Reflectivity (dBZ)')
                ax_line.set_ylim(static_ylim); ax_line.set_xlim(0, len(files))
                ax_line.set_ylabel("dBZ"); ax_line.set_xlabel("Time (Frames)"); ax_line.grid(True, alpha=0.2)
                ax_line.legend(loc='upper left')

                # Handle Exports
                if i in poster_indices:
                    poster_num = np.where(poster_indices == i)[0][0] + 1
                    poster_path = os.path.abspath(os.path.join(path, f"Poster_Frame_{poster_num}.png"))
                    fig.canvas.print_figure(poster_path, dpi=250, bbox_inches='tight')

                if self.var_gif.get():
                    buf = io.BytesIO()
                    fig.canvas.print_figure(buf, format='png', dpi=100) 
                    buf.seek(0)
                    gif_frames.append(Image.open(buf))

                plt.close(fig)

            self.progress['value'] = ((i + 1) / len(files)) * 100
            self.status.config(text=f"Frame {i+1} of {len(files)}...")
            self.root.update()

        # Finalize Output
        if self.var_gif.get() and gif_frames:
            self.status.config(text="Saving GIF...")
            self.root.update()
            gif_path = os.path.join(path, "Balcones_Topo_Animation.gif")
            gif_frames[0].save(gif_path, save_all=True, append_images=gif_frames[1:], duration=300, loop=0)

        if self.var_csv.get():
            pd.DataFrame(all_stats).to_csv(os.path.join(path, "Regional_Topo_Intensity.csv"), index=False)

        messagebox.showinfo("Success", "Analysis Suite Completed!")
        self.status.config(text="Complete")

if __name__ == "__main__":
    root = tk.Tk(); app = BalconesTopoFinalSuite(root); root.mainloop()