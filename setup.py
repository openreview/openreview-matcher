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
          'ortools',
          'pytest',
          'Flask',
          'flask-cors==3.0.8',
          'cffi>=1.0.0'
      ],
      zip_safe=False)
