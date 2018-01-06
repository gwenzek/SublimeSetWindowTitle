import sublime

import os
import time
from sublime_plugin import EventListener

WAS_DIRTY = "set_window_title_was_dirty"
PLATFORM = sublime.platform()

if PLATFORM == 'linux':
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
elif PLATFORM == 'windows':

  class Window:
    import ctypes as c
    u = c.windll.user32
    init_user32_done = False
    HWND = c.c_void_p
    LPARAM = c.c_void_p
    WNDENUMPROC = c.WINFUNCTYPE(c.c_bool, HWND, LPARAM)
    LPCWSTR = c.POINTER(c.c_uint16)

    def __init__(self, handle):
      self.handle = handle
      self.init_user32()

    def __str__(self):
      return "Window"

    def __repr__(self):
      return "Window({})".format(self.handle)

    @property
    def title(self):
      # Windows encodes window titles as an array of uint16s under UTF-16
      # To convert this to python, we cast this to an array of bytes, then decode it
      n = self.u.GetWindowTextLengthW(self.handle)
      t = (self.c.c_uint16 * (n+1))()
      n2 = self.u.GetWindowTextW(self.handle, t, n+1)
      assert n == n2
      return self.c.POINTER(self.c.c_char)(t)[0:n2*2].decode('utf16')

    @title.setter
    def title(self, title):
      b = title.encode('utf16')
      n = len(b)
      t = (self.c.c_char * (n+10))(*b)
      self.u.SetWindowTextW(self.handle, self.LPCWSTR(t))

    @classmethod
    def list_all(cls):
      handles = []
      def cb(handle, x):
        handles.append(handle)
        return True
      cls.u.EnumWindows(cls.WNDENUMPROC(cb), None)
      return [cls(handle) for handle in handles]

    @classmethod
    def init_user32(cls):
      if not cls.init_user32_done:
        cls.u.EnumWindows.argtypes = [cls.WNDENUMPROC, cls.LPARAM]
        cls.u.EnumWindows.restype = cls.c.c_bool
        cls.u.GetWindowTextLengthW.argtypes = [cls.HWND]
        cls.u.GetWindowTextLengthW.restype = cls.c.c_int
        cls.u.GetWindowTextW.argtypes = [cls.HWND, cls.LPCWSTR, cls.c.c_int]
        cls.u.GetWindowTextW.restype = cls.c.c_int
        cls.u.SetWindowTextW.argtypes = [cls.HWND, cls.LPCWSTR]
        cls.u.SetWindowTextW.restype = cls.c.c_bool
        cls.init_user32_done = True


_SCRIPT_PATH_ = None
_READY_ = False

def plugin_loaded():
  """Finds the script path and run the script for each window.

  Called by ST once this plugin has been fully loaded.
  """
  if PLATFORM == 'linux':
    global _SCRIPT_PATH_
    _SCRIPT_PATH_ = os.path.join(sublime.cache_path(),
                                 "list_window_with_title.sh")
    with open(_SCRIPT_PATH_, 'w') as o:
      o.write(SCRIPT)

  global _READY_
  _READY_ = True

  if PLATFORM == 'linux':
    # Set the title when the plugin is loaded.
    # Only enabled on Linux because for some reason it freezes ST on Windows.
    # TODO: Find how to enable a similar behavior on Windows.
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

    project = self.get_project(view)

    official_title = self.get_official_title(view, project)
    new_title = self.get_new_title(view, project, official_title)
    self.rename_window(view.window(), official_title, new_title)
    view.settings().set(WAS_DIRTY, view.is_dirty())

  def get_project(self, view):
    project = None
    window = view.window()
    if not window:
      return

    project = window.project_file_name()
    if not project:
      folders = window.folders()
      project = folders[0] if folders else ""
    if project:
      project = os.path.basename(project)
      project = os.path.splitext(project)[0]

    return project

  def get_official_title(self, view, project):
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
    settings = sublime.load_settings("set_window_title.sublime-settings")
    if settings.get("unregistered", False):
      official_title += " (UNREGISTERED)"

    return official_title

  def get_new_title(self, view, project, old_title):
    """Returns the new name for a view, according to the user preferences."""
    settings = sublime.load_settings("set_window_title.sublime-settings")

    path = self._pretty_path(view, settings)

    template = settings.get("template")
    template = self._replace_condition(template, "has_project", project,
                                       settings)
    template = self._replace_condition(template, "is_dirty",
                                       view.is_dirty(), settings)
    new_title = template.format(path=path, project=project)
    if settings.get("unregistered", False):
      new_title += " (UNREGISTERED)"
    return new_title

  def _pretty_path(self, view, settings):
    view_name = view.name()
    # view.name() is set by other plugins so it's probably the best choice.
    if view_name:
      return view_name

    full_path = view.file_name()
    if not full_path:
      return settings.get("untitled", "untitled")

    display = settings.get("path_display")
    if display in ("full", "shortest"):
      home = os.environ.get("HOME")
      if home and full_path.startswith(home):
        full_path = "~" + full_path[len(home):]

    if display in ("relative", "shortest"):
      window = view.window()
      folders = window.folders() if window else None
      root = folders[0] if folders else None
      rel_path = os.path.relpath(full_path, root) if root else full_path

    if display == "full":
      return full_path
    elif display == "relative":
      return rel_path
    else:  # default to "shortest"
      return full_path if len(full_path) <= len(rel_path) else rel_path

  def _replace_condition(self, template, condition, value, settings):
    if value:
      replacement = settings.get(condition + "_true")
    else:
      replacement = settings.get(condition + "_false")
    return template.replace("{%s}" % condition, replacement)

  def rename_window(self, window, official_title, new_title):
    """Rename a subl window using the fix_window_title.sh script."""
    if not window:
      return
    settings = sublime.load_settings("set_window_title.sublime-settings")
    debug = settings.get("debug")
    if PLATFORM == 'linux':
      self.rename_window_linux(window, official_title, new_title, debug)
    elif PLATFORM == 'windows':
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
          for line in os.popen(cmd).read().split('\n')
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
      for w in Window.list_all():
        if w.title.endswith(official_title):
          w.title = new_title
          # TODO: Understand why caching the windows handle cause crashes.
          # self.window_handle_cache[window.id()] = w
    else:
      w.title = new_title
