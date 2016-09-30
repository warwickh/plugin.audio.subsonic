#!/usr/bin/env python

"""
This file is part of py-sonic.

py-sonic is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

py-sonic is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with py-sonic.  If not, see <http://www.gnu.org/licenses/>
"""

from distutils.core import setup
from libsonic import __version__ as version

setup(name='py-sonic',
    version=version,
    author='Jay Deiman',
    author_email='admin@splitstreams.com',
    url='http://stuffivelearned.org',
    description='A python wrapper library for the Subsonic REST API.  '
        'http://subsonic.org',
    long_description='This is a basic wrapper library for the Subsonic '
        'REST API. This will allow you to connect to your server and retrieve '
        'information and have it returned in basic Python types.',
    packages=['libsonic'],
    package_dir={'libsonic': 'libsonic'},
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: System Administrators',
        'Intended Audience :: Information Technology',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Natural Language :: English',
        'Operating System :: POSIX',
        'Programming Language :: Python',
        'Topic :: System :: Systems Administration',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Software Development :: Libraries',
        'Topic :: System',
    ]
)
