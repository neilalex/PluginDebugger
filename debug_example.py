import sublime_plugin, sys, os

class DebugExampleCommand(sublime_plugin.WindowCommand):
    r'''Illustrate usage of plugin debugger.
    '''

    def run(self, **kwargs):
        sys.stderr.write("start debug\n")
        i = 4

        window = self.window
        view = window.active_view()
        view_settings = view.settings()

        import spdb ; spdb.start()
        x = os.path.join("foo", "bar")
        z = 5
        