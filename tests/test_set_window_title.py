import ntpath
import os
import sys
import unittest
from unittest import mock

swt = sys.modules["SetWindowTitle.set_window_title"]


def with_windows_os_path(fun):
  """Replace os.path methods by their Windows specific implementation."""
  os_path_api = os.path.__all__
  def patched_fn(os_path_mock, args):
    for method in os_path_api:
      windows_method = getattr(ntpath, method, None)
      if windows_method:
        os_path_mock.__setattr__(method, windows_method)
    fun(args)
  return mock.patch("os.path")(patched_fn)


class TestStringMethods(unittest.TestCase):

  def setUp(self):
    os.environ["HOME"] = "/home/hacker"

  def test_same_drive_on_linux(self):
    self.assertTrue(swt._same_drive("/home/hacker/Github/Project",
                                    "/home/hacker/Github/AnotherProject"))

  @with_windows_os_path
  def test_same_drive_on_windows(self):
    self.assertTrue(swt._same_drive("c:/home/hacker/Github/Project",
                                    "c:/home/hacker/Github/AnotherProject"))
    self.assertFalse(swt._same_drive("c:/home/hacker/Github/Project",
                                     "d:/home/hacker/Github/AnotherProject"))

  def test_rel_path(self):
    settings = {"path_display": "relative"}
    root = "/home/hacker/Github/Project"
    filename = "/home/hacker/Github/Project/hacking_like_a_boss.py"
    view = FakeView(filename, root)

    self.assertEqual("hacking_like_a_boss.py", swt._pretty_path(view, settings))

  @with_windows_os_path
  def test_rel_path_on_different_drive(self):
    settings = {"path_display": "relative"}
    root = "C:/home/hacker/Github/Project"
    filename = "D:/somewhere_else/hacking_like_a_boss.py"
    view = FakeView(filename, root)

    self.assertEqual(filename, swt._pretty_path(view, settings))

  def test_rel_path_outside_of_project(self):
    settings = {"path_display": "relative"}
    root = "/home/hacker/Github/Project"
    filename = "/home/hacker/Github/AnotherProject/hacking_for_dummies.py"
    view = FakeView(filename, root)

    self.assertEqual("../AnotherProject/hacking_for_dummies.py",
                     swt._pretty_path(view, settings))

  def test_use_view_name_when_available(self):
    settings = {"path_display": "full"}
    filename = "/home/hacker/Github/Project/hacking_like_a_boss.py"
    name = "H4CK3D"
    view = FakeView(filename, name=name)

    self.assertEqual(name, swt._pretty_path(view, settings))

  def test_full_path(self):
    settings = {"path_display": "full"}
    root = "/home/hacker/Github/Project"
    filename = "/home/hacker/Github/Project/hacking_like_a_boss.py"
    view = FakeView(filename, root)

    self.assertEqual("~/Github/Project/hacking_like_a_boss.py",
                     swt._pretty_path(view, settings))

  def test_shortest_path_chooses_full(self):
    settings = {"path_display": "shortest"}
    root = "/home/hacker/Github/Project"
    filename = "/home/hacker/another_place/hacking_like_a_boss.py"
    view = FakeView(filename, root)

    self.assertEqual("~/another_place/hacking_like_a_boss.py",
                     swt._pretty_path(view, settings))

  def test_shortest_path_chooses_relative(self):
    settings = {"path_display": "shortest"}
    root = "/home/hacker/Github/Project"
    filename = "/home/hacker/Github/AnotherProject/hacking_like_a_boss.py"
    view = FakeView(filename, root)

    self.assertEqual("../AnotherProject/hacking_like_a_boss.py",
                     swt._pretty_path(view, settings))

  def test_official_title(self):
    settings = {}
    view = FakeView("/home/hacker/Github/Project/hacking_like_a_boss.py")

    self.assertEqual("hacking_like_a_boss.py (Project) - Sublime Text",
                     swt.get_official_title(view, "Project", settings))

  def test_new_title(self):
    settings = {
        "path_display": "relative",
        "template": "({project}) {path} - ST"
    }
    root = "/home/hacker/Github/Project"
    filename = "/home/hacker/Github/Project/hacking_like_a_boss.py"
    view = FakeView(filename, root)

    self.assertEqual("(Project) hacking_like_a_boss.py - ST",
                     swt.get_new_title(view, "Project", settings))

  def test_new_title_with_has_project(self):
    settings = {
        "path_display": "relative",
        "template": "{has_project} {path} - ST",
        "has_project_false": "!!!",
        "has_project_true": "({project})"
    }
    root = "/home/hacker/Github/Project"
    filename = "/".join([root, "hacking_like_a_boss.py"])
    view = FakeView(filename, root)

    self.assertEqual("(Project) hacking_like_a_boss.py - ST",
                     swt.get_new_title(view, "Project", settings))

    self.assertEqual("!!! hacking_like_a_boss.py - ST",
                     swt.get_new_title(view, None, settings))


class FakeView:

  def __init__(
      self,
      file_name,
      root_folder=None,
      name=None,
      dirty=False):
    self.file_name_ = file_name
    self.window_ = FakeWindow([root_folder] if root_folder else [])
    self.name_ = name
    self.dirty_ = dirty

  def name(self):
    return self.name_

  def file_name(self):
    return self.file_name_

  def window(self):
    return self.window_

  def is_dirty(self):
    return self.dirty_


class FakeWindow:
  def __init__(self, folder_list):
    self.folder_list = folder_list

  def folders(self):
    return self.folder_list


if __name__ == '__main__':
  unittest.main()
