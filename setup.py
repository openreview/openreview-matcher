from setuptools import setup, find_packages

setup(name='openreview-matcher',
      version='0.3',
      description='OpenReview matching library',
      url='https://github.com/openreview/openreview-matcher',
      author='Michael Spector',
      author_email='spector@cs.umass.edu',
      license='MIT',
      packages=['matcher'],
      setup_requires=['cffi>=1.0.0'],
      cffi_modules=["matcher/solvers/bvn_extension/bvn_extension_build.py:ffibuilder"],
      install_requires=[
          'numpy',
          'openreview-py',
          'ortools>=8.1.8487',
          'pytest',
          'Flask',
          'flask-cors==3.0.9',
          'cffi>=1.0.0',
          'celery',
      ],
      zip_safe=False)
