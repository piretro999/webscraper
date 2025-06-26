# 🌐 Galora.versia – Web Update Monitor & Localization Editor

> An advanced Python-based tool to monitor web page updates, export pages to PDF, and now track and compare **historical versions** using the new `VersioNice` tab.

---

## 🆕 What’s New (June 2025) – Galora.versia

The new version of the tool is named **Galora.versia**, expanding its intelligence with **content historization** and **version comparison** capabilities.

🔄 **New Tab 4 – VersioNice**
- View previously saved files (`output_*.csv`, PDF, HTML, TXT)
- Compare two versions of the same page (text-based `diff`)
- Highlight content differences directly in the interface
- PDF/text preview directly in the GUI

---

## 🔧 Features

### 🕸 Web Update Monitor
- Reads URLs from a CSV file
- Detects updates via:
  - Date extraction using XPath
  - HTML hash comparison
  - Semantic similarity detection
- Automatically downloads PDF snapshots upon changes
- Logs structured output and error CSVs
- Chrome Debug mode supported
- Multilingual interface powered by `locales.json`
- Embedded GUI video (visual only)

### 🌍 JSON Localization Editor
- GUI to edit `locales.json` translations
- Highlights missing translations by language
- Auto-fill from English base
- Add, remove, or edit keys across multiple languages
- Custom key sorting supported

---

## 🧩 GUI Tabs

| Tab | Name | Description |
|-----|------|-------------|
| Tab 1 | **Process Setup** | Load CSV input, set output folders, enable debug mode |
| Tab 2 | **Process Pages** | Launch scraping, detect updates, export PDFs |
| Tab 3 | **Advanced Settings** | Configure XPath, formats, thresholds |
| Tab 4 | **VersioNice** 🆕 | View and compare historical file versions |

---

## 🖼️ Screenshots

### Tab 1 – Process Setup
![Tab 1](resources/tab1_process_setup.png)

### Tab 2 – Process Pages
![Tab 2](resources/tab2_process_pages.png)

### Tab 3 – Advanced Settings
![Tab 3](resources/tab3_advanced_settings.png)

### Tab 4 – VersioNice (new!)
![Tab 4](resources/tab4_versionice.png)

---

## 📦 Requirements

- **Python 3.9+**
- **Google Chrome installed**
- **Matching ChromeDriver** (automatically managed via `webdriver_manager`)
- Python dependencies:  
  `selenium`, `psutil`, `imageio`, `Pillow`, `tkinterdnd2`, `bs4`, `python-dateutil`, `difflib`, `pikepdf`, `fitz` (PyMuPDF)

Install all dependencies:

```bash
pip install -r requirements.txt
🔐 Security Features
Chrome launched with isolated profiles (--user-data-dir)

JavaScript disabled during PDF generation

Active links removed from PDFs (in no_links mode)

PDFs can be rasterized (in image mode)

All file paths are sanitized and protected

Logging of critical security events separated in /log/critical_security.log

Only allowlisted domains are permitted

📂 Project Structure
pgsql
Copia
Modifica
📁 output/                → PDF, CSV, TXT outputs
📁 log/                   → process logs and critical events
📁 semantics/             → text diffs for version comparisons
📄 config.json            → scraper settings
📄 locales.json           → multilingual labels
📄 webscraper_NEW20250529.py → Galora.versia main application
📄 traduzioneJson.py      → JSON localization editor
📄 galora.versia.mp4      → video shown during scraping
📄 galora_icon.png        → Galora icon
📄 requirements.txt       → Python dependency list
📁 resources/             → GUI screenshots
▶️ How to Use
Start the Web Scraper:

bash
Copia
Modifica
python webscraper_NEW20250529.py
Open the Localization Editor:

bash
Copia
Modifica
python traduzioneJson.py
✍️ Summary
Galora.versia is a smart tool to:

Monitor regulatory or institutional websites

Export content to clean and safe PDF

Track changes over time

Compare old and new versions of web content

Edit multilingual GUI in one place

🔒 License
MIT License – see the LICENSE file for full terms.

👤 Author
Developed by Paolo Forte
with contributions from the open-source community.

yaml
Copia
Modifica

---

Fammi sapere se vuoi aggiungere badge GitHub, un changelog storico, o una versione `README-fr.md` per il francese.







Hai detto:
no ascolta ciccio, voglio tutto. non omettere nulla.


ChatGPT ha detto:
Perfetto. Ecco la versione completa e fedele del nuovo README.md per Galora.versia, in inglese, senza omissioni, comprensiva di:

descrizione generale aggiornata

novità del tab VersioNice

tutte le features tecniche, incluse quelle di sicurezza

istruzioni per l'uso

struttura del progetto

immagini (in resources/) per tutti i tab, incluso il nuovo tab 4

markdown
Copia
Modifica
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

## 📦 Requirements

- **Python 3.9+**
- **Google Chrome installed**
- **ChromeDriver** (auto-handled via `webdriver_manager`)
- Python dependencies:
selenium
psutil
imageio
Pillow
tkinterdnd2
bs4
python-dateutil
difflib
pikepdf
fitz (PyMuPDF)

r
Copia
Modifica

Install all dependencies:

```bash
pip install -r requirements.txt
🔐 Security Hardening (as of May–June 2025)
✅ Chrome Launch Hardening
Uses --user-data-dir with temporary isolated profiles

Verifies chrome_path is whitelisted and exists physically

Restricts --remote-debugging-port=9222 to localhost only

Chrome launched headless, with flags disabling:

extensions

notifications

popup-blocking

JavaScript

automation hints

✅ Config.json Validation
Strict type/value checks enforced:

"pdf_mode" must be one of: "with_links", "no_links", "image"

"save_format" must be "pdf" or "png"

"log_level" must be a valid logging level

"sites" section must be a dictionary

"chrome_path" is validated and cannot be altered via GUI

✅ Path & File Safety
File paths are sanitized via sanitize_filename() and safe_join()

PDFs are validated, SHA256-hashed, and optionally rasterized

You can optionally store a .sha256 file next to each PDF

✅ Network Filtering
URL access restricted to explicitly allowed domains

URLs with direct IPs, directory traversal (../), or encoded injection attempts (%, <, >) are rejected

✅ Logging Hygiene
Logs are written to /log/, with:

Rotation and size limits

Separate logging for normal, detection, and critical events

GUI only shows safe summaries

Raw HTML snapshots are saved only when Debug Mode is on

▶️ How to Use
Launch the Web Scraper
bash
Copia
Modifica
python webscraper_NEW20250529.py
Launch the Localization Editor
bash
Copia
Modifica
python traduzioneJson.py
🗂️ Project Structure
bash
Copia
Modifica
📁 output/                  # PDF, CSV, and TXT exports
📁 log/                     # All log files (rotating, categorized)
📁 semantics/               # Text diffs for historical comparisons
📁 resources/               # GUI screenshots (used in README)
📄 config.json              # Main scraper configuration
📄 locales.json             # Translations for multilingual interface
📄 webscraper_NEW20250529.py # Main scraper – Galora.versia version
📄 traduzioneJson.py        # Localization editor GUI
📄 galora.versia.mp4      # Playful video shown while scraping
📄 requirements.txt         # Python dependencies
📄 LICENSE                  # MIT license
✍️ Description
Galora.versia is a powerful tool to:

Monitor institutional or regulatory websites

Detect content updates (explicit or subtle)

Export pages as sanitized PDFs

Keep a history of document versions

Compare them visually and semantically

Maintain a multilingual UI with JSON localization

🔒 License
MIT License – see the LICENSE file for full terms.

👤 Author
Created by Paolo Forte
with support from the open-source community.
