import time
import testModule3

def add(var1,var2):
	return var1+var2

def sleepAndAdd(var1,var2,sleeptime):
	time.sleep(sleeptime)
	return var1+var2

def calcSum(numList):
	sum=0
	for num in numList:
		sum+=num
	return sum

def returnComplexValues(testList,testInt,testStr,testFloat):
	return (testFloat,testStr,testInt,testList)

def returnList(count):
	retList=[]
	for i in range(count):
		retList.append(i)
	return retList

def reverseList(inputList):
	inputList.reverse()
	return inputList

def sleepAndAdd2(var1,var2,sleeptime):
	time.sleep(sleeptime)
	return (var1+var2, var1, var2, sleeptime)

def getRandomNum():
	return testModule3.getRandom()
