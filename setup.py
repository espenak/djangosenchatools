from setuptools import setup, find_packages
from djangosenchatools import version


setup(name = 'djangosenchatools',
      description = 'Django management command to simplify building extjs and sencha touch apps with Sencha tools.',
      version = version,
      long_description=open('README.rst').read(),
      url = 'https://github.com/espenak/djangosenchatools',
      license = 'BSD',
      author = 'Espen Angell Kristiansen',
      packages=find_packages(exclude=['ez_setup', 'fabfile']),
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
