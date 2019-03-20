# -----------------------------------------------------------------------------
# Name:        callback.py
# Purpose:     Sciflo callback classes.
#
# Author:      Gerald Manipon
#
# Created:     Fri Aug 12 13:44:02 2005
# Copyright:   (c) 2005, California Institute of Technology.
#              U.S. Government Sponsorship acknowledged.
# -----------------------------------------------------------------------------
import types
import re
import urllib.request
import urllib.error
import urllib.parse

from .utils import *


def getCallback(config):
    """Return a SciFloCallback object."""

    # validate config
    '''
    print "&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&"
    print "In getCallback():"
    print config.__class__
    print config[0]
    print config[-1]
    print len(config)
    print config
    print "&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&"
    '''
    if not isinstance(config, tuple) and not isinstance(config, list):
        raise RuntimeError("Argument must be a tuple, list, or ArrayType.  Got %s %s." % (
            type(config), config))

    # get type
    callbackType = config[0]

    # get rest of args
    args = config[1:]

    # validate
    if not callbackType in CallbackMapping:
        raise RuntimeError(
            "Cannot recognize callback type: %s." % callbackType)

    # get callback class
    callbackClass = CallbackMapping[callbackType]

    # create callback object
    callbackObj = callbackClass(args)

    # return
    return callbackObj


class ScifloCallback(object):
    """Base class for ScifloCallback classes."""

    def __init__(self, args=[]):
        """Constructor."""

        # set attributes
        self._args = args

        # set method/function to call
        self._callable = None

    def __call__(self, *args, **kargs):
        """Call."""
        return self._callable(*args, **kargs)


class FunctionCallbackError(Exception):
    """Exception class for FunctionCallback class."""
    pass


class FunctionCallback(ScifloCallback):
    """Function callback class."""

    def __init__(self, args):
        """Constructor."""

        # call super
        super(FunctionCallback, self).__init__(args)

        # arg is function call
        if len(self._args) == 1:
            self._funcCall = self._args[0]
        else:
            raise FunctionCallbackError("Cannot resolve args.")

        # set callable
        self._callable = getFunction(self._funcCall)


# mapping of sciflo call types to their respective ScifloCallback subclass
CallbackMapping = {
    'local': FunctionCallback
}
