#-----------------------------------------------------------------------------
# Name:        callback.py
# Purpose:     Sciflo callback classes.
#
# Author:      Gerald Manipon
#
# Created:     Fri Aug 12 13:44:02 2005
# Copyright:   (c) 2005, California Institute of Technology.
#              U.S. Government Sponsorship acknowledged.
#-----------------------------------------------------------------------------
import types
import SOAPpy
from SOAPpy import WSDL, SOAPProxy
#import pyGlobus
import re
import urllib2

#from sciflo.webservices import getGSISOAPProxy
from utils import *

def getCallback(config):
    """Return a SciFloCallback object."""

    #validate config
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
    if not isinstance(config, types.TupleType) and not isinstance(config, types.ListType) and \
    not isinstance(config, SOAPpy.Types.arrayType): # and not isinstance(config,pyGlobus.GSISOAP.arrayType):
        raise RuntimeError, "Argument must be a tuple, list, or ArrayType.  Got %s %s." % (type(config),config)

    #get type
    callbackType = config[0]

    #get rest of args
    args = config[1:]

    #validate
    if not callbackType in CallbackMapping:
        raise RuntimeError, "Cannot recognize callback type: %s." % callbackType

    #get callback class
    callbackClass = CallbackMapping[callbackType]

    #create callback object
    callbackObj = callbackClass(args)

    #return
    return callbackObj

class ScifloCallback(object):
    """Base class for ScifloCallback classes."""

    def __init__(self,args=[]):
        """Constructor."""

        #set attributes
        self._args = args

        #set method/function to call
        self._callable = None

    def __call__(self,*args,**kargs):
        """Call."""
        return self._callable(*args,**kargs)

class SoapCallbackError(Exception):
    """Exception class for SOAPCallback class."""
    pass

class SOAPCallback(ScifloCallback):
    """HTTP SOAP callback class."""

    def __init__(self,args):
        """Constructor."""

        #call super
        super(SOAPCallback,self).__init__(args)

        #if only 2 args, assume first arg is wsdl url and second is soap method
        if len(self._args) == 2:
            self._wsdl = self._args[0]
            self._method = self._args[1]

            #create proxy
            if self._wsdl.startswith('https://'):
                wsdl = urllib2.urlopen(self._wsdl)
            else: wsdl = self._wsdl
            self._proxy = WSDL.Proxy(wsdl)

        #if 3, args are address (http[s]://hostname:port), namespace, and method
        elif len(self._args) == 3:
            self._addr = self._args[0]
            self._namespace = self._args[1]
            self._method = self._args[2]

            #create proxy
            self._proxy = SOAPProxy(self._addr,namespace=self._namespace)
        else: raise SOAPCallbackError, "Cannot resolve args."

        #set callable
        self._callable = eval("self._proxy.%s" % self._method)

'''
class GSISOAPCallbackError(Exception):
    """Exception class for GSISOAPCallback class."""
    pass

class GSISOAPCallback(ScifloCallback):
    """GSI SOAP callback class."""

    def __init__(self,args):
        """Constructor."""

        #call super
        super(GSISOAPCallback,self).__init__(args)

        #args are addr (http[s]://hostname:port), namespace, and method
        if len(self._args) == 3:
            self._addr = self._args[0]
            self._namespace = self._args[1]
            self._method = self._args[2]

            #create proxy
            self._proxy = getGSISOAPProxy(self._addr,self._namespace)
        else: raise GSISOAPCallbackError, "Cannot resolve args."

        #set callable
        self._callable = eval("self._proxy.%s" % self._method)
'''

class FunctionCallbackError(Exception):
    """Exception class for FunctionCallback class."""
    pass

class FunctionCallback(ScifloCallback):
    """Function callback class."""

    def __init__(self,args):
        """Constructor."""

        #call super
        super(FunctionCallback,self).__init__(args)

        #arg is function call
        if len(self._args) == 1: self._funcCall = self._args[0]
        else: raise FunctionCallbackError, "Cannot resolve args."

        #set callable
        self._callable = getFunction(self._funcCall)

#mapping of sciflo call types to their respective ScifloCallback subclass
CallbackMapping = {
    'http': SOAPCallback,
    'ssl': SOAPCallback,
    #'gsi': GSISOAPCallback,
    'local': FunctionCallback
    }
