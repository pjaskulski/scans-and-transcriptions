import os
import tkinter as tk
from tkinter import messagebox

import ttkbootstrap as ttk
from ttkbootstrap.constants import BOTTOM, BOTH, LEFT, RIGHT, VERTICAL, X, Y
from ttkbootstrap.widgets.scrolled import ScrolledFrame

from app.models import AppConfig
from services.config_service import load_app_config, save_app_config
from services.gemini_service import (
    model_code_for_label,
    model_label_for_code,
    model_labels,
)


def open_batch_dialog(app):
    if app.is_transcribing:
        messagebox.showwarning(app.t["msg_warning"], app.t["msg_batch_warning_text"], parent=app.root)
        return

    if not app.file_pairs:
        messagebox.showinfo(app.t["msg_missing_files"], app.t["msg_missing_files_text"], parent=app.root)
        return

    batch_win = tk.Toplevel(app.root)
    batch_win.title(app.t["batch_win_title"])
    batch_win.geometry("800x700")
    batch_win.transient(app.root)
    batch_win.grab_set()

    ttk.Label(batch_win, text=app.t["batch_label_text"], font=("Segoe UI", 12, "bold")).pack(pady=10)
    ttk.Label(batch_win, text=app.t["batch_label_info"], bootstyle="secondary", font=("Segoe UI", 9)).pack(
        pady=(0, 10)
    )

    list_frame = ScrolledFrame(batch_win, autohide=False)
    list_frame.pack(fill=BOTH, expand=True, padx=10, pady=5)

    app.batch_vars = []
    app.batch_checkbox_widgets = []

    for idx, pair in enumerate(app.file_pairs):
        txt_path = pair["txt"]
        should_select = False
        status_text = ""

        if not os.path.exists(txt_path):
            should_select = True
            status_text = app.t["batch_status_text1"]
        elif os.path.getsize(txt_path) == 0:
            should_select = True
            status_text = app.t["batch_status_text2"]
        else:
            status_text = app.t["batch_status_text3"]

        var = tk.BooleanVar(value=should_select)
        app.batch_vars.append((idx, var))

        row = ttk.Frame(list_frame)
        row.pack(fill=X, pady=2)

        cb = ttk.Checkbutton(row, text=f"{pair['name']} {status_text}", variable=var, bootstyle="round-toggle")
        cb.pack(side=LEFT)
        app.batch_checkbox_widgets.append(cb)

    btn_panel = ttk.Frame(batch_win, padding=10)
    btn_panel.pack(fill=X, side=BOTTOM)

    app.batch_log_label = ttk.Label(batch_win, text=app.t["batch_log_label"], bootstyle="inverse-secondary")
    app.batch_log_label.pack(fill=X, side=BOTTOM, padx=10)

    app.batch_progress = ttk.Progressbar(batch_win, mode="determinate", bootstyle="success-striped")
    app.batch_progress.pack(fill=X, side=BOTTOM, padx=10, pady=5)

    def select_all():
        for _, v in app.batch_vars:
            v.set(True)

    def select_none():
        for _, v in app.batch_vars:
            v.set(False)

    def start_batch():
        selected_indices = [idx for idx, var in app.batch_vars if var.get()]
        if not selected_indices:
            messagebox.showwarning("Info", app.t["batch_no_files_selected"], parent=batch_win)
            return
        app.batch_controller.start_batch(selected_indices, batch_win, btn_start, btn_cancel_batch)

    ttk.Button(btn_panel, text=app.t["batch_select_all"], command=select_all, bootstyle="outline-secondary").pack(
        side=LEFT, padx=5
    )
    ttk.Button(btn_panel, text=app.t["batch_unselect_all"], command=select_none, bootstyle="outline-secondary").pack(
        side=LEFT, padx=5
    )

    btn_start = ttk.Button(btn_panel, text=app.t["btn_start"], command=start_batch, bootstyle="danger")
    btn_start.pack(side=RIGHT, padx=5)

    btn_cancel_batch = ttk.Button(
        btn_panel,
        text=app.t["btn_batch_cancel"],
        command=app.batch_controller.cancel_batch_processing,
        bootstyle="outline-danger",
        state="disabled",
    )
    btn_cancel_batch.pack(side=RIGHT, padx=5)


def edit_current_prompt(app):
    if not app.current_prompt_path or not os.path.exists(app.current_prompt_path):
        messagebox.showwarning(app.t["msg_edit_prompt_error_title"], app.t["msg_edit_prompt_error_text"], parent=app.root)
        return

    edit_win = tk.Toplevel(app.root)
    edit_win.title(app.t["edit_win_title"] + f": {os.path.basename(app.current_prompt_path)}")
    edit_win.geometry("850x600")
    edit_win.transient(app.root)
    edit_win.grab_set()

    btn_frame = ttk.Frame(edit_win)
    btn_frame.pack(side=BOTTOM, fill=X, pady=15)

    def save_prompt_changes():
        new_content = txt_edit.get(1.0, tk.END).strip()
        if not new_content:
            messagebox.showwarning(app.t["msg_error_title"], app.t["msg_save_prompt_empty"], parent=edit_win)
            return

        try:
            with open(app.current_prompt_path, "w", encoding="utf-8") as f:
                f.write(new_content)
            app.prompt_text = new_content
            messagebox.showinfo(app.t["msg_save_prompt_title"], app.t["msg_save_prompt_text"], parent=edit_win)
            edit_win.destroy()
        except Exception as e:
            messagebox.showerror(app.t["msg_save_prompy_error_title"], str(e), parent=edit_win)

    def restore_from_file():
        if messagebox.askyesno(app.t["msg_prompt_restore_title"], app.t["msg_prompt_restore_text"], parent=edit_win):
            try:
                with open(app.current_prompt_path, "r", encoding="utf-8") as f:
                    content = f.read()
                txt_edit.delete(1.0, tk.END)
                txt_edit.insert(tk.END, content)
            except Exception as e:
                messagebox.showerror(app.t["msg_error_title"], app.t["msg_prompt_restore_error"] + f": {e}", parent=edit_win)

    def on_close_prompt_edit():
        current_content = txt_edit.get(1.0, tk.END).strip()
        if current_content != app.prompt_text.strip():
            if messagebox.askyesno(app.t["msg_on_close_title"], app.t["msg_on_close_text"], parent=edit_win):
                edit_win.destroy()
        else:
            edit_win.destroy()

    edit_win.protocol("WM_DELETE_WINDOW", on_close_prompt_edit)

    btn_save = ttk.Button(btn_frame, text=app.t["btn_save_prompt"], command=save_prompt_changes, bootstyle="success")
    btn_save.pack(side=RIGHT, padx=20)

    btn_restore = ttk.Button(
        btn_frame,
        text=app.t["btn_restore_prompt"],
        command=restore_from_file,
        bootstyle="outline-secondary",
    )
    btn_restore.pack(side=LEFT, padx=20)

    text_container = ttk.Frame(edit_win)
    text_container.pack(fill=BOTH, expand=True, padx=15, pady=(15, 0))

    scrollbar = ttk.Scrollbar(text_container, orient=VERTICAL)
    scrollbar.pack(side=RIGHT, fill=Y)

    txt_edit = tk.Text(text_container, font=("Consolas", 11), wrap=tk.WORD, undo=True, yscrollcommand=scrollbar.set)
    txt_edit.insert(tk.END, app.prompt_text)
    txt_edit.pack(side=LEFT, fill=BOTH, expand=True)

    scrollbar.config(command=txt_edit.yview)
    txt_edit.focus_set()


def open_settings_dialog(app):
    settings_win = tk.Toplevel(app.root)
    settings_win.title(app.t["settings_win_title"])
    settings_win.geometry("700x560")
    settings_win.resizable(False, False)
    settings_win.transient(app.root)
    settings_win.grab_set()

    container = ttk.Frame(settings_win, padding=15)
    container.pack(fill=BOTH, expand=True)

    ttk.Label(container, text=app.t["settings_api_key_label"], font=("Segoe UI", 10, "bold")).pack(anchor="w")
    ttk.Label(
        container,
        text=app.t["settings_api_key_help"],
        bootstyle="secondary",
        font=("Segoe UI", 8),
        wraplength=560,
        justify=LEFT,
    ).pack(anchor="w", pady=(2, 10))

    config = load_app_config(app.config_file)
    api_key_var = tk.StringVar(value=config.api_key)
    htr_model_var = tk.StringVar(value=model_label_for_code("htr", config.htr_model))
    analysis_model_var = tk.StringVar(value=model_label_for_code("analysis", config.analysis_model))
    box_model_var = tk.StringVar(value=model_label_for_code("box", config.box_model))
    tts_model_var = tk.StringVar(value=model_label_for_code("tts", config.tts_model))

    entry = ttk.Entry(container, textvariable=api_key_var, width=72, show="*")
    entry.pack(fill=X, pady=(0, 6))
    entry.focus_set()

    show_var = tk.BooleanVar(value=False)

    def toggle_visibility():
        entry.config(show="" if show_var.get() else "*")

    ttk.Checkbutton(
        container,
        text=app.t["settings_show_key"],
        variable=show_var,
        command=toggle_visibility,
        bootstyle="round-toggle",
    ).pack(anchor="w", pady=(0, 12))

    ttk.Separator(container).pack(fill=X, pady=(4, 10))

    ttk.Label(container, text=app.t["settings_models_label"], font=("Segoe UI", 10, "bold")).pack(anchor="w")
    ttk.Label(
        container,
        text=app.t["settings_models_help"],
        bootstyle="secondary",
        font=("Segoe UI", 8),
        wraplength=640,
        justify=LEFT,
    ).pack(anchor="w", pady=(2, 10))

    ttk.Label(container, text=app.t["settings_htr_model_label"]).pack(anchor="w")
    htr_combo = ttk.Combobox(container, state="readonly", values=model_labels("htr"), textvariable=htr_model_var)
    htr_combo.pack(fill=X, pady=(2, 10))

    ttk.Label(container, text=app.t["settings_analysis_model_label"]).pack(anchor="w")
    analysis_combo = ttk.Combobox(
        container,
        state="readonly",
        values=model_labels("analysis"),
        textvariable=analysis_model_var,
    )
    analysis_combo.pack(fill=X, pady=(2, 10))

    ttk.Label(container, text=app.t["settings_box_model_label"]).pack(anchor="w")
    box_combo = ttk.Combobox(container, state="readonly", values=model_labels("box"), textvariable=box_model_var)
    box_combo.pack(fill=X, pady=(2, 10))

    ttk.Label(container, text=app.t["settings_tts_model_label"]).pack(anchor="w")
    tts_combo = ttk.Combobox(container, state="readonly", values=model_labels("tts"), textvariable=tts_model_var)
    tts_combo.pack(fill=X, pady=(2, 12))

    btn_row = ttk.Frame(container)
    btn_row.pack(fill=X, side=BOTTOM)

    def save_settings():
        app.api_key = api_key_var.get().strip()
        app.htr_model = model_code_for_label("htr", htr_model_var.get())
        app.analysis_model = model_code_for_label("analysis", analysis_model_var.get())
        app.box_model = model_code_for_label("box", box_model_var.get())
        app.tts_model = model_code_for_label("tts", tts_model_var.get())
        try:
            save_app_config(
                AppConfig(
                    font_size=app.font_size,
                    current_lang=app.current_lang,
                    default_prompt=app.default_prompt,
                    api_key=app.api_key,
                    tts_lang=getattr(app, "current_tts_lang_code", "pl"),
                    htr_model=app.htr_model,
                    analysis_model=app.analysis_model,
                    box_model=app.box_model,
                    tts_model=app.tts_model,
                ),
                app.config_file,
            )
            messagebox.showinfo(app.t["msg_save_config_title"], app.t["msg_save_config_ok"], parent=settings_win)
            settings_win.destroy()
        except Exception as e:
            messagebox.showerror(
                app.t["msg_error_title"],
                app.t["msg_save_config_file_error"] + f": {e}",
                parent=settings_win,
            )

    ttk.Button(
        btn_row,
        text=app.t["btn_settings_cancel"],
        command=settings_win.destroy,
        bootstyle="outline-secondary",
    ).pack(side=LEFT)
    ttk.Button(
        btn_row,
        text=app.t["btn_settings_save"],
        command=save_settings,
        bootstyle="success",
    ).pack(side=RIGHT)

    settings_win.wait_window()
