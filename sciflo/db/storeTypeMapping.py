#-----------------------------------------------------------------------------
# Name:        storeTypeMapping.py
# Purpose:     Mapping of store types.
#
# Author:      Gerald Manipon
#
# Created:     Mon Jun 27 11:32:25 2005
# Copyright:   (c) 2005, California Institute of Technology.
#              U.S. Government Sponsorship acknowledged.
#-----------------------------------------------------------------------------
#from rdbmsStore import RdbmsStore
from .bsddbStore import BsddbStore

#mapping of store types to their respective Store subclass
StoreTypeMapping = {
    'bsddb': BsddbStore,
    #'rdbms': RdbmsStore,
    }
