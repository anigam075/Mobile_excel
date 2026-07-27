import threading

from kivy.clock import Clock


class BackgroundTask:
    def __init__(self):
        self.cancel_event = threading.Event()
        self.thread = None

    def cancel(self):
        self.cancel_event.set()


def run_in_background(work, on_success, on_error):
    task = BackgroundTask()

    def runner():
        try:
            result = work(task.cancel_event)
        except Exception as exc:
            Clock.schedule_once(lambda *_, error=exc: on_error(error), 0)
            return
        Clock.schedule_once(lambda *_, value=result: on_success(value), 0)

    task.thread = threading.Thread(target=runner, daemon=True)
    task.thread.start()
    return task
