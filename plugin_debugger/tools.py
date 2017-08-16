import sublime, sublime_plugin
import sys, os, re, subprocess, signal, threading, time

try:    # python 2.x
    import thread
except ImportError: # python 3.x
    import _thread as thread

#
# preimport modules, which will be imported by rpdb2 later, such that they are
# imported from ST environment rather than python environment, when temporarily
# setting python env path.
#
import subprocess, threading, traceback, zipimport, tempfile, platform, operator
import weakref, os.path, zipfile, pickle, socket, getopt, string, random
import base64, atexit, locale, codecs, signal, errno, time, copy, hmac, stat
import zlib, sys, cmd, imp, os, re, hashlib

try:
    import compiler, sets
except:
    pass

try:
    import SimpleXMLRPCServer, xmlrpclib, SocketServer, commands, copy_reg
    import httplib, thread

except:
    #
    # The above modules were renamed in Python 3 so try to import them 'as'
    #
    import xmlrpc.server as SimpleXMLRPCServer, xmlrpc.client as xmlrpclib
    import socketserver as SocketServer, subprocess as commands
    import copyreg as copy_reg, http.client as httplib, _thread as thread

    #
    # Needed in py3k path.
    #
    import numbers

import logging

_log = logging.getLogger('spdb')
_log.setLevel(logging.ERROR)

g_log = []

def log(s, *args):

    g_log.append(s % args)
    if len(g_log) > 100:
        g_log.pop(0)

    _log.debug(s, *args)

g_sys_excepthook = None

g_debugging = False

PYTHON_FILES = {}

ST3 = sublime.version() >= '3000'

def plugin_debugger_dir():
    package_dir = sublime.packages_path()
    p = os.path.join(package_dir, 'Plugin Debugger')
    return p

def cached_resource(res, alias=None):
    #res = 'Packages/Plugin Debugger/start_sublime_winpdb.py'
    log("cached_resource: %s => %s" , res, alias)

    if alias is None:
        alias = os.path.basename(res)
        
    log("cached_resource: %s => %s" , res, alias)

    cache_dir = os.path.join(sublime.cache_path(), 'Plugin Debugger')
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)
    fn = os.path.join(cache_dir, alias)

    log("cached name: %s" , fn)

    if not os.path.exists(fn):
        log("create cached file: %s\n" % fn)
        data = sublime.load_binary_resource(res)
        with open(fn, 'wb') as fh:
            fh.write(data)

    log("cache done: %s" , fn)
    
    return fn

#PLUGIN_DEBUGGER_DIR = plugin_debugger_dir()

# make sure everyone can import sublime_plugin_debugger
#if PLUGIN_DEBUGGER_DIR not in sys.path:
#    sys.path.append(PLUGIN_DEBUGGER_DIR)

def import_rpdb2():

    if 'rpdb2' not in sys.modules: 

        global g_sys_excepthook

        g_sys_excepthook = sys.excepthook

        python = get_python_interpreter()

        log("python: %s", python)

        import subprocess, tempfile
        rpdb2_file = subprocess.Popen(
            [python, '-c', 'import rpdb2 ; print(rpdb2.__file__)'],
            cwd    = tempfile.gettempdir(),
            stdout = subprocess.PIPE).communicate()[0].strip()

        if not rpdb2_file:
            sublime.error_message(
                "I could not find find out the packageYou have to install winpdb graphical python debugger\n"
                "for your configured python interpreter (%s).\n"
                "\n"
                "Follow instructions on http://winpdb.org/download/\n"
                % python
                )

        dir = os.path.dirname(rpdb2_file)

        if ST3:
            dir = dir.decode()

        try:
            sys.path.insert(0, dir)
            log("path: %s", sys.path)
            import rpdb2

            # never abort the debugged program => plugin_host stays alive
            rpdb2_atexit = rpdb2._atexit
            def my_atexit(fabort = False):
                return rpdb2_atexit(fabort = False)

            rpdb2._atexit = my_atexit
        finally:
            sys.path.remove(dir)

    return sys.modules['rpdb2']

def update_packages_path():
    package_dir = sublime.packages_path()
    for d, ds, fs in os.walk(package_dir):
        for f in fs:
            if f.endswith('.py'):
                PYTHON_FILES[f] = os.path.join(d, f)


class SublimeTextSourceProvider:

    HANDLERS = ['existing', 'zip', 'plugin_file', 'st2_pylib', 'packages_file']


    def __init__(self):
        self._package_python_files = None
        self._python_lib_zip = None
        self._lock = threading.Lock()
        self._packaged_path = sublime.packages_path()


    def _update_package_files(self):
        if self._package_python_files is None:
            self._package_python_files = {}
            package_dir = sublime.packages_path()
            log("    package_dir: %s" , package_dir)
            for d, ds, fs in os.walk(package_dir):
                for f in fs:
                    fn = os.path.join(d, f)
                    if f.endswith('.py'):
                        log("      fn: %s => %s" , f, fn)
                        self._package_python_files[f] = fn

    def _handle_existing(self, filename):
        log("  existing? %s" , filename)
        if os.path.exists(filename):
            with open(filename, 'r') as fh:
                return fh.read()

        raise IOError()


    def _handle_zip(self, filename):
        log("  zip? %s" , filename)
        if self._python_lib_zip is None:
            pyth = 'Python-%s.%s.%s' % sys.version_info[:3]
            zipname = '%s-Lib.zip' % pyth

            if ST3:
                zipname = cached_resource('Packages/Plugin Debugger/'+zipname)
            else:
                zipname = os.path.join(plugin_debugger_dir(), zipname)

            import zipfile
            self._python_lib_zip = zipfile.PyZipFile(zipname)

        if ST3:
            m = re.match(r'^(.*python3.3.zip)/(.*)$', filename)
        else:
            m = re.match(r'^(.*python26.zip)/(.*)$', filename)

        path, fn = m.groups()
        fn = re.sub(r'^\./', '', fn)

        fn = ('Python-%s.%s.%s/Lib/' % sys.version_info[:3])+fn

        return self._python_lib_zip.read(fn)


    def _handle_st2_pylib(self, filename):
        log("  st2_pylib? %s", filename)
        if not ST3:
            filename = re.sub(r'^\./', '', filename)

            if not os.path.isabs(filename):
                return self._handle_zip('python26.zip/'+filename)

        raise IOError()


    def _handle_plugin_file(self, filename):
        log("  plugin_file? %s", filename)
        self._update_package_files()
        fn = self._package_python_files[os.path.basename(filename)]
        with open(fn, 'r') as fh:
            return fh.read()

        raise IOError()

    def _handle_packages_file(self, filename):
        log("  packages_file? %s", filename)

        if '.sublime-package' in filename:
            filename = 'Packages'+filename.split('Packages', 1)[1]
            filename = filename.replace('.sublime-package', '')

        if filename.startswith('Packages/'):
            _fn = os.path.join(self._packaged_path, filename[9:])
            if os.path.exists(_fn):
                with open(_fn, 'r') as fh:
                    return fh.read()
            return sublime.load_resource(filename)

        raise IOError()

    def __call__(self, filename):
        try:
            self._lock.acquire()

            filename = os.path.normpath(filename)
            filename = filename.replace('\\', '/')

            log("request: %s", filename)

            for x in self.HANDLERS:
                x = '_handle_'+x
                try:
                    result = getattr(self, x)(filename)
#                    log("  => res: %s", result)
                    return result

                except Exception as e:
                    log("  => exc: %s", e)
                    pass

            raise IOError()
        finally:
            self._lock.release()



def sublime_text_source_provider(filename):
    log("request: %s", filename)

    log("try exists")
    if os.path.exists(filename):
        log("exists: %s", filename)
        with open(filename, 'r') as fh:
            return fh.read()

    log("try sublime_plugin")
    if re.match(r'^\.[\\/]sublime_plugin.py$', filename):
        log("sublime_plugin: %s", filename)
        if ST3:
            with open(os.path.join(plugin_debugger_dir(), 'sublime_plugin.py-3')) as fh:
                return fh.read()
        else:
            with open(os.path.join(plugin_debugger_dir(), 'sublime_plugin.py-2')) as fh:
                return fh.read()

    log("try relative")
    m = re.match(r'^\.[\\/](.*)', filename)
    if m:
        log("relative name: %s", filename)

        _fn = m.group(1)
        if not len(PYTHON_FILES):
            log("upd packages path")
            update_packages_path()
            log("PYTHON_FILES: %s", PYTHON_FILES)

        if _fn in PYTHON_FILES:
            with open(PYTHON_FILES[_fn], 'r') as fh:
                return fh.read()

        assert not ST3

        try:
            fn = os.path.join('python26.zip', m.group(1))
            return sublime_text_source_provider(fn)
        except IOError:
            return sublime_text_source_provider(os.path.join('from_package', m.group(1)))

    log("try sublime package")
    m = re.search(r'/([^/]*)\.sublime-package/(.*))', filename)
    if m:
        pkg_name = m.group(1)
        fn       = m.group(2)

    log("try python3.3.zip")

    zipname = cached_resource('Packages/Plugin Debugger/Python-%s.%s.%s-Lib.zip' % sys.version_info[:3])

    log("zipname: %s", zipname)

    filename = os.path.normpath(filename)
    m = re.match(r'^(.*python3.3.zip)[/\\](.*)$', filename)
    path, fn = m.groups()
    fn = re.sub(r'^[\.\\/]+', '', fn)
    fn = fn.replace('\\', '/')
    fn = ('Python-%s.%s.%s/Lib/' % sys.version_info[:3])+fn
    log("fn: %s", fn)

    import zipfile

    z = zipfile.PyZipFile(zipname)


    try:
        return z.read(fn)
    except:
        raise IOError()


    fn = filename.rsplit('/', 1)[1]
    if fn not in PYTHON_FILES:
        update_packages_path()
        if fn not in PYTHON_FILES:
            if ST3:
                fn = 'Packages'+fn.split('Packages', 1)[1]
                fn = fn.replace('.sublime-package', '')
                return sublime.load_resource(fn)

            raise IOError()


    with open(PYTHON_FILES[fn], 'r') as fh:
        return fh.read()

PYTHON_CHECKED = False

def get_python_interpreter():
    global PYTHON_CHECKED

    settings = sublime.active_window().active_view().settings()
    python = settings.get('plugin_debugger_python', "python")

    if not PYTHON_CHECKED:
        r = subprocess.call([python, '-c', 'import winpdb'])

        if r != 0:
            exe = subprocess.Popen([python, '-c', 'import sys;print(sys.executable)'],
                stdout = subprocess.PIPE).communicate()[0].strip()

            sublime.error_message(
                "You have to install winpdb graphical python debugger\n"
                "for your configured python interpreter (%s).\n"
                "\n"
                "Follow instructions on http://winpdb.org/download/\n"
                % exe
                )

        PYTHON_CHECKED = True

    return python

def start(*args, **kargs):
    global g_debugging, g_debug_session_ready

    python = get_python_interpreter()

    log("START (g_debugging: %s)" % g_debugging)

    # todo wrap at exit, such that end of winpdb without detaching does not make
    # plugin host stop and st2 exit

    rpdb2 = import_rpdb2()

    if g_debugging:
        if g_winpdb is None:
            winpdb = debug_session(python, shutdown_at_exit=False)
            rpdb2.g_thread_start_new_thread(debug_session_monitor, (winpdb,))

        time.sleep(0.1)

        rpdb2.setbreak(depth=1)
        return

    #rpdb2.g_thread_start_new_thread(debug_session, tuple(python, False))

    time.sleep(0.1)

    # initialize debugger (there is a thread starting, so we have to wait for it)
    rpdb2.start_embedded_debugger("sublime", timeout=0, 
        source_provider=SublimeTextSourceProvider())

    log("wait for debug server")

    # wait for running debugger thread
    wait_for_debug_server()

    if g_winpdb is None:
        winpdb = debug_session(python, shutdown_at_exit=False)
        rpdb2.g_thread_start_new_thread(debug_session_monitor, (winpdb,))

    #g_debug_session_ready = False

    #while not g_debug_session_ready:
        #time.sleep(0.1)

    log("break")
    rpdb2.setbreak(depth=1)

    g_debugging = True


g_debug_session_ready = None

def debug_session_monitor(winpdb):
    global g_winpdb
    r = winpdb.wait()
    g_winpdb = None
    
    # this does not yet work
#    unload_rpdb2()
#    g_debugging = False
#    log("Debug session shut down\n")



def debug_session(python_interpreter=None, shutdown_at_exit=True):
    '''this thread controls debug session'''

    log("Debug session prepared")

    #while g_debug_session_ready is None:
        #time.sleep(0.1)

    log("Debug session started")
    #global g_debugging, g_debug_session_ready

    winpdb = start_winpdb(python_interpreter)
    
    log("Debug session ready")

    g_debug_session_ready = True

    if shutdown_at_exit:
        log("waiting for winpdb")
        # now wait for debugger
        r = winpdb.wait()

        log("winpdb done, unloading rpdb2")
        # and finally unload rpdb2
        unload_rpdb2()

        log("done debugging")
        g_debugging = False

    return winpdb


g_winpdb = None

def start_winpdb(python_interpreter):
    rpdb2 = import_rpdb2()
    global g_winpdb

    tmp = rpdb2.g_fignorefork
    rpdb2.g_fignorefork = True

    g_winpdb = winpdb(rpdb2.g_server.m_filename, python=python_interpreter)

    rpdb2.g_fignorefork = tmp
    return g_winpdb


def winpdb(attach=None, python=None):
    if python is None:
        python = get_python_interpreter()

    if ST3:
        script = cached_resource('Packages/Plugin Debugger/start_sublime_winpdb.py', 
            alias='start_sublime_winpdb')
    else:
        script = os.path.join(plugin_debugger_dir(), 'start_sublime_winpdb.py')

    return subprocess.Popen([ python, script, attach ])


def setbreak(depth=0):
    rpdb2 = import_rpdb2()
    rpdb2.setbreak(depth=depth+1)


def wait_for_debug_server():
    rpdb2 = import_rpdb2()
    started = time.time()
    while True:
        time.sleep(0.1)
        log('rpdb2.g_server: %s', rpdb2.g_server)
        if rpdb2.g_server is None:
            continue
        log('rpdb2.g_server.m_thread: %s', rpdb2.g_server.m_thread)
        if rpdb2.g_server.m_thread is None:
            continue
        log('rpdb2.g_server.m_thread.is_alive(): %s', rpdb2.g_server.m_thread.is_alive())
        if rpdb2.g_server.m_thread.is_alive():
            log('took %ss' % (time.time()-started))
            break

        if time.time() - started > 60:
            sublime.error_message("Waited 60s for debug server to start, giving up")
            return

### following does not yet work. idea is to shutdown debugger at exit of winpdb



def shutdown_debugger():
    sys.excepthook = g_sys_excepthook
    
    rpdb2 = import_rpdb2()

    # run _atexit, which closes server and debugger engine

   # ign_at_exit = rpdb2.g_fignore_atexit
    #rpdb2.g_fignore_atexit = False
    #rpdb2._atexit(fabort=False)

    if rpdb2.g_debugger is not None:
        rpdb2.g_debugger.stoptrace()

    #rpdb2.g_debugger.send_event_exit()
    time.sleep(1.0)

    if rpdb2.g_server is not None:
        rpdb2.g_server.shutdown()

    time.sleep(1.0)

    if rpdb2.g_debugger is not None:
        rpdb2.g_debugger.shutdown() 
        
    time.sleep(1.0)


    # from now on ignore _atexit

    #rpdb2.g_fignore_atexit = True


def undo_rpdb2():
    rpdb2 = import_rpdb2()

    # remove _atexit
    import atexit
    if hasattr(atexit, '_exithandlers'):
        _at_exit = None
        for x in atexit._exithandlers:
            if x[0] is rpdb2._atexit:
                _at_exit = x
                break
        if _at_exit: 
            atexit._exithandlers.remove(_at_exit)
    else:
        atexit.unregister(rpdb2._atexit)

    import threading

    sys.stderr.write("%s\n" % threading.enumerate())

    signal.signal           = rpdb2.g_signal_signal
    signal.getsignal        = rpdb2.g_signal_getsignal
    thread.start_new_thread = rpdb2.g_thread_start_new_thread
    sys.exc_info            = rpdb2.g_sys_exc_info
    sys.setrecursionlimit   = rpdb2.g_sys_setrecursionlimit
    rpdb2.g_builtins_module.__import__ = rpdb2.g_import
    os.fork                 = rpdb2.g_os_fork
    os.exit                 = rpdb2.g_os_exit
    os.close                = rpdb2.g_os_close
    os.dup2                 = rpdb2.g_os_dup2
    os.execv                = rpdb2.g_os_execv
    os.execve               = rpdb2.g_os_execve

def unload_rpdb2():
    
    if g_winpdb is not None:
        # terminate winpdb
        g_winpdb.terminate()

    log("shutdown debugger")
    shutdown_debugger()
    log("undo rpdb2 changes")
    undo_rpdb2()
    log("remove rpdb2")
    del sys.modules['rpdb2']
