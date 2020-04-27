from setuptools import setup, find_packages

setup(name='openreview-matcher',
      version='0.2',
      description='OpenReview matching library',
      url='https://github.com/openreview/openreview-matcher',
      author='Michael Spector',
      author_email='spector@cs.umass.edu',
      license='MIT',
      packages=['matcher'],
      install_requires=[
          'numpy',
          'openreview-py',
          'ortools',
          'pytest',
          'redis',
          'Flask'
      ],
      zip_safe=False)
