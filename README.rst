PluginDebugger
==============

This package contains some little glue code to use nice Winpdb_ graphical 
python debugger for debugging sublime plugins.


Usage
-----

Here is a little python snippet of ``debug_example.py``::

    import sublime_plugin
    import sys

    class DebugExampleCommand(sublime_plugin.WindowCommand):

        def run(self, **kwargs):

            sys.stderr.write("started\n")
            i = 4
            import spdb ; spdb.start()
            z = 5


``spdb.start()``
    winpdb will be launched, if not yet launched from Plugin Debugger. 
    Each later call of this function sets a breakpoint.  If winpdb 
    (started from Plugin Debugger) has been terminated in between, it 
    will be restarted.

``spdb.setbreak()``
    sets a breakpoint.  You need to have to attached debug client for 
    using this.

.. note:: If you start winpdb manually, use **sublime** as password for
    finding scripts on localhost.



Install
-------

Install this Package using `Package Control`_. 

Additionally to this package you have to install Winpdb_ from http://winpdb.org/download/ (or ``apt-get install winpdb`` on debian-like systems).

.. _Winpdb: http://winpdb.org
.. _Package Control: http://sublime.wbond.net
.. _Preferences Editor: http://sublime.wbond.net/packages/Preferences%20Editor

Configuration
-------------

The only configuration option is ``plugin_debugger_python``, which can be
set in your User Settings file ``Packages/User/Preferences.sublime-sttings``. 
This specifies the full path to your python installation, where you 
installed Winpdb_.  Please note, that this must be a python 2.x (2.7 
recommended).  You can also debug Python3 with this.

I recommend using `Preferences Editor`_ to set it ;) .



Test your installation
----------------------

Run "Plugin Debugger: run debug_example (opens Debugger)" from command 
palette.

Your sublime text will freeze for few seconds and then will open a winpdb 
window ready for debugging ``DebugExampleCommand``.

Module `rpdb2` havily hooks into python interpreter, so if you really want to 
quit the debug session, you have to restart your sublime text.

Once Winpdb has opened, you should keep it open, because it will inform you
on any uncaught exception.  If you close winpdb, your sublime simply freezes
on an uncaught exception (because it breaks on that exception), but you are 
not informed on this because of missing frontend.


Snippets
--------

There is a ``spdb`` snippet, which inserts::

    import spdb ; spdb.start(0)


Bugs
----

Please post bugs to https://bitbucket.org/klorenz/plugindebugger/issues.


Known Issues
~~~~~~~~~~~~

I tried to automatically unload rpdb2 library and undo all its hooking
into python system, but failed till now.

I also tried to get a nice status bar message about loading the Plugin 
Debugger using Package Control's thread_progress, but I did not manage yet
to run a thread unattended of the debugger yet (that it is not affected
by setbreak call).

For now I will stop working on automatic unloading, because restarting
sublime text after a debug session is fine for me (at least for now).


Changes
-------

2014-04-12
    - Add Python-3.3.3-Lib.zip, for correct display of pyhton lib debugging.
    - Handle now also all Packages files, even if in .sublime-package files.

2014-01-22
    - pre-import packages, which are imported by rpdb2, such that they are
      loaded from ST environment rather than from environment, where winpdb
      is installed

    - replace ``Plugin Debugger.sublime-settings`` by 
      ``Preferences.sublime-settings`` for easier settings handling.

    - run external python from temporary directory, to prevent to have 
      sublime text folder in modules path.

Author
------

Kay-Uwe (Kiwi) Lorenz <kiwi@franka.dyndns.org> (http://quelltexter.org)

Support my work on `Sublime Text Plugins`_: `Donate via Paypal`_

.. _Sublime Text Plugins:
    https://sublime.wbond.net/browse/authors/Kay-Uwe%20%28Kiwi%29%20Lorenz%20%28klorenz%29
    
.. _Donate via Paypal:
    https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=WYGR49LEGL9C8
