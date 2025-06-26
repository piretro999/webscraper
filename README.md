
# 🌐 Galora.versia – Web Update Monitor & Localization Editor

> An advanced Python-based tool for monitoring website updates, exporting pages to PDF, and detecting changes using one of three strategies — now with version history tracking and comparison via the new `VersioNice` tab.

---

## 🆕 What’s New (June 2025) – Galora.versia

The project is now called **Galora.versia**, and introduces a major new feature:  
🔄 **File versioning and content comparison.**

### 🔍 New Tab 4 – VersioNice
- Explore all saved outputs from previous sessions (`output_*.csv`, PDFs, HTML, TXT)
- Select and compare two versions of the same page
- View semantic `diff` with highlighted changes (powered by `difflib`)
- Visual preview of text and PDF content directly within the GUI
- Easily track document evolution across time

---

## 🔧 Features

### 🕸 Web Update Monitor
- Read list of URLs from a CSV file
- Detect updates using:
  - **Explicit date extraction** (via XPath + formatting rules)
  - **Hash comparison** (HTML snapshot fingerprint)
  - **Semantic similarity** (via difflib)
- Automatically download PDF when changes are detected
- Save structured logs: both output and errors as CSV
- Supports Chrome Debug mode with `--remote-debugging-port`
- Multilingual interface (driven by `locales.json`)
- Embedded GUI video (visual only) for feedback while scraping

### 🌍 JSON Localization Editor
- Full-featured GUI to edit `locales.json`
- Highlight missing translations across all configured languages
- Auto-fill untranslated entries using English as fallback
- Add / Remove / Edit keys across multiple languages
- Respects original JSON structure and allows custom sorting

---

## 🧩 GUI Tabs

| Tab   | Name               | Description                                                    |
|--------|--------------------|----------------------------------------------------------------|
| Tab 1 | **Process Setup**   | Load CSV input, configure output paths, enable debug mode      |
| Tab 2 | **Process Pages**   | Run the scraping process, monitor status, and track changes    |
| Tab 3 | **Advanced Settings** | Set up XPath selectors, formats, thresholds per domain         |
| Tab 4 | **VersioNice** 🆕    | Browse historical documents and compare previous versions      |

---

## 🖼️ Screenshots

### Tab 1 – Process Setup
![Tab 1](resources/tab1_process_setup.png)

### Tab 2 – Process Pages
![Tab 2](resources/tab2_process_pages.png)

### Tab 3 – Advanced Settings
![Tab 3](resources/tab3_advanced_settings.png)

### Tab 4 – VersioNice
![Tab 4](resources/tab4_versionice.png)

---

## 💾 Download Windows Executable

You can download the latest **Galora.versia** executable (.ZIP) for Windows here:

🔗 [Download Galora.versia – Windows Executable (ZIP)](https://1drv.ms/u/c/f8709043f1d7bc46/EXPXitmpmH9MnNc4DL7x4TsBpcmTM7HqOpcP3X3UCAS1ow?e=VbcOJz)

> No Python installation required – just extract and run `webscraper_NEW20250529.exe`.

---

## 📦 Requirements

- **Python 3.9+**
- **Google Chrome installed**
- **ChromeDriver** (auto-handled via `webdriver_manager`)
- Python dependencies:
  - selenium
  - psutil
  - imageio
  - Pillow
  - tkinterdnd2
  - bs4
  - python-dateutil
  - difflib
  - pikepdf
  - fitz (PyMuPDF)

```bash
pip install -r requirements.txt
```

---

## 🔐 Security Hardening (as of May–June 2025)

✅ **Chrome Launch Hardening**
- Uses --user-data-dir with temporary isolated profiles
- Verifies chrome_path is whitelisted and exists physically
- Restricts --remote-debugging-port=9222 to localhost only
- Chrome launched headless, with flags disabling:
  - extensions
  - notifications
  - popup-blocking
  - JavaScript
  - automation hints

✅ **Config.json Validation**
- Strict type/value checks enforced:
  - "pdf_mode" must be one of: "with_links", "no_links", "image"
  - "save_format" must be "pdf" or "png"
  - "log_level" must be a valid logging level
  - "sites" section must be a dictionary
  - "chrome_path" is validated and cannot be altered via GUI

✅ **Path & File Safety**
- File paths are sanitized via sanitize_filename() and safe_join()
- PDFs are validated, SHA256-hashed, and optionally rasterized
- You can optionally store a .sha256 file next to each PDF

✅ **Network Filtering**
- URL access restricted to explicitly allowed domains
- URLs with direct IPs, directory traversal (../), or encoded injection attempts (%, <, >) are rejected

✅ **Logging Hygiene**
- Logs are written to /log/, with:
  - Rotation and size limits
  - Separate logging for normal, detection, and critical events
  - GUI only shows safe summaries
  - Raw HTML snapshots are saved only when Debug Mode is on

---

## ▶️ How to Use

Launch the Web Scraper:
```bash
python webscraper_NEW20250529.py
```

Launch the Localization Editor:
```bash
python traduzioneJson.py
```

---

## 🗂️ Project Structure

```
📁 output/                  # PDF, CSV, and TXT exports
📁 log/                     # All log files (rotating, categorized)
📁 semantics/               # Text diffs for historical comparisons
📁 resources/               # GUI screenshots (used in README)
📄 config.json              # Main scraper configuration
📄 locales.json             # Translations for multilingual interface
📄 webscraper_NEW20250529.py # Main scraper – Galora.versia version
📄 traduzioneJson.py        # Localization editor GUI
📄 galora.versia.mp4        # Playful video shown while scraping
📄 requirements.txt         # Python dependencies
📄 LICENSE                  # MIT license
```

---

## ✍️ Summary

Galora.versia is a powerful tool to:
- Monitor institutional or regulatory websites
- Detect content updates (explicit or subtle)
- Export pages as sanitized PDFs
- Keep a history of document versions
- Compare them visually and semantically
- Maintain a multilingual UI with JSON localization

---

## 🔒 License

MIT License – see the LICENSE file for full terms.

---

## 👤 Author

Created by Paolo Forte  
with support from the open-source community.

