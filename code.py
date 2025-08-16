import subprocess
import os
import re
import threading
import time
import tkinter as tk
from tkinter import messagebox, ttk
import sys

# -------- Settings --------
REPORT_PATH = os.path.join(os.path.expanduser("~"), "battery-report.html")
APP_TITLE = "Battery Report Generator"
BRANDING = "Made by BiLLuMiNaTi and Twilight"

# -------- Helpers --------
def resource_path(relative_path):
    """Get absolute path to resource, works for dev and PyInstaller bundle"""
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


def _num_from_text(t: str):
    """Extract an integer like 55,997 from '55,997 mWh' robustly."""
    if not t:
        return None
    # normalize spaces and case
    t = t.replace("\xa0", " ").strip()
    m = re.search(r"([\d,]+)", t)
    if not m:
        return None
    try:
        return int(m.group(1).replace(",", ""))
    except:
        return None

def extract_battery_health(report_path: str):
    """Parse the battery-report.html for Full/Design capacity and compute health%."""
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        # Graceful error if bs4 isn't installed
        raise RuntimeError("BeautifulSoup (bs4) not installed. Run: pip install beautifulsoup4")

    try:
        with open(report_path, "r", encoding="utf-8", errors="ignore") as f:
            soup = BeautifulSoup(f, "html.parser")

        full_charge = None
        design_capacity = None

        # Find all label spans; value is in the next <td>
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

        # Fallback: scan table rows directly if needed
        for row in soup.find_all("tr"):
            tds = row.find_all("td")
            if len(tds) >= 2:
                key = tds[0].get_text(" ", strip=True).lower()
                val = _num_from_text(tds[1].get_text(" ", strip=True))
                if val is None:
                    continue
                if "design capacity" in key:
                    design_capacity = val
                elif "full charge capacity" in key:
                    full_charge = val

        if full_charge and design_capacity and design_capacity > 0:
            health = round((full_charge / design_capacity) * 100, 2)
            return full_charge, design_capacity, health

        return None, None, None

    except Exception as e:
        # Bubble up so GUI can show the error
        raise

# -------- Actions --------
def generate_report():
    # Disable both buttons during work
    generate_btn.config(state=tk.DISABLED)
    open_btn.config(state=tk.DISABLED)
    progress.start(10)

    def task():
        try:
            cmd = f'powercfg /batteryreport /output "{REPORT_PATH}"'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

            # Small delay for smoother UX
            time.sleep(1.0)

            if result.returncode != 0:
                raise RuntimeError(result.stderr.strip() or "powercfg failed")

            if not os.path.exists(REPORT_PATH):
                raise FileNotFoundError("Report file not found after generation.")

            # Extract & show health
            full, design, health = extract_battery_health(REPORT_PATH)
            if full and design and health is not None:
                color = "green" if health > 80 else ("orange" if health > 60 else "red")
                health_label.config(
                    text=f"🔋 Battery Health: {health}%\n(Full: {full} mWh / Design: {design} mWh)",
                    foreground=color
                )
                # Enable "Open Report" after a successful generation
                open_btn.config(state=tk.NORMAL)
            else:
                health_label.config(text="⚠️ Could not extract battery health.", foreground="red")

        except Exception as e:
            messagebox.showerror("Error", f"{type(e).__name__}: {e}")
        finally:
            progress.stop()
            generate_btn.config(state=tk.NORMAL)

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
root = tk.Tk()
root.title(APP_TITLE)
root.geometry("500x380")
root.resizable(False, False)

icon_path = resource_path("logo.ico")
try:
    root.iconbitmap(icon_path)
except Exception as e:
    print("Icon load failed:", e)



style = ttk.Style()
style.configure("TButton", font=("Segoe UI", 11), padding=6)
style.configure("TLabel", font=("Segoe UI", 11))

title_label = ttk.Label(root, text="🔋 Battery Report Generator", font=("Segoe UI", 16, "bold"))
title_label.pack(pady=15)

progress = ttk.Progressbar(root, mode="indeterminate", length=320)
progress.pack(pady=10)

generate_btn = ttk.Button(root, text="Generate Report", command=generate_report)
generate_btn.pack(pady=6)

open_btn = ttk.Button(root, text="Open Report", command=open_report, state=tk.DISABLED)
open_btn.pack(pady=6)

info_label = ttk.Label(root, text="Generate a detailed report and instantly see your battery health.", font=("Segoe UI", 10))
info_label.pack(pady=6)

health_label = ttk.Label(root, text="Battery Health: Not Generated Yet", font=("Segoe UI", 11, "bold"), foreground="gray")
health_label.pack(pady=16)

branding_label = ttk.Label(root, text=BRANDING, font=("Segoe UI", 9, "italic"), foreground="gray")
branding_label.pack(side="bottom", pady=10)

root.mainloop()
