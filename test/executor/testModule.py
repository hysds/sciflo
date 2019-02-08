import time


def add(var1, var2):
    return var1+var2


def sleepAndAdd(var1, var2, sleeptime):
    time.sleep(sleeptime)
    return var1+var2


def calcSum(numList):
    sum = 0
    for num in numList:
        sum += num
    return sum


def returnComplexValues(testList, testInt, testStr, testFloat):
    return (testFloat, testStr, testInt, testList)


def returnComplexValues2(testList, testInt, testStr, testFloat, testDict):
    return (testList, testStr, testInt, testFloat, testDict)


def returnList(count):
    retList = []
    for i in range(count):
        retList.append(i)
    return retList


def returnDict(count):
    retDict = {}
    for i in range(count):
        retDict['key_%s' % str(i)] = 'Hello World %s' % str(i)
    return retDict


def reverseList(inputList):
    inputList.reverse()
    return inputList


def sleepAndAdd2(var1, var2, sleeptime):
    time.sleep(sleeptime)
    return (var1+var2, var1, var2, sleeptime)


def getTestXml():
    return '''<?xml version='1.0'?>
<resultSet xmlns:xs='http://www.w3.org/2001/XMLSchema' xmlns='http://sciflo.jpl.nasa.gov/2006v1/sf' id='AIRS'>
  <result>
    <objectid>AIRS.2003.01.02.240</objectid>
    <starttime>2003-01-02T23:59:26</starttime>
    <endtime>2003-01-03T00:05:26</endtime>
    <lonMin type='xs:float'>19.5368</lonMin>
    <lonMax type='xs:float'>58.0793</lonMax>
    <latMin type='xs:float'>43.5846</latMin>
    <latMax type='xs:float'>67.6574</latMax>
  </result>
  <result>
    <objectid>AIRS.2003.01.03.001</objectid>
    <starttime>2003-01-03T00:05:26</starttime>
    <endtime>2003-01-03T00:11:26</endtime>
    <lonMin type='xs:float'>15.9131</lonMin>
    <lonMax type='xs:float'>40.4548</lonMax>
    <latMin type='xs:float'>22.6194</latMin>
    <latMax type='xs:float'>46.0483</latMax>
  </result>
  <result>
    <objectid>AIRS.2003.01.03.239</objectid>
    <starttime>2003-01-03T23:53:26</starttime>
    <endtime>2003-01-03T23:59:26</endtime>
    <lonMin type='xs:float'>-159.3084</lonMin>
    <lonMax type='xs:float'>-122.2881</lonMax>
    <latMin type='xs:float'>-66.0514</latMin>
    <latMax type='xs:float'>-41.8693</latMax>
  </result>
  <result>
    <objectid>AIRS.2003.01.03.240</objectid>
    <starttime>2003-01-03T23:59:26</starttime>
    <endtime>2003-01-04T00:05:26</endtime>
    <lonMin type='xs:float'>-162.8152</lonMin>
    <lonMax type='xs:float'>-138.6116</lonMax>
    <latMin type='xs:float'>-44.5279</latMin>
    <latMax type='xs:float'>-20.9305</latMax>
  </result>
</resultSet>'''
