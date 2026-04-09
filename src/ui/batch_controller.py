import os
import threading
from tkinter import messagebox


class BatchController:
    def __init__(self, app):
        self.app = app

    def refresh_batch_list_ui(self):
        for i, (idx, var) in enumerate(self.app.batch_vars):
            pair = self.app.file_pairs[idx]
            txt_path = pair["txt"]

            exists = os.path.exists(txt_path)
            is_not_empty = exists and os.path.getsize(txt_path) > 0

            if is_not_empty:
                var.set(False)
                status = self.app.t["batch_status_text3"]
            else:
                status = self.app.t["batch_status_text1"] if not exists else self.app.t["batch_status_text2"]

            if i < len(self.app.batch_checkbox_widgets):
                self.app.batch_checkbox_widgets[i].config(text=f"{pair['name']} {status}")

    def cancel_batch_processing(self):
        if self.app.is_transcribing:
            self.app.stop_batch_flag = True
            self.app.batch_log_label.config(text=self.app.t["msg_stop_batch"])

    def start_batch(self, selected_indices, batch_win, btn_start, btn_cancel_batch):
        btn_start.config(state="disabled")
        btn_cancel_batch.config(state="normal")

        self.app.is_transcribing = True
        self.app.stop_batch_flag = False

        thread = threading.Thread(
            target=self.batch_worker,
            args=(selected_indices, batch_win, btn_start, btn_cancel_batch),
        )
        thread.daemon = True
        thread.start()

    def batch_worker(self, selected_indices, window, btn_start, btn_cancel_batch):
        total = len(selected_indices)
        errors = 0
        processed_count = 0

        for i, idx in enumerate(selected_indices):
            processed_count = i + 1

            if self.app.stop_batch_flag:
                self.app.root.after(0, lambda: self.app.batch_log_label.config(text=self.app.t["msg_process_stopped"]))
                break

            if not window.winfo_exists():
                break

            pair = self.app.file_pairs[idx]
            img_path = pair["img"]
            txt_path = pair["txt"]

            progress_pct = (i / total) * 100 if total else 100
            msg = self.app.t["batch_process_text"] + f" [{i+1}/{total}]: {pair['name']}..."
            self.app.root.after(0, lambda m=msg, v=progress_pct: self.update_batch_ui(m, v))

            try:
                result_text = self.app._call_gemini_api(img_path)
                with open(txt_path, "w", encoding="utf-8") as f:
                    f.write(result_text + "\n")
            except Exception as e:
                errors += 1
                print(self.app.t["batch_worker_file_error"] + f" {pair['name']}: {e}")

            self.app.root.after(0, self.refresh_batch_list_ui)

        was_stopped = self.app.stop_batch_flag
        self.app.is_transcribing = False
        self.app.stop_batch_flag = False

        if window.winfo_exists():
            status = self.app.t["msg_finished"] if not was_stopped else self.app.t["msg_interrupted"]
            final_msg = (
                status
                + self.app.t["batch_final_msg1"]
                + f": {processed_count}/{total}. "
                + self.app.t["batch_final_msg2"]
                + f": {errors}."
            )
            self.app.root.after(0, lambda: self.update_batch_ui(final_msg, 100))
            self.app.root.after(0, lambda: btn_start.config(state="normal"))
            self.app.root.after(0, lambda: btn_cancel_batch.config(state="disabled"))
            self.app.root.after(0, self.refresh_batch_list_ui)
            self.app.root.after(
                0,
                lambda: messagebox.showinfo(self.app.t["batch_final_msg_title"], final_msg, parent=window),
            )
            self.app.root.after(0, lambda: self.app.load_pair(self.app.current_index))

    def update_batch_ui(self, message, progress_value):
        try:
            self.app.batch_log_label.config(text=message)
            self.app.batch_progress["value"] = progress_value
        except Exception as e:
            print(e)
