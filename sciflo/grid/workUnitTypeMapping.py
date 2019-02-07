# -----------------------------------------------------------------------------
# Name:        workUnitTypeMapping.py
# Purpose:     Mapping of work unit types.
#
# Author:      Gerald Manipon
#
# Created:     Mon Jun 27 11:32:25 2005
# Copyright:   (c) 2005, California Institute of Technology.
#              U.S. Government Sponsorship acknowledged.
# -----------------------------------------------------------------------------

from .workUnit import *

# mapping of work unit types to their respective WorkUnit subclass
WorkUnitTypeMapping = {
    'soap': SoapWorkUnit,
    'python function': PythonFunctionWorkUnit,
    'inline python function': InlinePythonFunctionWorkUnit,
    'executable': ExecutableWorkUnit,
    'sciflo': ScifloWorkUnit,
    'rest': RestWorkUnit,
    'xquery': XqueryWorkUnit,
    'xpath': XpathWorkUnit,
    'template': TemplateWorkUnit,
    'post': PostWorkUnit,
    'cmdline': CommandLineWorkUnit,
    'map python function': ParMapWorkUnit,
    'parallel python function': ParWorkUnit,
}
