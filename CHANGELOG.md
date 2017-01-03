# Changelog

## v2.0.X
Released XXX
* Added multilanguage support

## v2.0.5
Released 15 October 2016
* Fixed images when listing entries

## v2.0.4
Released 5 October 2016
* Cache (permanently) starred items so we can know everywhere if an item is starred or not without querying it
* Colorize starred items
* Hide artist in lists if it is unique
* Removed list_artist_albums()
* Include simpleplugin v2.0.1 as library and remove KODI dependency

## v2.0.3
Released 4 October 2016
* Random tracks submenu
* Download tracks
* Star tracks
* Context menu for downloading or marking items as favorite

## v2.0.2
* main code (main.py) fully rewritten
* Use SimplePlugin framework (http://romanvm.github.io/script.module.simpleplugin/index.html)
* Cache datas

## v2.0.1
* New setting 'albums_per_page'
* New menu structure
* Albums : Newest / Most played / Rencently played / by Genre
* Tracks : Starred / Random by genre / Random by year
* Upgraded: libsonic to v.0.5.0 (https://github.com/crustymonkey/py-sonic)
* Code cleanup

## v2.0.0
Released 14 September 2015

Highlight:
* Added: support for starred items.
* Fixed: transcode format property was incorrect.
* Improved: playlist handling.
* Improved: metadata.
* Upgraded: libsonic.
* Upgraded: libsonic_extra.s

The full list of commits can be found [here](https://github.com/rembo10/headphones/compare/v1.0.0...v2.0.0).

## v1.0.0
Released 31 May 2015

Highlights:
* Added: support for playlists.
* Added: number of random items to show.
* Improved: metadata for items.
* Fixed: migrated to [`py-sonic`](https://github.com/crustymonkey/py-sonic) to interact with Subsonic.

The full list of commits can be found [here](https://github.com/rembo10/headphones/compare/ff86dfa49f914a18233dee295df74b73a70200e8...v1.0.0).
