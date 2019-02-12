import os
import re
import unittest
import shutil
import sys
from tempfile import mkdtemp

import sciflo


# directory that this file is located in
dirName = os.path.dirname(os.path.abspath(__file__))

# exception regexes
SEGFAULT_RE = re.compile(
    r'Work unit was scheduled for cancellation and consequently cancelled.')
KABOOM_RE = re.compile(r'KABOOM!')
MISSING_ARG_RE = re.compile(r'missing 1 required positional argument')


class ExecutorTestCase(unittest.TestCase):
    """Test case for ScifloManager's execution of SciFlo workflow."""

    def setUp(self):
        """Setup."""

        # prep test dir
        self.testDir = "/tmp/testdir"
        if not os.path.isdir(self.testDir):
            os.makedirs(self.testDir, 0x755)

        # get temporary output directory
        self.outputDir = mkdtemp()

        # change to test directory
        os.chdir(dirName)

        # append to sys.path
        sys.path.append(dirName)

    def _execute(self, sfl_file):
        """Test execution of test_all.sf.xml."""

        # get workflow string
        with open(sfl_file) as f:
            sfl = f.read()

        # run
        return sciflo.grid.executor.runSciflo(sfl, {}, timeout=None,
                                              outputDir=self.outputDir,
                                              configDict={'isLocal': True})

    def testAll(self):
        """Test execution of test_all.sf.xml."""

        results = self._execute("test_all.sf.xml")
        self.assertAlmostEqual(results[0], 101.0)
        self.assertEqual(results[1], 'listing /tmp/testdir\n')

    def testIntenseCpu(self):
        """Test execution of intenseCpu.sf.xml."""

        results = self._execute("intenseCpu.sf.xml")
        self.assertAlmostEqual(results[0], 100001103.3999994)

    def testIntenseCpuSegfault(self):
        """Test execution of intenseCpu_segfault.sf.xml."""

        try:
            results = self._execute("intenseCpu_segfault.sf.xml")
        except Exception as e:
            assert isinstance(e, sciflo.grid.executor.ScifloExecutorError)
            assert SEGFAULT_RE.search(str(e))
            return
        raise RuntimeError("Expected exception but none was thrown.")

    def testSegfault(self):
        """Test execution of segfault.sf.xml."""

        try:
            results = self._execute("segfault.sf.xml")
        except Exception as e:
            assert isinstance(e, sciflo.grid.executor.ScifloExecutorError)
            assert SEGFAULT_RE.search(str(e))
            return
        raise RuntimeError("Expected exception but none was thrown.")

    def testError(self):
        """Test execution of test_error.sf.xml."""

        try:
            results = self._execute("test_error.sf.xml")
        except Exception as e:
            assert isinstance(e, sciflo.grid.executor.ScifloExecutorError)
            assert KABOOM_RE.search(str(e))
            return
        raise RuntimeError("Expected exception but none was thrown.")

    def testError2(self):
        """Test execution of test_error2.sf.xml."""

        try:
            results = self._execute("test_error2.sf.xml")
        except Exception as e:
            assert isinstance(e, sciflo.grid.executor.ScifloExecutorError)
            assert MISSING_ARG_RE.search(str(e))
            return
        raise RuntimeError("Expected exception but none was thrown.")

    def testGlobalOutput(self):
        """Test execution of test_globaloutput.sf.xml."""

        results = self._execute("test_globaloutput.sf.xml")
        self.assertAlmostEqual(results[0], 1502.3999994)
        self.assertAlmostEqual(results[1], 1002.3999994)
        self.assertAlmostEqual(results[2], 1502)

    def testLongSleepSegfault(self):
        """Test execution of test_longsleepsegfault.sf.xml."""

        try:
            results = self._execute("test_longsleepsegfault.sf.xml")
        except Exception as e:
            assert isinstance(e, sciflo.grid.executor.ScifloExecutorError)
            assert SEGFAULT_RE.search(str(e))
            return
        raise RuntimeError("Expected exception but none was thrown.")

    def testMany(self):
        """Test execution of test_many.sf.xml."""

        results = self._execute("test_many.sf.xml")
        self.assertAlmostEqual(results[0], 1502.3999994)

    def testManySciflos(self):
        """Test execution of test_manysciflos.sf.xml."""

        results = self._execute("test_manysciflos.sf.xml")
        self.assertAlmostEqual(results[0], 250031302.19999525)

    def testManySegfault(self):
        """Test execution of test_manysegfault.sf.xml."""

        try:
            results = self._execute("test_manysegfault.sf.xml")
        except Exception as e:
            assert isinstance(e, sciflo.grid.executor.ScifloExecutorError)
            assert SEGFAULT_RE.search(str(e))
            return
        raise RuntimeError("Expected exception but none was thrown.")

    def testSciflo(self):
        """Test execution of test_sciflo.sf.xml."""

        results = self._execute("test_sciflo.sf.xml")
        self.assertAlmostEqual(results[0][0], 2504.7999988)

    def testSegfault(self):
        """Test execution of test_segfault.sf.xml."""

        try:
            results = self._execute("test_segfault.sf.xml")
        except Exception as e:
            assert isinstance(e, sciflo.grid.executor.ScifloExecutorError)
            assert SEGFAULT_RE.search(str(e))
            return
        raise RuntimeError("Expected exception but none was thrown.")

    def testSleep(self):
        """Test execution of test_sleep.sf.xml."""

        results = self._execute("test_sciflo.sf.xml")
        self.assertAlmostEqual(results[0][0], 2504.7999988)

    def tearDown(self):
        """Cleanup."""

        # cleanup test directory
        if os.path.exists(self.testDir):
            shutil.rmtree(self.testDir)

        # cleanup output directory
        if os.path.exists(self.outputDir):
            shutil.rmtree(self.outputDir)


# create testsuite function
def getTestSuite():
    """Creates and returns a test suite."""
    # run tests
    executorTestSuite = unittest.TestSuite()
    executorTestSuite.addTest(ExecutorTestCase("testAll"))
    executorTestSuite.addTest(ExecutorTestCase("testIntenseCpu"))
    executorTestSuite.addTest(ExecutorTestCase("testIntenseCpuSegfault"))
    executorTestSuite.addTest(ExecutorTestCase("testSegfault"))
    executorTestSuite.addTest(ExecutorTestCase("testError"))
    executorTestSuite.addTest(ExecutorTestCase("testError2"))
    executorTestSuite.addTest(ExecutorTestCase("testGlobalOutput"))
    executorTestSuite.addTest(ExecutorTestCase("testLongSleepSegfault"))
    executorTestSuite.addTest(ExecutorTestCase("testMany"))
    executorTestSuite.addTest(ExecutorTestCase("testManySciflos"))
    executorTestSuite.addTest(ExecutorTestCase("testManySegfault"))
    executorTestSuite.addTest(ExecutorTestCase("testSciflo"))
    executorTestSuite.addTest(ExecutorTestCase("testSegfault"))
    executorTestSuite.addTest(ExecutorTestCase("testSleep"))

    # return
    return executorTestSuite


# main
if __name__ == "__main__":

    # get testSuite
    testSuite = getTestSuite()

    # run it
    runner = unittest.TextTestRunner()
    runner.run(testSuite)
