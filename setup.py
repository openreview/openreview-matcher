from setuptools import setup

setup(name='openreview-matching',
      version='0.1',
      description='OpenReview matching library',
      url='https://github.com/iesl/openreview-matching',
      author='Michael Spector',
      author_email='spector@cs.umass.edu',
      license='MIT',
      packages=['openreview_matcher'],
      install_requires=[
          'numpy'
      ],
      zip_safe=False)
