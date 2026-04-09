import ttkbootstrap as ttk

from ui.editor_window import ManuscriptEditor


def create_app_window():
    return ttk.Window(themename="journal", className="ScansAndTranscriptions")


def create_main_window():
    app_window = create_app_window()
    app = ManuscriptEditor(app_window)
    return app_window, app


def launch():
    app_window, _app = create_main_window()
    app_window.mainloop()
