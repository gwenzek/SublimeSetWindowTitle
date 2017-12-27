## Overview

This plugin allows you to configure the title of your Sublime Text windows.
Every time you switch view, save a view, start editing a view,
it will update the window title.

## Installation

This package is avalaible on [PackageControl](https://packagecontrol.io/).

## Requirement

On Windows it should work out of the box.
On Linux the plugin assume you have installed `xdotool`.
If you have any ideas on how to do that on MacOS, please submit a PR.

## Configuration

Please look at the [settings](./set_window_title.sublime-settings) to read the
documentation.

## Room for improvement

* Currently the code that modifies the window title needs the PID of the 
  target window. As there is no ST API for that, we list all ST windows and
  rename the one with a name matching the expected name.
  If there was a reliable way to find the PID of the correct window then we
  could drop the `get_official_name` method, and simplify the plugin a lot.

* (Linux) For some reason some chars aren't displayed correctly.

* (Windows) The plugin is more brittle on Windows, some features have been
disabled as a consequence. If you have knowledge of the `user32` API we might
use your help !

## Thanks

Thanks to [cjdoris](https://github.com/cjdoris) for implementing Windows support.
