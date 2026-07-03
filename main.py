import os
import traceback

os.environ.setdefault("KIVY_NO_FILELOG", "1")

from kivy.app import App
from kivy.core.window import Window
from kivy.uix.screenmanager import ScreenManager

from app.screens.editor_screen import EditorScreen
from app.screens.home_screen import HomeScreen
from app.services.file_service import FileServiceError, load_workbook, save_workbook


class MobileXLApp(App):
    title = "Mobile XL"

    def build(self):
        try:
            Window.softinput_mode = "resize"
        except Exception:
            pass

        self.workbook = None
        self.current_path = None

        self.manager = ScreenManager()
        self.home_screen = HomeScreen(name="home")
        self.editor_screen = EditorScreen(name="editor")
        self.manager.add_widget(self.home_screen)
        self.manager.add_widget(self.editor_screen)
        return self.manager

    def open_workbook(self, path):
        try:
            self.workbook = load_workbook(path)
            self.current_path = path
        except FileServiceError as exc:
            message = str(exc)
            self.home_screen.show_message(message)
            self.manager.current = "home"
            return False, message
        except Exception as exc:
            message = "".join(traceback.format_exception_only(type(exc), exc)).strip()
            self.home_screen.show_message(message)
            self.manager.current = "home"
            return False, message

        self.editor_screen.set_workbook(self.workbook)
        self.manager.current = "editor"
        return True, "File loaded successfully."

    def save_current_workbook(self, path=None):
        if not self.workbook:
            return False, "No workbook is open."

        target_path = path or self.current_path
        if not target_path:
            return False, "Choose Save As for a new file."

        try:
            save_workbook(self.workbook, target_path)
        except FileServiceError as exc:
            return False, str(exc)

        self.current_path = target_path
        self.workbook.path = target_path
        self.workbook.dirty = False
        self.editor_screen.refresh_title()
        return True, "Saved."


if __name__ == "__main__":
    MobileXLApp().run()
