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

class SonicError(Exception):
    pass

class ParameterError(SonicError):
    pass

class VersionError(SonicError):
    pass

class CredentialError(SonicError):
    pass

class AuthError(SonicError):
    pass

class LicenseError(SonicError):
    pass

class DataNotFoundError(SonicError):
    pass

class ArgumentError(SonicError):
    pass

# This maps the error code numbers from the Subsonic server to their
# appropriate Exceptions
ERR_CODE_MAP = {
    0: SonicError ,
    10: ParameterError ,
    20: VersionError ,
    30: VersionError ,
    40: CredentialError ,
    50: AuthError ,
    60: LicenseError ,
    70: DataNotFoundError ,
}

def getExcByCode(code):
    code = int(code)
    if code in ERR_CODE_MAP:
        return ERR_CODE_MAP[code]
    return SonicError
