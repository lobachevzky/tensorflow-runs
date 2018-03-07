#! /usr/bin/env python
import codecs

from setuptools import setup

with codecs.open('README.rst', encoding='utf-8') as f:
    long_description = f.read()

setup(name='lab-notebook',
      version='2.1.6',
      description='A utility for tracking and reproducing Tensorflow runs.',
      long_description=long_description,
      url='https://github.com/lobachevzky/tf-run-manager',  # TODO
      author='Ethan Brooks',
      author_email='ethanbrooks@gmail.com',
      license='MIT',
      classifiers=[
          'Development Status :: 3 - Alpha',
          'Intended Audience :: Developers',
          'Topic :: Scientific/Engineering :: Artificial Intelligence',
          'License :: OSI Approved :: MIT License',
          'Programming Language :: Python :: 2',
          'Programming Language :: Python :: 3',
      ],
      keywords='tensorflow utilities development',
      packages=['runs'],
      entry_points={
          'console_scripts': [
              'runs = runs.main:main',
          ],
      },
      scripts=['runs-git'],
      install_requires=[
          'anytree==2.4.3',
          'termcolor==1.1.0',
          'PyYAML==3.12',
          'tabulate==0.8.1',
          'nose==1.3.7',
      ])
