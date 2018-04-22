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
    view = FakeView("SecretProject", root, filename)

    self.assertEqual("hacking_like_a_boss.py", swt._pretty_path(view, settings))

  @with_windows_os_path
  def test_rel_path_on_different_drive(self):
    settings = {"path_display": "relative"}
    root = "C:/home/hacker/Github/Project"
    filename = "D:/somewhere_else/hacking_like_a_boss.py"
    view = FakeView("SecretProject", root, filename)

    self.assertEqual(filename, swt._pretty_path(view, settings))

  def test_rel_path_outside_of_project(self):
    settings = {"path_display": "relative"}
    filename = "/home/hacker/Github/Project/hacking_like_a_boss.py"
    view = FakeView("SecretProject", None, filename)

    self.assertEqual("~/Github/Project/hacking_like_a_boss.py",
                     swt._pretty_path(view, settings))

  def test_use_view_name_when_available(self):
    settings = {"path_display": "full"}
    root = "/home/hacker/Github/Project"
    filename = "/home/hacker/Github/Project/hacking_like_a_boss.py"
    name = "H4CK3D"
    view = FakeView("SecretProject", root, filename, name)

    self.assertEqual(name, swt._pretty_path(view, settings))

  def test_full_path(self):
    settings = {"path_display": "full"}
    root = "/home/hacker/Github/Project"
    filename = "/home/hacker/Github/Project/hacking_like_a_boss.py"
    view = FakeView("SecretProject", root, filename)

    self.assertEqual("~/Github/Project/hacking_like_a_boss.py",
                     swt._pretty_path(view, settings))

  def test_full_path_abb(self):
    settings = {"path_display": "full"}
    root = "/home/hacker/Github/Project"
    filename = "/home/hacker/Github/Project/hacking_like_a_boss.py"
    view = FakeView("SecretProject", root, filename)

    self.assertEqual("~/Github/Project/hacking_like_a_boss.py",
                     swt._pretty_path(view, settings))

  def test_shortest_path_chooses_full(self):
    settings = {"path_display": "shortest"}
    root = "/home/hacker/Github/Project"
    filename = "/home/hacker/another_place/hacking_like_a_boss.py"
    view = FakeView("SecretProject", root, filename)

    self.assertEqual("~/another_place/hacking_like_a_boss.py",
                     swt._pretty_path(view, settings))

  def test_shortest_path_chooses_relative(self):
    settings = {"path_display": "shortest"}
    root = "/home/hacker/Github/Project"
    filename = "/home/hacker/Github/AnotherProject/hacking_like_a_boss.py"
    view = FakeView("SecretProject", root, filename)

    self.assertEqual("../AnotherProject/hacking_like_a_boss.py",
                     swt._pretty_path(view, settings))


class FakeView:

  def __init__(self, project_name, root_folder, file_name, name=None):
    self.project_name = project_name
    self.file_name_ = file_name
    self.name_ = name
    self.window_ = FakeWindow([root_folder] if root_folder else [])

  def name(self):
    return self.name_

  def file_name(self):
    return self.file_name_

  def window(self):
    return self.window_


class FakeWindow:
  def __init__(self, folder_list):
    self.folder_list = folder_list

  def folders(self):
    return self.folder_list


if __name__ == '__main__':
  unittest.main()
