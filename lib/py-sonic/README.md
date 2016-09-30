# py-sonic #

## INSTALL ##

Installation is fairly simple.  Just do the standard install as root:

    tar -xvzf py-sonic-*.tar.gz
    cd py-sonic-*
    python setup.py install

You can also install directly using *pip* or *easy_install*

    pip install py-sonic

## PYTHON 3 ##

I've added experimental support for Python 3.  This is not fully tested, but I
do encourage people to fork the repository and test off the "python3" branch
and issue pull requests.  If you don't want to go through that trouble, bug
reports are always welcome too!

## USAGE ##

This library follows the REST API almost exactly (for now).  If you follow the 
documentation on http://www.subsonic.org/pages/api.jsp or you do a:

    pydoc libsonic.connection

I have also added documentation at http://stuffivelearned.org/doku.php?id=programming:python:py-sonic

## BASIC TUTORIAL ##

This is about as basic as it gets.  We are just going to set up the connection
and then get a couple of random songs.

```python
#!/usr/bin/env python

from pprint import pprint
import libsonic

# We pass in the base url, the username, password, and port number
# Be sure to use https:// if this is an ssl connection!
conn = libsonic.Connection('https://music.example.com' , 'myuser' , 
    'secretpass' , port=443)
# Let's get 2 completely random songs
songs = conn.getRandomSongs(size=2)
# We'll just pretty print the results we got to the terminal
pprint(songs)
```

As you can see, it's really pretty simple.  If you use the documentation 
provided in the library:

    pydoc libsonic.connection

or the api docs on subsonic.org (listed above), you should be able to make use
of your server without too much trouble.

Right now, only plain old dictionary structures are returned.  The plan 
for a later release includes the following:

* Proper object representations for Artist, Album, Song, etc.
* Lazy access of members (the song objects aren't created until you want to
  do something with them)

## TODO ##

In the future, I would like to make this a little more "pythonic" and add
some classes to wrap up the data returned from the server.  Right now, the data
is just returned in the form of a dict, but I would like to have actual
Song, Album, Folder, etc. classes instead, or at least an alternative.  For
now, it works.

*NOTE:* I've noticed a wart with the upstream Subsonic API wherein any
of the Connection methods that would normally return a list of dictionary
elements (getPlaylists() for example), will only return a dictionary if there
is a single return element.  I plan on changing this in py-sonic so that
any methods of that nature will *always* return a list, even if there is
only a single dict in the list.
