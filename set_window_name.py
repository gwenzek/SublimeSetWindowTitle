import sublime

import os
from sublime_plugin import EventListener


class SetWindowName(EventListener):

  settings = sublime.load_settings("set_window_name.sublime-settings")
  SCRIPT_PATH = os.path.join(
      sublime.packages_path(),
      "SetWindowName",
      "fix_st_title.sh")
  PROJECT_PREFIX = settings.get('project_prefix')
  GENERIC_SUFFIX = settings.get('generic_suffix')
  IGNORE_EMPTY_PROJECT = settings.get('ignore_empty_project')
  USE_REL_PATH = settings.get('use_rel_path')
  DEBUG = settings.get('debug')

  def on_activated_async(self, view):

    view_name = view.name() or view.file_name()
    project = self.get_project_name(view)

    official_name = self.get_official_name(view, view_name, project)
    window_name = self.get_new_name(view, view_name, project)
    self.rename_window(official_name, window_name)

  def get_project_name(self, view):
    project = view.window().project_file_name() or ''
    if project:
      project = os.path.basename(project)
      project = os.path.splitext(project)[0]

    return project

  def get_official_name(self, view, view_name, project_name):
    """
    Returns the official name for a given view.

    /!\ The full file path isn't computed,
    because ST uses `~` to shorten the path.
    """
    official_name = os.path.basename(view_name) if view_name else "untitled"
    if view.is_dirty():
      official_name += " •"
    if project_name:
      official_name += " (%s)" % project_name
    official_name += " - Sublime Text"
    return official_name

  def get_new_name(self, view, view_name, project_name):
    """
    Returns the new name for a given view, according to the user preferences.
    """
    if view_name and self.USE_REL_PATH:
      folders = view.window().folders()
      root = folders[0] if folders else None
      if root:
        view_name = os.path.relpath(view_name, root)
    if not view_name:
      view_name = 'untitled'
    print("view_name:", view_name)

    project_prefix = ''
    generic_suffix = self.GENERIC_SUFFIX
    if project_name or not self.IGNORE_EMPTY_PROJECT:
      project_prefix = self.PROJECT_PREFIX.format(project=project_name)

    return ''.join([project_prefix, view_name, generic_suffix])

  def rename_window(self, official_name, new_name):
    """Rename a subl window using the fix_st_title.sh script."""
    if self.DEBUG:
      print("pid", os.getpid())
      print("ppid", os.getppid())
      print("renaming window  '%s' to '%s'" % (official_name, new_name))

    cmd = 'bash %s "%s" "%s"' % (
        self.SCRIPT_PATH, official_name, new_name)
    if self.DEBUG:
      print('$', cmd)
    output = os.popen(cmd + " 1&2").read()
    if self.DEBUG:
      print(output)
