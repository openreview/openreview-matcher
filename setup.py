from setuptools import setup, find_packages

setup(name='openreview-matcher',
      version='0.1',
      description='OpenReview matching library',
      url='https://github.com/iesl/openreview-matcher',
      author='Michael Spector',
      author_email='spector@cs.umass.edu',
      license='MIT',
      packages=['matcher'],
      install_requires=[
          'numpy',
          'openreview-py',
          'ortools',
      ],
      zip_safe=False)
