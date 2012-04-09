from setuptools import setup, find_packages

setup(name = 'djangosenchatools',
      description = 'Django management command to simplify building extjs and sencha touch apps with Sencha tools.',
      version = '1.0',
      url = 'https://github.com/espenak/djangosenchatools',
      license = 'BSD',
      author = 'Espen Angell Kristiansen',
      packages=find_packages(exclude=['ez_setup']),
      install_requires = ['setuptools', 'Django']
)
