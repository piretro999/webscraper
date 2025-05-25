# 🌐 Web Update Monitor & Localization Editor

An advanced Python-based tool for **monitoring website updates**, exporting pages to **PDF**, and detecting changes using **one of three strategies**:  
- **Explicit date extraction via XPath**
- **Hash comparison**
- **Semantic text similarity**

Includes a GUI-based JSON editor to manage the multilingual interface via `locales.json`.

---

## 🔧 Features

### 🕸 Web Update Monitor
- Reads list of URLs from a CSV file
- Detects updates using:
  -  **Date extraction** from specific HTML elements (XPath + formatting rules)
  -  **Hash comparison** to detect structural changes
  -  **Semantic similarity** to detect content changes
- Automatically downloads a PDF snapshot when changes are detected
- Saves structured CSV logs (output and errors)
- Chrome Debug mode supported
- Multilingual interface powered by `locales.json`
- Embedded GUI video (visual only)

### 🌍 JSON Localization Editor
- GUI for editing `locales.json`
- Highlights missing translations per language
- Auto-fill from English (`en`)
- Add/remove/edit translation keys across multiple languages
- Maintains JSON structure and allows custom key sorting

---

## 🖼️ Screenshots

### 🧩 Tab 1 – Process Setup
This tab allows you to load your CSV input, set output directories, and enable debug mode.

![Tab 1 – Process Setup](assets/tab1.png)

---

### 📄 Tab 2 – Process Pages (with progress and detection)
Start the detection process, monitor progress, and observe updates based on date, hash, or semantic analysis.

![Tab 2 – Process Pages](assets/tab2.png)

---

### ⚙️ Tab 3 – Advanced Settings
Configure site-specific detection methods, XPath selectors, formats, and thresholds.

![Tab 3 – Advanced Settings](assets/tab3.png)

---

💾 Windows Executable available here (ZIP package):
https://1drv.ms/u/c/f8709043f1d7bc46/EXPXitmpmH9MnNc4DL7x4TsBpcmTM7HqOpcP3X3UCAS1ow?e=VbcOJz


## 📦 Requirements

- Python 3.9+
- Google Chrome installed
- Matching `chromedriver.exe` in the same directory of the .exe or .py
- Python dependencies:
  - `selenium`, `psutil`, `imageio`, `Pillow`, `tkinterdnd2`, `bs4`, `python-dateutil`

Install all dependencies:

```bash
pip install -r requirements.txt
```

---


## 🔧 New Features (2025-05)

- 🚀 PDF mode selector (with_links / no_links / image) with real-time GUI control.
- 🎥 Embedded video preview in GUI (via imageio + PIL), linked to process actions.
- 🔍 Automatic semantic or hash-based change detection with threshold.
- 🔐 Secure PDF handling:
  - JavaScript disabled during rendering (`--disable-javascript`)
  - All PDF links removed in "no_links" mode (via PikePDF)
  - PDF rasterization supported ("image" mode with PyMuPDF)
- 🧠 Intelligent logging:
  - Separate logs for normal process, critical events, and detection updates.
  - Rotating log files with size limits.
- 🛡️ Config validation with strict whitelisting and type checks.
- 📁 All logs now stored in `/log/` with automated creation and permission management.


## 🔐 Security Hardening (May 2025)

The application now includes multiple defensive layers to ensure secure automation of regulatory web portals:

### ✅ Chrome Launch Hardening
- Uses `--user-data-dir` with **temporary isolated profiles**
- Verifies `chrome_path` is in a hardcoded whitelist and exists physically
- Only allows `--remote-debugging-port=9222` on `127.0.0.1`
- Chrome launched in headless mode with multiple disabling flags (`popup-blocking`, `notifications`, `extensions`, etc.)

### ✅ Config.json Validation
- Strict value/type checking for keys like:
  - `"pdf_mode"` ∈ ["with_links", "no_links", "image"]
  - `"save_format"` ∈ ["pdf", "png"]
  - `"log_level"` ∈ standard logging levels
  - `"sites"` must be a dictionary

### ✅ Path Traversal & File Safety
- All output file paths are sanitized with `sanitize_filename()` and `safe_join()`
- PDF output is verified, hashed (SHA256), and optionally rasterized
- Optional saving of `.sha256` signature next to the PDF

### ✅ Network Filtering
- URLs must belong to an allowlist (`allowed_domains`)
- IP-based URLs and suspicious paths (e.g. `../`, `%`, `<`, `>`) are automatically rejected

### ✅ Logging Hygiene
- All logs written to `/log/`, rotated with size limits
- GUI displays only safe summaries, raw HTML optionally saved in debug mode only


## ▶️ How to Use

### Start the Web Scraper

```bash
python webscraper_NEW.py
```

### Launch the Localization Editor

```bash
python traduzioneJson.py
```

---

## 🗂️ Project Structure

```
📁 output/                # PDF and CSV output
📁 log/                   # Log files
📁 semantics/             # semantic txt files for version comparaison will be created here
📄 config.json            # Scraper configuration
📄 locales.json           # UI translations
📄 webscraper_NEW.py      # Main scraping application
📄 traduzioneJson.py      # JSON localization editor
📄 webscraperRobot.mp4    # Just a funny video running in Tab 2 while working.
📄 webscraper_icon.ico    # icon for compiling
📄 webscraper_icon.ico    # Original icon png
📄 webscraper_leggero.bat # Batch to create an exe file. you need appropriate include
📄 requirements.txt       # requirements to make the script work into a python environment
```

---

## ✍️ Description

> **Web update monitor with PDF export, date parsing, hash and semantic change detection**

---

## 🔒 License

MIT License – see the `LICENSE` file for full details.

---

## 👤 Author

**Paolo Forte**  


Install all dependencies:

```bash
pip install -r requirements.txt

