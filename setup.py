from setuptools import setup, find_packages
from setuptools.extension import Extension
import subprocess
import sys

def install(package):
  subprocess.check_call([sys.executable, "-m", "pip", "install", package])

try:
  from Cython.Build import cythonize
except:
  install('cython')
  from Cython.Build import cythonize

with open("README.md", "r") as fh:
  long_description = fh.read()

extensions = [
  Extension(
    "btrader.*",
    ["btrader/*.py"],
  ),
  Extension(
    "btrader.core.*",
    ["btrader/core/*.py"],
  ),
  Extension(
    "btrader.extensions",
    sources=["btrader/src/extensions.cpp"],
    libraries=["boost_python3"],
  )
]

setup(
  name = 'btrader',
  version = '0.1.0',
  license='GPL-3.0',
  description = 'Arbitrage trading bot for Binance, based on https://github.com/bmino/binance-triangle-arbitrage',
  long_description = long_description,
  long_description_content_type="text/markdown",
  packages=find_packages(),
  author = 'Gabriel Gazola Milan',
  author_email = 'gabriel.gazola@poli.ufrj.br',
  url = 'https://github.com/gabriel-milan/btrader',
  keywords = ['bot', 'algotrading', 'cryptocurrencies', 'binance', 'bitcoin', 'arbitrage'],
  install_requires=[
   'Cython>=0.29.17',
   'python_binance>=0.7.5',
   'numpy>=1.18.1'
  ],
  classifiers=[
    'Development Status :: 4 - Beta',
    'Intended Audience :: Developers',
    'Topic :: Software Development :: Libraries :: Python Modules',
    'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
    'Programming Language :: Python :: 3',
    'Programming Language :: Python :: 3.4',
    'Programming Language :: Python :: 3.5',
    'Programming Language :: Python :: 3.6',
    'Programming Language :: Python :: 3.7',
    'Programming Language :: Python :: 3.8',
  ],
  ext_modules = cythonize(extensions, language_level = "3")
)
