#-----------------------------------------------------------------------------
# Name:        subsetter.py
# Purpose:     Base class for data subsetting classes.
#
# Author:      Gerald Manipon
#
# Created:     Thu May 05 09:52:26 2005
# Copyright:   (c) 2005, California Institute of Technology.
#              U.S. Government Sponsorship acknowledged.
#-----------------------------------------------------------------------------
import types

class DataFileVariableSubsetterError(Exception):
	"""Exception class for DataFileVariableSubsetter class."""
	pass

class DataFileVariableSubsetter(object):
	"""Base class for data file variable subsetting."""

	def __init__(self,fileUrl,varList,outputFile,excludeFlag=None,
				 mandatory=['time','lat','lon','alt']):
		"""Constructor."""

		#data fileUrl to subset
		self._fileUrl = fileUrl

		#output file to write to
		self._outputFile = outputFile

		#excludeFlag -- if set, the list of variables if varList are
		#variables to exclude
		self._excludeFlag = excludeFlag

		#get list
		try: self._varList = self._createList(varList)
		except Exception, e:
			raise DataFileVariableSubsetterError, "Error with 'varList' arg: %s" % e

		#get mandatory list
		try: self._mandatoryList = self._createList(mandatory)
		except Exception, e:
			raise DataFileVariableSubsetterError, "Error with 'mandatory' arg: %s" % e

	def _createList(self,obj):
		"""Return a list."""

		#if this is a list or tuple, return it already.
		if isinstance(object,types.TupleType) or isinstance(obj,types.ListType): return obj
		#if it is a string, then create a single list
		elif isinstance(obj,types.StringType): return [obj]
		#if it is None, return an empty list
		elif obj is None: return []
		#otherwise raise error
		else:
			raise DataFileVariableSubsetterError, "Argument is not a list, tuple, or string: %s" % type(obj)

	def _validateForSlicing(self):
		"""Return 1 if all lists are in a state to allow for slicing."""

		#make sure mandatory list is not empty
		if len(self._mandatoryList) == 0:
			raise DataFileVariableSubsetterError, "'mandatory' variables list cannot be empty."

		#make sure variable list is not empty
		if len(self._varList) == 0:
			raise DataFileVariableSubsetterError, "'varList' variables list cannot be empty."

	def getFileUrl(self):
		"""Return the input file url."""
		return self._fileUrl

	def getOutputFile(self):
		"""Return the output file path."""
		return self._outputFile

	def getVarList(self):
		"""Return the list of variables."""
		return self._varList

	def getMandatoryList(self):
		"""Return the list of mandatory variables."""
		return self._mandatoryList

	def getExcludeFlag(self):
		"""Return the exclude flag."""
		return self._excludeFlag

	def setFileUrl(self,fileUrl):
		"""Set the input file url."""
		self._fileUrl = fileUrl

	def setOutputFile(self,outputFile):
		"""Set the output file path."""
		self._outputFile = outputFile

	def setVarList(self,varList):
		"""Set the variable list."""

		try: self._varList = self._createList(varList)
		except Exception, e: raise DataFileVariableSubsetterError, e

	def setMandatoryList(self,mandatory):
		"""Set the mandatory variables list."""

		try: self._mandatoryList=self._createList(mandatory)
		except Exception, e: raise DataFileVariableSubsetterError, e

	def setExcludeFlag(self,flag):
		"""Set the exclude flag."""
		self._excludeFlag = flag

	def subset(self):
		"""Subset the variables out to the output file.  Return 1 upon
		successful slicing.  Otherwise raise an error.  Subclasses will
		implement this method.
		"""

		#validate the lists
		self._validateForSlicing()

		'''
		<subclass implementation...>
		'''

	def __del__(self):
		"""Destructor."""
		pass
