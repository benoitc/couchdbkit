import os

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README')).read()

requires = [
    'pyramid',
    'pyramid_debugtoolbar',
    'waitress',
    'couchdbkit',
    ]

setup(name='pyramid_couchdb_example',
      version='0.0',
      description='pyramid_couchdb_example',
      long_description=README,
      classifiers=[
        "Programming Language :: Python",
        "Framework :: Pyramid",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
        ],
      author='',
      author_email='',
      url='',
      keywords='web pyramid pylons',
      packages=find_packages(),
      include_package_data=True,
      zip_safe=False,
      install_requires=requires,
      tests_require=requires,
      test_suite="pyramid_couchdb_example",
      entry_points = """\
      [paste.app_factory]
      main = pyramid_couchdb_example:main
      """,
      )

