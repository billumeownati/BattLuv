import subprocess
import os
import re
import threading
import time
import sys
import datetime
import customtkinter as ctk
from tkinter import messagebox

# -------- Settings --------
REPORT_PATH = os.path.join(os.path.expanduser("~"), "battery-report.html")
APP_TITLE = "BattLuv"
BRANDING = "⚡ Made by BiLLuMiNaTi & Twilight"
ICON_FILE = "logo.ico"   # icon file name

# -------- Theme Palettes --------
THEMES = {
    "dark": {
        "bg": "#1E1E2E",
        "card": "#252535",
        "footer": "#151521",
        "text_main": "white",
        "text_sub": "#BBBBBB",
        "text_faded": "#777777"
    },
    "light": {
        "bg": "#F2F2F7",
        "card": "#FFFFFF",
        "footer": "#E5E5EA",
        "text_main": "#000000",
        "text_sub": "#444444",
        "text_faded": "#666666"
    }
}
current_theme = "dark"
last_health_color = "#AAAAAA"  # preserve health color after toggle

def apply_theme():
    theme = THEMES[current_theme]

    root.configure(fg_color=theme["bg"])
    header_frame.configure(fg_color="transparent")
    content_frame.configure(fg_color="transparent")
    health_frame.configure(fg_color=theme["card"])
    footer.configure(fg_color=theme["footer"])

    # Static texts adapt to theme
    title_label.configure(text_color=theme["text_main"])
    subtitle_label.configure(text_color=theme["text_sub"])
    last_checked_label.configure(text_color=theme["text_faded"])
    branding_label.configure(text_color=theme["text_main"])

    # Preserve dynamic battery colors
    health_percent_label.configure(text_color=last_health_color)
    health_detail_label.configure(text_color=last_health_color)

def toggle_mode():
    global current_theme
    current_theme = "light" if current_theme == "dark" else "dark"
    apply_theme()
    toggle_btn.configure(
        text="🌙 Dark Mode" if current_theme == "light" else "☀️ Light Mode"
    )

# -------- Helpers --------
def _num_from_text(t: str):
    if not t:
        return None
    t = t.replace("\xa0", " ").strip()
    m = re.search(r"([\d,]+)", t)
    if not m:
        return None
    try:
        return int(m.group(1).replace(",", ""))
    except:
        return None

def extract_battery_health(report_path: str):
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        raise RuntimeError("BeautifulSoup (bs4) not installed. Run: pip install beautifulsoup4")

    with open(report_path, "r", encoding="utf-8", errors="ignore") as f:
        soup = BeautifulSoup(f, "html.parser")

    full_charge, design_capacity = None, None
    for span in soup.find_all("span", class_="label"):
        label = (span.get_text(strip=True) or "").lower()
        td_label = span.find_parent("td")
        value_td = td_label.find_next_sibling("td") if td_label else None
        if not value_td:
            continue
        val = _num_from_text(value_td.get_text(" ", strip=True))
        if val is None:
            continue
        if "design capacity" in label:
            design_capacity = val
        elif "full charge capacity" in label:
            full_charge = val

    if full_charge and design_capacity and design_capacity > 0:
        health = round((full_charge / design_capacity) * 100, 2)
        return full_charge, design_capacity, health

    return None, None, None

# -------- Actions --------
def generate_report():
    generate_btn.configure(state="disabled")
    open_btn.configure(state="disabled")
    progress.set(0)
    progress.start()

    def task():
        global last_health_color
        try:
            cmd = f'powercfg /batteryreport /output "{REPORT_PATH}"'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

            time.sleep(1.0)

            if result.returncode != 0:
                raise RuntimeError(result.stderr.strip() or "powercfg failed")

            if not os.path.exists(REPORT_PATH):
                raise FileNotFoundError("Report file not found after generation.")

            full, design, health = extract_battery_health(REPORT_PATH)

            if full and design and health is not None:
                if health > 80:
                    last_health_color = "#4CAF50"
                    status_text = "✅ GOOD"
                elif health > 60:
                    last_health_color = "#FFA500"
                    status_text = "⚠ MEDIUM"
                else:
                    last_health_color = "#FF5555"
                    status_text = "❌ POOR"
                    messagebox.showwarning("Battery Warning",
                                           "⚠ Your battery health is low!\nConsider replacement soon.")

                health_percent_label.configure(
                    text=f"Current Battery Health: {health}%",
                    text_color=last_health_color
                )

                wear = round(100 - health, 2)

                health_detail_label.configure(
                    text=(
                        f"{status_text}\n\n"
                        f"⚡ Full Charge: {full} mWh\n"
                        f"🏭 Design Capacity: {design} mWh\n"
                        f"📉 Battery Wear: {wear}%"
                    ),
                    text_color=last_health_color
                )

                health_gauge.set(health / 100)
                health_gauge.configure(progress_color=last_health_color)

                last_checked_label.configure(
                    text=f"Last Checked: {datetime.datetime.now().strftime('%d-%b-%Y %I:%M %p')}"
                )

                open_btn.configure(state="normal")
            else:
                last_health_color = "#FF5555"
                health_percent_label.configure(text="Current Battery Health: --%", text_color=last_health_color)
                health_detail_label.configure(text="⚠ Could not extract battery health.", text_color=last_health_color)
                health_gauge.set(0)

        except Exception as e:
            messagebox.showerror("Error", f"{type(e).__name__}: {e}")
        finally:
            progress.stop()
            progress.set(0)
            generate_btn.configure(state="normal")

    threading.Thread(target=task, daemon=True).start()

def open_report():
    if os.path.exists(REPORT_PATH):
        try:
            os.startfile(REPORT_PATH)
        except Exception as e:
            messagebox.showerror("Error", f"Could not open report:\n{e}")
    else:
        messagebox.showerror("Error", "Battery report not found. Generate it first.")

# -------- GUI --------
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

root = ctk.CTk()
root.title(APP_TITLE)
root.geometry("750x720")   # more vertical space
root.minsize(650, 600)     # resizable

# --- Add Icon Support ---
if hasattr(sys, "_MEIPASS"):
    icon_path = os.path.join(sys._MEIPASS, "logo.ico")  # bundled exe
else:
    icon_path = "logo.ico"  # running from source
try:
    root.iconbitmap(icon_path)
except Exception as e:
    print("Could not set icon:", e)

root.grid_rowconfigure(0, weight=0)
root.grid_rowconfigure(1, weight=1)
root.grid_rowconfigure(2, weight=0)
root.grid_columnconfigure(0, weight=1)

# ----- HEADER -----
header_frame = ctk.CTkFrame(root, fg_color="transparent")
header_frame.grid(row=0, column=0, pady=(20, 10), sticky="ew")
header_frame.grid_columnconfigure(0, weight=1)
header_frame.grid_columnconfigure(1, weight=0)

title_label = ctk.CTkLabel(header_frame, text="🔋 BattLuv", font=("Segoe UI", 28, "bold"))
title_label.grid(row=0, column=0, sticky="w", padx=20)

toggle_btn = ctk.CTkButton(
    header_frame,
    text="☀️ Light Mode",
    command=toggle_mode,
    width=160,
    height=38,
    font=("Segoe UI", 14, "bold")
)
toggle_btn.grid(row=0, column=1, sticky="e", padx=20)

subtitle_label = ctk.CTkLabel(
    header_frame,
    text="Generate a Windows battery report\nand instantly check your laptop’s battery health.",
    font=("Segoe UI", 16)
)
subtitle_label.grid(row=1, column=0, columnspan=2, pady=(8, 0))

# ----- MAIN CONTENT -----
content_frame = ctk.CTkFrame(root, fg_color="transparent")
content_frame.grid(row=1, column=0, sticky="nsew", pady=10)

progress = ctk.CTkProgressBar(content_frame, width=500, height=14, corner_radius=8)
progress.set(0)
progress.pack(pady=20)

generate_btn = ctk.CTkButton(content_frame, text="⚡ Generate Report", command=generate_report, width=240, height=50, font=("Segoe UI", 16, "bold"))
generate_btn.pack(pady=10)

open_btn = ctk.CTkButton(content_frame, text="📂 Open Report", command=open_report, state="disabled", width=240, height=50, font=("Segoe UI", 16, "bold"))
open_btn.pack(pady=10)

health_frame = ctk.CTkFrame(content_frame, corner_radius=12)
health_frame.pack(pady=30, padx=30, fill="both", expand=False)

health_percent_label = ctk.CTkLabel(
    health_frame,
    text="Current Battery Health: --%",
    font=("Segoe UI", 23, "bold"),
    justify="center"
)
health_percent_label.pack(pady=(20, 10))

health_gauge = ctk.CTkProgressBar(health_frame, width=400, height=18, corner_radius=8)
health_gauge.set(0)
health_gauge.pack(pady=10)

health_detail_label = ctk.CTkLabel(
    health_frame,
    text="Battery Status: Not Generated Yet",
    font=("Segoe UI", 18),  # bigger
    justify="center"
)
health_detail_label.pack(pady=(10, 20))

last_checked_label = ctk.CTkLabel(
    health_frame,
    text="Last Checked: --",
    font=("Segoe UI", 14, "italic")
)
last_checked_label.pack(pady=(0, 15))

# ----- FOOTER -----
footer = ctk.CTkFrame(root, height=40, corner_radius=0)
footer.grid(row=2, column=0, sticky="ew")
branding_label = ctk.CTkLabel(footer, text=BRANDING, font=("Segoe UI", 14, "italic", "bold"))
branding_label.pack(pady=5)

apply_theme()
root.mainloop()

