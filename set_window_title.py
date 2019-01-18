import sublime

import os
import time
from sublime_plugin import EventListener

WAS_DIRTY = "set_window_title_was_dirty"
PLATFORM = sublime.platform()

if PLATFORM == "linux":
  # xdotool script to find all windows pid matching a given name.
  # Note: it would be simpler if there was an API to get the pid
  # of a given Sublime window.
  SCRIPT = """
pids=$(xdotool search --class --onlyvisible subl)
for pid in $pids; do
    if [[ $(xdotool getwindowname $pid) == *"$1" ]]; then
        echo $pid
    fi
done
"""
elif PLATFORM == "windows":
  import ctypes
  HWND = ctypes.c_void_p
  LPARAM = ctypes.c_void_p
  WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, HWND, LPARAM)
  LPCWSTR = ctypes.POINTER(ctypes.c_uint16)

  def init_user32():
    user32 = ctypes.windll.user32
    user32.EnumWindows.argtypes = [WNDENUMPROC, LPARAM]
    user32.EnumWindows.restype = ctypes.c_bool
    user32.GetWindowTextLengthW.argtypes = [HWND]
    user32.GetWindowTextLengthW.restype = ctypes.c_int
    user32.GetWindowTextW.argtypes = [HWND, LPCWSTR, ctypes.c_int]
    user32.GetWindowTextW.restype = ctypes.c_int
    user32.SetWindowTextW.argtypes = [HWND, LPCWSTR]
    user32.SetWindowTextW.restype = ctypes.c_bool
    return user32

  USER_32 = init_user32()

  class Window:
    """Represents a window handle under Windows OS."""

    def __init__(self, handle):
      self.handle = handle

    def __str__(self):
      return "Window"

    def __repr__(self):
      return "Window({})".format(self.handle)

    @property
    def title(self):
      # Windows encodes window titles as an array of uint16s under UTF-16
      # To convert this to python, we cast this to an array of bytes,
      # then decode it
      n = USER_32.GetWindowTextLengthW(self.handle)
      t = (ctypes.c_uint16 * (n+1))()
      n2 = USER_32.GetWindowTextW(self.handle, t, n+1)
      assert n == n2
      return ctypes.POINTER(ctypes.c_char)(t)[0:n2*2].decode("utf16")

    @title.setter
    def title(self, title):
      b = title.encode("utf16")
      n = len(b)
      t = (ctypes.c_char * (n+10))(*b)
      USER_32.SetWindowTextW(self.handle, LPCWSTR(t))

  def list_all_windows():
    handles = []
    def cb(handle, _):
      handles.append(handle)
      return True
    USER_32.EnumWindows(WNDENUMPROC(cb), None)
    return [Window(handle) for handle in handles]


_SCRIPT_PATH_ = None
_READY_ = False


def plugin_loaded():
  """Finds the script path and run the script for each window.

  Called by ST once this plugin has been fully loaded.
  """
  if PLATFORM == "linux":
    global _SCRIPT_PATH_
    _SCRIPT_PATH_ = os.path.join(sublime.cache_path(),
                                 "list_window_with_title.sh")
    with open(_SCRIPT_PATH_, "w") as o:
      o.write(SCRIPT)

  global _READY_
  _READY_ = True

  # Update all window titles on setting change.
  settings = sublime.load_settings("set_window_title.sublime-settings")
  setting_keys = [
    "unregistered",
    "template",
    "has_project_true",
    "has_project_false",
    "is_dirty_true",
    "is_dirty_false",
    "path_display",
    "untitled",
  ]
  for k in setting_keys:
    settings.add_on_change(k, refresh_all)

  if PLATFORM == "linux":
    # Set the title when the plugin is loaded.
    # Only enabled on Linux because for some reason it freezes ST on Windows.
    # TODO: Find how to enable a similar behavior on Windows.
    refresh_all()


def refresh_all():
  title_setter = SetWindowTitle()
  for window in sublime.windows():
    title_setter.run(window.active_view())


class SetWindowTitle(EventListener):
  """Updates the window title when the selected view changes."""
  window_handle_cache = {}

  def on_activated_async(self, view):
    self.run(view)

  def on_modified_async(self, view):
    if view.settings().get(WAS_DIRTY, None) != view.is_dirty():
      self.run(view)

  def on_post_save_async(self, view):
    self.run(view)

  def run(self, view):
    if not _READY_:
      print("[SetWindowTitle] Info: ST haven't finished loading yet, skipping.")
      return

    settings = sublime.load_settings("set_window_title.sublime-settings")
    project = self.get_project(view)

    official_title = get_official_title(view, project, settings)
    new_title = get_new_title(view, project, settings)
    self.rename_window(view.window(), official_title, new_title, settings)
    view.settings().set(WAS_DIRTY, view.is_dirty())

  def get_project(self, view):
    project = None
    window = view.window()
    if not window:
      return

    project = window.project_file_name()
    if not project:
      folders = window.folders()
      project = ", ".join(get_folder_name(x) for x in folders) if folders else None
    else:
      project = get_folder_name(project)

    return project

  def rename_window(self, window, official_title, new_title, settings):
    """Rename a subl window using the fix_window_title.sh script."""
    if not window:
      return
    debug = settings.get("debug")
    if PLATFORM == "linux":
      self.rename_window_linux(window, official_title, new_title, debug)
    elif PLATFORM == "windows":
      self.rename_window_windows(window, official_title, new_title)

  def rename_window_linux(self, window, official_title, new_title, debug=False):
    pid = self.window_handle_cache.get(window.id())
    pids = [pid]
    if not pid:
      # Get pids of ST windows with a title similar to this one.
      if debug:
        print(
            "[SetWindowTitle] Debug: Looking for window '%s'" % official_title)
      cmd = 'bash "%s" "%s"' % (_SCRIPT_PATH_, official_title)
      pids = [
          int(line.strip())
          for line in os.popen(cmd).read().split("\n")
          if line
      ]
      if debug:
        print("[SetWindowTitle] Debug: pids found:", pids)

      # Cache if we found exactly one pid for this window.
      if len(pids) == 1:
        self.window_handle_cache[window.id()] = pids[0]
    elif debug:
      print("[SetWindowTitle] Debug: Using pid", pid, "for window", window.id())

    if pids:
      for pid in pids:
        # If all the window have the same title, then we can assume it's safe
        # to rename all of them with the new title. Also renaming will allow
        # to find the correct pids the next time ST will try to change the
        # title of one of the windows.
        output = os.popen('xdotool set_window --name "%s" %d 2>&1' % (
            new_title, pid)).read()
        if output:
          print("[SetWindowTitle] Error: Failure when renaming:", output)

  def rename_window_windows(self, window, official_title, new_title):
    w = self.window_handle_cache.get(window.id(), None)
    if w is None:
      for w in list_all_windows():
        if w.title.endswith(official_title):
          w.title = new_title
          # TODO: Understand why caching the windows handle cause crashes.
          # self.window_handle_cache[window.id()] = w
    else:
      w.title = new_title

def get_folder_name(path):
    return os.path.splitext( os.path.basename( path ) )[0]

def get_official_title(view, project, settings):
  """Returns the official name for a given view.

  Note: The full file path isn't computed,
  because ST uses `~` to shorten the path.
  """
  view_name = view.name() or view.file_name() or "untitled"
  official_title = os.path.basename(view_name)
  if view.is_dirty():
    official_title += " •"
  if project:
    official_title += " (%s)" % project
  official_title += " - Sublime Text"
  if settings.get("unregistered", False):
    official_title += " (UNREGISTERED)"

  return official_title


def get_new_title(view, project, settings):
  """Returns the new name for a view, according to the user preferences."""
  path = _pretty_path(view, settings)
  filename = (
      view.name()
      or os.path.basename(view.file_name() or "")
      or settings.get("untitled", "untitled"))

  template = settings.get("template")
  template = _replace_condition(template, "has_project", project, settings)
  template = _replace_condition(template, "is_dirty", view.is_dirty(), settings)
  new_title = template.format(path=path,
                              project=project or "",
                              file=filename)
  if settings.get("unregistered", False):
    new_title += " (UNREGISTERED)"
  return new_title


def _pretty_path(view, settings):
  """Computes a nice path to display for a given view."""
  view_name = view.name()
  # view.name() is set by other plugins so it's probably the best choice.
  if view_name:
    return view_name

  full_path = view.file_name()
  if not full_path:
    return settings.get("untitled", "untitled")

  home = os.environ.get("HOME")
  if home and full_path.startswith(home):
    full_path = "~" + full_path[len(home):]

  display = settings.get("path_display")
  if display in ("relative", "shortest"):
    window = view.window()
    folders = window.folders() if window else None
    root = folders[0] if folders else None

    # check that the two path are on the same drive.
    # Use the non shortened path to have the drive information.
    original_path = view.file_name()
    if root and _same_drive(original_path, root):
      rel_path = os.path.relpath(original_path, root)
    else:
      rel_path = full_path

  if display == "relative":
    return rel_path
  elif display == "shortest":
    return full_path if len(full_path) <= len(rel_path) else rel_path
  else:
    # default to "full", this one is always set.
    return full_path


def _same_drive(file1, file2):
  if not file1 or not file2:
    return False
  return os.path.splitdrive(file1)[0] == os.path.splitdrive(file2)[0]


def _replace_condition(template, condition, value, settings):
  if value:
    replacement = settings.get(condition + "_true")
  else:
    replacement = settings.get(condition + "_false")
  return template.replace("{%s}" % condition, replacement or "")
