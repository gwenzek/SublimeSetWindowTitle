import sublime

import os
from sublime_plugin import EventListener

WAS_DIRTY = "set_window_name_was_dirty"

class SetWindowTitle(EventListener):

  settings = sublime.load_settings("set_window_title.sublime-settings")
  SCRIPT_PATH = os.path.join(
        sublime.packages_path(),
        "SetWindowTitle",
        "fix_window_title.sh")
  TEMPLATE = settings.get('template')
  HAS_PROJECT_TRUE = settings.get('has_project_true')
  HAS_PROJECT_FALSE = settings.get('has_project_false')
  IS_DIRTY_TRUE = settings.get('is_dirty_true')
  IS_DIRTY_FALSE = settings.get('is_dirty_false')
  UNTITLED = settings.get('untitled')

  DEBUG = settings.get('debug')

  def on_activated_async(self, view):
    self.run(view)

  def on_modified_async(self, view):
    if view.settings().get(WAS_DIRTY, None) != view.is_dirty():
      self.run(view)

  def on_post_save_async(self, view):
    self.run(view)

  def run(self, view):
    view_name = view.name() or view.file_name()
    project = self.get_project(view)

    official_title = self.get_official_title(view, view_name, project)
    window_name = self.get_new_title(view, view_name, project)
    self.rename_window(official_title, window_name)
    view.settings().set(WAS_DIRTY, view.is_dirty())

  def get_project(self, view):
    project = view.window().project_file_name()
    if not project:
      folders = view.window().folders()
      project = folders[0] if folders else ''
    if project:
      project = os.path.basename(project)
      project = os.path.splitext(project)[0]

    return project

  def get_official_title(self, view, view_name, project):
    """
    Returns the official name for a given view.

    /!\ The full file path isn't computed,
    because ST uses `~` to shorten the path.
    """
    official_title = os.path.basename(view_name) if view_name else "untitled"
    if view.is_dirty():
      official_title += " •"
    if project:
      official_title += " (%s)" % project
    official_title += " - Sublime Text"
    return official_title

  def get_new_title(self, view, view_name, project):
    """
    Returns the new name for a given view, according to the user preferences.
    """
    full_path = view_name
    folders = view.window().folders()
    root = folders[0] if folders else None
    if root and view_name:
      rel_path = os.path.relpath(view_name, root)
    if not view_name:
      full_path = self.UNTITLED
      rel_path = self.UNTITLED

    has_project = _format_condition(
        project, self.HAS_PROJECT_TRUE, self.HAS_PROJECT_FALSE,
        rel_path=rel_path, full_path=full_path, project=project)
    is_dirty = _format_condition(
        view.is_dirty(), self.IS_DIRTY_TRUE, self.IS_DIRTY_FALSE,
        rel_path=rel_path, full_path=full_path, project=project)

    return self.TEMPLATE.format(
        has_project=has_project, is_dirty=is_dirty,
        rel_path=rel_path, full_path=full_path, project=project)

  def rename_window(self, official_title, new_title):
    """Rename a subl window using the fix_window_title.sh script."""
    cmd = 'bash %s "%s" "%s"' % (
        self.SCRIPT_PATH, official_title, new_title)
    if self.DEBUG:
      print('$', cmd)
    output = os.popen(cmd + " 1&2").read()
    if self.DEBUG:
      print(output)

def _format_condition(condition, template_true, template_false, **kwargs):
  template = template_true if condition else template_false
  if template:
    return template.format(**kwargs)
