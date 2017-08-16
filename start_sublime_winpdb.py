if __name__ == '__main__':
    import os, sys

    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'winpdb-1.4.8'))

    ATTACH_SCRIPT = sys.argv[1]

    def my_main(StartClient_func, version):
        StartClient_func(ATTACH_SCRIPT, True, False, 'sublime', True, 
            False, 'localhost')

    import rpdb2
    import winpdb

    rpdb2.g_fFirewallTest = False

    rpdb2.main = my_main

    winpdb.main()
