from setuptools import setup, find_packages
import os
import sys
sys.path.append('test')

packages = find_packages()

scripts = [os.path.join('scripts', 'gridServerCtl.py'),
           os.path.join('scripts', 'sflExec.py'),
           os.path.join('scripts', 'ldapSearch.py'),
           os.path.join('scripts', 'ldapAuth.py'),
           os.path.join('scripts', 'webservices', 'exposer.py'),
           os.path.join('scripts', 'webservices', 'soap.cgi'),
           os.path.join('scripts', 'insertDataFromXml.py'),
           os.path.join('scripts', 'stopGridServer.sh'),
           os.path.join('scripts', 'startGridServer.sh'),
           os.path.join('scripts', 'cleanAndStartGridServer.sh'),
           os.path.join('scripts', 'startMysql.sh'),
           os.path.join('scripts', 'stopMysql.sh'),
           os.path.join('scripts', 'startExposer.sh'),
           os.path.join('scripts', 'stopExposer.sh'),
           os.path.join('scripts', 'stopCacheServer.sh'),
           os.path.join('scripts', 'startCacheServer.sh'),
           os.path.join('scripts', 'cleanAndStartCacheServer.sh'),
           os.path.join('scripts', 'crawlAll.py'),
           os.path.join('scripts', 'getConfigVal.py'),
           os.path.join('scripts', 'sciflod'),
           os.path.join('scripts', 'cgiInterface', 'submit_sciflo.cgi'),
           os.path.join('scripts', 'cgiInterface', 'monitor_sciflo.cgi'),
           os.path.join('scripts', 'cgiInterface', 'cancel_sciflo.cgi'),
           os.path.join('scripts', 'cgiInterface', 'get_sciflos.cgi'),
           os.path.join('scripts', 'cgiInterface', 'mold_results.cgi'),
           os.path.join('scripts', 'cgiInterface', 'utils.cgi'),
           os.path.join('scripts', 'cgiInterface', 'pageTemplate.py'),
           os.path.join('scripts', 'cgiInterface', 'basicPageTemplate.py'),
           os.path.join('scripts', 'cgiInterface', 'cgiUtils.py'),
           os.path.join('scripts', 'cgiInterface', 'rest.py'),
           os.path.join('scripts', 'dashboard', 'flowcheck.py'),
           os.path.join('scripts', 'dashboard', 'flowcheck.sh'),
           os.path.join('scripts', 'dashboard', 'sciflodiagnostic.cgi'),
           os.path.join('scripts', 'exposerWatcher.sh'),
           os.path.join('scripts', 'gridServerWatcher.sh'),
           ]

data_files = [('tac', [os.path.join('tac', 'PersistentDictServer.tac')])]

setup(name='sciflo',
      version="1.2.0",
      description="SciFlo workflow framework and engine",
      author='Brian Wilson',
      author_email='Brian.Wilson@jpl.nasa.gov',
      maintainer='Gerald Manipon',
      maintainer_email='Geraldjohn.M.Manipon@jpl.nasa.gov',
      url="https://github.com/hysds/sciflo",
      zip_safe=False,
      packages=packages,
      package_data={
           '': ['*.xsl']
      },
      scripts=scripts,
      data_files=data_files,
      entry_points={
          'console_scripts': [
              'filelist.py=sciflo.utils.filelist:main',
              'subsetAeronet.py=sciflo.data.aeronet.subset:main',
              'hdfMetadata.py=sciflo.data.hdf:main',
          ],
      },
      test_suite="runAllTests.getAllTestsTestSuite",
      )
