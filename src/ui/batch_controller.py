from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
import logging
import os
import threading
from tkinter import messagebox


logger = logging.getLogger(__name__)


class BatchController:
    def __init__(self, app):
        self.app = app

    def refresh_batch_item_ui(self, idx):
        batch_vars = getattr(self.app, "batch_vars", {}) or {}
        batch_tree = getattr(self.app, "batch_tree", None)
        if idx not in batch_vars:
            return

        pair = self.app.file_pairs[idx]
        txt_path = pair["txt"]

        exists = os.path.exists(txt_path)
        is_not_empty = exists and os.path.getsize(txt_path) > 0

        if is_not_empty:
            batch_vars[idx] = False
            status = self.app.t["batch_status_text3"]
        else:
            status = self.app.t["batch_status_text1"] if not exists else self.app.t["batch_status_text2"]

        if batch_tree and batch_tree.exists(str(idx)):
            selected_mark = "☑" if batch_vars.get(idx, False) else "☐"
            batch_tree.item(str(idx), values=(selected_mark, pair["name"], status))

    def refresh_batch_list_ui(self):
        batch_vars = getattr(self.app, "batch_vars", {}) or {}

        for idx in batch_vars:
            self.refresh_batch_item_ui(idx)

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
        workers = max(1, int(getattr(self.app, "batch_parallel_workers", 1) or 1))
        if getattr(self.app, "llm_provider", "gemini") == "gemini" and workers > 1:
            self._parallel_batch_worker(selected_indices, window, btn_start, btn_cancel_batch, workers)
            return

        self._sequential_batch_worker(selected_indices, window, btn_start, btn_cancel_batch)

    def _process_one_file(self, idx, ordinal, total):
        pair = self.app.file_pairs[idx]
        img_path = self.app.get_transcription_image_path(pair)
        txt_path = pair["txt"]

        msg = self.app.t["batch_process_text"] + f" [{ordinal}/{total}]: {pair['name']}..."
        logger.info("Batch transcription started for %s [%s/%s]", pair["name"], ordinal, total)
        self.app.root.after(0, lambda m=msg: self.update_batch_ui(m, None))

        result_text = self.app._call_gemini_api(img_path)
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(result_text + "\n")

        logger.info("Batch transcription finished for %s [%s/%s]", pair["name"], ordinal, total)
        return idx, pair["name"]

    def _sequential_batch_worker(self, selected_indices, window, btn_start, btn_cancel_batch):
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
            img_path = self.app.get_transcription_image_path(pair)
            txt_path = pair["txt"]

            progress_pct = (i / total) * 100 if total else 100
            msg = self.app.t["batch_process_text"] + f" [{i+1}/{total}]: {pair['name']}..."
            logger.info("Batch transcription started for %s [%s/%s]", pair["name"], i + 1, total)
            self.app.root.after(0, lambda m=msg, v=progress_pct: self.update_batch_ui(m, v))

            try:
                result_text = self.app._call_gemini_api(img_path)
                with open(txt_path, "w", encoding="utf-8") as f:
                    f.write(result_text + "\n")
                logger.info("Batch transcription finished for %s [%s/%s]", pair["name"], i + 1, total)
            except Exception as e:
                errors += 1
                logger.exception("%s %s: %s", self.app.t["batch_worker_file_error"], pair["name"], e)

            self.app.root.after(0, lambda item_idx=idx: self.refresh_batch_item_ui(item_idx))

        self._finish_batch(window, btn_start, btn_cancel_batch, processed_count, total, errors)

    def _parallel_batch_worker(self, selected_indices, window, btn_start, btn_cancel_batch, workers):
        total = len(selected_indices)
        errors = 0
        processed_count = 0
        next_index = 0
        futures = {}

        def submit_next(executor):
            nonlocal next_index
            if next_index >= total or self.app.stop_batch_flag:
                return
            idx = selected_indices[next_index]
            ordinal = next_index + 1
            next_index += 1
            futures[executor.submit(self._process_one_file, idx, ordinal, total)] = idx

        with ThreadPoolExecutor(max_workers=workers) as executor:
            for _ in range(min(workers, total)):
                submit_next(executor)

            while futures:
                if self.app.stop_batch_flag or not window.winfo_exists():
                    for future in futures:
                        future.cancel()
                    break

                done, _pending = wait(futures, timeout=0.2, return_when=FIRST_COMPLETED)
                if not done:
                    continue

                for future in done:
                    idx = futures.pop(future)
                    processed_count += 1
                    try:
                        future.result()
                    except Exception as e:
                        errors += 1
                        pair = self.app.file_pairs[idx]
                        logger.exception("%s %s: %s", self.app.t["batch_worker_file_error"], pair["name"], e)

                    progress_pct = (processed_count / total) * 100 if total else 100
                    status_msg = (
                        self.app.t["batch_process_text"]
                        + f" [{processed_count}/{total}]"
                    )
                    self.app.root.after(0, lambda m=status_msg, v=progress_pct: self.update_batch_ui(m, v))
                    self.app.root.after(0, lambda item_idx=idx: self.refresh_batch_item_ui(item_idx))
                    submit_next(executor)

        self._finish_batch(window, btn_start, btn_cancel_batch, processed_count, total, errors)

    def _finish_batch(self, window, btn_start, btn_cancel_batch, processed_count, total, errors):
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
            if progress_value is not None:
                self.app.batch_progress["value"] = progress_value
        except Exception as e:
            print(e)
