from pathlib import Path

path = Path("main.py")
text = path.read_text(encoding="utf-8")


def replace_once(old: str, new: str, label: str) -> None:
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, found {count}")
    text = text.replace(old, new, 1)


replace_once(
    'APP_VERSION = "0.6.4"',
    'APP_VERSION = "0.6.5"',
    "version",
)

replace_once(
    '        self.queue_count_var = tk.StringVar(value="No items queued")\n',
    '        self.queue_count_var = tk.StringVar(value="No items queued")\n'
    '        self.speed_var = tk.StringVar(value="—")\n'
    '        self.eta_var = tk.StringVar(value="—")\n',
    "transfer vars",
)

replace_once(
    '            columns=("title", "format", "quality", "status"),',
    '            columns=("title", "format", "quality", "status", "open"),',
    "queue columns",
)

replace_once(
    '        self.queue_tree.heading("status", text="STATUS")\n',
    '        self.queue_tree.heading("status", text="STATUS")\n'
    '        self.queue_tree.heading("open", text="")\n',
    "open heading",
)

replace_once(
    '        self.queue_tree.column("status", width=125, minwidth=105, stretch=False, anchor="center")\n',
    '        self.queue_tree.column("status", width=125, minwidth=105, stretch=False, anchor="center")\n'
    '        self.queue_tree.column("open", width=110, minwidth=100, stretch=False, anchor="center")\n',
    "open column width",
)

replace_once(
    '        scrollbar.pack(side="right", fill="y")\n',
    '        scrollbar.pack(side="right", fill="y")\n'
    '        self.queue_tree.bind("<ButtonRelease-1>", self._on_queue_click, add="+")\n',
    "queue click binding",
)

replace_once(
    '            values=(job["title"], output_format.replace(" Video", "").replace(" Audio", ""), quality, job["status"]),\n',
    '            values=(job["title"], output_format.replace(" Video", "").replace(" Audio", ""), quality, job["status"], ""),\n',
    "queue insert values",
)

replace_once(
    '        while len(values) < 4:\n            values.append("")\n',
    '        while len(values) < 5:\n            values.append("")\n',
    "queue value count",
)

replace_once(
    '        if status is not None:\n            values[3] = "Downloading" if status == "Running" else status\n',
    '        if status is not None:\n'
    '            values[3] = "Downloading" if status == "Running" else status\n'
    '            values[4] = "Open Folder" if status == "Complete" else ""\n',
    "queue completed action",
)

progress_old = '''        ttk.Progressbar(
            progress_card,
            variable=self.progress_var,
            maximum=100,
            style="Horizontal.TProgressbar",
        ).pack(fill="x")
'''
progress_new = progress_old + '''
        transfer_row = ttk.Frame(progress_card, style="Card.TFrame")
        transfer_row.pack(fill="x", pady=(9, 0))
        ttk.Label(transfer_row, text="DOWNLOAD SPEED", style="MutedCard.TLabel").pack(side="left")
        ttk.Label(transfer_row, textvariable=self.speed_var, style="Card.TLabel").pack(side="left", padx=(8, 28))
        ttk.Label(transfer_row, text="TIME REMAINING", style="MutedCard.TLabel").pack(side="left")
        ttk.Label(transfer_row, textvariable=self.eta_var, style="Card.TLabel").pack(side="left", padx=(8, 0))
'''
replace_once(progress_old, progress_new, "transfer metrics UI")

replace_once(
    '                        self.progress_var.set(max(0, min(100, pct)))\n                        self.status_var.set(message)\n',
    '                        self.progress_var.set(max(0, min(100, pct)))\n'
    '                        self.status_var.set(message)\n'
    '                        self._update_transfer_metrics(message)\n',
    "progress metrics event",
)

replace_once(
    '                    self.progress_var.set(100)\n                    self.status_var.set("Saved: " + Path(output).name)\n',
    '                    self.progress_var.set(100)\n'
    '                    self.speed_var.set("—")\n'
    '                    self.eta_var.set("—")\n'
    '                    self.status_var.set("Saved: " + Path(output).name)\n',
    "done metrics reset",
)

replace_once(
    '                    self._refresh_queue_count()\n                    self.status_var.set(state)\n                    if state == "Failed":\n',
    '                    self._refresh_queue_count()\n'
    '                    self.speed_var.set("—")\n'
    '                    self.eta_var.set("—")\n'
    '                    self.status_var.set(state)\n'
    '                    if state == "Failed":\n',
    "error metrics reset",
)

open_folder_old = '''    def _open_folder(self):
        folder = Path(self.folder_var.get()).expanduser()
        folder.mkdir(parents=True, exist_ok=True)
        try:
            if os.name == "nt":
                os.startfile(folder)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(folder)])
            else:
                subprocess.Popen(["xdg-open", str(folder)])
        except Exception as exc:
            messagebox.showerror("Open folder", str(exc))
'''
open_folder_new = '''    def _on_queue_click(self, event):
        if self.queue_tree.identify_region(event.x, event.y) != "cell":
            return
        if self.queue_tree.identify_column(event.x) != "#5":
            return

        iid = self.queue_tree.identify_row(event.y)
        if not iid:
            return

        try:
            job_id = int(iid)
        except ValueError:
            return

        with self.jobs_lock:
            job = next((item for item in self.jobs if item["id"] == job_id), None)
            if not job or job["status"] != "Complete":
                return
            folder = job["output_dir"]

        self._open_specific_folder(folder)

    def _open_specific_folder(self, folder):
        folder = Path(folder).expanduser()
        if not folder.exists():
            messagebox.showerror("Open folder", f"Folder no longer exists:\n{folder}")
            return
        try:
            if os.name == "nt":
                os.startfile(folder)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(folder)])
            else:
                subprocess.Popen(["xdg-open", str(folder)])
        except Exception as exc:
            messagebox.showerror("Open folder", str(exc))

    def _open_folder(self):
        folder = Path(self.folder_var.get()).expanduser()
        folder.mkdir(parents=True, exist_ok=True)
        self._open_specific_folder(folder)

    def _update_transfer_metrics(self, message):
        speed_match = re.search(r"•\\s+([^•]+?/s)", message)
        eta_match = re.search(r"ETA\\s+([^•]+?)\\s*$", message)
        self.speed_var.set(speed_match.group(1).strip() if speed_match else "—")
        self.eta_var.set(eta_match.group(1).strip() if eta_match else "—")
'''
replace_once(open_folder_old, open_folder_new, "folder helpers")

path.write_text(text, encoding="utf-8")
print("Patched main.py for desktop V0.6.5")
