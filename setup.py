from setuptools import setup, find_packages

setup(name='openreview-matcher',
      version='0.1',
      description='OpenReview matching library',
      url='https://github.com/iesl/openreview-matching',
      author='Michael Spector',
      author_email='spector@cs.umass.edu',
      license='MIT',
      packages=find_packages(),
      install_requires=[
          'numpy',
          'openreview-py',
          'gensim',
          'nltk',
          'gurobipy'
      ],
      zip_safe=False)
