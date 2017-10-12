#-----------------------------------------------------------------------------
# Name:        status.py
# Purpose:     Define the status states for workUnit.
#
# Author:      Gerald Manipon
#
# Created:     Wed Jun 29 07:43:21 2005
# Copyright:   (c) 2005, California Institute of Technology.
#              U.S. Government Sponsorship acknowledged.
#-----------------------------------------------------------------------------

#sciflomanager sent work unit
sentStatus = 'sent'

#manager called callback to sciflomanager
calledBackStatus = 'called back'

#work unit is waiting for dependencies to be resolved
waitingStatus = 'waiting'

#work unit has dependencies resolved and is ready to run
readyStatus = 'ready'

#work unit is staging files prior to execution
stagingStatus = 'staging'

#work unit is executing
workingStatus = 'working'

#work unit finished successfully
doneStatus = 'done'

#work unit finished with an exception
exceptionStatus = 'exception'

#work unit resolved to a previously run work unit
cachedStatus = 'cached'

#post execution of work unit
postExecutionStatus = 'finalizing'

#work unit was cancelled
cancelledStatus = 'cancelled'

#work unit is paused
pausedStatus = 'paused'

#work unit is retrying
retryStatus = 'retry'

#list of statuses that indicate work unit is not working any more
finishedStatusList = [doneStatus,exceptionStatus,cachedStatus,cancelledStatus]
