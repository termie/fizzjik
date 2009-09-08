# Copyright (c) 2001-2006 Twisted Matrix Laboratories.
# See LICENSE for details.

"""
This module provides Cocoa's AppKit event loop support for Twisted.

In order to use this support, simply do the following::

    |  from twisted.internet import cocoareactor
    |  cocoareactor.install()

Then use twisted.internet APIs as usual. Stop the event loop using
reactor.stop(), not AppHelper.stopEvemtLoop().

IMPORTANT: tests will fail when run under this reactor. This is
expected and probably does not reflect on the reactor's ability to run
real applications.

API Stability: stable

Maintainer: U{Andy Smith<mailto:twisted@anarkystic.com>}
"""

import Queue

from Foundation import *
from AppKit import *
from PyObjCTools import AppHelper


from twisted.python import log, runtime
from twisted.internet import _threadedselect



class CocoaReactor(_threadedselect.ThreadedSelectReactor):
    """
    wxPython reactor.

    wxPython drives the event loop, select() runs in a thread.
    """

    _stopping = False

    def _installSignalHandlersAgain(self):
        """
        wx sometimes removes our own signal handlers, so re-add them.
        """
        try:
            # make _handleSignals happy:
            import signal
            signal.signal(signal.SIGINT, signal.default_int_handler)
        except ImportError:
            return
        self._handleSignals()

    def stop(self):
        """
        Stop the reactor.
        """
        if self._stopping:
            return
        self._stopping = True
        _threadedselect.ThreadedSelectReactor.stop(self)

    def _runInMainThread(self, f):
        """
        Schedule function to run in main cocoa/Twisted thread.

        Called by the select() thread.
        """
        AppHelper.callAfter(f)

    def run(self, installSignalHandlers=True):
        """
        Start the reactor.
        """
        self._postQueue = Queue.Queue()

        # start select() thread:
        self.interleave(AppHelper.callAfter,
                        installSignalHandlers=installSignalHandlers)
        #if installSignalHandlers:
        #    self.callLater(0, self._installSignalHandlersAgain)

        # add cleanup events:
        self.addSystemEventTrigger("after", "shutdown", AppHelper.stopEventLoop)
        self.addSystemEventTrigger("after", "shutdown",
                                   lambda: self._postQueue.put(None))

        AppHelper.runConsoleEventLoop(installInterrupt=True)
            
        if not self._stopping:
            # if event loop exited without reactor.stop() being
            # called.  At this point events from select() thread will
            # be added to _postQueue
            self.stop()
            while 1:
                try:
                    f = self._postQueue.get(timeout=0.01)
                except Queue.Empty:
                    continue
                else:
                    if f is None:
                        break
                    try:
                        f()
                    except:
                        log.err()


def install():
    """
    Configure the twisted mainloop to be run inside the wxPython mainloop.
    """
    reactor = CocoaReactor()
    from twisted.internet.main import installReactor
    installReactor(reactor)
    return reactor


__all__ = ['install']
