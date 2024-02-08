import uc
import ucactions
import importlib
import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import os


def reload():
  importlib.reload(ucactions)


class MyHandler(FileSystemEventHandler):

  def on_modified(self, event):
    # Check if the modified file is the one we're interested in
    if event.src_path == ucactions.__file__:
      try:
        importlib.reload(ucactions)
        print('ucactions reloaded!')
      except Exception as e:
        print('Reloading failed... Waiting on a fix...')
        print(str(e))
      # print(f'Module file modified: {event.src_path}')


def start_watching(file_path):
  event_handler = MyHandler()
  observer = Observer()
  observer.schedule(event_handler, file_path, recursive=False)
  observer.start()
  print("ucaction.py thread started!")
  return observer  # Return the observer to manage it outside


def stop_watching(observer):
  observer.stop()
  observer.join()


# Set up and start the file watcher in a separate thread
def run_watcher_in_thread(module_file_path):
  observer = start_watching(module_file_path)
  watcher_thread = threading.Thread(target=stop_watching, args=(observer, ))
  watcher_thread.daemon = True  # Daemonize thread
  watcher_thread.start()


module_dir = os.path.dirname(ucactions.__file__)
observer = start_watching(module_dir)

driver = uc.get_driver()
