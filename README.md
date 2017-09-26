## Overview

This plugin allows you to configure the title of your Sublime Text windows.
Every time you switch view, save a view, start editing a view,
it will update the window title.

## Installation

If you don't install this plugin through Package Control, ensure you name the
folder to `SetWindowTitle`.

## Requirement

This plugin assume you are using Linux and you have installed `xdotools`.
If you have any ideas on how to do that on MacOS or Windows, please submit a PR.

## Configuration

Please look at the [settings](./set_window_title.sublime-settings) to read the
documentation.

## Room for improvement

* Currently the bash script that modifies the window title needs the PID of the 
  target window. As there is no ST API for that, the script list all ST windows
  and rename the one with a name matching the expected name.
  If there was a reliable way to find the PID of the correct window then we could drop the `get_official_name` method, and simplify the script a lot.

* For some reason some chars aren't displayed correctly.
