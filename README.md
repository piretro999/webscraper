# 🌐 Galora.versia – Web Update Monitor & Localization Editor

An advanced Python-based tool to monitor web page updates, export pages to PDF, and now track and compare historical versions using the new **VersioNice** tab.

---

## 🆕 What’s New (June 2025) – Galora.versia

The new version of the tool is named **Galora.versia**, expanding its intelligence with **content historization** and **version comparison** capabilities.

### 🔄 New Tab 4 – VersioNice

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

| Tab   | Name               | Description                                       |
|--------|--------------------|---------------------------------------------------|
| Tab 1 | Process Setup       | Load CSV input, set output folders, enable debug |
| Tab 2 | Process Pages       | Launch scraping, detect updates, export PDFs     |
| Tab 3 | Advanced Settings   | Configure XPath, formats, thresholds             |
| Tab 4 | VersioNice 🆕        | View and compare historical file versions        |

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

- Python 3.9+
- Google Chrome installed
- Matching ChromeDriver (automatically managed via `webdriver_manager`)
- Python dependencies:

```bash
selenium
psutil
imageio
Pillow
tkinterdnd2
bs4
python-dateutil
difflib
pikepdf
fitz  # PyMuPDF
Install all dependencies:

bash
Copia
Modifica
pip install -r requirements.txt
🔐 Security Features
✅ Chrome launched with isolated profiles (--user-data-dir)
Prevents contamination from personal sessions

✅ JavaScript disabled during PDF generation
Reduces the risk of malicious execution

✅ Active links removed from PDFs (no_links mode)
Prevents unintentional navigation or tracking

✅ PDFs can be rasterized (image mode)
Optional fallback for full visual capture

✅ All file paths are sanitized and protected
Ensures safe output even from unsafe URLs

✅ Critical logs separated in /log/critical_security.log
Tracks warnings, errors, and suspicious behavior

✅ Only allowlisted domains are permitted
Any other domain or IP-based link is rejected

🗂️ Project Structure
pgsql
Copia
Modifica
📁 output/                  → PDF, CSV, TXT outputs
📁 log/                     → process logs and critical events
📁 semantics/               → text diffs for version comparisons
📁 resources/               → GUI screenshots
📄 config.json              → scraper settings
📄 locales.json             → multilingual labels
📄 webscraper_NEW20250529.py → Galora.versia main application
📄 traduzioneJson.py        → JSON localization editor
📄 galora.versia.mp4        → video shown during scraping
📄 galora_icon.png          → Galora icon
📄 requirements.txt         → Python dependency list
📄 LICENSE                  → MIT license
▶️ How to Use
Start the Web Scraper
bash
Copia
Modifica
python webscraper_NEW20250529.py
Open the Localization Editor
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

👤 Author
Created by Paolo Forte
with support from the open-source community.
