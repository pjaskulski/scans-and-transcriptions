BASE_SCREEN_WIDTH = 1920
BASE_SCREEN_HEIGHT = 1080
MAX_SCREEN_FRACTION = 0.92


def display_scale(widget, min_scale=1.0, max_scale=1.6):
    screen_width = widget.winfo_screenwidth()
    screen_height = widget.winfo_screenheight()
    scale = min(screen_width / BASE_SCREEN_WIDTH, screen_height / BASE_SCREEN_HEIGHT)
    return max(min_scale, min(max_scale, scale))


def scaled_size(widget, width, height):
    scale = display_scale(widget)
    return int(width * scale), int(height * scale)


def set_scaled_geometry(window, width, height, parent=None):
    scaled_width, scaled_height = scaled_size(window, width, height)
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()

    scaled_width = min(scaled_width, int(screen_width * MAX_SCREEN_FRACTION))
    scaled_height = min(scaled_height, int(screen_height * MAX_SCREEN_FRACTION))

    if parent:
        parent.update_idletasks()
        parent_x = parent.winfo_rootx()
        parent_y = parent.winfo_rooty()
        parent_width = parent.winfo_width()
        parent_height = parent.winfo_height()
        x = parent_x + max(0, (parent_width - scaled_width) // 2)
        y = parent_y + max(0, (parent_height - scaled_height) // 2)
    else:
        x = max(0, (screen_width - scaled_width) // 2)
        y = max(0, (screen_height - scaled_height) // 2)

    window.geometry(f"{scaled_width}x{scaled_height}+{x}+{y}")
    return scaled_width, scaled_height
