from setuptools import setup, find_packages
import os
import sys
sys.path.append('test')

packages = find_packages()

scripts = [os.path.join('scripts', 'sflExec.py'),
           os.path.join('scripts', 'ldapSearch.py'),
           os.path.join('scripts', 'ldapAuth.py'),
           os.path.join('scripts', 'insertDataFromXml.py'),
           os.path.join('scripts', 'startMysql.sh'),
           os.path.join('scripts', 'stopMysql.sh'),
           os.path.join('scripts', 'stopCacheServer.sh'),
           os.path.join('scripts', 'startCacheServer.sh'),
           os.path.join('scripts', 'cleanAndStartCacheServer.sh'),
           os.path.join('scripts', 'crawlAll.py'),
           os.path.join('scripts', 'getConfigVal.py'),
           os.path.join('scripts', 'sciflod'),
           os.path.join('scripts', 'dashboard', 'flowcheck.py'),
           os.path.join('scripts', 'dashboard', 'flowcheck.sh'),
           os.path.join('scripts', 'dashboard', 'sciflodiagnostic.cgi'),
           ]

data_files = [('tac', [os.path.join('tac', 'PersistentDictServer.tac')])]

setup(name='sciflo',
      version = "1.3.7",
      description="SciFlo workflow framework and engine",
      url="https://github.com/hysds/sciflo",
      author='Brian Wilson',
      author_email='Brian.Wilson@jpl.nasa.gov',
      maintainer='Gerald Manipon',
      maintainer_email='Geraldjohn.M.Manipon@jpl.nasa.gov',
      zip_safe=False,
      install_requires=[
          'twisted>=18.9.0', 'pillow>=5.4.1', 'formencode>=1.3.1',
          'sqlobject>=3.7.1', 'service_identity>=18.1.0',
          'python-magic>=0.4.15',
          # pin setuptools until this is fixed: https://github.com/pypa/setuptools/issues/4399
          "setuptools<70.0.0"
      ],
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
      }
      )
