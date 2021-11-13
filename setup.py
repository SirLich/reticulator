from distutils.core import setup

import os


long_description = open(
    os.path.join(
        os.path.dirname(__file__),
        'readme.rst'
    )
).read()

setup(
  name = 'reticulator',
  packages = ['reticulator'],
  version = 'v0.0.6-beta',
  license='MIT',
  description = 'Reticulator is a pack-access library for Minecraft Bedrock Addons.',
  author = 'SirLich',
  long_description=long_description,
  author_email = 'sirlich.business@gmail.com',
  url = 'https://github.com/SirLich/reticulator',
  keywords = ['MINECRAFT', 'BEDROCK-EDITION', 'BEDROCK-ADDONS'],
  install_requires=[
    'Send2Trash',
    'dpath',
  ],
  classifiers=[
    'Development Status :: 4 - Beta',
    'Intended Audience :: Developers',      # Define that your audience are developers
    'Topic :: Software Development :: Libraries',
    'License :: OSI Approved :: MIT License',   # Again, pick a license
    'Programming Language :: Python :: 3',
  ],
)