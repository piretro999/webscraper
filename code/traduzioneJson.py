import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import json
import os
from tkinterdnd2 import TkinterDnD

class JSONEditorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("JSON Localization Editor")
        self.root.geometry("1000x600")

        self.data = {}
        self.languages = []
        self.keys = []
        self.sort_order = {}  # keep track of sort direction per column

        self.create_widgets()

    def create_widgets(self):
        self.create_menu()

        self.frame = ttk.Frame(self.root)
        self.frame.pack(fill=tk.BOTH, expand=True)

        self.tree = ttk.Treeview(self.frame, columns=(), show='headings', selectmode='browse')
        self.tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)

        self.tree_scroll = ttk.Scrollbar(self.frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=self.tree_scroll.set)
        self.tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.bind('<Double-1>', self.on_double_click)

        # Drag and drop support
        self.root.drop_target_register('*')
        self.root.dnd_bind('<<Drop>>', self.on_drop)

        # Bottom buttons
        self.button_frame = ttk.Frame(self.root)
        self.button_frame.pack(pady=10)

        self.save_button = ttk.Button(self.button_frame, text="Salva con nome", command=self.save_file)
        self.save_button.grid(row=0, column=0, padx=5)

        self.highlight_button = ttk.Button(self.button_frame, text="Evidenzia mancanti", command=self.highlight_missing)
        self.highlight_button.grid(row=0, column=1, padx=5)

        self.fill_button = ttk.Button(self.button_frame, text="Completa da 'en'", command=self.fill_from_en)
        self.fill_button.grid(row=0, column=2, padx=5)

        self.add_button = ttk.Button(self.button_frame, text="Aggiungi record", command=self.add_record)
        self.add_button.grid(row=0, column=3, padx=5)

        self.delete_button = ttk.Button(self.button_frame, text="Elimina record selezionato", command=self.delete_selected)
        self.delete_button.grid(row=0, column=4, padx=5)

    def create_menu(self):
        menubar = tk.Menu(self.root)
        filemenu = tk.Menu(menubar, tearoff=0)
        filemenu.add_command(label="Apri", command=self.load_file)
        filemenu.add_command(label="Salva con nome", command=self.save_file)
        filemenu.add_separator()
        filemenu.add_command(label="Esci", command=self.root.quit)
        menubar.add_cascade(label="File", menu=filemenu)
        self.root.config(menu=menubar)

    def on_drop(self, event):
        path = event.data.strip('{').strip('}')
        if os.path.isfile(path):
            self.load_json(path)

    def load_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
        if file_path:
            self.load_json(file_path)

    def load_json(self, file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            self.data = json.load(f)

        self.languages = list(self.data.keys())
        all_keys = set()
        for lang in self.languages:
            all_keys.update(self.data[lang].keys())
        self.keys = sorted(all_keys)

        self.build_table()

    def build_table(self):
        for col in self.tree["columns"]:
            self.tree.heading(col, text="")
        self.tree.delete(*self.tree.get_children())

        self.tree["columns"] = ["key"] + self.languages
        for col in self.tree["columns"]:
            self.tree.heading(col, text=col, command=lambda c=col: self.sort_by_column(c))
            self.tree.column(col, anchor='w', width=200)

        for key in self.keys:
            row = [key]
            missing_langs = []
            for lang in self.languages:
                value = self.data.get(lang, {}).get(key, "")
                if value == "":
                    missing_langs.append(lang)
                row.append(value)

            item = self.tree.insert('', tk.END, values=row)

            if missing_langs:
                if "en" in self.languages and key in self.data.get("en", {}):
                    self.tree.item(item, tags=("yellow",))
                else:
                    self.tree.item(item, tags=("red",))

        self.tree.tag_configure("yellow", background="#fff8dc")  # light yellow
        self.tree.tag_configure("red", background="#ffe4e1")     # light red

    def highlight_missing(self):
        self.build_table()

    def fill_from_en(self):
        if "en" not in self.languages:
            messagebox.showwarning("Errore", "Lingua 'en' non trovata nel file.")
            return

        for key in self.keys:
            en_value = self.data["en"].get(key, "")
            for lang in self.languages:
                if lang == "en":
                    continue
                if key not in self.data.get(lang, {}) or self.data[lang].get(key, "") == "":
                    self.data.setdefault(lang, {})[key] = en_value

        self.build_table()

    def delete_selected(self):
        selected_item = self.tree.selection()
        if not selected_item:
            messagebox.showwarning("Attenzione", "Seleziona un record da eliminare.")
            return

        values = self.tree.item(selected_item, 'values')
        if not values:
            return

        key_to_delete = values[0]
        for lang in self.languages:
            if key_to_delete in self.data.get(lang, {}):
                del self.data[lang][key_to_delete]

        self.tree.delete(selected_item)
        self.keys = [key for key in self.keys if key != key_to_delete]

    def add_record(self):
        new_key = simpledialog.askstring("Nuovo record", "Inserisci il nome della nuova chiave:")
        if not new_key:
            return

        for lang in self.languages:
            self.data.setdefault(lang, {})[new_key] = ""

        if new_key not in self.keys:
            self.keys.append(new_key)
        self.build_table()

    def sort_by_column(self, col):
        col_index = self.tree["columns"].index(col)
        data = [(self.tree.set(child, col), child) for child in self.tree.get_children('')]
        reverse = self.sort_order.get(col, False)
        data.sort(reverse=reverse)

        for index, (val, child) in enumerate(data):
            self.tree.move(child, '', index)

        self.sort_order[col] = not reverse

    def on_double_click(self, event):
        item_id = self.tree.identify_row(event.y)
        column = self.tree.identify_column(event.x)
        if not item_id or not column:
            return

        col_index = int(column.replace('#', '')) - 1
        x, y, width, height = self.tree.bbox(item_id, column)
        value = self.tree.item(item_id, 'values')[col_index]
        entry = tk.Entry(self.tree)
        entry.place(x=x, y=y, width=width, height=height)
        entry.insert(0, value)
        entry.focus()

        def save_value():
            new_value = entry.get()
            current = list(self.tree.item(item_id, 'values'))

            if col_index == 0:
                old_key = current[0]
                new_key = new_value
                current[0] = new_key
                for lang in self.languages:
                    lang_dict = self.data.get(lang, {})
                    if old_key in lang_dict:
                        lang_dict[new_key] = lang_dict.pop(old_key)
            else:
                current[col_index] = new_value
                key = current[0]
                lang = self.languages[col_index - 1]
                self.data.setdefault(lang, {})[key] = new_value

            self.tree.item(item_id, values=current)
            self.keys = list({v[0] for v in [self.tree.item(iid, 'values') for iid in self.tree.get_children()]})
            entry.destroy()

        entry.bind('<Return>', lambda e: save_value())
        entry.bind('<FocusOut>', lambda e: save_value())

    def save_file(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")])
        if file_path:
            sorted_keys = self.keys[:]
            original_order = sorted_keys[:]
            displayed_order = [self.tree.item(iid)['values'][0] for iid in self.tree.get_children()]

            if displayed_order != original_order:
                answer = messagebox.askyesno("Ordina per salvataggio", "L'ordine dei record è stato modificato. Vuoi salvare usando il nuovo ordine?")
                if answer:
                    sorted_keys = displayed_order

            data_to_save = {lang: {} for lang in self.languages}
            for key in sorted_keys:
                for lang in self.languages:
                    value = self.data.get(lang, {}).get(key, "")
                    data_to_save[lang][key] = value

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data_to_save, f, indent=2, ensure_ascii=False)

            messagebox.showinfo("Salvato", f"File salvato in:\n{file_path}")

if __name__ == '__main__':
    root = TkinterDnD.Tk()
    app = JSONEditorApp(root)
    root.mainloop()
