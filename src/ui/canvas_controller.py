import json
import os
import tkinter as tk
from tkinter import messagebox

from PIL import Image, ImageEnhance, ImageOps, ImageTk
import ttkbootstrap as ttk


class CanvasController:
    def __init__(self, app):
        self.app = app

    def apply_filter(self, mode):
        if not self.app.original_image:
            return
        self.app.active_filter = mode
        img = self.app.original_image.copy()

        if mode == "invert":
            if img.mode != "RGB":
                img = img.convert("RGB")
            img = ImageOps.invert(img)
        elif mode == "contrast":
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(2.0)
            img = ImageEnhance.Sharpness(img).enhance(1.5)

        self.app.processed_image = img
        self.redraw_image()

    def redraw_image(self):
        source_img = self.app.processed_image if self.app.processed_image else self.app.original_image
        if not source_img:
            return

        w = int(source_img.width * self.app.scale)
        h = int(source_img.height * self.app.scale)
        try:
            resized = source_img.resize((w, h), Image.Resampling.BILINEAR)
            self.app.tk_image = ImageTk.PhotoImage(resized)
            self.app.canvas.delete("all")
            self.app.canvas.create_image(self.app.img_x, self.app.img_y, image=self.app.tk_image, anchor="nw")
            self.app.zoom_label.config(text=f"Zoom: {int(self.app.scale * 100)}%")
        except Exception as e:
            print(self.app.t["msg_redraw_error"] + f": {e}")

    def fit_to_width(self):
        if not self.app.original_image:
            return

        self.app.canvas.delete("ner_box")
        canvas_w = self.app.canvas.winfo_width()
        if canvas_w > 1:
            self.app.scale = (canvas_w - 10) / self.app.original_image.width
            self.app.img_x, self.app.img_y = 0, 0
            self.redraw_image()

    def on_mouse_down(self, event):
        self.app.last_mouse_x = event.x
        self.app.last_mouse_y = event.y

    def on_mouse_drag(self, event):
        dx = event.x - self.app.last_mouse_x
        dy = event.y - self.app.last_mouse_y
        self.app.img_x += dx
        self.app.img_y += dy
        self.app.canvas.move("all", dx, dy)
        self.app.last_mouse_x = event.x
        self.app.last_mouse_y = event.y

    def on_mouse_wheel(self, event):
        factor = 0.9 if (event.num == 4 or event.delta > 0) else 1.1
        self.app.scale *= factor
        self.app.scale = max(self.app.scale, 0.05)
        self.app.scale = min(self.app.scale, 10.0)
        self.redraw_image()

    def show_magnifier(self, event):
        if not self.app.original_image:
            return

        self.app.MAG_WIDTH, self.app.MAG_HEIGHT = 750, 300
        self.app.ZOOM_FACTOR = 2.0

        self.app.magnifier_win = tk.Toplevel(self.app.root)
        self.app.magnifier_win.overrideredirect(True)
        self.app.magnifier_win.attributes("-topmost", True)

        frame = ttk.Frame(self.app.magnifier_win, bootstyle="info", padding=2)
        frame.pack(fill=tk.BOTH, expand=True)
        self.app.mag_label = ttk.Label(frame, background="white")
        self.app.mag_label.pack(fill=tk.BOTH, expand=True)

        self.update_magnifier(event)

    def update_magnifier(self, event):
        if not self.app.magnifier_win or not self.app.original_image:
            return

        src = self.app.processed_image if self.app.processed_image else self.app.original_image

        pos_x = int(event.x_root - (self.app.MAG_WIDTH / 2))
        pos_y = int(event.y_root - (self.app.MAG_HEIGHT / 2))
        self.app.magnifier_win.geometry(f"{self.app.MAG_WIDTH}x{self.app.MAG_HEIGHT}+{pos_x}+{pos_y}")

        orig_x = (event.x - self.app.img_x) / self.app.scale
        orig_y = (event.y - self.app.img_y) / self.app.scale

        crop_w = self.app.MAG_WIDTH / self.app.ZOOM_FACTOR
        crop_h = self.app.MAG_HEIGHT / self.app.ZOOM_FACTOR

        x1, y1 = orig_x - (crop_w / 2), orig_y - (crop_h / 2)
        x2, y2 = x1 + crop_w, y1 + crop_h

        try:
            region = src.crop((x1, y1, x2, y2))
            magnified_img = region.resize((self.app.MAG_WIDTH, self.app.MAG_HEIGHT), Image.Resampling.BILINEAR)
            self.app.tk_mag_img = ImageTk.PhotoImage(magnified_img)
            self.app.mag_label.config(image=self.app.tk_mag_img)
        except Exception as e:
            print(e)

    def hide_magnifier(self, event):
        if self.app.magnifier_win:
            self.app.magnifier_win.destroy()
            self.app.magnifier_win = None
            self.app.tk_mag_img = None

    def draw_boxes_only(self, entities_data):
        self.app.canvas.delete("ner_box")
        self.app.box_to_data_map = {}
        orig_w, orig_h = self.app.original_image.width, self.app.original_image.height

        for i, item in enumerate(entities_data):
            name = item["name"]
            c = item["coords"]
            cat = item.get("category", "?")
            bg_color = self.app.category_colors.get(cat, "#fbfaf7")
            line_color = "#ff0000"

            x1 = (c[1] * orig_w / 1000) * self.app.scale + self.app.img_x
            y1 = (c[0] * orig_h / 1000) * self.app.scale + self.app.img_y
            x2 = (c[3] * orig_w / 1000) * self.app.scale + self.app.img_x
            y2 = (c[2] * orig_h / 1000) * self.app.scale + self.app.img_y

            entity_tag = f"box_{i}"

            self.app.canvas.create_rectangle(
                x1, y1, x2, y2,
                outline=line_color, width=3, fill=line_color, stipple="gray12",
                tags=("ner_box", entity_tag, "main_rect"),
            )

            text_id = self.app.canvas.create_text(
                x1, y1 - 2, text=f"{name}", anchor="sw",
                fill="black", font=("Segoe UI", 9, "bold"),
                tags=("ner_box", entity_tag, "label_text"),
            )

            bbox = self.app.canvas.bbox(text_id)
            bg_id = self.app.canvas.create_rectangle(
                bbox, fill=bg_color, outline=line_color,
                tags=("ner_box", entity_tag, "label_bg"),
            )
            self.app.canvas.tag_raise(text_id, bg_id)

            h_size = 4
            self.app.canvas.create_rectangle(
                x2 - h_size, y2 - h_size, x2 + h_size, y2 + h_size,
                fill="white", outline=line_color, width=1,
                tags=("ner_box", entity_tag, "resize_handle"),
            )

            self.app.canvas.tag_bind(entity_tag, "<Button-1>", lambda e, t=entity_tag: self.on_box_press(e, t))
            self.app.canvas.tag_bind(entity_tag, "<B1-Motion>", self.on_box_drag)
            self.app.canvas.tag_bind(entity_tag, "<ButtonRelease-1>", self.on_box_release)
            self.app.canvas.tag_bind(entity_tag, "<Control-Button-1>", lambda e, t=entity_tag: self.on_box_delete(e, t))
            self.app.canvas.tag_bind(entity_tag, "<Motion>", lambda e, t=entity_tag: self.on_box_hover(e, t))

            self.app.box_to_data_map[entity_tag] = i

    def on_box_hover(self, event, entity_tag):
        item_under_mouse = self.app.canvas.find_closest(event.x, event.y)[0]
        tags = self.app.canvas.gettags(item_under_mouse)

        if "resize_handle" in tags:
            self.app.canvas.config(cursor=self.app.cursor_resizing)
        else:
            self.app.canvas.config(cursor=self.app.cursor_move)
        return "break"

    def on_box_drag(self, event):
        if not hasattr(self.app, "active_box_tag") or self.app.active_box_tag is None:
            return

        dx = event.x - self.app.last_mouse_x
        dy = event.y - self.app.last_mouse_y
        items = self.app.canvas.find_withtag(self.app.active_box_tag)

        rect_id = None
        handle_id = None
        for item in items:
            tags = self.app.canvas.gettags(item)
            if "resize_handle" in tags:
                handle_id = item
            elif "main_rect" in tags:
                rect_id = item

        if self.app.box_action == "move":
            self.app.canvas.move(self.app.active_box_tag, dx, dy)
        elif self.app.box_action == "resize" and rect_id and handle_id:
            coords = self.app.canvas.coords(rect_id)
            new_x2 = max(coords[0] + 10, event.x)
            new_y2 = max(coords[1] + 10, event.y)
            self.app.canvas.coords(rect_id, coords[0], coords[1], new_x2, new_y2)
            h_s = 4
            self.app.canvas.coords(handle_id, new_x2 - h_s, new_y2 - h_s, new_x2 + h_s, new_y2 + h_s)

        self.app.last_mouse_x = event.x
        self.app.last_mouse_y = event.y
        return "break"

    def on_box_release(self, event):
        tag = getattr(self.app, "active_box_tag", None)
        if not tag:
            return

        items = self.app.canvas.find_withtag(tag)
        rect_id = None
        for item in items:
            if "main_rect" in self.app.canvas.gettags(item):
                rect_id = item
                break

        if rect_id:
            coords = self.app.canvas.coords(rect_id)
            orig_w = self.app.original_image.width
            orig_h = self.app.original_image.height

            x1_model = int(((coords[0] - self.app.img_x) / self.app.scale) * 1000 / orig_w)
            y1_model = int(((coords[1] - self.app.img_y) / self.app.scale) * 1000 / orig_h)
            x2_model = int(((coords[2] - self.app.img_x) / self.app.scale) * 1000 / orig_w)
            y2_model = int(((coords[3] - self.app.img_y) / self.app.scale) * 1000 / orig_h)

            json_path = self.app._get_ner_json_path()
            if json_path and os.path.exists(json_path):
                try:
                    with open(json_path, "r", encoding="utf-8") as f:
                        cache_data = json.load(f)

                    idx = self.app.box_to_data_map[tag]
                    cache_data["coordinates"][idx]["coords"] = [y1_model, x1_model, y2_model, x2_model]

                    with open(json_path, "w", encoding="utf-8") as f:
                        json.dump(cache_data, f, ensure_ascii=False, indent=4)
                except Exception as e:
                    print(self.app.t["msg_json_save_error"] + f": {e}")

        self.app.canvas.config(cursor="")
        self.app.active_box_tag = None
        self.app.box_action = None

    def on_box_delete(self, event, entity_tag):
        idx = self.app.box_to_data_map.get(entity_tag)
        if idx is None:
            return

        json_path = self.app._get_ner_json_path()
        if json_path and os.path.exists(json_path):
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    cache_data = json.load(f)

                if "coordinates" in cache_data:
                    cache_data["coordinates"].pop(idx)
                    with open(json_path, "w", encoding="utf-8") as f:
                        json.dump(cache_data, f, ensure_ascii=False, indent=4)
                    self.draw_boxes_only(cache_data["coordinates"])
            except Exception as e:
                messagebox.showerror(
                    self.app.t["msg_error_title"],
                    self.app.t["msg_json_update_error"] + f": {e}",
                )

    def on_box_press(self, event, entity_tag):
        self.app.active_box_tag = entity_tag
        self.app.last_mouse_x = event.x
        self.app.last_mouse_y = event.y

        item_under_mouse = self.app.canvas.find_closest(event.x, event.y)[0]
        tags = self.app.canvas.gettags(item_under_mouse)

        if "resize_handle" in tags:
            self.app.box_action = "resize"
            self.app.canvas.config(cursor=self.app.cursor_resizing)
        else:
            self.app.box_action = "move"
            self.app.canvas.config(cursor=self.app.cursor_move)

        return "break"
