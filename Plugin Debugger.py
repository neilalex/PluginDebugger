import os, sys, sublime, signal

try:
    from plugin_debugger import tools
    #from plugin_debugger.thread_progress import ThreadProgress

except ImportError:
    sys.stderr.write("importing tools\n")
    from .plugin_debugger import tools
    #from .plugin_debugger.thread_progress import ThreadProgress


ST3 = sublime.version() >= '3000'

# create a module alias
sys.modules['sublime_plugin_debugger'] = tools
sys.modules['spdb'] = tools

#def plugin_debugger_dir():
#    package_dir = sublime.packages_path()
#    p = os.path.join(package_dir, 'Plugin Debugger')
#    if not os.path.exists(p):
#        p = os.path.join(package_dir, 'PluginDebugger')
#    return p

#PLUGIN_DEBUGGER_DIR = plugin_debugger_dir()
#PLUGIN_DEBUGGER_LIB = os.path.join(plugin_debugger_dir(), 'lib')

#if sublime.version() < '3000':
    # make sure everyone can import sublime_plugin_debugger
    #if PLUGIN_DEBUGGER_LIB not in sys.path:
        #sys.path.append(PLUGIN_DEBUGGER_LIB)
    
import sublime_plugin_debugger
import sublime_plugin

if 0:
  class EnableDebuggerCommand(sublime_plugin.ApplicationCommand):

    def __init__(self, *args, **kargs):
        self.enabled = True

    def is_enabled(self):
        return self.enabled

#    def is_checked(self):
#        return g_debugger_enabled

    def run(self):
        if sublime_plugin_debugger.g_debugger_enabled:
            self.disable_debugger()
        else:
            self.enable_debugger()

    def description(self, *args, **kargs):
        if sublime_plugin_debugger.g_debugger_enabled:
            return "Disable Debugger"
        else:
            return "Enable Debugger"

    def on_debugger_enabled(self):
        self.enabled = True

    def on_debugger_disabled(self):
        self.enabled = True

    def enable_debugger(self):
        if sublime_plugin_debugger.g_debugger_enabled: return

        self.enabled = False
        t = sublime_plugin_debugger.enable(self.on_debugger_enabled)
        if t is not None:
            ThreadProgress(t, "Enabling debugger", "Debugger disabled")

    def disable_debugger(self):
        if not sublime_plugin_debugger.g_debugger_enabled: return

        self.enabled = False
        t = sublime_plugin_debugger.disable(self.on_debugger_disabled)
        if t is not None:
            ThreadProgress(t, "Disabling debugger", "Debugger disabled")


g_signal_signal    = None
g_signal_getsignal = None

def _my_signal(*args, **kargs):
    #sys.stderr.write("signal: args: %s, kargs: %s\n" % (args, kargs))
    g_signal_signal(*args, **kargs)

def _my_getsignal(*args, **kargs):
    # in python3 calling signal.getsignal(0) raises
    # ValueError: signal number out of range, so

    if args[0] == 0:
        return signal.SIG_IGN
        # SIG_IGN is ignored in rpdb2

    #sys.stderr.write("getsignal: args: %s, kargs: %s\n" % (args, kargs))
    g_signal_getsignal(*args, **kargs)


def _my_print_exc(*args, **kargs):
    try:
        g_traceback_print_exc(*args, **kargs)
    except:
        print("Exception: %s" % traceback.format_exc())

import traceback
g_traceback_print_exc = None

g_sys_stderr = None
g_sys_stdout = None

def show_console_panel():
    print("Hello World")

    import sublime
    w = sublime.active_window()
    if w:
        cprint("window")
        v = w.active_view()
        if v:
            cprint("veiw")
            settings = v.settings()
            name = 'plugin_debugger_show_console_on_exception'
            show_console = settings.get(name, False)
            if show_console:
                cprint("show console")
                w.run_command('show_panel', {'panel': 'console'})


class _MyLogWriter:
    def flush(self):
        pass

    def write(self, s):
        if "Traceback (most recent call last)" in s:
            show_console_panel()
        sublime_api.log_message(s)

def begin_module():
    global g_signal_signal
    global g_signal_getsignal
    global g_traceback_print_exc
    ##
    # rpdb2 overwrites rpdb2.g_builtins_module.__import__ (=> g_import)
    # sys.exc_info (=> g_sys_exc_info)
    # sys.setrecursionlimit (=> g_sys_setrecursionlimit)
    # signal.signal (g_signal_signal)
    # signal.getsignal (g_signal_getsignal)
    # os.fork (g_os_fork)
    # os.exit (g_os_exit)
    # os.close (g_os_close)
    # os.dup2  (g_os_dup2)
    # os.execv  (g_os_execv)
    # os.execve (g_os_execve)
    # thread.start_new_thread (g_thread_start_new_thread)
    #

    if g_signal_signal is None:
        g_signal_signal = signal.signal
        signal.signal = _my_signal

    if g_signal_getsignal is None:
        g_signal_getsignal = signal.getsignal
        signal.getsignal = _my_getsignal

    # global g_sys_stdout
    # global g_sys_stderr
    # if g_sys_stdout is None:
    #     g_sys_stdout = sys.stdout
    #     g_sys_stderr = sys.stderr
    #     sys.stdout = _MyLogWriter()
    #     sys.stderr = _MyLogWriter()

#    if g_traceback_print_exc is None:
#        g_traceback_print_exc = traceback.print_exc
#        traceback.print_exc = _my_print_exc


def end_module():
    global g_signal_signal
    global g_signal_getsignal
    global g_traceback_print_exc

    sublime_plugin_debugger.unload_rpdb2()

    if g_signal_signal is not None:
        signal.signal = g_signal_signal
        g_signal_signal = None

    if g_signal_getsignal is not None:
        signal.getsignal = g_signal_getsignal
        g_signal_getsignal = None

    # global g_sys_stdout
    # global g_sys_stderr
    # if g_sys_stdout is not None:
    #     sys.stdout = g_sys_stdout
    #     sys.stderr = g_sys_stderr
    #     g_sys_stdout = None
    #     g_sys_stderr = None
    # if g_traceback_print_exc is None:
    #     traceback.print_exc = g_traceback_print_exc
    #     g_traceback_print_exc = None

if ST3:
    def plugin_unloaded():
        end_module()

    def plugin_loaded():
        begin_module()

else:
    def unload_handler():
        end_module()

    begin_module()

