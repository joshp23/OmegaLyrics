# OmegaLyrics
A versitile lyrics plugin for the [Quod Libet](https://github.com/quodlibet/quodlibet) audio player

---

This plugin first attempts to load either tag or file-based lyrics, and will then attempt to load lyrics from the web using the [Lyrics.ovh](https://quodlibet.readthedocs.io/en/latest/) API, if needed.

### Installation
- Clone this repo (or extract the `events` folder) into `~/.quodlibet/plugins` or `~./config/quodlibet/plugins` with:
```
git clone https://github.com/joshp23/OmegaLyrics.git ~/.config/quodlibet/plugins
```
- Restart Quod Libet
- Enable the plugin under `Files -> Plugins -> Events -> Omega Lyrics`

---
Credit:
This plugin builds on / borrows from the native Quod Libet plugins `View Lyrics` and `Web Lyrics` 
