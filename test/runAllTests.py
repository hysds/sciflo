#-----------------------------------------------------------------------------
# Name:        runAllTests.py
# Purpose:     Run all tests.
#
# Author:      Gerald Manipon
#
# Created:     Thu May 12 15:31:42 2005
# Copyright:   (c) 2005, California Institute of Technology.
#              U.S. Government Sponsorship acknowledged.
#-----------------------------------------------------------------------------
import os
import sys
import unittest

#skip files
skipFiles = ()#'soapWithGetMethodTest.py','scifloManagerLocalExecutionTest.py','dbxmlLibrarianTest.py')

#make cwd a path
sys.path.append('.')

def getAllTestsTestSuite():
    """Return test suite encompassing all unit tests."""
    
    #change to this directory
    os.chdir(os.path.abspath(os.path.dirname(__file__)))
    
    #walk this directory and populate the testDict
    testDict = {}
    for root,dirs,files in os.walk('.'):
    
        #if this directory is the current, skip
        if root == '.': continue
    
        #if this directory is CVS, skip
        if root.endswith('CVS') or root.endswith('svn'): continue
    
        #generate list of test scripts
        testScripts = []
        for file in files:
            if file.endswith('Test.py'):
                if file in skipFiles:
                    print(("Skipping file: %s" % file))
                    continue
                testScripts.append(file)
    
        #populate testDict
        testDict[root] = testScripts
    
    #save our root directory
    rootDir = os.path.abspath(os.curdir)
    
    #create allTestsTestSuite
    allTestsTestSuite = unittest.TestSuite()
    
    #loop over testDict and create list of testSuites
    testDirs = list(testDict.keys())
    for testDir in testDirs:
    
        #loop over scripts
        for testScript in testDict[testDir]:
    
            #chdir to testdir
            os.chdir(testDir)
    
            #get base
            (base,ext) = os.path.splitext(testScript)
    
            #import test file
            exec("import %s" % base)
    
            #get testSuite
            getTestSuiteCall = "%s.getTestSuite()" % base
            allTestsTestSuite.addTest(eval(getTestSuiteCall))
    
            #change back to rootDir
            os.chdir(rootDir)
            
    return allTestsTestSuite

#main
if __name__ == "__main__":
    
    #run test
    runner = unittest.TextTestRunner()
    result = runner.run(getAllTestsTestSuite())
