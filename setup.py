from setuptools import setup, find_packages

setup(name='openreview-matcher',
      version='0.3',
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
          'Flask',
          'flask-cors==3.0.8'
      ],
      zip_safe=False)
