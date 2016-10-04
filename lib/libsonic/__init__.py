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

For information on method calls, see 'pydoc libsonic.connection'

----------
Basic example:
----------

import libsonic

conn = libsonic.Connection('http://localhost' , 'admin' , 'password')
print conn.ping()

"""

from connection import *

__version__ = '0.6.2'
