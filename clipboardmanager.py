import ttkbootstrap as tb
from ttkbootstrap.constants import *
from ttkbootstrap.scrolled import ScrolledFrame
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
import pyperclip
import threading
import time
import json
import os
import io
import base64
from datetime import datetime

class ModernClipboardManager:
    def __init__(self, root):
        self.root = root
        self.root.title("Modern Clipboard Manager")
        self.root.geometry("1200x800")
        self.history = []
        self.max_items = 100
        self.history_file = "clipboard_history.json"
        self.search_var = tk.StringVar()
        self.search_var.trace('w', self.filter_entries)
        self.build_ui()
        self.load_history()
        self.monitor_clipboard()

    def build_ui(self):
        style = tb.Style("darkly")
        font = ("Segoe UI", 12)

        search_frame = tb.Frame(self.root, padding=10)
        search_frame.pack(fill=X)
        self.search_entry = tb.Entry(search_frame, textvariable=self.search_var, font=font, bootstyle="dark")
        self.search_entry.pack(side=LEFT, fill=X, expand=True, padx=(0, 10))
        tb.Label(search_frame, text="(Ctrl+F to search)", font=font, bootstyle="secondary").pack(side=RIGHT)

        main_pane = tb.PanedWindow(self.root, orient=HORIZONTAL, bootstyle="dark")
        main_pane.pack(fill=BOTH, expand=True, padx=10, pady=10)

        left_frame = tb.Frame(main_pane, padding=5)
        main_pane.add(left_frame, weight=1)
        columns = ("favorite", "content", "timestamp", "category")
        self.tree = tb.Treeview(left_frame, columns=columns, show="headings", bootstyle="dark")
        self.tree.heading("favorite", text="★")
        self.tree.heading("content", text="Clipboard Content")
        self.tree.heading("timestamp", text="Time")
        self.tree.heading("category", text="Category")
        self.tree.column("favorite", width=40, anchor=CENTER)
        self.tree.column("content", width=400)
        self.tree.column("timestamp", width=180)
        self.tree.column("category", width=120)
        self.tree.pack(fill=BOTH, expand=True, side=LEFT)
        tb.Scrollbar(left_frame, orient=VERTICAL, command=self.tree.yview, bootstyle="dark-round").pack(side=RIGHT, fill=Y)
        self.tree.configure(yscrollcommand=lambda f, l: self.tree.yview_moveto(f))

        right_frame = tb.Frame(main_pane, padding=10)
        main_pane.add(right_frame, weight=2)
        self.preview_label = tb.LabelFrame(right_frame, text="Preview", bootstyle="dark", padding=10)
        self.preview_text = tb.Text(self.preview_label, font=font, wrap=WORD, height=10, bg="#23272b", fg="#f8f9fa", relief="flat", borderwidth=0)
        self.preview_text.pack(fill=BOTH, expand=True)
        self.preview_image_label = tb.Label(self.preview_label, bootstyle="dark")
        self.preview_image_label.pack_forget()

        btn_frame = tb.Frame(self.root, padding=10)
        btn_frame.pack(fill=X)
        tb.Button(btn_frame, text="Copy Selected (Ctrl+C)", command=self.copy_selected, bootstyle="success-outline").pack(side=LEFT, padx=5)
        tb.Button(btn_frame, text="Delete Selected (Del)", command=self.delete_selected, bootstyle="danger-outline").pack(side=LEFT, padx=5)
        tb.Button(btn_frame, text="Toggle Favorite (Ctrl+D)", command=self.toggle_favorite, bootstyle="warning-outline").pack(side=LEFT, padx=5)
        tb.Button(btn_frame, text="Clear All", command=self.clear_all, bootstyle="secondary-outline").pack(side=LEFT, padx=5)

        self.tree.bind('<<TreeviewSelect>>', self.update_preview)

    def update_preview(self, event=None):
        selected = self.tree.selection()
        if not selected:
            self.preview_label.pack_forget()
            return
        if not self.preview_label.winfo_ismapped():
            self.preview_label.pack(fill=BOTH, expand=True)
        item = self.tree.item(selected[0])
        content = item['values'][1]
        if self.is_image(content):
            self.preview_text.pack_forget()
            image = self.decode_image(content)
            if image:
                img_width, img_height = image.size
                max_width, max_height = self.preview_label.winfo_width()-40, self.preview_label.winfo_height()-40
                scale = min(max_width / img_width, max_height / img_height, 1)
                image = image.resize((int(img_width * scale), int(img_height * scale)), Image.LANCZOS)
                photo = ImageTk.PhotoImage(image)
                self.preview_image_label.configure(image=photo)
                self.preview_image_label.image = photo
                self.preview_image_label.pack(fill=tk.BOTH, expand=True)
        else:
            self.preview_image_label.pack_forget()
            self.preview_text.pack(fill=tk.BOTH, expand=True)
            self.preview_text.delete(1.0, tk.END)
            self.preview_text.insert(1.0, content)

    def filter_entries(self, *args):
        search_term = self.search_var.get().lower()
        for item in self.tree.get_children():
            content = str(self.tree.item(item)['values'][1]).lower()
            if search_term in content:
                self.tree.reattach(item, '', 'end')
            else:
                self.tree.detach(item)

    def copy_selected(self):
        selected = self.tree.selection()
        if selected:
            item = self.tree.item(selected[0])
            content = item['values'][1]
            if self.is_image(content):
                messagebox.showinfo("Copy", "Image copy to clipboard is not fully supported in this demo.")
            else:
                pyperclip.copy(content)

    def delete_selected(self):
        selected = self.tree.selection()
        if selected:
            for sel in selected:
                item = self.tree.item(sel)
                content = item['values'][1]
                self.history = [h for h in self.history if h['content'] != content]
                self.tree.delete(sel)
            self.save_history()
            all_items = self.tree.get_children()
            if all_items:
                self.tree.selection_set(all_items[0])
                self.update_preview()
            else:
                self.preview_text.delete(1.0, tk.END)
                self.preview_image_label.pack_forget()

    def toggle_favorite(self):
        selected = self.tree.selection()
        if selected:
            item_id = selected[0]
            item = self.tree.item(item_id)
            values = list(item['values'])
            values[0] = '★' if values[0] != '★' else ''
            self.tree.item(item_id, values=values)
            for h in self.history:
                if h['content'] == values[1]:
                    h['favorite'] = values[0]
            self.save_history()

    def clear_all(self):
        self.tree.delete(*self.tree.get_children())
        self.history = []
        self.save_history()
        self.preview_text.delete(1.0, tk.END)
        self.preview_image_label.pack_forget()

    def is_image(self, content):
        try:
            base64.b64decode(content)
            return True
        except Exception:
            return False

    def decode_image(self, content):
        try:
            image_data = base64.b64decode(content)
            return Image.open(io.BytesIO(image_data))
        except Exception:
            return None

    def load_history(self):
        pass

    def monitor_clipboard(self):
        def poll():
            last_clipboard = None
            while True:
                try:
                    image_data = None
                    text = None
                    try:
                        self.root.clipboard_get(type='image/png')
                    except Exception:
                        pass
                    try:
                        text = pyperclip.paste()
                    except Exception:
                        text = None
                    if text and text != last_clipboard and text.strip():
                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        entry = {"favorite": "", "content": text, "timestamp": timestamp, "category": "Text"}
                        self.history.insert(0, entry)
                        self.tree.insert('', 0, values=(entry["favorite"], entry["content"], entry["timestamp"], entry["category"]))
                        self.save_history()
                        last_clipboard = text
                    if hasattr(self.root, 'clipboard_get'):
                        try:
                            img = self.root.clipboard_get(type='image')
                            if img != last_clipboard:
                                pass
                        except Exception:
                            pass
                except Exception:
                    pass
                time.sleep(1)
        threading.Thread(target=poll, daemon=True).start()

    def save_history(self):
        pass

    def show_latest_preview(self):
        all_items = self.tree.get_children()
        if all_items:
            self.tree.selection_set(all_items[0])
            self.update_preview()

if __name__ == "__main__":
    root = tb.Window(themename="darkly")
    app = ModernClipboardManager(root)
    root.mainloop() 