from os.path import join, dirname
from setuptools import setup, find_packages

this_dir = dirname(__file__)

try:
    f = open(join(this_dir, 'README.rst'))
    long_description = f.read().strip()
    f.close()
except IOError:
    long_description = None

setup(name = 'djangosenchatools',
      description = 'Django management command to simplify building extjs and sencha touch apps with Sencha tools.',
      version = '1.0',
      long_description=long_description,
      url = 'https://github.com/espenak/djangosenchatools',
      license = 'BSD',
      author = 'Espen Angell Kristiansen',
      packages=find_packages(exclude=['ez_setup']),
      install_requires = ['setuptools', 'Django'],
      include_package_data=True,
      zip_safe=False,
      classifiers=['Development Status :: 5 - Production/Stable',
                   'Environment :: Web Environment',
                   'Framework :: Django',
                   'Intended Audience :: Developers',
                   'License :: OSI Approved :: BSD License',
                   'Operating System :: OS Independent',
                   'Programming Language :: Python'
                  ],
)
