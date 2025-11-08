from import_libs import *
try:
    from i18n import t
except Exception:
    def t(key, **fmt):
        return key.format(**fmt) if fmt else key
def backup_whole_directory(source_folder, backup_folder):
    import datetime as dt
    def get_timestamp():
        if hasattr(dt, 'datetime') and hasattr(dt.datetime, 'now'):
            return dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        raise RuntimeError("The datetime module is broken or shadowed on this system.")
    if not os.path.isabs(backup_folder):
        base_path = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        backup_folder = os.path.abspath(os.path.join(base_path, backup_folder))
    if not os.path.exists(backup_folder): os.makedirs(backup_folder)
    print("Now backing up the whole directory of the Level.sav's location...")
    timestamp = get_timestamp()
    backup_path = os.path.join(backup_folder, f"PalworldSave_backup_{timestamp}")
    shutil.copytree(source_folder, backup_path)
    print(f"Backup of {source_folder} created at: {backup_path}")
def sav_to_json(filepath):
    with open(filepath, "rb") as f:
        data = f.read()
        raw_gvas, save_type = decompress_sav_to_gvas(data)
    gvas_file = GvasFile.read(raw_gvas, PALWORLD_TYPE_HINTS, SKP_PALWORLD_CUSTOM_PROPERTIES, allow_nan=True)
    return gvas_file.dump()
def json_to_sav(json_data, output_filepath):
    gvas_file = GvasFile.load(json_data)
    save_type = 0x32 if "Pal.PalworldSaveGame" in gvas_file.header.save_game_class_name or "Pal.PalLocalWorldSaveGame" in gvas_file.header.save_game_class_name else 0x31
    sav_file = compress_gvas_to_sav(gvas_file.write(SKP_PALWORLD_CUSTOM_PROPERTIES), save_type)
    with open(output_filepath, "wb") as f:
        f.write(sav_file)
class SlotNumUpdaterApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(t("tool.slot_injector"))
        self.geometry("600x200")
        self.config(bg="#2f2f2f")
        try:
            self.iconbitmap(ICON_PATH)
        except Exception as e:
            print(f"Could not set icon: {e}")
        font_style = ("Arial", 10)
        style = ttk.Style(self)
        style.theme_use('clam')
        for opt in [
            ("TFrame", {"background": "#2f2f2f"}),
            ("TLabel", {"background": "#2f2f2f", "foreground": "white", "font": font_style}),
            ("TEntry", {"fieldbackground": "#444444", "foreground": "white", "font": font_style}),
            ("Dark.TButton", {"background": "#555555", "foreground": "white", "font": font_style, "padding": 6}),
        ]:
            style.configure(opt[0], **opt[1])
        style.map("Dark.TButton",
            background=[("active", "#666666"), ("!disabled", "#555555")],
            foreground=[("disabled", "#888888"), ("!disabled", "white")]
        )
        frame = ttk.Frame(self, style="TFrame")
        frame.pack(padx=20, pady=10, fill='x', expand=True)
        row = 0
        browse_btn = ttk.Button(frame, text=t("Browse"), command=self.browse_file, style="Dark.TButton")
        browse_btn.grid(row=row, column=0, sticky='w')
        ttk.Label(frame, text=t("Select Level.sav File:"), style="TLabel").grid(row=row, column=1, sticky='w', padx=(10,5))
        self.file_entry = ttk.Entry(frame, style="TEntry")
        self.file_entry.grid(row=row, column=2, sticky='ew')
        row += 1
        ttk.Label(frame, text=t("Total Pages:"), style="TLabel").grid(row=row, column=0, sticky='w', pady=5)
        self.pages_entry = ttk.Entry(frame, style="TEntry", width=10)
        self.pages_entry.grid(row=row, column=1, sticky='w', pady=5)
        row += 1
        ttk.Label(frame, text=t("Total Slots:"), style="TLabel").grid(row=row, column=0, sticky='w', pady=5)
        self.slots_entry = ttk.Entry(frame, style="TEntry", width=10)
        self.slots_entry.grid(row=row, column=1, sticky='w', pady=5)
        row += 1
        ttk.Label(frame, text=t("Total SlotNum:"), style="TLabel").grid(row=row, column=0, sticky='w', pady=5)
        self.current_val_entry = ttk.Entry(frame, style="TEntry", width=10)
        self.current_val_entry.grid(row=row, column=1, sticky='w', pady=5)
        self.current_val_entry.insert(0, "960")
        row += 1
        apply_btn = ttk.Button(frame, text=t("Apply Slot Injection"), command=self.apply_slotnum_update, style="Dark.TButton")
        apply_btn.grid(row=row, column=0, columnspan=3, pady=10)
        frame.columnconfigure(2, weight=1)
        center_window(self)
    def browse_file(self):
        file = filedialog.askopenfilename(title=t("Select Level.sav file"), filetypes=[("SAV files", "Level.sav")])
        if file:
            self.file_entry.delete(0, tk.END)
            self.file_entry.insert(0, file)
    def apply_slotnum_update(self):
        filepath = self.file_entry.get()
        if not filepath or not os.path.isfile(filepath) or not filepath.endswith("Level.sav"):
            messagebox.showerror(t("Error"), t("Select a valid Level.sav file"))
            return
        try:
            pages = int(self.pages_entry.get())
            slots = int(self.slots_entry.get())
            current_val = int(self.current_val_entry.get())
            if pages < 1 or slots < 1:
                raise ValueError
        except ValueError:
            messagebox.showerror(t("Error"), t("Please enter valid positive integers for pages, slots, and current value"))
            return
        new_value = pages * slots
        confirm = messagebox.askyesno(t("Confirm Update"), t("Are you sure you want to update SlotNum values from {current_val} to {new_value} (pages × slots)?", current_val=current_val, new_value=new_value))
        if not confirm:
            return
        level_json = sav_to_json(filepath)
        container = level_json['properties']['worldSaveData']['value'].get('CharacterContainerSaveData', {})
        if not container:
            messagebox.showerror(t("Error"), t("CharacterContainerSaveData not found."))
            return
        val = container.get('value', [])
        if not isinstance(val, list):
            messagebox.showerror(t("Error"), t("CharacterContainerSaveData.value is not a list."))
            return
        updated_count = 0
        for entry in val:
            slotnum_entry = entry.get('value', {}).get('SlotNum', {})
            if slotnum_entry.get('value') == current_val:
                slotnum_entry['value'] = new_value
                updated_count += 1
        if updated_count == 0:
            messagebox.showinfo(t("Info"), t("No SlotNum entries with value {current_val} found.", current_val=current_val))
            return
        backup_whole_directory(os.path.dirname(filepath), "Backups/Slot Injector")
        json_to_sav(level_json, filepath)
        messagebox.showinfo(t("Success"), t("Updated {updated_count} SlotNum entries from {current_val} to {new_value} in Level.sav!", updated_count=updated_count, current_val=current_val, new_value=new_value))
def center_window(win):
    win.update_idletasks()
    w, h = win.winfo_width(), win.winfo_height()
    ws, hs = win.winfo_screenwidth(), win.winfo_screenheight()
    x, y = (ws - w) // 2, (hs - h) // 2
    win.geometry(f'{w}x{h}+{x}+{y}')
def slot_injector():
    def on_exit(): app.destroy()
    app = SlotNumUpdaterApp()
    app.protocol("WM_DELETE_WINDOW", app.destroy)
    return app
if __name__ == "__main__":
    app = slot_injector()
    app.mainloop()