# Video Player for Blender

Watch **internet or local videos without leaving Blender**. Paste a URL (YouTube, Vimeo,
direct link… any site supported by [yt-dlp](https://github.com/yt-dlp/yt-dlp)) or pick a local
file, and the video opens playing inside Blender **with audio** and **auto-fitting** to its
window size.

Made for following tutorials while you model.

---

## ✨ Features

- ▶️ Plays **internet videos** (YouTube and 1000+ sites via yt-dlp) and **local files**.
- 🔊 **Video + audio** synchronized inside Blender.
- 🔳 **Auto-fit**: frames the video on load and **re-fits when you resize** the area.
- 💾 URLs are **downloaded** (more reliable than streaming) and optionally **saved** where you choose.
- 🧹 **Unload button**: removes the video and audio from the scene and **restores the
  timeline** (frame range, FPS, sync) exactly as it was before loading.
- 📦 **Self-contained**: yt-dlp is bundled; buttons to **update yt-dlp** and **install ffmpeg**.
- 🖥️ **Cross-platform**: Windows, macOS and Linux.

---

## 📋 Requirements

- **Blender 4.2 or newer** (developed and tested on 5.1).
- **ffmpeg** to download from YouTube in maximum quality (merges separate video + audio).
  - On **Linux/macOS** it's usually available (`sudo apt install ffmpeg`, `brew install ffmpeg`).
  - On **Windows** it isn't bundled with the OS: use the panel's **"Install ffmpeg"** button
    (downloads `imageio-ffmpeg`) or install it yourself and add it to PATH. *Without ffmpeg* it
    still works, but download quality may be limited (~720p) and some videos will fail.
- To hear audio: **Edit → Preferences → System → Sound**, with *Audio Device* other than *None*.
- `yt-dlp` is **bundled** (no separate install needed). Internet is only needed to download
  videos and for the update/install-dependency buttons.

---

## 📥 Installation

1. Download the `.zip` from the [latest release](../../releases) (or build it, see *Development*).
2. In Blender: **Edit → Preferences → Get Extensions → ▾ → Install from Disk…** and pick the zip.
   *(You can also drag the zip onto the Blender window.)*
3. Enable it if it isn't enabled automatically.

---

## 🚀 Usage

Panel in **3D Viewport → `N` sidebar → "Video" tab**:

1. Choose the source: **Internet URL** or **Local file**.
2. Paste the URL (or select the file). For URLs, check *Keep local copy* and a folder if you want
   to save the download (otherwise it goes to a temp dir).
3. Click **Load & Play**. For URLs you'll see the download progress.
4. Use **Play / Pause** to control playback. Resize the little video window: it re-fits by itself.
5. When you're done, click the **trash button** next to Play / Pause: it removes the video, its
   audio strip and the player window, and restores the timeline (frame range, FPS and sync mode)
   from before the load. Loading a video changes those scene settings; unloading puts them back.

Extra buttons: **Update yt-dlp** (if a site stops working), **Install ffmpeg** (appears if it's
missing), **Open in Browser** (fallback).

---

## ⚙️ How it works

- **Video** → loaded as a movie image in an **Image Editor**, which auto-fits and advances with
  the timeline. A lightweight monitor re-fits when the area size changes.
- **Audio** → a **sound strip** in the Video Sequence Editor, which plays during timeline
  playback (with *Sync to Audio*), even when the VSE is not visible.
- **Playback** → uses Blender's timeline: to model, pause; to watch, play.

The VSE preview was ruled out because its view can't be reliably auto-fitted from a script.

---

## 🧩 Compatibility

| Platform | Local files | Internet downloads |
|----------|:---:|:---|
| **Linux** | ✅ | ✅ (system ffmpeg) |
| **macOS** | ✅ | ✅ (system ffmpeg or "Install ffmpeg") |
| **Windows** | ✅ | ✅ with the **"Install ffmpeg"** button (or ffmpeg on PATH) |

The only bundled wheel is `yt-dlp` (pure Python, `py3-none-any`), valid on all platforms.

---

## ⚠️ Limitations and notices

- Playback uses Blender's timeline: while it plays it isn't comfortable to model (pause to work).
  It's the inherent trade-off of playing with audio inside Blender.
- If yt-dlp becomes outdated and a site fails, use **Update yt-dlp**. Local files **do not depend
  on yt-dlp**.
- **Legal notice**: downloading content from YouTube and other sites may violate their Terms of
  Service and copyright. Use only your own content, Creative Commons, or public domain. Use is at
  your own responsibility.

---

## 🛠️ Development

Pure logic (no `bpy`, testable with pytest) in `source.py`, `downloader.py`, `deps.py`; the
Blender layer in `player.py`, `operators.py`, `panel.py`, `properties.py`, `__init__.py`.

```bash
# Unit tests (mock yt-dlp/ffmpeg; no Blender needed):
python3 -m pytest tests/

# Integration test (player mount, inside Blender):
blender --background --python tests/test_player_integration.py

# Build the installable extension zip:
blender --command extension build
```

The yt-dlp wheel is obtained with `pip download yt-dlp --no-deps -d wheels/`.

---

## 📄 License

GPL-3.0-or-later. Bundles [yt-dlp](https://github.com/yt-dlp/yt-dlp) (Unlicense).
