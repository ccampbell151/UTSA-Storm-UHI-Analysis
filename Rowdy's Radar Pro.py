import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling
import numpy as np
import geopandas as gpd
import contextily as cx
from shapely.geometry import Point
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import pandas as pd

class UTSARadarUHIDual:
    def __init__(self, root):
        self.root = root
        self.root.title("Rowdy's Radar Pro - Spatial Edition")
        self.root.geometry("640x950")
        
        self.utsa_orange = "#f15a22"
        self.utsa_blue = "#0c2340"
        self.bg_color = "#ffffff"
        self.soft_gray = "#f5f7fa"
        
        self.root.configure(bg=self.bg_color)
        self.b_lon, self.b_lat = -98.4936, 29.4241 
        
        self.var_gif = tk.BooleanVar(value=True)
        self.var_poster = tk.BooleanVar(value=True)
        self.var_csv = tk.BooleanVar(value=True)
        self.var_plot = tk.BooleanVar(value=True)
        self.var_dist_plot = tk.BooleanVar(value=True) # New Checkbox
        
        self.setup_styles()
        self.create_ui()

    def setup_styles(self):
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure("Title.TLabel", font=("Segoe UI Semibold", 20), foreground=self.utsa_blue, background=self.bg_color)
        self.style.configure("Action.TButton", font=("Segoe UI", 11, "bold"), background=self.utsa_blue, foreground="white")
        self.style.map("Action.TButton", background=[('active', self.utsa_orange)])
        self.style.configure("Sleek.Horizontal.TProgressbar", thickness=10, background=self.utsa_orange)

    def create_ui(self):
        self.wrapper = ttk.Frame(self.root, padding="30")
        self.wrapper.pack(fill=tk.BOTH, expand=True)
        ttk.Label(self.wrapper, text="Rowdy's Radar Pro", style="Title.TLabel").pack(anchor='w')
        ttk.Label(self.wrapper, text="ADVANCED SPATIAL ANALYSIS", font=("Segoe UI", 9, "bold"), foreground="#6a737d").pack(anchor='w', pady=(0, 20))
        
        path_container = tk.Frame(self.wrapper, bg=self.soft_gray, bd=1, relief="solid")
        path_container.pack(fill='x', pady=10)
        self.folder_path = tk.StringVar()
        self.entry_path = tk.Entry(path_container, textvariable=self.folder_path, bg=self.soft_gray, relief="flat", font=("Segoe UI", 11))
        self.entry_path.pack(side=tk.LEFT, fill='x', expand=True, padx=10, ipady=8)
        ttk.Button(path_container, text="BROWSE", command=self.browse_folder, style="Action.TButton").pack(side=tk.RIGHT, padx=5, pady=5)
        
        opts_frame = tk.LabelFrame(self.wrapper, text=" Output Configuration ", bg=self.bg_color, font=("Segoe UI", 10, "bold"), pady=10, padx=10)
        opts_frame.pack(fill='x', pady=10)
        
        ttk.Checkbutton(opts_frame, text="Generate Animated GIF (.gif)", variable=self.var_gif).pack(anchor='w', pady=2)
        ttk.Checkbutton(opts_frame, text="Export Poster Series (6 Images)", variable=self.var_poster).pack(anchor='w', pady=2)
        ttk.Checkbutton(opts_frame, text="Generate CSV Data (.csv)", variable=self.var_csv).pack(anchor='w', pady=2)
        ttk.Checkbutton(opts_frame, text="Generate Final Trend Plot (.png)", variable=self.var_plot).pack(anchor='w', pady=2)
        ttk.Checkbutton(opts_frame, text="Generate Distance/Intensity Plot", variable=self.var_dist_plot).pack(anchor='w', pady=2)

        self.progress = ttk.Progressbar(self.wrapper, orient=tk.HORIZONTAL, mode='determinate', style="Sleek.Horizontal.TProgressbar")
        self.progress.pack(fill='x', pady=20)
        ttk.Button(self.wrapper, text="EXECUTE MODEL", command=self.run_logic, style="Action.TButton").pack(fill='x', ipady=15)

    def browse_folder(self):
        folder = filedialog.askdirectory()
        if folder: self.folder_path.set(folder)

    def run_logic(self):
        path = self.folder_path.get()
        if not path: return
        files = sorted([f for f in os.listdir(path) if f.lower().endswith(('.tif', '.tiff'))])
        if not files: return
        
        poster_indices = np.linspace(0, len(files) - 1, 6).astype(int) if self.var_poster.get() else []
        all_stats = []
        distance_data = [] # Storage for radial math

        fig = plt.figure(figsize=(22, 11), constrained_layout=True)
        gs = fig.add_gridspec(2, 2, width_ratios=[2, 1], height_ratios=[2.5, 1], wspace=0.05)
        ax_map = fig.add_subplot(gs[0, 0]); ax_bar = fig.add_subplot(gs[0, 1]); ax_trend = fig.add_subplot(gs[1, :])
        
        center_gs = gpd.GeoSeries([Point(self.b_lon, self.b_lat)], crs="EPSG:4326").to_crs("EPSG:3857")
        bx_x, bx_y = center_gs[0].x, center_gs[0].y
        view_rx, view_ry = 110000, 85000 
        xlim, ylim = [bx_x - view_rx, bx_x + view_rx], [bx_y - view_ry, bx_y + view_ry]

        def process_frame(i):
            ax_map.clear(); ax_bar.clear(); ax_trend.clear()
            ax_trend.set_visible(True)
            
            filename = files[i]
            with rasterio.open(os.path.join(path, filename)) as src:
                transform, width, height = calculate_default_transform(src.crs, 'EPSG:3857', src.width, src.height, *src.bounds)
                data = np.zeros((height, width), dtype=np.float32)
                reproject(source=rasterio.band(src, 1), destination=data, src_transform=src.transform, 
                          src_crs=src.crs, dst_transform=transform, dst_crs='EPSG:3857', resampling=Resampling.nearest)
                
                data[data < 15] = np.nan
                left, bottom, right, top = rasterio.transform.array_bounds(height, width, transform)
                
                ax_map.imshow(data, extent=[left, right, bottom, top], cmap='turbo', vmin=15, vmax=65, 
                              alpha=0.8, zorder=5, origin='upper', aspect='equal')
                
                lon_vals = np.linspace(self.b_lon - 1.0, self.b_lon + 1.0, 7)
                lat_vals = np.linspace(self.b_lat - 0.7, self.b_lat + 0.7, 5)
                pts_lon = gpd.GeoSeries([Point(x, self.b_lat) for x in lon_vals], crs="EPSG:4326").to_crs("EPSG:3857")
                pts_lat = gpd.GeoSeries([Point(self.b_lon, y) for y in lat_vals], crs="EPSG:4326").to_crs("EPSG:3857")
                ax_map.set_xticks([p.x for p in pts_lon]); ax_map.set_xticklabels([f"{abs(x):.1f}°W" for x in lon_vals])
                ax_map.set_yticks([p.y for p in pts_lat]); ax_map.set_yticklabels([f"{y:.1f}°N" for y in lat_vals])
                ax_map.set_xlim(xlim); ax_map.set_ylim(ylim)
                
                for boundary in [-25000, 25000]:
                    ax_map.axvline(bx_x + boundary, color='white', linestyle='--', linewidth=1.5, alpha=0.8, zorder=15)
                
                ax_map.text(bx_x - 65000, ylim[1] - 15000, "UPWIND", color='white', ha='center', fontweight='bold', fontsize=13, zorder=20)
                ax_map.text(bx_x, ylim[1] - 15000, "URBAN CORE", color='cyan', ha='center', fontweight='bold', fontsize=13, zorder=20)
                ax_map.text(bx_x + 65000, ylim[1] - 15000, "DOWNWIND", color='white', ha='center', fontweight='bold', fontsize=13, zorder=20)
                ax_map.plot(bx_x, bx_y, 'r*', markersize=14, markeredgecolor='white', zorder=25)

                try: cx.add_basemap(ax_map, crs="EPSG:3857", source=cx.providers.CartoDB.DarkMatter, zoom=9, zorder=1)
                except: pass

                zonal_means = [0, 0, 0]
                rows, cols = np.where(~np.isnan(data))
                if rows.size > 0:
                    xs, ys = transform * (cols, rows)
                    dx, dy = xs - bx_x, ys - bx_y
                    
                    # RADIAL MATH: Calculate Distance from center (in km)
                    dists = np.sqrt(dx**2 + dy**2) / 1000.0 
                    # Store values for the Distance vs Intensity plot
                    for d_val, i_val in zip(dists, data[rows, cols]):
                        distance_data.append({"Dist": d_val, "Intensity": i_val})

                    masks = [(dx < -25000), (dx >= -25000) & (dx < 25000), (dx >= 25000)]
                    for idx, m in enumerate(masks):
                        if np.any(m):
                            z_vals = data[rows[m], cols[m]]
                            zonal_means[idx] = np.mean(z_vals[z_vals >= np.percentile(z_vals, 90)])

                all_stats.append({"Frame": i, "Upwind": zonal_means[0], "Urban": zonal_means[1], "Downwind": zonal_means[2]})
                
                # Pulse Counter
                u_val = zonal_means[1]
                status_color = self.utsa_orange if (u_val > zonal_means[0] and u_val > zonal_means[2]) else "white"
                ax_map.text(xlim[0] + 2000, ylim[1] - 4000, f"CORE PULSE: {u_val:.1f} dBZ", color='white', fontsize=17, fontweight='bold', bbox=dict(facecolor='black', alpha=0.7, pad=4))
                ax_map.text(xlim[0] + 2000, ylim[1] - 9500, f"STATUS: {'UHI ACTIVE' if status_color == self.utsa_orange else 'STABLE'}", color=status_color, fontsize=13, fontweight='bold')

                ax_bar.bar(['Rural', 'Urban', 'Downwind'], zonal_means, color=['#4a90e2', self.utsa_orange, '#50c878'], edgecolor='black')
                ax_bar.set_ylim(0, 70)
                
                df_temp = pd.DataFrame(all_stats)
                ax_trend.plot(df_temp.index, df_temp['Upwind'], color='#4a90e2', alpha=0.8)
                ax_trend.plot(df_temp.index, df_temp['Urban'], color=self.utsa_orange, lw=3)
                ax_trend.plot(df_temp.index, df_temp['Downwind'], color='#50c878', alpha=0.8)

                if i in poster_indices:
                    ax_trend.set_visible(False)
                    poster_num = np.where(poster_indices == i)[0][0] + 1
                    plt.savefig(os.path.join(path, f"Poster_Frame_{poster_num}.png"), dpi=250, bbox_inches='tight')
                    ax_trend.set_visible(True)

            self.progress['value'] = ((i + 1) / len(files)) * 100
            self.root.update()

        if self.var_gif.get():
            ani = FuncAnimation(fig, process_frame, frames=len(files), repeat=False)
            ani.save(os.path.join(path, "UHI_Stabilized_Final.gif"), writer='pillow', fps=2)
        else:
            for i in range(len(files)): process_frame(i)

        # DISTANCE VS INTENSITY PLOT
        if self.var_dist_plot.get() and distance_data:
            df_dist = pd.DataFrame(distance_data)
            # Group into 5km bins
            df_dist['Dist_Bin'] = (df_dist['Dist'] // 5) * 5
            bin_means = df_dist.groupby('Dist_Bin')['Intensity'].mean()
            
            plt.figure(figsize=(10, 6))
            plt.plot(bin_means.index, bin_means.values, color=self.utsa_orange, marker='o', lw=3)
            plt.axvline(0, color='red', linestyle='--', label='City Center')
            plt.title("Mean Storm Intensity vs. Distance from San Antonio", fontweight='bold')
            plt.xlabel("Distance from City Center (km)"); plt.ylabel("Avg Reflectivity (dBZ)")
            plt.grid(True, alpha=0.3); plt.legend()
            plt.savefig(os.path.join(path, "UHI_Distance_Intensity_Profile.png"), dpi=300)

        df_final = pd.DataFrame(all_stats)
        if self.var_csv.get(): df_final.to_csv(os.path.join(path, "UHI_Zonal_Telemetry.csv"), index=False)
        if self.var_plot.get():
            plt.figure(figsize=(14, 7))
            plt.plot(df_final.index, df_final['Upwind'], label='Rural', color='#4a90e2')
            plt.plot(df_final.index, df_final['Urban'], label='Urban Core (UHI)', color=self.utsa_orange, lw=4)
            plt.plot(df_final.index, df_final['Downwind'], label='Downwind', color='#50c878')
            plt.title("UHI Pulse Analysis - Final Trend"); plt.legend(); plt.grid(True, alpha=0.2)
            plt.savefig(os.path.join(path, "UHI_Final_Trend_Plot.png"), dpi=300)
        
        plt.close('all'); messagebox.showinfo("Success", "Spatial analysis complete! Added Distance Profile.")

if __name__ == "__main__":
    root = tk.Tk(); app = UTSARadarUHIDual(root); root.mainloop()