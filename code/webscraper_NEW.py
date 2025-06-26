import json
import os
import csv
import time
import logging
from logging.handlers import RotatingFileHandler
import threading
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from datetime import datetime
import psutil
from webdriver_manager.chrome import ChromeDriverManager
import sys
import re
from urllib.parse import urlparse
import pikepdf
import hashlib
import difflib
from bs4 import BeautifulSoup
from dateutil.parser import parse as parse_date
import base64
import fitz  # PyMuPDF
from PIL import Image
import imageio
from PIL import ImageTk
import io
from tkinterdnd2 import TkinterDnD
AVAILABLE_LANGUAGES = ["it", "en", "fr", "de", "es", "sw"]

# === Config ===
CONFIG_FILE = "config.json"
LOG_FILE ="process_log.txt"
DEFAULT_CONFIG = {
    "csv_path": "",
    "html_save_path": "",
    "output_csv_path": "",
    "timeout": 10,
    "language": "en",
    "save_format": "pdf",
    "enable_logs": True,
    "force_download": False,
    "use_debug_mode": False,
    "log_file": LOG_FILE,
    "chrome_path": "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    "allowed_domains": ["ec.europa.eu", "agenziaentrate.gov.it"]
}

CHROME_PATH_ALLOWED = [
    "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe"
]

def validate_config(config):
    errors = []

    # Percorso Chrome: whitelist + file esistente
    chrome_path = os.path.normpath(config.get("chrome_path", ""))
    allowed_normalized = [os.path.normpath(p) for p in CHROME_PATH_ALLOWED]
    if chrome_path not in allowed_normalized or not os.path.isfile(chrome_path):
        errors.append(f"chrome_path non valido o inesistente: {chrome_path}")

    # Timeout: deve essere intero positivo
    if not isinstance(config.get("timeout", 10), int) or config["timeout"] < 0:
        errors.append("timeout deve essere un intero positivo")

    # Lingua
    if not isinstance(config.get("language", "en"), str):
        errors.append("language deve essere una stringa")

    # allowed_domains: deve essere lista
    if not isinstance(config.get("allowed_domains", []), list):
        errors.append("allowed_domains deve essere una lista di domini autorizzati")

    # Modalità PDF
    if config.get("pdf_mode") not in ["with_links", "no_links", "image"]:
        errors.append(f"pdf_mode non valido: {config.get('pdf_mode')}")

    # Formato di salvataggio
    if config.get("save_format") not in ["pdf", "png"]:
        errors.append(f"save_format non valido: {config.get('save_format')}")

    # Log level (se presente)
    if "log_level" in config and config.get("log_level") not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
        errors.append(f"log_level non valido: {config.get('log_level')}")

    # Configurazione siti
    if "sites" in config and not isinstance(config.get("sites"), dict):
        errors.append("La sezione 'sites' deve essere un dizionario")

    if errors:
        raise ValueError("Configurazione non valida:\n" + "\n".join(errors))

    return config




# Function: load_config
# Description: Function to load config.
# Inputs: None
# Output: Dict
# Called by: __init__, load_sites_into_table, process_pages, save_config, save_debug_level
# Calls: open, save_config
def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)
            return validate_config(config)
    else:
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG


# Function: load_locale
# Description: Function to load locale.
# Inputs: lang
# Output: [None]
# Called by: __init__, on_language_change
# Calls: open, print
def load_locale(lang="en"):
    """
    Carica le impostazioni locali dal file 'locales.json' per la lingua specificata.
    """
    try:
        with open("locales.json", encoding="utf-8") as f:
            return json.load(f).get(lang, {})
    except Exception as e:
        print(f"[Locale] Errore caricamento: {e}")
        return {}

# Inizializzazione della variabile 'locale' con la lingua predefinita
locale = load_locale("en")

# Configurazione del logging utilizzando la variabile 'locale'
#logging.basicConfig(
#    level=logging.DEBUG,
#    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
#    handlers=[
#        logging.FileHandler(locale.get("selenium_debuglog", "selenium_debug.log")),
#        logging.StreamHandler()
#    ]
#)
# === Logging eventi critici separato ===
base_dir = os.path.dirname(os.path.abspath(__file__))  # Percorso corrente del file
log_dir = os.path.join(base_dir, "log")
os.makedirs(log_dir, exist_ok=True)
critical_log_path = os.path.join(log_dir, "critical_security.log")





critical_handler = logging.FileHandler(critical_log_path, encoding="utf-8")
critical_handler.setLevel(logging.WARNING)  # Solo WARNING, ERROR, CRITICAL
critical_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logging.getLogger().addHandler(critical_handler)
# Caricamento della configurazione dell'applicazione
config = load_config()  # Assicurati che questa funzione sia definita altrove nel tuo codice

# Aggiornamento della variabile 'locale' con la lingua specificata nella configurazione
locale = load_locale(config.get("language", "en"))


def sanitize_filename(name):
    """
    Rende sicuro un nome file rimuovendo o sostituendo caratteri non validi per il filesystem.
    """
    name = re.sub(r'[\\/*?:"<>|]', "_", name)
    name = re.sub(r'[\x00-\x1f\x7f]', "", name)
    if not name.strip():
        raise ValueError("Nome file vuoto non consentito")
    return name.strip()

# Function: save_config
# Description: Function to save config.
# Inputs: cfg
# Output: [None]
# Called by: load_config, on_language_change, save_debug_level
# Calls: eval, float, len, load_config, open, print, save_config_to_file
def save_config(cfg):
    """
    Salva il file di configurazione solo se valido.
    """
    validated = validate_config(cfg)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(validated, f, indent=2, ensure_ascii=False)


def safe_join(base_dir, unsafe_name):
    safe_name = sanitize_filename(unsafe_name)
    full_path = os.path.abspath(os.path.join(base_dir, safe_name))
    if not full_path.startswith(os.path.abspath(base_dir)):
        raise ValueError("Tentativo di directory traversal bloccato")
    return full_path


# === VideoPlayer (imageio + PIL) ===



class VideoPlayer:
    def __init__(self, canvas, path):
        self.canvas = canvas
        self.path = path
        self.thread = None
        self.stop_flag = threading.Event()
        self.pause_flag = threading.Event()
        self.image_id = None
        self.loop = False
        self.fit_canvas = False

    def start(self, loop=False, fit_canvas=False):
        self.loop = loop
        self.fit_canvas = fit_canvas
        self.stop_flag.clear()
        self.pause_flag.clear()
        if not self.thread or not self.thread.is_alive():
            self.thread = threading.Thread(target=self._play_video)
            self.thread.start()

        # Bind events for keyboard and window state
        self._bind_events()

    def pause(self):
        self.pause_flag.set()

    def resume(self):
        self.pause_flag.clear()

    def stop(self):
        self.stop_flag.set()

    def _play_video(self):
        try:
            reader = imageio.get_reader(self.path)
            fps = reader.get_meta_data()['fps']
            while not self.stop_flag.is_set():
                for frame in reader:
                    if self.stop_flag.is_set():
                        break
                    while self.pause_flag.is_set():
                        time.sleep(0.1)
                    frame_image = Image.fromarray(frame)

                    if self.fit_canvas and self.canvas:
                        canvas_width = self.canvas.winfo_width()
                        canvas_height = self.canvas.winfo_height()
                        frame_image = frame_image.resize((canvas_width, canvas_height), Image.Resampling.LANCZOS)

                    tk_image = ImageTk.PhotoImage(frame_image)
                    self.canvas.img = tk_image  # keep reference
                    if self.image_id is None:
                        self.image_id = self.canvas.create_image(0, 0, anchor="nw", image=tk_image)
                    else:
                        self.canvas.itemconfig(self.image_id, image=tk_image)
                    self.canvas.update_idletasks()
                    time.sleep(1 / fps)
                if not self.loop:
                    break
            reader.close()
        except Exception as e:
            print(locale.get("localegetvideoplaybackerror_err", f"{locale.get('video_playback_error', 'Errore durante la riproduzione del video')}: {e}"))


    def _bind_events(self):
        self.canvas.bind_all("<Key>", self._on_key)
        self.canvas.bind("<Unmap>", lambda event: self.pause())
        self.canvas.bind("<Map>", lambda event: self.resume())
        self.canvas.focus_set()

    def _on_key(self, event):
        if event.keysym == "space":
            if self.pause_flag.is_set():
                self.resume()
            else:
                self.pause()
        elif event.keysym.lower() == "s":
            self.stop()






# Function: is_chrome_debug_running
# Description: Function to is chrome debug running.
# Inputs: port
# Output: False
# Called by: launch_chrome_debug_if_needed, process_pages
# Calls: [none]
def is_chrome_debug_running(port=9222):
    """
    Function: is_chrome_debug_running
    Description: Function to is chrome debug running.
    Args:
        port
    Returns:
        False
    """
    for proc in psutil.process_iter(['name', 'cmdline']):
        try:
            if 'chrome' in proc.info['name'].lower():
                cmdline = ' '.join(proc.info['cmdline']).lower()
                if f'--remote-debugging-port={port}' in cmdline:
                    return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    return False


# Function: launch_chrome_debug_if_needed
# Description: Function to launch chrome debug if needed.
# Inputs: chrome_path, port
# Output: [None]
# Called by: get_debug_driver
# Calls: FileNotFoundError, is_chrome_debug_running
def launch_chrome_debug_if_needed(chrome_path, port=9222, locale=None):
    """
    Avvia Chrome in modalità debug con profilo isolato temporaneo.
    Controlla se già in esecuzione con profilo autorizzato, altrimenti avvia nuovo e fa cleanup.
    """
    import tempfile
    import shutil
    import atexit

    def extract_user_data_dir(cmdline):
        for part in cmdline.split():
            if part.startswith("--user-data-dir="):
                return part.split("=", 1)[1].strip('"')
        return None

    # === CONTROLLO: Chrome già attivo sulla porta 9222? ===
    if is_chrome_debug_running(port):
        #logging.info("Porta di debug già in uso. Controllo processo.")
        logging.debug(locale.get("debug_port_already_in_use_checking_process"))
        for proc in psutil.process_iter(['name', 'cmdline']):
            try:
                if 'chrome' in proc.info['name'].lower():
                    cmdline = ' '.join(proc.info['cmdline']).lower()
                    if f'--remote-debugging-port={port}' in cmdline:
                        active_dir = extract_user_data_dir(cmdline)
                        if active_dir:
                            logging.info(f"Chrome debug attivo con profilo: {active_dir}")
                            return
                        else:

                            logging.debug(locale.get("debug_port_used_by_unknown_or_unisolated_profile"))
                            from tkinter import messagebox
                            messagebox.showwarning(
                                "Sicurezza",
                                "Chrome è attivo con un profilo sconosciuto (senza --user-data-dir)."
                            )
                            return
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return

    # === CREAZIONE profilo solo ora ===
    if not os.path.exists(chrome_path):
        raise FileNotFoundError(
            f"{locale.get('chrome_not_found_in_specified_path', 'Chrome non trovato nel percorso specificato')}: {chrome_path}"
        )

    user_data_dir = tempfile.mkdtemp(prefix="chrome_debug_profile_")
    logging.info(f"Profilo Chrome temporaneo creato in: {user_data_dir}")

    def cleanup_temp_dir():
        try:
            shutil.rmtree(user_data_dir)
            logging.info(f"Profilo temporaneo rimosso: {user_data_dir}")
        except Exception as e:
            logging.warning(f"Errore durante la rimozione del profilo temporaneo {user_data_dir}: {e}")

    atexit.register(cleanup_temp_dir)

    args = [
        chrome_path,
        f"--remote-debugging-port={port}",
        "--remote-debugging-address=127.0.0.1",
        "--remote-allow-origins=http://localhost",
        f"--user-data-dir={user_data_dir}",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-popup-blocking"
    ]

    subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(3)



# Function: get_debug_driver
# Description: Function to retrieve debug driver.
# Inputs: chrome_path
# Output: [None]
# Called by: process_pages
# Calls: Options, RuntimeError, launch_chrome_debug_if_needed
def get_debug_driver(chrome_path):
    """
    Function: get_debug_driver
    Description: Function to retrieve debug driver.
    Args:
        chrome_path
    Returns:
        [None]
    """
    """
    Restituisce un WebDriver connesso a una sessione Chrome in modalità debug.
    """
    try:
        launch_chrome_debug_if_needed(chrome_path)
        options = Options()
        options.debugger_address = "127.0.0.1:9222"
        driver = webdriver.Chrome(options=options)
        return driver
    except Exception as e:
        logging.error(locale.get("error_connecting_browesr_debug_mode", f"Errore nel connettersi al browser in modalità debug: {e}"))
        raise RuntimeError(locale.get("ensure_chrome_started_with_debug_flag", "Assicurati che Chrome sia avviato correttamente con il flag --remote-debugging-port=9222")) from e



# Default configuration structure
DEFAULT_CONFIG = {
    "csv_path": "",
    "html_save_path": "",
    "output_csv_path": "",
    "timeout": 10,
    "language": "en",
    "save_format": "pdf",
    "enable_logs": True,
    "force_download": False,
    "use_debug_mode": False,  # <- nuovo
    "log_file": LOG_FILE,
    "use_debug_mode": False,   
    "chrome_path": "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"  # <- NON modificabile dalla GUI
}


DEFAULT_CONFIG = {
    "video_autoplay": True,
    "volume": 100
}


# Function: load_config
# Description: Function to load config.
# Inputs: None
# Output: [None]
# Called by: __init__, load_sites_into_table, process_pages, save_config, save_debug_level
# Calls: open, save_config
def load_config():
    """
    Function: load_config
    Description: Function to load config.
    Args:
        None
    Returns:
        [None]
    """
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as file:
            return json.load(file)
    else:
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG
    

# Function: save_config_to_file
# Description: Function to save config to file.
# Inputs: config_data, config_path
# Output: [None]
# Called by: save_config, save_debug_level
# Calls: open
def save_config_to_file(config_data, config_path=CONFIG_FILE):
    """
    Function: save_config_to_file
    Description: Function to save config to file.
    Args:
        config_data, config_path
    Returns:
        [None]
    """
    """Salva il dizionario di configurazione nel file JSON specificato."""
    import json
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config_data, f, indent=4, ensure_ascii=False)


# Function: write_log
# Description: Function to write log.
# Inputs: log_file, message
# Output: [None]
# Called by: save_page_as_pdf_with_selenium
# Calls: open
def write_log(log_file, message):
    """
    Function: write_log
    Description: Function to write log.
    Args:
        log_file, message
    Returns:
        [None]
    """
    if log_file:
        with open(log_file, "a") as log:
            log.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {message}\n")


# Function: read_csv
# Description: Function to read csv.
# Inputs: csv_path
# Output: [None]
# Called by: process_pages
# Calls: FileNotFoundError, list, open
def read_csv(csv_path):
    """
    Legge un file CSV in modalità posizionale, ignorando l'intestazione.
    Restituisce una lista di righe, dove ciascuna riga è una lista di valori.

    Args:
        csv_path (str): Percorso del file CSV.

    Returns:
        Tuple: (data, fieldnames)
            - data: lista di liste (righe del CSV, escluse le intestazioni)
            - fieldnames: intestazioni fisse ["Url", "Nome Nazione", "Data precedentemente rilevata", "Data Ultimo Aggiornamento"]
    """
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    with open(csv_path, mode="r", encoding="utf-8") as file:
        reader = csv.reader(file, delimiter=';')
        try:
            next(reader)  # Salta l'intestazione
        except StopIteration:
            raise ValueError("CSV file is empty or missing header")

        data = []
        for row in reader:
            # Ignora righe vuote o incomplete
            if len(row) < 4:
                continue
            data.append(row[:4])  # Usa solo i primi 4 campi

    # Intestazioni fisse, indipendenti dal contenuto del file
    fieldnames = ["Url", "Nome Nazione", "Data precedentemente rilevata", "Data Ultimo Aggiornamento"]

    return data, fieldnames




# Function: write_csv
# Description: Function to write csv.
# Inputs: data, output_path, fieldnames
# Output: [None]
# Called by: [unknown]
# Calls: open
def write_csv(data, output_path, fieldnames, use_localization=True):
    """
    Scrive un file CSV con i dati forniti.

    Args:
        data (list[dict]): Lista di righe da scrivere (dizionari con chiavi standard come 'Url', ecc.).
        output_path (str): Percorso del file CSV di destinazione.
        fieldnames (list[str]): Lista delle chiavi standard da usare nei dizionari ('Url', ecc.).
        use_localization (bool): Se True, usa i nomi localizzati come intestazioni.
    """
    if use_localization:
        localized_fieldnames = [locale.get(fn.lower().replace(" ", "_"), fn) for fn in fieldnames]
    else:
        localized_fieldnames = fieldnames

    with open(output_path, mode="w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=localized_fieldnames, delimiter=';')
        writer.writeheader()

        for row in data:
            mapped_row = {}
            for fn in fieldnames:
                key = locale.get(fn.lower().replace(" ", "_"), fn) if use_localization else fn
                mapped_row[key] = row.get(fn, "")
            writer.writerow(mapped_row)




# Function: translate_month
# Description: Function to translate month.
# Inputs: date_str
# Output: date_str
# Called by: parse_date_with_translation
# Calls: [none]
def translate_month(date_str):
    """
    Function: translate_month
    Description: Function to translate month.
    Args:
        date_str
    Returns:
        date_str
    """
    months_translation = {
        "gen": "Jan", "feb": "Feb", "mar": "Mar", "apr": "Apr",
        "mag": "May", "giu": "Jun", "lug": "Jul", "ago": "Aug",
        "set": "Sep", "ott": "Oct", "nov": "Nov", "dic": "Dec"
    }
    for ita, eng in months_translation.items():
        date_str = date_str.replace(ita, eng)
    return date_str


# Function: parse_date_with_translation
# Description: Function to parse date with translation.
# Inputs: date_str
# Output: [None]
# Called by: extract_last_updated_with_selenium
# Calls: parse_date, translate_month
def parse_date_with_translation(date_str):
    """
    Function: parse_date_with_translation
    Description: Function to parse date with translation.
    Args:
        date_str
    Returns:
        [None]
    """
    try:
        translated_date_str = translate_month(date_str)
        return parse_date(translated_date_str)
    except Exception as e:
        logging.error(locale.get("localegeterrorparsingdate_error", f"{locale.get('error_parsing_date', 'Error parsing date')} '{date_str}': {e}"))
        raise


# Function: get_base_dir
# Description: Function to retrieve base dir.
# Inputs: None
# Output: [None]
# Called by: extract_last_updated_with_selenium, process_pages, save_page_as_pdf_with_selenium
# Calls: getattr
def get_base_dir():
    """
    Function: get_base_dir
    Description: Function to retrieve base dir.
    Args:
        None
    Returns:
        [None]
    """
    """
    Restituisce il percorso della directory in cui si trova lo script (anche se compilato con PyInstaller).
    """
    if getattr(sys, 'frozen', False):
        # Se eseguito come .exe (PyInstaller)
        return os.path.dirname(sys.executable)
    else:
        # Se eseguito come script Python normale
        return os.path.dirname(os.path.abspath(__file__))


# Function: ensure_directory_exists
# Description: Function to ensure directory exists.
# Inputs: path
# Output: [None]
# Called by: process_pages, save_page_as_pdf_with_selenium
# Calls: [none]
def ensure_directory_exists(path):
    """
    Crea la directory se non esiste. Rende i permessi restrittivi (0700 su Unix).
    """
    if not os.path.exists(path):
        os.makedirs(path)
        try:
            os.chmod(path, 0o700)
        except Exception:
            pass
        logging.info(f"Created directory: {path}")


# Function: save_page_as_pdf_with_selenium
# Description: Function to save page as pdf with selenium.
# Inputs: url, output_path, timeout, log_file
# Output: [None]
# Called by: process_pages
# Calls: FileNotFoundError, Options, Service, ensure_directory_exists, get_base_dir, open, write_log
def save_page_as_pdf_with_selenium(url, output_path, timeout, debug_mode=False, log_file=None):
    """
    Salva una pagina web come PDF. Se la pagina è vuota o fallisce la generazione del PDF,
    salva uno screenshot PNG come fallback.

    Args:
        url (str): L'URL della pagina da salvare.
        output_path (str): Percorso completo per il file PDF.
        timeout (int): Tempo massimo di attesa per il caricamento della pagina.
        log_file (str): Percorso del file di log (opzionale).

    Returns:
        bool: True se il PDF è stato salvato correttamente, False altrimenti.
    """
    try:
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-javascript")
        driver = webdriver.Chrome(service=Service("chromedriver.exe"), options=options)
        driver.get(url)

        # Rimuovi script e iframe prima della stampa
        driver.execute_script("""
            let scripts = document.querySelectorAll('script, iframe');
            scripts.forEach(e => e.remove());
        """)

        if debug_mode:
            from urllib.parse import urlparse
            from datetime import datetime
        
            parsed = urlparse(url)
            host = parsed.hostname.replace(".", "_") if parsed.hostname else "unknownhost"
            ts = datetime.now().strftime("%Y%m%d-%H%M%S")
            debug_dir = os.path.join(get_base_dir(), "debug_html")
            os.makedirs(debug_dir, exist_ok=True)
            filename = os.path.join(debug_dir, f"debug_{host}_{ts}.html")

        
            html = driver.execute_script("return document.documentElement.outerHTML;")
            with open(filename, "w", encoding="utf-8") as f:
                f.write(html)
            logging.info(f"HTML salvato per debug: {filename}")

        time.sleep(timeout)

        # Verifica contenuto testuale
        body_text = driver.execute_script("return document.body.innerText.trim();")
        if not body_text:
            logging.warning(f"Pagina vuota per {url}, PDF non generato.")
            screenshot_path = output_path.replace(".pdf", ".png")
            driver.save_screenshot(screenshot_path)
            logging.info(f"Screenshot salvato come fallback: {screenshot_path}")
            driver.quit()
            return False

        # Log HTML troncato
        html_sample = driver.execute_script("return document.body.innerHTML;")
        html_sample = html_sample[:200] + "..." if len(html_sample) > 200 else html_sample
        if debug_mode:
            logging.debug(f"[{url}] HTML troncato: {html_sample}")
        else:
            logging.debug(locale.get("html_debug_deactivated", f"[{url}] Modalità debug disattivata, HTML non loggato."))


        # Genera PDF
        result = driver.execute_cdp_cmd("Page.printToPDF", {
            "printBackground": True,
            "preferCSSPageSize": True
        })

        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        with open(output_path, "wb") as f:
            f.write(base64.b64decode(result["data"]))

        # Firma SHA256 del PDF
        import hashlib
        pdf_hash = hashlib.sha256(open(output_path, 'rb').read()).hexdigest()
        logging.info(f"SHA256 PDF: {pdf_hash}")

        logging.info(f"PDF salvato in {output_path}")
        driver.quit()
        return True

    except Exception as e:
        logging.error(f"Errore durante il salvataggio PDF da {url}: {e}")
        return False




# Function: extract_last_updated_with_selenium
# Description: Function to extract last updated with selenium.
# Inputs: url, timeout
# Output: [None]
# Called by: [unknown]
# Calls: Options, Service, get_base_dir, parse_date_with_translation
def extract_last_updated_with_selenium(url, timeout):
    """
    Function: extract_last_updated_with_selenium
    Description: Function to extract last updated with selenium.
    Args:
        url, timeout
    Returns:
        [None]
    """
    driver_path = os.path.join(get_base_dir(), "chromedriver.exe")
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    # chrome_options.add_argument("--no-sandbox")

    service = Service(driver_path)
    driver = webdriver.Chrome(service=service, options=chrome_options)

    try:
        logging.info(locale.get("navigating_to_url_for_extracting", "Navigating to {url} for extracting 'Last updated' date.").format(url=url))

        driver.get(url)
        time.sleep(timeout)

        element = driver.find_element("xpath", "//span[@class='conf-macro output-inline' and @data-macro-name='last-updated']")
        last_updated_text = element.text.strip()
        logging.info(locale.get("last_updated_date_found", "'Last updated' date found: {last_updated_text}").format(last_updated_text=last_updated_text))

        return parse_date_with_translation(last_updated_text)
    except Exception as e:
        logging.error(locale.get("error_extracting_last_updated_date", "Error extracting 'Last updated' date for {url}: {e}").format(url=url, e=e))

        return None
    finally:
        driver.quit()

def setup_secure_logging(log_file_path=LOG_FILE, max_bytes=1048576, backup_count=5):
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    ensure_directory_exists(os.path.dirname(log_file_path))
    handler = RotatingFileHandler(log_file_path, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8")
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.addHandler(console_handler)
    # logging.info("Logging configurato in modo sicuro e con rotazione.")
    logging.warning(locale.get("debug_port_used_by_unknown_or_unisolated_profile"))
def get_secure_chrome_options():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-extensions")
    options.add_argument("--no-first-run")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--disable-translate")
    options.add_argument("--window-size=1920,1080")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    return options

def is_domain_allowed(url, allowed_domains):
    parsed = urlparse(url)
    netloc = parsed.netloc.lower()
    for allowed in allowed_domains:
        if netloc == allowed or netloc.endswith("." + allowed):
            return True
    return False

def sanitize_pdf_links(pdf_path):
    try:
        with pikepdf.open(pdf_path, allow_overwriting_input=True) as pdf:
            for page in pdf.pages:
                if "/Annots" in page:
                    page.Annots = []
            pdf.save(pdf_path)
            logging.info(f"Rimossi link attivi da: {pdf_path}")
    except Exception as e:
        logging.warning(f"Errore nella sanitizzazione PDF {pdf_path}: {e}")


def close_chrome_debug(port=9222):
    """
    Termina il processo Chrome avviato in modalità debug.
    """
    for proc in psutil.process_iter(['name', 'cmdline']):
        try:
            if 'chrome' in proc.info['name'].lower():
                cmdline = ' '.join(proc.info['cmdline']).lower()
                if f'--remote-debugging-port={port}' in cmdline:
                    proc.terminate()
                    # logging.info("Chrome debug terminato automaticamente.")
                    logging.info(locale.get("chrome_debug_terminated_automatically"))

        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue



# Function: process_pages
# Description: Function to process pages.
# Inputs: config, progress_table, progress_bar, progress_count, pause_event, stop_event
# Output: [None]
# Called by: run_process_pages
# Calls: Options, Service, ValueError, close_loggers, detect_page_change, ensure_directory_exists, enumerate, extract_date, get_base_dir, get_debug_driver, is_chrome_debug_running, len, load_config, open, read_csv, save_page_as_pdf_with_selenium, str, update_progress, urlparse, write_detection_log
def process_pages(config, progress_table, progress_bar, progress_count, locale, pause_event=None, stop_event=None):
    import os
    import csv
    import time
    import logging
    import psutil
    from datetime import datetime
    from urllib.parse import urlparse
    from tkinter import messagebox
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service

    def is_url_safe(url):
        from urllib.parse import urlparse
        import ipaddress
        parsed = urlparse(url)
        try:
            ipaddress.ip_address(parsed.hostname)
            return False  # Blocca URL con IP diretti
        except:
            pass
        return (
            parsed.scheme in ["http", "https"]
            and not any(x in parsed.path for x in ["..", "%", "<", ">", "\"", "'"])
        )

    def is_chrome_debug_running():
        for proc in psutil.process_iter(['name', 'cmdline']):
            try:
                if 'chrome.exe' in proc.info['name'].lower():
                    cmdline = ' '.join(proc.info['cmdline']).lower()
                    if '--remote-debugging-port=9222' in cmdline:
                        return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        return False

    timestamp_dir = datetime.now().strftime("%Y%m%d%H%M")
    save_path = os.path.join(config["html_save_path"], timestamp_dir)
    ensure_directory_exists(save_path)

    try:
        raw_data, fieldnames = read_csv(config["csv_path"])
    except Exception as e:
        logging.error(locale.get("error_reading_csv", "Errore durante la lettura del CSV: {e}").format(e=e))
        messagebox.showerror(
            locale.get("error_title", locale.get("error", "Errore")),
            locale.get("error_reading_csv", "Errore durante la lettura del CSV: {e}").format(e=e)
        )
        return

    site_configs = load_config().get("sites", {})
    total_rows = len(raw_data)
    progress_bar["maximum"] = total_rows
    progress_bar["value"] = 0
    progress_count.config(text=f"0/{total_rows}")

    standard_keys = ["Url", "Nome Nazione", "Data precedentemente rilevata", "Data Ultimo Aggiornamento"]
    localized_keys = [locale.get(k.lower().replace(" ", "_"), k) for k in standard_keys]
    error_fieldnames = localized_keys + [locale.get("errore", "Errore")]

    output_csv_path = os.path.join(save_path, f"output_{timestamp_dir}.csv")
    error_csv_path = os.path.join(save_path, f"errors_{timestamp_dir}.csv")

    use_debug = config.get("use_debug_mode", False)
    chrome_path = config.get("chrome_path", r"C:\Program Files\Google\Chrome\Application\chrome.exe")
    timeout = config["timeout"]

    if use_debug:
        launch_chrome_debug_if_needed(chrome_path)

    with open(output_csv_path, "w", encoding="utf-8", newline="") as outfile,open(error_csv_path, "w", encoding="utf-8", newline="") as errorfile:

        writer = csv.DictWriter(outfile, fieldnames=localized_keys, delimiter=';')
        writer.writeheader()
        error_writer = csv.DictWriter(errorfile, fieldnames=error_fieldnames, delimiter=';')
        error_writer.writeheader()

        for idx, row in enumerate(raw_data, start=1):
            if stop_event and stop_event.is_set():
                logging.info(locale.get("stop_requested", "Stop richiesto."))
                break
            if pause_event:
                while not pause_event.is_set():
                    if stop_event and stop_event.is_set():
                        return
                    time.sleep(0.5)

            url = row[0].strip()
            country_name = row[1].strip()
            current_signature = row[3].strip()
            if not is_url_safe(url):
                warning_msg = locale.get("url_non_sicuro_ignorato", f"URL non sicuro ignorato: {url}").format(url=url)
                logging.warning(warning_msg)
                continue
            if not is_domain_allowed(url, config.get("allowed_domains", [])):
                logging.warning(f"Dominio non autorizzato: {url}")
                continue

            parsed_url = urlparse(url)
            domain = parsed_url.netloc.replace("www.", "")
            site_config = site_configs.get(domain)

            progress_table.insert("", "end", values=(url, country_name, current_signature, locale.get("starting", "Inizio...")))
            progress_table.update_idletasks()

            record = {
                "Url": url,
                "Nome Nazione": country_name,
                "Data precedentemente rilevata": current_signature,
                "Data Ultimo Aggiornamento": ""
            }

            if not site_config:
                status = locale.get("config_not_found", "Config Not Found")
                progress_table.item(progress_table.get_children()[-1], values=(url, country_name, current_signature, status))
                writer.writerow({locale.get(k.lower().replace(" ", "_"), k): record[k] for k in standard_keys})
                update_progress(progress_bar, progress_count, idx, total_rows)
                continue

            try:
                driver = get_debug_driver(chrome_path) if use_debug else webdriver.Chrome(service=Service(os.path.join(os.getcwd(), "chromedriver.exe")), options=get_secure_chrome_options())
                driver.get(url)
                time.sleep(timeout)

                method = site_config.get("update_method", "date").lower()

                filename_base = url.split('/')[-1].split('?')[0].split('#')[0]
                filename = safe_join(save_path, f"{filename_base}.pdf")

                if method == "detection":
                    changed, new_signature, reason, similarity = detect_page_change(driver, site_config, current_signature, filename_base)
                    record["Data Ultimo Aggiornamento"] = new_signature

                    if changed or not current_signature or config.get("force_download", False):
                        saved = save_page_as_pdf_with_selenium(url, filename, timeout, config["log_file"])
                        if saved:
                            logging.warning(f"[DEBUG CHECK] PDF_MODE={config.get('pdf_mode')} | FILE={filename} | SAVED={saved}")
                            # Salva file TXT accanto al PDF, sempre e comunque
                            if saved:
                                try:
                                    extracted_text = extract_text_from_pdf(filename)
                                    txt_output_path = filename.replace(".pdf", ".txt")
                                    with open(txt_output_path, "w", encoding="utf-8") as f:
                                        f.write(extracted_text)
                                    logging.info(f"[TXT] Creato file testo: {txt_output_path}")
                                except Exception as e:
                                    logging.warning(f"[TXT] Errore durante salvataggio del TXT per {filename}: {e}")

                            if config.get("pdf_mode", "with_links") == "no_links":
                                sanitize_pdf_links(filename)
                            elif config.get("pdf_mode") == "image":
                                logging.info(f"[RASTER] Modalità 'PDF immagine' attiva per: {filename}")
                                image_paths = convert_pdf_to_images_fitz(filename)
                                if image_paths:
                                    replace_pdf_with_images_fitz(filename, image_paths)
                                else:
                                    logging.warning(f"[RASTER] Conversione PDF→immagine fallita, file originale mantenuto: {filename}")
                        else:
                            logging.error(f"[ERROR] Salvataggio PDF fallito per {filename}")
                        status = locale.get("PDF_Saved", "PDF salvato") if saved else locale.get("Error_saving_PDF", "Errore salvataggio PDF")
                        write_detection_log(f"[{country_name} - {url}] Metodo: {site_config.get('detection_type')} | Cambiata: {changed} | Similarità: {similarity:.3f} | PDF: {'SÌ' if saved else 'NO'}")
                    else:
                        status = locale.get("no_change_detected", "Nessun cambiamento")
                else:
                    try:
                        new_date = extract_date(driver, site_config)
                        if new_date in [locale.get("date_not_found", "DATE_NOT_FOUND"), locale.get("date_not_parsed", "DATE_NOT_PARSED")]:
                            raise ValueError(new_date)
                        new_date_str = new_date.strftime("%Y-%m-%d %H:%M:%S")
                        record["Data Ultimo Aggiornamento"] = new_date_str
                        if (new_date_str != current_signature) or config.get("force_download", False):
                            saved = save_page_as_pdf_with_selenium(
                                        url,
                                        filename,
                                        timeout,
                                        debug_mode=config.get("debug_mode", False),
                                        log_file=config["log_file"]
                                    )
                            if saved:
                                # Salva file TXT accanto al PDF, sempre e comunque
                                if saved:
                                    try:
                                        extracted_text = extract_text_from_pdf(filename)
                                        txt_output_path = filename.replace(".pdf", ".txt")
                                        with open(txt_output_path, "w", encoding="utf-8") as f:
                                            f.write(extracted_text)
                                        logging.info(f"[TXT] Creato file testo: {txt_output_path}")
                                    except Exception as e:
                                        logging.warning(f"[TXT] Errore durante salvataggio del TXT per {filename}: {e}")
                                logging.warning(f"[DEBUG CHECK] PDF_MODE={config.get('pdf_mode')} | FILE={filename} | SAVED={saved}")
                                if config.get("pdf_mode", "with_links") == "no_links":
                                    sanitize_pdf_links(filename)
                                elif config.get("pdf_mode") == "image":
                                    logging.info(f"[RASTER] Modalità 'PDF immagine' attiva per: {filename}")
                                    image_paths = convert_pdf_to_images_fitz(filename)
                                    if image_paths:
                                        replace_pdf_with_images_fitz(filename, image_paths)
                                    else:
                                        logging.warning(f"[RASTER] Conversione PDF→immagine fallita, file originale mantenuto: {filename}")
                            else:
                                logging.error(f"[ERROR] Salvataggio PDF fallito per {filename}")

                            status = locale.get("updated_and_pdf_saved", "Aggiornato e PDF salvato") if saved else locale.get("pdf_error", "Errore PDF")
                        else:
                            status = locale.get("no_update_needed", "Nessun aggiornamento necessario")
                    except Exception as ex:
                        record["Errore"] = str(ex)
                        progress_table.item(progress_table.get_children()[-1], values=(url, country_name, current_signature, record["Errore"]))
                        error_writer.writerow({locale.get(k.lower().replace(" ", "_"), k): record.get(k, "") for k in standard_keys} |
                                              {locale.get("errore", "Errore"): record["Errore"]})
                        writer.writerow({locale.get(k.lower().replace(" ", "_"), k): record.get(k, "") for k in standard_keys})
                        driver.quit()
                        update_progress(progress_bar, progress_count, idx, total_rows)
                        continue

                progress_table.item(progress_table.get_children()[-1], values=(url, country_name, record["Data Ultimo Aggiornamento"], status))
                if not use_debug:
                    driver.quit()

            except Exception as e:
                record["Errore"] = str(e)
                progress_table.item(progress_table.get_children()[-1], values=(url, country_name, current_signature, str(e)))
                error_writer.writerow({locale.get(k.lower().replace(" ", "_"), k): record.get(k, "") for k in standard_keys} |
                                      {locale.get("errore", "Errore"): record["Errore"]})

            writer.writerow({locale.get(k.lower().replace(" ", "_"), k): record.get(k, "") for k in standard_keys})
            update_progress(progress_bar, progress_count, idx, total_rows)

    messagebox.showinfo(locale.get("process_completed_title", "Processo completato"),
                        f"Output salvato: {output_csv_path}\nErrori: {error_csv_path}")
    if config.get("use_debug_mode", False):
        close_chrome_debug()
    close_loggers()

# Function: generate_signature_hash
# Description: Function to generate signature hash.
# Inputs: html_content
# Output: [call]
# Called by: detect_page_change
# Calls: BeautifulSoup, soup
def generate_signature_hash(html_content: str) -> str:
    """
    Function: generate_signature_hash
    Description: Function to generate signature hash.
    Args:
        html_content
    Returns:
        [call]
    """
    soup = BeautifulSoup(html_content, "html.parser")
    for tag in soup(["script", "style", "meta", "noscript"]):
        tag.decompose()
    clean_text = soup.get_text(separator=" ", strip=True)
    return hashlib.sha256(clean_text.encode("utf-8")).hexdigest()



# Function: generate_signature_text
# Description: Function to generate signature text.
# Inputs: driver
# Output: [call]
# Called by: detect_page_change
# Calls: [none]
def generate_signature_text(driver) -> str:
    """
    Function: generate_signature_text
    Description: Function to generate signature text.
    Args:
        driver
    Returns:
        [call]
    """
    body = driver.find_element("tag name", "body")
    return body.text.strip()



# Function: compute_text_similarity
# Description: Function to compute text similarity.
# Inputs: old_text, new_text
# Output: [call]
# Called by: detect_page_change
# Calls: [none]
def compute_text_similarity(old_text: str, new_text: str) -> float:
    """
    Function: compute_text_similarity
    Description: Function to compute text similarity.
    Args:
        old_text, new_text
    Returns:
        [call]
    """
    return difflib.SequenceMatcher(None, old_text, new_text).ratio()



# Function: parse_detection_signature
# Description: Function to parse detection signature.
# Inputs: signature_str
# Output: [None]
# Called by: detect_page_change
# Calls: float
def parse_detection_signature(signature_str: str) -> tuple[str, str, float]:
    """
    Function: parse_detection_signature
    Description: Function to parse detection signature.
    Args:
        signature_str
    Returns:
        [None]
    """
    try:
        timestamp, hash_val, similarity = signature_str.strip().split("_")
        return timestamp, hash_val, float(similarity)
    except ValueError:
        return "", "", 1.0  # valore di default se parsing fallisce



# Function: build_detection_signature
# Description: Function to build detection signature.
# Inputs: hash_val, similarity
# Output: [expression]
# Called by: detect_page_change
# Calls: [none]
def build_detection_signature(hash_val: str, similarity: float) -> str:
    """
    Function: build_detection_signature
    Description: Function to build detection signature.
    Args:
        hash_val, similarity
    Returns:
        [expression]
    """
    timestamp = datetime.now().isoformat(timespec="seconds")
    return f"{timestamp}_{hash_val}_{similarity:.3f}"



# Function: write_detection_log
# Description: Function to write detection log.
# Inputs: message
# Output: [None]
# Called by: process_pages
# Calls: open
def write_detection_log(message: str):
    """
    Scrive un messaggio nel file 'detection.log' nella directory 'log/' dello script.

    Args:
        message (str): Messaggio completo da registrare nel log.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_dir = os.path.join(get_base_dir(), "log")
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, "detection.log")

    try:
        with open(log_path, "a", encoding="utf-8") as log_file:
            log_file.write(f"[{timestamp}] {message}\n")
    except Exception as e:
        logging.error(f"Errore durante la scrittura del log detection: {e}")


# Function: detect_page_change
# Description: Function to detect page change.
# Inputs: driver, site_config, previous_signature
# Output: [expression]
# Called by: process_pages
# Calls: build_detection_signature, compute_text_similarity, float, generate_signature_hash, generate_signature_text, parse_detection_signature
def detect_page_change(driver, site_config: dict, previous_signature: str, filename_base: str) -> tuple[bool, str, str, float]:
    """
    Determina se la pagina è cambiata usando hash e/o similarità semantica.
    Salva o confronta i testi in 'semantics/' solo se richiesto dal metodo.

    Args:
        driver: WebDriver attivo sulla pagina
        site_config: Configurazione del sito corrente
        previous_signature: Firma precedente (hash + similarity)
        filename_base: Nome base del file (senza estensione)

    Returns:
        (page_changed: bool, new_signature: str, reason: str, similarity: float)
    """
    import os

    method = site_config.get("detection_type", "hash")
    threshold = float(site_config.get("detection_threshold", 0.900))

    # Directory dove salvare i testi semantic
    semantics_dir = os.path.join(get_base_dir(), "semantics")
    ensure_directory_exists(semantics_dir)
    txt_path = os.path.join(semantics_dir, f"{filename_base}.txt")

    # Parsing firma precedente
    _, old_hash, old_sim = parse_detection_signature(previous_signature or "___1.0")

    html_content = driver.page_source
    new_hash = generate_signature_hash(html_content) if method in ["hash", "both"] else "XXX"
    new_text = generate_signature_text(driver) if method in ["semantic", "both"] else ""
    similarity = 1.0
    old_text = ""

    if method in ["semantic", "both"] and os.path.exists(txt_path):
        with open(txt_path, "r", encoding="utf-8") as f:
            old_text = f.read()

    if method == "semantic":
        similarity = compute_text_similarity(old_text, new_text)
        if not old_text or similarity < threshold:
            # Cambiamento semantico
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(new_text)
            page_changed = True
            reason = locale.get("similarity_below_threshold", "similarità {similarity:.3f} < {threshold:.3f}").format(similarity=similarity, threshold=threshold)
        else:
            page_changed = False
            reason = "No semantic change"

    elif method == "hash":
        page_changed = new_hash != old_hash
        reason = locale.get("hash_different", "hash differente") if page_changed else "Hash identical"

    elif method == "both":
        page_changed = False
        if new_hash != old_hash:
            if old_text:
                similarity = compute_text_similarity(old_text, new_text)
                if similarity < threshold:
                    page_changed = True
                    with open(txt_path, "w", encoding="utf-8") as f:
                        f.write(new_text)
                    reason = locale.get("hash_and_similarity_below_threshold", "hash differente e similarità {similarity:.3f} < {threshold:.3f}").format(similarity=similarity, threshold=threshold)
                else:
                    reason = "Hash changed, semantic similarity ok"
            else:
                page_changed = True
                with open(txt_path, "w", encoding="utf-8") as f:
                    f.write(new_text)
                reason = "Hash changed, no previous semantic text"
        else:
            reason = "Hash identical"

    else:
        page_changed = False
        reason = "Unknown method"

    new_signature = build_detection_signature(new_hash, similarity)
    return page_changed, new_signature, reason, similarity

    
import logging


# Function: close_loggers
# Description: Function to close loggers.
# Inputs: None
# Output: [None]
# Called by: process_pages
# Calls: [none]
def close_loggers():
    """
    Function: close_loggers
    Description: Function to close loggers.
    Args:
        None
    Returns:
        [None]
    """
    """
    Chiude tutti i gestori di log attivi, inclusi quelli configurati da Selenium.
    """
    logging.info(locale.get("chiudendo_tutti_i_gestori_di_log", "Chiudendo tutti i gestori di log..."))
    handlers = logging.root.handlers[:]
    for handler in handlers:
        try:
            handler.close()
        except Exception as e:
            #logging.error(locale.get("errore_durante_la_chiusura_del_gestore_d", f"Errore durante la chiusura del gestore di log: {e}"))
            logging.error(locale.get("error_closing_log_handler", "Errore durante la chiusura del gestore di log: {e}").format(e=e))

        finally:
            logging.root.removeHandler(handler)

    # Rimuove i gestori specifici di Selenium
    selenium_logger = logging.getLogger(locale.get("seleniumwebdriverremoteremote_connection", "selenium.webdriver.remote.remote_connection"))
    for handler in selenium_logger.handlers[:]:
        try:
            handler.close()
        except Exception as e:
            logging.error(locale.get("error_closing_selenium_handler", "Errore durante la chiusura del gestore Selenium: {e}").format(e=e))

        finally:
            selenium_logger.removeHandler(handler)

    logging.info(locale.get("tutti_i_gestori_di_log_sono_stati_chiusi_e_rimossi", "Tutti i gestori di log sono stati chiusi e rimossi."))




# Function: extract_date
# Description: Function to extract date.
# Inputs: driver, site_config
# Output: [None]
# Called by: process_pages
# Calls: identify_date_selector
def extract_date(driver, site_config):
    """
    Function: extract_date
    Description: Function to extract date.
    Args:
        driver, site_config
    Returns:
        [None]
    """
    """
    Estrae e analizza la data di aggiornamento da una pagina web.
    """
    try:
        date_selector = identify_date_selector(site_config.get("date_selector", ""))
        logging.info(locale.get("using_date_selector_dateselector", f"Using date selector: {date_selector}"))

        time.sleep(2)

        try:
            element = driver.find_element("xpath", date_selector)
        except Exception as e:
            logging.warning(locale.get("element_not_found_for_selector_datesel", f"Element not found for selector {date_selector}: {e}"))
            return locale.get("date_not_found", "DATE_NOT_FOUND")

        if not element:
            logging.warning(locale.get("no_element_found_for_selector_datesel", f"No element found for selector: {date_selector}"))
            logging.warning(locale.get("date_not_found", "Date not found"))
            return locale.get("date_not_found", "DATE_NOT_FOUND")

        date_text = element.text.strip()
        logging.info(locale.get("raw_date_text_datetext", f"Raw date text: {date_text}"))

        date_text = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', date_text)

        prefix_to_remove = site_config.get("prefix_to_remove", "")
        if prefix_to_remove:
            try:
                date_text = re.sub(prefix_to_remove, "", date_text).strip()
                logging.debug(locale.get("date_text_after_prefix_removal_datete", f"Date text after prefix removal: {date_text}"))
            except re.error as e:
                logging.error(locale.get("invalid_regex_in_prefixtoremove_e", f"Invalid regex in prefix_to_remove: {e}"))

        month_translations = site_config.get("month_translations", {})
        for ita, eng in month_translations.items():
            date_text = date_text.replace(ita, eng)

        date_format = site_config.get("date_format", "")
        try:
            parsed_date = datetime.strptime(date_text, date_format)
            logging.info(locale.get("parsed_date_with_format_parseddate", f"Parsed date with format: {parsed_date}"))
            return parsed_date
        except Exception as e:
            logging.warning(locale.get("failed_to_parse_date_datetext_with", f"Failed to parse date '{date_text}' with format '{date_format}': {e}"))
            return locale.get("date_not_parsed", "DATE_NOT_PARSED")

    except Exception as e:
        logging.error(locale.get("unexpected_error_extracting_date_e", f"Unexpected error extracting date: {e}"))
        return None





# Function: identify_date_selector
# Description: Function to identify date selector.
# Inputs: selector
# Output: selector
# Called by: extract_date
# Calls: [none]
def identify_date_selector(selector):
    """
    Function: identify_date_selector
    Description: Function to identify date selector.
    Args:
        selector
    Returns:
        selector
    """
    """
    Logga il selettore individuato e restituisce il selettore.
    """
    logging.info(locale.get("start_of_date_selector_identification", "*************** Start of Date Selector Identification ***************"))
    logging.info(locale.get("date_selector_identified_selector", f"Date selector identified: {selector}"))
    logging.info(locale.get("end_of_date_selector_identification", "*************** End of Date Selector Identification ***************"))
    return selector



# Funzione 14: run_process_pages
# Avvia il processo di elaborazione delle pagine in un thread separato per mantenere reattiva l'interfaccia grafica.
# Input:
#   - self: Riferimento all'istanza della classe App.
# Output: Nessuno.
# Chiamata da: start_process.
# Chiama: process_pages (funzione globale per l'elaborazione delle pagine).


# Function: run_process_pages
# Description: Function to run process pages.
# Inputs: self
# Output: [None]
# Called by: [unknown]
# Calls: process_pages
def run_process_pages(self):
    """
    Function: run_process_pages
    Description: Function to run process pages.
    Args:
        self
    Returns:
        [None]
    """
    """Esegue il processo principale usando i parametri configurati."""
    try:
        process_pages(
        config=self.config,
        progress_table=self.progress_table,
        progress_bar=self.progress_bar,
        progress_count=self.progress_count,
        locale=self.locale,  # <--- aggiunto!
        )
    except Exception as e:
        logging.error(locale.get("error_during_process_e", "Error during process: {e}").format(e=e))





# Function: update_progress
# Description: Function to update progress.
# Inputs: progress_bar, progress_count, completed, total
# Output: [None]
# Called by: process_pages
# Calls: [none]
def update_progress(progress_bar, progress_count, completed, total):
    """
    Function: update_progress
    Description: Function to update progress.
    Args:
        progress_bar, progress_count, completed, total
    Returns:
        [None]
    """
    
    """
    Aggiorna la barra di avanzamento e l'etichetta di progresso.
    """
    progress_bar["value"] = completed
    progress_count.config(text=f"{completed}/{total}")
    progress_bar.update_idletasks()




# Function: configure_logging
# Description: Function to configure logging.
# Inputs: log_level
# Output: [None]
# Called by: __init__, save_debug_level, test_logging
# Calls: [none]
def configure_logging(log_level):
    import os
    import logging
    from selenium.webdriver.remote.remote_connection import LOGGER as selenium_logger

    # 🔧 Mappa livelli stringa → logging levels
    level_mapping = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
        "NONE": logging.CRITICAL + 1,
    }

    # ✅ Converte stringa in livello effettivo
    desired_level = level_mapping.get(str(log_level).upper(), logging.INFO)

    # 🔧 Crea directory 'log' se non esiste
    log_dir = os.path.join(get_base_dir(), "log")
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, "selenium_debug.log")

    # ❌ Rimuove gestori esistenti
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
        try:
            handler.close()
        except Exception:
            pass

    # ✅ Configura logging su file + console
    logging.basicConfig(
        level=desired_level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler()
        ]
    )

    # 🔧 Applica lo stesso livello ai logger di Selenium
    selenium_logger.setLevel(desired_level)

    logging.info(f"Logging configurato al livello: {logging.getLevelName(desired_level)}")
    logging.info(f"Log file path: {log_path}")



# Function: test_logging
# Description: Function to test logging.
# Inputs: None
# Output: [None]
# Called by: [unknown]
# Calls: configure_logging, print
def test_logging():
    """
    Function: test_logging
    Description: Function to test logging.
    Args:
        None
    Returns:
        [None]
    """
    levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL", "NONE"]
    for level in levels:
        print(locale.get("ntesting_logging_at_level_level", f"\nTesting logging at level: {level}"))
        configure_logging(level)
        logging.debug(locale.get("this_is_a_debug_log", "This is a DEBUG log."))
        logging.info(locale.get("this_is_an_info_log", "This is an INFO log."))
        logging.warning(locale.get("this_is_a_warning_log", "This is a WARNING log."))
        logging.error(locale.get("this_is_an_error_log", "This is an ERROR log."))
        logging.critical(locale.get("this_is_a_critical_log", "This is a CRITICAL log."))




# Function: save_debug_level
# Description: Function to save debug level.
# Inputs: self
# Output: [None]
# Called by: [unknown]
# Calls: configure_logging, load_config, save_config, save_config_to_file
def save_debug_level(self):
    """
    Function: save_debug_level
    Description: Function to save debug level.
    Args:
        self
    Returns:
        [None]
    """
    """Save and apply the new debug level."""
    selected_level = self.log_level_var.get()  # Get the selected level
    self.config["log_level"] = selected_level  # Save it in the config
    save_config(self.config)  # Persist to file
    configure_logging(selected_level)  # Update logging dynamically

    # Test logging behavior
    logging.debug(locale.get("this_is_a_debug_log", "This is a DEBUG log."))
    logging.info(locale.get("this_is_an_info_log", "This is an INFO log."))
    logging.warning(locale.get("this_is_a_warning_log", "This is a WARNING log."))
    logging.error(locale.get("this_is_an_error_log", "This is an ERROR log."))
    logging.critical(locale.get("this_is_a_critical_log", "This is a CRITICAL log."))

    messagebox.showinfo(locale.get("config_saved_title", locale.get("saved", "Saved")), f"Logging level set to {selected_level}.")



# Function: build_treeview
# Description: Function to create a Treeview with standardized configuration and optional localized headers.
# Inputs: parent, columns, column_width=150, minwidth=100, locale=None, locale_keys=None
# Output: ttk.Treeview
# Called by: setup_tab1, setup_tab2, setup_tab3, load_csv
# Calls: ttk.Treeview

def build_treeview(parent, columns, column_width=150, minwidth=100, locale=None, locale_keys=None):
    """
    Create a Treeview with standardized configuration.

    Args:
        parent: Parent widget.
        columns: List of column identifiers.
        column_width: Default column width.
        minwidth: Minimum width per column.
        locale: Optional localization object.
        locale_keys: Optional list of locale keys matching the columns.

    Returns:
        Configured ttk.Treeview widget.
    """
    # Destroy previous children if regenerating
    for widget in parent.winfo_children():
        widget.destroy()

    tree = ttk.Treeview(parent, columns=columns, show="headings")
    for i, col in enumerate(columns):
        if locale and locale_keys and i < len(locale_keys):
            heading = locale.get(locale_keys[i], col)
        else:
            heading = col
        tree.heading(col, text=heading)
        tree.column(col, anchor="w", width=column_width, minwidth=minwidth, stretch=True)

    # Add scrollbar by default
    scrollbar = ttk.Scrollbar(parent, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)
    tree.pack(fill="both", expand=True, side="left")
    scrollbar.pack(side="right", fill="y")

    return tree

def extract_text_from_pdf(pdf_path, locale=None):
    try:
        doc = fitz.open(pdf_path)
        text = "\n".join([page.get_text() for page in doc])
        return text
    except Exception as e:
        message = "Error extracting PDF text."
        if locale:
            message = locale.get("pdf_extraction_error", message)
        logging.error(f"{message}: {e}")
        return ""


def diff_texts_colored(old_text, new_text):
    diff = difflib.ndiff(old_text.splitlines(), new_text.splitlines())
    result = []
    for line in diff:
        if line.startswith("  "):
            result.append(("black", line[2:]))
        elif line.startswith("- "):
            result.append(("red", line[2:]))
        elif line.startswith("+ "):
            result.append(("darkgreen", line[2:]))
    return result
def build_changes_index(base_path):
    changes_dir = os.path.join(base_path, "changes")
    os.makedirs(changes_dir, exist_ok=True)
    output = {}

    # 🔍 Costruisce elenco completo .txt già presenti
    existing_txt_paths = set()
    for root, _, files in os.walk(base_path):
        for file in files:
            if file.endswith(".txt"):
                relative_txt = os.path.relpath(os.path.join(root, file), base_path)
                existing_txt_paths.add(relative_txt.replace("\\", "/"))

    for root, dirs, files in os.walk(base_path):
        if root.startswith(changes_dir):
            continue
        for file in files:
            if file.endswith(".pdf"):
                pdf_path = os.path.join(root, file)
                relative_pdf = os.path.relpath(pdf_path, base_path).replace("\\", "/")
                timestamp = datetime.fromtimestamp(os.path.getmtime(pdf_path)).isoformat()

                txt_path = relative_pdf.replace(".pdf", ".txt")
                full_txt_path = os.path.join(base_path, txt_path)

                # ✅ VERIFICA tramite lista pre-esistente
                if txt_path in existing_txt_paths:
                    logging.info(f"[SKIP] File .txt già presente: {txt_path}")
                else:
                    try:
                        text = extract_text_from_pdf(pdf_path)
                        os.makedirs(os.path.dirname(full_txt_path), exist_ok=True)
                        with open(full_txt_path, "w", encoding="utf-8") as f:
                            f.write(text)
                        logging.info(f"[CREATO] {full_txt_path}")
                    except Exception as e:
                        logging.error(f"Errore nell'estrazione/scrittura di {file}: {e}")
                        continue

                url = os.path.basename(file).replace(".pdf", "")
                country = os.path.basename(os.path.dirname(root))

                if url not in output:
                    output[url] = {"country": country, "versions": []}

                output[url]["versions"].append({
                    "timestamp": timestamp,
                    "pdf_path": relative_pdf,
                    "txt_path": txt_path
                })

    output_path = os.path.join(changes_dir, "changes.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)


class App:
    def __init__(self, root):
        self.root = root
        self.config = load_config()
        self.locale = load_locale(self.config.get("language", "en"))
    
        # ✅ Estrae il livello di log come stringa
        log_level = self.config.get("log_level", "DEBUG")
        configure_logging(log_level)
    
        # 🔍 Test logging multilivello localizzato
        logging.debug(self.locale.get("logging_configured_to_loglevel", "Log configurato al livello") + f": {log_level}")
        logging.info(self.locale.get("test_info_log", "Questo è un log informativo"))
        logging.warning(self.locale.get("test_warning_log", "Questo è un log di avviso"))
        logging.error(self.locale.get("test_error_log", "Questo è un log di errore"))
    
        self.language_var = tk.StringVar(value=self.config.get("language", "en"))
        # Istanza senza canvas inizialmente
        self.video_player = VideoPlayer(canvas=None, path="Galora.versia.mp4")

        self.force_download_var = tk.BooleanVar(value=self.config.get("force_download", False))
        # Mappa modalità stringa → intero per il cursore
        pdf_mode_map = {"with_links": 0, "no_links": 1, "image": 2}
        initial_mode = self.config.get("pdf_mode", "with_links")
        self.pdf_mode_var = tk.IntVar(value=pdf_mode_map.get(initial_mode, 0))
        self.csv_data = []
        self.csv_columns = []
        self.csv_path = None

        self.setup_gui()

        self.video_player.canvas = self.video_canvas  # ✅ Qui il canvas è già creato
        self.load_initial_csv()
        configure_logging(self.config.get("log_level", "INFO"))

    def setup_gui(self):
        self.root.title(self.locale.get("web_scraper_and_updater", "Web Scraper and Updater"))
        self.root.geometry("1600x700")

        self.notebook = ttk.Notebook(self.root)  # ✅ Usa self
        self.notebook.pack(fill="both", expand=True)

        self.tab1 = ttk.Frame(self.notebook)
        self.tab2 = ttk.Frame(self.notebook)
        self.tab4 = ttk.Frame(self.notebook)
        self.tab3 = ttk.Frame(self.notebook)

        self.notebook.add(self.tab1, text=self.locale.get("process_setup", "Process Setup"))
        self.notebook.add(self.tab2, text=self.locale.get("process_pages", "Process Pages"))
        # self.notebook.add(self.tab4, text=self.locale.get("versioNice", "Versioni"))
        self.notebook.add(self.tab3, text=self.locale.get("advanced_settings", "Advanced Settings"))
        self.setup_tab1()
        self.setup_tab2()
        self.setup_tab4()
        self.setup_tab3()


    def refresh_ui_texts(self):
        widgets_to_update = {
            'label_file': "select_csv",
            'button_start': "start_process",
            'pause_button': "pause_process",
            'resume_button': "resume_process",
            'stop_button': "force_stop",
            'progress_label': "progress",
            'progress_count': "0/0",
            'add_site_btn': "add_site",
            'remove_site_btn': "remove_selected_site",
            'save_config_btn': "save_config",
            'debug_label': "selenium_debug_level",
            'save_debug_btn': "save_debug_level",
            'check_versions_btn': "check_chrome_and_chromedriver_version",
            'button_browse_csv': "browse",
            'button_browse_save': "browse",
            'checkbox_force_download': "force_download_pdf_if_date_missing_or_unchanged",
            'checkbox_debug_mode': "open_chrome_in_debug_mode",
            'button_add_record': "add_record",
            'button_remove_record': "remove_record",
            'button_save_csv': "save_csv",
            'reprocess_button': "reprocess_selected"
        }

        for attr_name, locale_key in widgets_to_update.items():
            widget = getattr(self, attr_name, None)
            if widget:
                widget.config(text=self.locale.get(locale_key, f"[{locale_key}]"))

        # TAB 1 — CSV Table
        if hasattr(self, 'progress_table'):
            for col_id in self.progress_table["columns"]:
                self.progress_table.heading(col_id, text=self.locale.get(col_id.lower(), col_id))

        if hasattr(self, 'csv_table') and hasattr(self, 'csv_columns'):
            progress_keys = ["url", "country", "previously_detected_date", "last_updated"]
            for i, col in enumerate(self.csv_columns):
                key = progress_keys[i] if i < len(progress_keys) else col.lower().replace(" ", "_")
                self.csv_table.heading(col, text=self.locale.get(key, col))

        # ✅ TAB 1 – Etichetta "Modalità PDF"
        if hasattr(self, 'label_pdf_mode'):
            self.label_pdf_mode.config(text=self.locale.get("pdf_mode", "Modalità PDF"))
            
            

        if hasattr(self, 'label_save_path'):
            self.label_save_path.config(text=self.locale.get("select_save_path", "Select Save Directory:"))
            
        if hasattr(self, 'pdf_mode_status_label') and hasattr(self, 'pdf_mode_slider'):
            self.pdf_mode_status_label.config(
                text=f"{self.locale.get('pdf_mode', 'Modalità PDF')}: {self.get_pdf_mode_label(self.pdf_mode_slider.get())}"
            )


        # ✅ Tab 1 – Aggiorna etichetta dinamica PDF
        if hasattr(self, 'pdf_mode_scale') and hasattr(self, 'on_pdf_mode_change'):
            try:
                current_value = int(self.pdf_mode_scale.get())
                self.on_pdf_mode_change(current_value)
            except Exception as e:
                logging.warning(f"Errore aggiornando etichetta PDF dinamica: {e}")


        # TAB 2 — Progress Table
        if hasattr(self, 'progress_table'):
            progress_keys = ["url", "country", "last_updated", "status"]
            for i, col in enumerate(self.progress_table["columns"]):
                self.progress_table.heading(col, text=self.locale.get(progress_keys[i], col))

        # ✅ TAB 2 – Timeout
        if hasattr(self, 'timeout_label'):
            self.timeout_label.config(text=self.locale.get("timeout_label", "Timeout (s):"))


        # TAB 3 — Site Table
        if hasattr(self, 'site_table'):
            site_keys = [
                "site", "method", "selector", "date_format", "language",
                "prefix", "month_translations", "day_translations", "detection_type", "threshold"
            ]
            for i, col in enumerate(self.site_table["columns"]):
                self.site_table.heading(col, text=self.locale.get(site_keys[i], col))

        # Notebook tab labels
        if hasattr(self, 'notebook'):
            self.notebook.tab(0, text=self.locale.get("process_setup", "Process Setup"))
            self.notebook.tab(1, text=self.locale.get("process_pages", "Process Pages"))
            self.notebook.tab(2, text=self.locale.get("versioNice", "Versioni"))
            self.notebook.tab(3, text=self.locale.get("advanced_settings", "Advanced Settings"))

        self.root.title(self.locale.get("web_scraper_and_updater", "Web Scraper and Updater"))



        # ✅ TAB 4 – Bottone "Aggiorna stato"
        if hasattr(self, 'update_versions_btn'):
            self.update_versions_btn.config(text=self.locale.get("update_state", "Aggiorna stato"))

        # ✅ TAB 4 – Treeview header
        if hasattr(self, 'versions_tree'):
            self.versions_tree.heading("#0", text=self.locale.get("versions_tree", "Versioni disponibili"))

        


    def setup_tab1(self):
        """Configura la scheda Process Setup (Tab 1) con immagine, campi, pulsanti, checkbox e tabella."""
    
        # Header con immagine e lingua
        header_frame = ttk.Frame(self.tab1)
        header_frame.pack(fill="x", padx=10, pady=10)
    
        # Immagine a sinistra
        try:
            self.tab1_img = tk.PhotoImage(file="webscraper_icon.png")
            self.tab1_img = self.tab1_img.subsample(8, 8)
            img_label = tk.Label(header_frame, image=self.tab1_img)
            img_label.pack(side="left", padx=10)
        except Exception as e:
            logging.warning(self.locale.get("error_loading_image_tab1", f"Errore caricamento immagine tab1: {e}"))
    
        # Menu lingua in alto a destra
        language_menu = ttk.Combobox(
            header_frame,
            textvariable=self.language_var,
            values=AVAILABLE_LANGUAGES,
            state="readonly",
            width=6
        )
        language_menu.pack(anchor="ne", side="right", padx=10)
        language_menu.bind("<<ComboboxSelected>>", self.on_language_change)
    
        # Area contenuti (input file + output + checkbox)
        content_frame = ttk.Frame(header_frame)
        content_frame.pack(side="left", fill="x", expand=True)
    
        # Selezione CSV
        self.label_file = tk.Label(content_frame, text=self.locale.get("select_csv", "Select CSV File:"))
        self.label_file.pack(anchor="w")
        self.csv_path_var = tk.StringVar(value=self.config.get("csv_path", ""))
        tk.Entry(content_frame, textvariable=self.csv_path_var, width=50).pack(anchor="w", pady=2)
        self.button_browse_csv = tk.Button(content_frame, text=self.locale.get("browse", "Browse"), command=self.select_csv)
        self.button_browse_csv.pack(anchor="w", pady=2)
    
        # Output directory
        self.label_save_path = tk.Label(content_frame, text=self.locale.get("select_save_path", "Select Save Directory:"))
        self.label_save_path.pack(anchor="w", pady=(10, 0))
        self.save_path_var = tk.StringVar(value=self.config.get("html_save_path", ""))
        tk.Entry(content_frame, textvariable=self.save_path_var, width=50).pack(anchor="w", pady=2)
        self.button_browse_save = tk.Button(content_frame, text=self.locale.get("browse", "Browse"), command=self.select_save_path)
        self.button_browse_save.pack(anchor="w", pady=2)
    
        # Checkbox per forzare download PDF
        self.force_download_var = tk.BooleanVar(value=self.config.get("force_download", False))
        self.checkbox_force_download = tk.Checkbutton(
            content_frame,
            text=self.locale.get("force_download_pdf_if_date_missing_or_unchanged", "Force download PDF anche se data non trovata o uguale"),
            variable=self.force_download_var
        )
        self.checkbox_force_download.pack(anchor="w", pady=5)

        self.label_pdf_mode = tk.Label(
            content_frame,
            text=self.locale.get("pdf_mode", "Modalità PDF")
        )
        self.label_pdf_mode.pack(anchor="w", pady=(5, 0))
        
        # Etichetta dinamica che mostra la modalità selezionata
        self.pdf_mode_label = tk.Label(content_frame)
        self.pdf_mode_label.pack(anchor="w")
        
        # Cursore modalità PDF (valori 0, 1, 2)
        self.pdf_mode_scale = tk.Scale(
            content_frame,
            from_=0,
            to=2,
            orient="horizontal",
            showvalue=False,
            variable=self.pdf_mode_var,
            command=self.on_pdf_mode_change,
            length=200
        )
        self.pdf_mode_scale.pack(anchor="w", pady=(0, 5))
        
        # Aggiorna inizialmente l'etichetta in base al valore corrente
        self.on_pdf_mode_change(self.pdf_mode_var.get())

    
        # Checkbox per Debug mode
        self.use_debug_mode_var = tk.BooleanVar(value=self.config.get("use_debug_mode", False))
        self.checkbox_debug_mode = tk.Checkbutton(
            content_frame,
            text=self.locale.get("open_chrome_in_debug_mode", "Apri Chrome in modalità debug"),
            variable=self.use_debug_mode_var
        )
        self.checkbox_debug_mode.pack(anchor="w", pady=2)
    
        # Frame tabella CSV
        self.csv_table_frame = ttk.Frame(self.tab1)
        self.csv_table_frame.pack(fill="both", expand=True, padx=10, pady=10)
    
        # Inizializza tabella vuota (verrà popolata da load_csv)
        self.csv_columns = []
        self.csv_table = build_treeview(
            parent=self.csv_table_frame,
            columns=[],
            locale=self.locale
        )

        # Abilita il drag and drop su csv_table
        self.root.drop_target_register('*')
        self.root.dnd_bind('<<Drop>>', self.on_treeview_file_drop) 
        
        # Pulsanti gestione tabella
        table_controls_frame = ttk.Frame(self.tab1)
        table_controls_frame.pack(fill="x", pady=10)
    
        self.button_add_record = ttk.Button(table_controls_frame, text=self.locale.get("add_record", "Add Record"), command=self.add_record)
        self.button_add_record.pack(side="left", padx=5)
    
        self.button_remove_record = ttk.Button(table_controls_frame, text=self.locale.get("remove_record", "Remove Selected"), command=self.remove_selected_record)
        self.button_remove_record.pack(side="left", padx=5)
    
        self.button_save_csv = ttk.Button(table_controls_frame, text=self.locale.get("save_csv", "Save CSV"), command=self.save_csv)
        self.button_save_csv.pack(side="right", padx=5)
    
        # Carica CSV se già impostato
        self.load_initial_csv()

    def on_pdf_mode_change(self, value):
        """Aggiorna l'etichetta della modalità PDF e la config"""
        mode_map = {
            0: self.locale.get("pdf_with_links", "PDF con link"),
            1: self.locale.get("pdf_no_links", "PDF senza link"),
            2: self.locale.get("pdf_image", "PDF immagine")
        }
    
        try:
            value = int(value)
        except ValueError:
            value = 0
    
        self.pdf_mode_label.config(text=mode_map.get(value, "PDF con link"))
    
        # Salva il valore corrispondente nella config
        reverse_map = {0: "with_links", 1: "no_links", 2: "image"}
        self.config["pdf_mode"] = reverse_map.get(value, "with_links")


    def reprocess_selected_row(self):
        selected = self.progress_table.selection()
        if not selected:
            messagebox.showwarning(
                self.locale.get("no_selection_title", "Nessuna selezione"),
                self.locale.get("select_row_to_reprocess", "Seleziona almeno una riga da rielaborare nel Tab 2")
            )
            return

        from urllib.parse import urlparse
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.chrome.options import Options

        # Recupera directory con timestamp dal file CSV più recente
        output_dir_csv = self.config.get("output_csv_path")
        if not output_dir_csv or not os.path.exists(output_dir_csv):
            messagebox.showerror("Errore", "Directory output CSV non trovata.")
            return

        output_files = sorted(
            [f for f in os.listdir(output_dir_csv) if f.startswith("output_") and f.endswith(".csv")],
            reverse=True
        )
        if not output_files:
            messagebox.showerror("Errore", "Nessun file output_*.csv trovato nella directory output CSV.")
            return

        timestamp_dir = output_files[0].replace("output_", "").replace(".csv", "")
        output_dir_with_timestamp = os.path.join(output_dir_csv, timestamp_dir)
        if not os.path.exists(output_dir_with_timestamp):
            os.makedirs(output_dir_with_timestamp, exist_ok=True)

        for item_id in selected:
            row_values = self.progress_table.item(item_id, "values")
            record = {
                "Url": row_values[0],
                "Nome Nazione": row_values[1],
                "Data Ultimo Aggiornamento": row_values[2]
            }

            parsed_url = urlparse(record["Url"])
            domain = parsed_url.netloc.replace("www.", "")
            site_configs = load_config().get("sites", {})
            site_config = site_configs.get(domain)

            if not site_config:
                messagebox.showerror(
                    self.locale.get("error", "Errore"),
                    f"{self.locale.get('config_not_found_for_domain', 'Nessuna configurazione trovata per il dominio')}: {domain}"
                )
                continue

            try:
                options = Options()
                options.add_argument("--headless")
                options.add_argument("--disable-gpu")
                options.add_argument("--disable-dev-shm-usage")
                options.add_argument("--window-size=1920,1080")
                options.add_argument("--disable-blink-features=AutomationControlled")
                options.add_argument("--disable-javascript")
                driver = webdriver.Chrome(
                    service=Service(os.path.join(get_base_dir(), "chromedriver.exe")),
                    options=options
                )

                driver.get(record["Url"])
                time.sleep(self.config.get("timeout", 5))

                status = ""
                current_signature = record["Data Ultimo Aggiornamento"]

                update_method = site_config.get("update_method", "date")

                do_reprocess = False
                if update_method == "detection":
                    changed, new_signature, reason, similarity = detect_page_change(
                        driver, site_config, current_signature
                    )
                    record["Data Ultimo Aggiornamento"] = new_signature
                    do_reprocess = changed or self.force_download_var.get()
                elif update_method in ("semantic", "both"):
                    changed, new_signature, reason, similarity = detect_page_change(
                        driver, site_config, current_signature, method=update_method
                    )
                    record["Data Ultimo Aggiornamento"] = new_signature
                    do_reprocess = changed or self.force_download_var.get()
                else:
                    new_date = extract_date(driver, site_config)
                    if new_date in [
                        self.locale.get("date_not_found", "DATE_NOT_FOUND"),
                        self.locale.get("date_not_parsed", "DATE_NOT_PARSED")
                    ]:
                        status = self.locale.get("date_extraction_error", "Errore nella lettura della data")
                        do_reprocess = False
                    else:
                        new_date_str = new_date.strftime("%Y-%m-%d %H:%M:%S")
                        record["Data Ultimo Aggiornamento"] = new_date_str
                        do_reprocess = (new_date_str != current_signature) or self.force_download_var.get()

                if do_reprocess:
                    pdf_filename = os.path.join(
                        output_dir_with_timestamp,
                        sanitize_filename(f"{record['Nome Nazione']}_{domain}.pdf")
                    )
                    saved = save_page_as_pdf_with_selenium(
                        record["Url"],
                        pdf_filename,
                        self.config["timeout"],
                        debug_mode=self.config.get("debug_mode", False),
                        log_file=self.config["log_file"]
                    )
                    if saved:
                        try:
                            extracted_text = extract_text_from_pdf(pdf_filename)
                            txt_output_path = pdf_filename.replace(".pdf", ".txt")
                            with open(txt_output_path, "w", encoding="utf-8") as f:
                                f.write(extracted_text)
                            logging.info(f"[TXT] Creato file testo: {txt_output_path}")
                        except Exception as e:
                            logging.warning(f"[TXT] Errore durante salvataggio del TXT per {pdf_filename}: {e}")

                        if self.config.get("pdf_mode", "with_links") == "no_links":
                            sanitize_pdf_links(pdf_filename)
                        elif self.config.get("pdf_mode", "image"):
                            logging.info(f"[RASTER] Modalità 'PDF immagine' attiva per: {pdf_filename}")
                            image_paths = convert_pdf_to_images_fitz(pdf_filename)
                            if image_paths:
                                replace_pdf_with_images_fitz(pdf_filename, image_paths)
                            else:
                                logging.warning(f"[RASTER] Conversione PDF→immagine fallita, file originale mantenuto: {pdf_filename}")

                        status = self.locale.get("updated_and_pdf_saved", "Aggiornato e PDF salvato")
                    else:
                        status = self.locale.get("pdf_error", "Errore PDF")
                else:
                    if not status:
                        status = self.locale.get("no_update_needed", "Nessun aggiornamento necessario")

                driver.quit()

                self.progress_table.item(item_id, values=(
                    record["Url"],
                    record["Nome Nazione"],
                    record["Data Ultimo Aggiornamento"],
                    status
                ))

                if output_files:
                    output_path = os.path.join(output_dir_csv, output_files[0])
                    with open(output_path, "r", encoding="utf-8") as f:
                        reader = list(csv.reader(f, delimiter=';'))
                        headers = reader[0]
                        rows = reader[1:]

                    url_index = headers.index(self.locale.get("url", "Url"))
                    date_index = headers.index(self.locale.get("last_updated_date", "Data Ultimo Aggiornamento"))

                    for i, row in enumerate(rows):
                        if row[url_index].strip() == record["Url"]:
                            rows[i][date_index] = record["Data Ultimo Aggiornamento"]
                            break

                    with open(output_path, "w", encoding="utf-8", newline="") as f:
                        writer = csv.writer(f, delimiter=';')
                        writer.writerow(headers)
                        writer.writerows(rows)

            except Exception as e:
                logging.error(f"Errore durante la rielaborazione per {record['Url']}: {e}")
                messagebox.showerror(
                    self.locale.get("error", "Errore"),
                    f"{self.locale.get('error_during_process_e', 'Errore durante il processo')}: {e}")


    def on_language_change(self, event=None):
        new_lang = self.language_var.get()
        self.locale = load_locale(new_lang)
        self.config["language"] = new_lang
        save_config(self.config)
        self.refresh_ui_texts()

    def load_initial_csv(self):
        """Loads the initial CSV content into the table if the file exists."""
        csv_path = self.config.get("csv_path", "")
        if os.path.exists(csv_path):
            self.csv_path = csv_path
            self.csv_path_var.set(csv_path)
            self.load_csv()

    def load_csv(self, path=None):
        if path is None:
            path = self.csv_path_var.get()
    
        if not os.path.isfile(path):
            logging.error(f"File CSV non trovato: {path}")
            return
    
        try:
            with open(path, newline='', encoding='utf-8') as csvfile:
                reader = csv.reader(csvfile, delimiter=';')
                rows = list(reader)
    
            if not rows:
                messagebox.showwarning("CSV vuoto", "Il file CSV è vuoto.")
                return
    
            headers = rows[0]
            self.csv_columns = headers
    
            # Cancella contenuto esistente
            for col in self.csv_table["columns"]:
                self.csv_table.heading(col, text="")  # reset intestazioni
            self.csv_table.delete(*self.csv_table.get_children())
    
            # Aggiorna colonne
            self.csv_table["columns"] = headers
            for col in headers:
                self.csv_table.heading(col, text=col)
                self.csv_table.column(col, width=120)
    
            # Aggiungi righe
            for row in rows[1:]:
                self.csv_table.insert("", "end", values=row)
    
            # Salva il percorso attuale
            self.csv_path = path
            self.csv_path_var.set(path)
    
            logging.info(f"CSV caricato correttamente: {path}")
    
        except Exception as e:
            logging.error(f"Errore durante il caricamento del CSV: {e}")
            messagebox.showerror("Errore", f"Impossibile caricare il CSV:\n{e}")
    

            

    def on_treeview_file_drop(self, event):
        try:
            path = event.data.strip('{}')  # Rimuove eventuali {} attorno al path
            if os.path.isfile(path) and path.endswith(".csv"):
                self.csv_path_var.set(path)
                self.load_csv(path)
            else:
                messagebox.showerror("Errore", "Il file trascinato non è un file CSV valido.")
        except Exception as e:
            logging.error(f"Errore durante il drop del file CSV: {e}")
            messagebox.showerror("Errore", str(e))


    def setup_tab2(self):
        """Configura la scheda Process Pages."""
    
        header_frame = ttk.Frame(self.tab2)
        header_frame.pack(fill="x", padx=10, pady=10)
    
        language_menu = ttk.Combobox(
            header_frame,
            textvariable=self.language_var,
            values=AVAILABLE_LANGUAGES,
            state="readonly",
            width=6
        )
        language_menu.pack(anchor="ne", side="right", padx=10)
        language_menu.bind("<<ComboboxSelected>>", self.on_language_change)
    
        video_frame = ttk.Frame(header_frame)
        video_frame.pack(side="left", padx=10)
    
        self.video_canvas = tk.Canvas(video_frame, width=200, height=150, bg="black")
        self.video_canvas.pack()
    
        if self.video_player.canvas is None:
            self.video_player.canvas = self.video_canvas
    
        content_frame = ttk.Frame(header_frame)
        content_frame.pack(side="left", fill="x", expand=True)
    
        self.timeout_label = tk.Label(content_frame, text=self.locale.get("timeout_label", "Timeout (seconds):"))
        self.timeout_label.pack(anchor="w")
        self.timeout_var = tk.IntVar(value=self.config.get("timeout", 10))
        tk.Entry(content_frame, textvariable=self.timeout_var, width=10).pack(anchor="w", pady=2)
    
        button_frame = ttk.Frame(content_frame)
        button_frame.pack(anchor="w", pady=5)
    
        self.button_start = ttk.Button(button_frame, text=self.locale.get("start_process", "Start Process"), command=self.start_process)
        self.button_start.pack(side="left", padx=5)
        self.pause_button = ttk.Button(button_frame, text=self.locale.get("pause_process", "Pausa Processo"), command=self.pause_process)
        self.pause_button.pack(side="left", padx=5)
        self.resume_button = ttk.Button(button_frame, text=self.locale.get("resume_process", "Riprendi Processo"), command=self.resume_process)
        self.resume_button.pack(side="left", padx=5)
        self.stop_button = ttk.Button(button_frame, text=self.locale.get("force_stop", "Ferma Definitivamente"), command=self.stop_process)
        self.stop_button.pack(side="left", padx=5)

        # Pulsante "Rielabora selezionato"
        self.reprocess_button = ttk.Button(
            button_frame,
            text=self.locale.get("reprocess_selected", "Rielabora selezionato"),
            command=self.reprocess_selected_row
        )
        self.reprocess_button.pack(side="left", padx=5)

    
        self.progress_label = tk.Label(self.tab2, text=self.locale.get("progress", "Progress:"))
        self.progress_label.pack(pady=5)
    
        self.progress_frame = ttk.Frame(self.tab2)
        self.progress_frame.pack(fill="x", padx=10, pady=5)
    
        self.progress_bar = ttk.Progressbar(self.progress_frame, orient="horizontal", mode="determinate")
        self.progress_bar.pack(fill="x", side="left", expand=True, padx=(0, 10))
    
        self.progress_count = tk.Label(self.progress_frame, text=self.locale.get("0/0", "0/0"))
        self.progress_count.pack(side="right")
    
        self.progress_table_frame = ttk.Frame(self.tab2)
        self.progress_table_frame.pack(fill="both", expand=True, padx=10, pady=10)
    
        columns = ["url", "country", "last_updated", "status"]
        self.progress_table = build_treeview(
            self.progress_table_frame,
            columns=columns,
            locale=self.locale,
            locale_keys=columns
        )
    
    def start_process(self):
        logging.info(locale.get("process_started_from_start_process", "Processo avviato da Start Process."))
        self.video_player.stop()
        self.video_player.canvas = self.video_canvas
        self.video_player.start(loop=True, fit_canvas=True)
    
        self.config["csv_path"] = self.csv_path_var.get()
        self.config["html_save_path"] = self.save_path_var.get()
        self.config["timeout"] = self.timeout_var.get()
        self.config["force_download"] = self.force_download_var.get()
    
        self.pause_event = threading.Event()
        self.pause_event.set()
        self.stop_event = threading.Event()
    
        def wrapped_process():
            try:
                self.run_process_pages(self.pause_event, self.stop_event)
            finally:
                logging.info(locale.get("process_ended_stopping_video", "Processo terminato. Fermiamo il video."))
                self.video_player.stop()
    
        process_thread = threading.Thread(
            target=wrapped_process,
            daemon=True
        )
        process_thread.start()
    
    def pause_process(self):
        if hasattr(self, "pause_event"):
            self.pause_event.clear()
            logging.info(locale.get("process_paused", "Processo messo in pausa."))
            self.video_player.pause()
    
    def resume_process(self):
        if hasattr(self, "pause_event"):
            self.pause_event.set()
            logging.info(locale.get("process_resumed", "Processo ripreso."))
            self.video_player.resume()
    
    def stop_process(self):
        if hasattr(self, "stop_event"):
            self.stop_event.set()
            logging.info(locale.get("process_forcefully_stopped", "Processo fermato definitivamente."))
            self.video_player.stop()

            

    def setup_tab3(self):
        """Configura la scheda per le configurazioni avanzate dei siti."""
    
        header_frame = ttk.Frame(self.tab3)
        header_frame.pack(fill="x", padx=10, pady=10)
    
        language_menu = ttk.Combobox(
            header_frame,
            textvariable=self.language_var,
            values=AVAILABLE_LANGUAGES,
            state="readonly",
            width=6
        )
        language_menu.pack(anchor="ne", side="right", padx=10)
        language_menu.bind("<<ComboboxSelected>>", self.on_language_change)
    
        try:
            self.tab3_img = tk.PhotoImage(file="webscraper_icon.png")
            self.tab3_img = self.tab3_img.subsample(8, 8)
            img_label = tk.Label(header_frame, image=self.tab3_img)
            img_label.pack(side="left", padx=10)
        except Exception as e:
            logging.warning(self.locale.get("error_loading_image_tab3", f"Errore caricamento immagine tab3: {e}"))
    
        control_frame = ttk.Frame(header_frame)
        control_frame.pack(side="left", fill="x", expand=True)
    
        row1 = ttk.Frame(control_frame)
        row1.pack(fill="x", pady=2)
        self.add_site_btn = ttk.Button(row1, text=self.locale.get("add_site", "Add Site"), command=self.add_site_row)
        self.add_site_btn.pack(side="left", padx=5)
        self.remove_site_btn = ttk.Button(row1, text=self.locale.get("remove_selected_site", "Remove Selected Site"), command=self.remove_selected_site)
        self.remove_site_btn.pack(side="left", padx=5)
        self.save_config_btn = ttk.Button(row1, text=self.locale.get("save_config", "Save Config"), command=self.save_config)
        self.save_config_btn.pack(side="left", padx=5)
    
        row2 = ttk.Frame(control_frame)
        row2.pack(fill="x", pady=2)
        self.debug_label = tk.Label(row2, text=self.locale.get("selenium_debug_level", "Selenium Debug Level:"))
        self.debug_label.pack(side="left", padx=(5, 2))
        self.log_level_var = tk.StringVar(value=self.config.get("log_level", "INFO"))
        self.log_level_menu = ttk.Combobox(
            row2,
            textvariable=self.log_level_var,
            values=["NONE", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
            state="readonly"
        )
        self.log_level_menu.pack(side="left", padx=5)
        self.save_debug_btn = ttk.Button(row2, text=self.locale.get("save_debug_level", "Save Debug Level"), command=self.save_debug_level)
        self.save_debug_btn.pack(side="left", padx=5)
    
        self.site_frame = ttk.Frame(self.tab3)
        self.site_frame.pack(fill="both", expand=True, padx=10, pady=10)
    
        columns = [
            "Site", "Metodo", "Selector", "Date Format", "Language",
            "Prefix", "Month Translations", "Day Translations", "Tipo Detection", "Soglia"
        ]
        locale_keys = [
            "site", "method", "selector", "date_format", "language",
            "prefix", "month_translations", "day_translations", "detection_type", "threshold"
        ]
    
        self.site_table = build_treeview(
            self.site_frame,
            columns=columns,
            locale=self.locale,
            locale_keys=locale_keys
        )
        self.site_table.bind("<Double-1>", self.edit_site_cell)
    
        self.check_versions_btn = ttk.Button(
            self.tab3,
            text=self.locale.get("check_chrome_and_chromedriver_version", "Check Chrome & Chromedriver Version"),
            command=self.check_chrome_and_chromedriver
        )
        self.check_versions_btn.pack(pady=10)
    
        self.load_sites_into_table()


    
    def load_sites_into_table(self):
        self.site_table.delete(*self.site_table.get_children())
        config_data = load_config()
        for domain, values in config_data.get("sites", {}).items():
            selector = values.get("date_selector", "")
            date_format = values.get("date_format", "")
            language = values.get("language", "")
            prefix = values.get("prefix_to_remove", "")
            months = json.dumps(values.get("month_translations", {}), ensure_ascii=False)
            days = json.dumps(values.get("day_translations", {}), ensure_ascii=False)
            method = values.get("update_method", "date")
            detection_type = values.get("detection_type", "")
            threshold = values.get("detection_threshold", "")
    
            row = (
                domain,              # Site
                method,              # Metodo
                selector,            # Selector
                date_format,         # Date Format
                language,            # Language
                prefix,              # Prefix
                months,              # Month Translations (as JSON string)
                days,                # Day Translations (as JSON string)
                detection_type,      # Tipo Detection
                threshold            # Soglia
            )
            self.site_table.insert("", "end", values=row)


    def save_debug_level(self):
        """Salva il livello di debug selezionato nel file di configurazione."""
        config_data = load_config()
        config_data["log_level"] = self.log_level_var.get()
        save_config_to_file(config_data)
        messagebox.showinfo("Debug Level", f"Livello di debug salvato: {self.log_level_var.get()}")


    def edit_site_cell(self, event):
        item_id = self.site_table.focus()
        if not item_id:
            return

        col = self.site_table.identify_column(event.x)
        col_index = int(col.replace("#", "")) - 1
        values = list(self.site_table.item(item_id, "values"))

        if col_index >= len(values):
            return  # prevenzione IndexError

        current_value = values[col_index]
        x, y, width, height = self.site_table.bbox(item_id, col)

        # Ottieni la chiave di localizzazione associata alla colonna
        locale_keys = [
            "site", "method", "selector", "date_format", "language",
            "prefix", "month_translations", "day_translations", "detection_type", "threshold"
        ]
        if col_index >= len(locale_keys):
            return

        key = locale_keys[col_index]

        # Combobox per le colonne a valori fissi
        if key == "method":
            combo = ttk.Combobox(self.site_table, values=["date", "detection"], state="readonly")
        elif key == "detection_type":
            combo = ttk.Combobox(self.site_table, values=["hash", "semantic", "both"], state="readonly")
        else:
            combo = None

        if combo:
            combo.set(current_value)
            combo.place(x=x, y=y, width=width, height=height)
            combo.focus_set()

            def save_combo(event=None):
                new_value = combo.get()
                combo.destroy()
                values[col_index] = new_value
                self.site_table.item(item_id, values=values)

            combo.bind("<<ComboboxSelected>>", save_combo)
            combo.bind("<FocusOut>", save_combo)
        else:
            entry = tk.Entry(self.site_table)
            entry.insert(0, current_value)
            entry.place(x=x, y=y, width=width, height=height)
            entry.focus_set()

            def save_edit(event=None):
                new_value = entry.get()
                entry.destroy()
                values[col_index] = new_value
                self.site_table.item(item_id, values=values)

            entry.bind("<Return>", save_edit)
            entry.bind("<FocusOut>", save_edit)
 
    def save_config(self):
        """Salva la configurazione aggiornata nel file JSON, mantenendo le chiavi non modificabili come 'chrome_path'."""
        try:
            original_config = load_config()  # Leggi l'originale per conservare le chiavi non toccabili
            self.config["csv_path"] = self.csv_path_var.get()
            self.config["html_save_path"] = self.save_path_var.get()
            self.config["timeout"] = self.timeout_var.get()
            self.config["force_download"] = self.force_download_var.get()
            self.config["use_debug_mode"] = self.use_debug_mode_var.get()
    
            # Recupera configurazione dei siti
            sites_config = {}
            for row in self.site_table.get_children():
                values = self.site_table.item(row)["values"]
                if len(values) >= 10:
                    (
                        site,
                        method,
                        selector,
                        date_format,
                        language,
                        prefix_to_remove,
                        month_translations_str,
                        day_translations_str,
                        detection_type,
                        threshold
                    ) = values
    
                    try:
                        month_translations = json.loads(month_translations_str) if month_translations_str.strip() else {}
                    except json.JSONDecodeError as e:
                        messagebox.showerror("Errore", f"Errore nel parsing del campo 'Month Translations' per il sito {site}:\n{e}")
                        continue
    
                    try:
                        day_translations = json.loads(day_translations_str) if day_translations_str.strip() else {}
                    except json.JSONDecodeError as e:
                        messagebox.showerror("Errore", f"Errore nel parsing del campo 'Day Translations' per il sito {site}:\n{e}")
                        continue
    
                    sites_config[site] = {
                        "update_method": method,
                        "date_selector": selector,
                        "date_format": date_format,
                        "language": language or "",
                        "prefix_to_remove": prefix_to_remove or "",
                        "month_translations": month_translations,
                        "day_translations": day_translations,
                        "detection_type": detection_type,
                        "detection_threshold": float(threshold) if threshold else ""
                    }
    
            self.config["sites"] = sites_config
            save_config_to_file({**original_config, **self.config})
            messagebox.showinfo("Salvataggio riuscito", locale.get("configurazione_salvata_correttamente", "Configurazione salvata correttamente."))
    
        except Exception as e:
            messagebox.showerror(locale.get("error_saving_config_title", "Save Error"), f"{locale.get('error_saving_config', 'An error occurred while saving the configuration')}:\n{e}")
    
    
    def check_chrome_and_chromedriver(self):
        """Controlla le versioni di Chrome e Chromedriver."""
        chrome_version = self.get_chrome_version()
        chromedriver_version = self.get_chromedriver_version()
    
        if not chrome_version or not chromedriver_version:
            messagebox.showerror(locale.get("error_title", locale.get("error", "Error")), "Unable to determine Chrome or Chromedriver version.")
            return
    
        chrome_major = chrome_version.split(".")[0]
        chromedriver_major = chromedriver_version.split(".")[0]
    
        if chrome_major == chromedriver_major:
            messagebox.showinfo(locale.get("version_check_title", "Version Check"), locale.get("version_check_result", "Versions are compatible:\nChrome: {chrome}\nChromedriver: {driver}").format(chrome=chrome_version, driver=chromedriver_version))
        else:
            if messagebox.askyesno(
                "Version Mismatch",
                f"Version mismatch detected:\nChrome: {chrome_version}\nChromedriver: {chromedriver_version}\nDo you want to download the correct Chromedriver?"
            ):
                self.download_chromedriver()
    
    def download_chromedriver(self):
        """Scarica la versione corretta di Chromedriver."""
        try:
            ChromeDriverManager().install()
            messagebox.showinfo("Download Complete", locale.get("chromedriver_has_been_downloaded_successfully", "Chromedriver has been downloaded successfully."))
        except Exception as e:
            messagebox.showerror(locale.get("error_title", locale.get("error", "Error")), f"Failed to download Chromedriver: {e}")



    def select_csv(self):
        """Permette all'utente di selezionare un file CSV e caricarlo nella tabella."""
        file_path = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv")])
        if file_path:
            self.csv_path = file_path
            self.csv_path_var.set(file_path)
            self.load_csv()




    def save_csv(self):
        """Salva i dati modificati dalla tabella CSV (Tab 1) con intestazioni localizzate nella lingua attiva."""
        try:
            if not self.csv_path or not self.csv_columns:
                messagebox.showwarning(self.locale.get("warning", "Avviso"), self.locale.get("no_csv_loaded", "Nessun CSV caricato."))
                return
    
            localized_columns = [
                self.locale.get(col.lower().replace(" ", "_"), col)
                for col in self.csv_columns
            ]
    
            with open(self.csv_path, "w", encoding="utf-8", newline="") as file:
                writer = csv.writer(file, delimiter=';')
                writer.writerow(localized_columns)  # Intestazioni localizzate
    
                for item in self.csv_table.get_children():
                    values = list(self.csv_table.item(item)["values"])
                    writer.writerow(values)
    
            messagebox.showinfo("Success", self.locale.get("csv_saved_successfully!", "CSV salvato con successo!"))
        except Exception as e:
            messagebox.showerror(self.locale.get("error_title", "Errore"), f"Errore nel salvataggio del CSV:\n{e}")

    

    def add_record(self):
        """Aggiunge una riga vuota alla tabella."""
        self.csv_table.insert("", "end", values=[""] * len(self.csv_columns))

    def remove_selected_record(self):
        """Rimuove la riga selezionata dalla tabella."""
        selected_item = self.csv_table.selection()
        if selected_item:
            self.csv_table.delete(selected_item)


    def add_site_row(self):
        """Aggiunge una nuova riga vuota alla tabella dei siti."""
        self.site_table.insert(
            "", "end",
            values=(
                "newsite.com",     # Site
                "date",            # Metodo
                "",                # Selector
                "",                # Date Format
                "",                # Language
                "",                # Prefix
                "{}",              # Month Translations
                "{}",              # Day Translations
                "hash",            # Tipo Detection
                "0.900"            # Soglia
            )
        )

    def remove_selected_site(self):
        """Rimuove il sito selezionato dalla tabella."""
        selected_item = self.site_table.selection()
        if selected_item:
            self.site_table.delete(selected_item)

  

    def select_save_path(self):
        """Permette all'utente di selezionare una directory per salvare i file."""
        folder_path = filedialog.askdirectory()
        if folder_path:
            self.save_path_var.set(folder_path)

    def edit_cell(self, event):
        """Permette di modificare una cella della tabella CSV (Tab 1) e memorizza la modifica in attesa del salvataggio."""
        region = self.csv_table.identify("region", event.x, event.y)
        if region != "cell":
            return
    
        row_id = self.csv_table.identify_row(event.y)
        column_id = self.csv_table.identify_column(event.x)
        col_index = int(column_id[1:]) - 1
    
        # Coordinate pixel della cella
        x, y, width, height = self.csv_table.bbox(row_id, column_id)
        current_value = self.csv_table.item(row_id, "values")[col_index]
    
        entry = tk.Entry(self.csv_table)
        entry.insert(0, current_value)
        entry.place(x=x, y=y, width=width, height=height)
        entry.focus_set()
    
        def save_entry(event=None):
            new_value = entry.get()
            entry.destroy()
    
            if new_value != current_value:
                values = list(self.csv_table.item(row_id, "values"))
                values[col_index] = new_value
                self.csv_table.item(row_id, values=values)
                logging.info(locale.get("cell_updated_message_rowid", f"Valore aggiornato nella riga {row_id}, colonna {col_index}: {new_value}"))
    
        entry.bind("<Return>", save_entry)
        entry.bind("<FocusOut>", save_entry)




        def save_edit(event=None):
            # Salva il nuovo valore nella tabella
            new_value = entry.get()
            entry.destroy()
            values = list(self.site_table.item(row_id, "values"))
            values[col_index] = new_value
            self.site_table.item(row_id, values=values)
        
            # Gestisci evento Enter o perdita del focus
            entry.bind("<Return>", save_edit)
            entry.bind("<FocusOut>", lambda e: entry.destroy())
            entry.focus()

   

  

    def run_process_pages(self, pause_event=None, stop_event=None):
        try:
            process_pages(
                config=self.config,
                progress_table=self.progress_table,
                progress_bar=self.progress_bar,
                progress_count=self.progress_count,
                locale=self.locale,
                pause_event=pause_event,
                stop_event=stop_event
            )
        except Exception as e:
            logging.error(locale.get("error_during_process_e", "Error during process: {e}").format(e=e))
        finally:
            self.video_player.stop()

    def check_chrome_compatibility(self):
        """Verifica la compatibilità tra Chrome e ChromeDriver."""
        try:
            # Ottieni la versione di ChromeDriver
            chromedriver_version = self.get_chromedriver_version()
            # Ottieni la versione di Chrome
            chrome_version = self.get_chrome_version()
    
            if chromedriver_version and chrome_version:
                chromedriver_major = chromedriver_version.split(".")[0]
                chrome_major = chrome_version.split(".")[0]
    
                # Se le versioni non sono compatibili, mostra un popup
                if chromedriver_major != chrome_major:
                    self.show_incompatible_popup()
            else:
                self.show_incompatible_popup()
        except Exception as e:
            messagebox.showerror(locale.get("error_title", locale.get("errore", "Errore")), f"Errore durante il controllo della compatibilità: {e}")
    
    def get_chromedriver_version(self):
        """Ritorna la versione di ChromeDriver."""
        try:
            result = subprocess.run(["./chromedriver", "--version"], capture_output=True, text=True)
            version = result.stdout.strip().split(" ")[1]
            return version
        except Exception:
            return None

    def get_chrome_version(self):
        """
        Ritorna la versione di Google Chrome installata sul sistema operativo.
        Supporta Windows, MacOS e Linux.
        """

        try:
            if os.name == "nt":  # Windows
                import winreg
    
                # Cerca Chrome nel registro di sistema
                reg_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe"
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path) as key:
                    chrome_path = winreg.QueryValueEx(key, None)[0]
    
                    # Esegui il comando per ottenere la versione
                    result = subprocess.run(
                        [chrome_path, "--version"],
                        capture_output=True,
                        text=True,
                        shell=True,
                    )
                    if result.returncode == 0 and result.stdout:
                        return result.stdout.strip().split(" ")[-1]
    
            elif sys.platform == "darwin":  # MacOS
                # Usa il comando specifico per MacOS
                result = subprocess.run(
                    ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "--version"],
                    capture_output=True,
                    text=True,
                )
                if result.returncode == 0 and result.stdout:
                    return result.stdout.strip().split(" ")[-1]
    
            elif sys.platform.startswith("linux"):  # Linux
                # Usa il comando specifico per Linux
                result = subprocess.run(
                    ["google-chrome", "--version"],
                    capture_output=True,
                    text=True,
                )
                if result.returncode == 0 and result.stdout:
                    return result.stdout.strip().split(" ")[-1]
                else:
                    # Prova con "chromium-browser" nel caso Google Chrome non sia il comando principale
                    result = subprocess.run(
                        ["chromium-browser", "--version"],
                        capture_output=True,
                        text=True,
                    )
                    if result.returncode == 0 and result.stdout:
                        return result.stdout.strip().split(" ")[-1]
    
            return None  # Chrome non trovato
    
        except FileNotFoundError:
            print(locale.get("chrome_not_found_in_the_system", "Chrome non trovato sul sistema."))
        except Exception as e:
            print(locale.get("error_obtaining_chrome_version", f"Errore durante l'ottenimento della versione di Chrome: {e}"))
    
        return None

    def get_chrome_and_chromedriver_versions(self):
        """
        Ottiene la versione di Google Chrome e di Chromedriver in modo silenzioso.
        Supporta Windows, MacOS e Linux.
        """
        import os
        import subprocess
        import sys
    
        chrome_version = "Non trovato"
        chromedriver_version = "Non trovato"
    
        try:
            # Trova la versione di Chrome
            if os.name == "nt":  # Windows
                import winreg
                reg_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe"
                try:
                    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path) as key:
                        chrome_path = winreg.QueryValueEx(key, None)[0]
                        result = subprocess.run(
                            [chrome_path, "--version"],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            text=True,
                            shell=True,
                        )
                        if result.returncode == 0 and result.stdout:
                            chrome_version = result.stdout.strip().split(" ")[-1]
                except Exception as e:
                    print(locale.get("error_finding_chrome_version", f"Errore nel trovare la versione di Chrome su Windows: {e}"))
    
            elif sys.platform == "darwin":  # MacOS
                result = subprocess.run(
                    ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "--version"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                if result.returncode == 0 and result.stdout:
                    chrome_version = result.stdout.strip().split(" ")[-1]
    
            elif sys.platform.startswith("linux"):  # Linux
                for chrome_cmd in ["google-chrome", "chromium-browser", "chrome"]:
                    result = subprocess.run(
                        [chrome_cmd, "--version"],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                    )
                    if result.returncode == 0 and result.stdout:
                        chrome_version = result.stdout.strip().split(" ")[-1]
                        break
    
            # Trova la versione di Chromedriver
            chromedriver_path = os.path.join(os.getcwd(), "chromedriver.exe" if os.name == "nt" else "chromedriver")
            if os.path.exists(chromedriver_path):
                result = subprocess.run(
                    [chromedriver_path, "--version"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                if result.returncode == 0 and result.stdout:
                    chromedriver_version = result.stdout.strip().split(" ")[1]
    
        except Exception as e:
            print(locale.get("error_finding_chrome_versions", f"Errore nel trovare le versioni di Chrome/Chromedriver: {e}"))
    
        return chrome_version, chromedriver_version



    def show_incompatible_popup(self):
        """Mostra un popup per scaricare la versione corretta di ChromeDriver."""
        def download_chromedriver():
            """Scarica automaticamente la versione corretta di ChromeDriver."""
            try:
                ChromeDriverManager().install()
                messagebox.showinfo("Download completato", locale.get("chromedriver_has_been_downloaded_successfully", "ChromeDriver è stato scaricato correttamente."))
            except Exception as e:
                messagebox.showerror(locale.get("error_title", locale.get("errore", "Errore")), f"Errore durante il download di ChromeDriver: {e}")
    
        # Popup di errore con pulsante di download
        if messagebox.askyesno(
            locale.get("incompatible_chromedriver", "Incompatibilità rilevata \nE' necessario scaricare la versione di Chromedriver più aggiornata. Vuoi scaricarla ora?")
        ):
            download_chromedriver()

    def on_enter(self, event):
        """Gestisce la pressione di Enter per salvare una cella modificata."""
        widget = event.widget
        new_value = widget.get()  # Ottieni il nuovo valore dalla cella
        widget.destroy()  # Rimuovi il campo di input
    
        # Trova la riga e la colonna selezionata
        row_id = self.csv_table.selection()[0]  # Riga selezionata
        column_id = self.csv_table.identify_column(event.x)  # Colonna selezionata
        col_index = int(column_id[1:]) - 1  # Indice della colonna (0-based)
    
        # Aggiorna i valori nella tabella
        current_values = list(self.csv_table.item(row_id, "values"))
        current_values[col_index] = new_value
        self.csv_table.item(row_id, values=current_values)
    
        # Salva il CSV dopo la modifica
        self.save_csv()
        logging.info(locale.get("updated_cell_in_row_rowid_column_co", f"Updated cell in row {row_id}, column {col_index}: {new_value}"))


    def setup_tab4(self):
        self.pdf_zoom = 1.0
        self.current_pdf_page = 0
        self.total_pdf_pages = 1
    
        self.tab4 = ttk.Frame(self.notebook)
        self.notebook.insert(2, self.tab4, text=self.locale.get("versioNice", "Versioni"))
    
        # ✅ Intestazione con selettore lingua
        header_frame = ttk.Frame(self.tab4)
        header_frame.pack(fill="x", pady=5, padx=10)
    
    
        language_menu = ttk.Combobox(
            header_frame,
            textvariable=self.language_var,
            values=AVAILABLE_LANGUAGES,
            state="readonly",
            width=6
        )
        language_menu.pack(side="right", padx=5)
        language_menu.bind("<<ComboboxSelected>>", self.on_language_change)
    
        top_frame = ttk.Frame(self.tab4)
        top_frame.pack(fill="x", padx=10, pady=5)
    
        self.update_versions_btn = tk.Button(
            top_frame,
            text=self.locale.get("update_state", "Aggiorna stato"),
            command=self.aggiorna_stato_versioni
        )
        self.update_versions_btn.pack(side="left")
    
        center_frame = ttk.Frame(self.tab4)
        center_frame.pack(fill="both", expand=True, padx=10, pady=5)
    
        self.versions_tree = ttk.Treeview(center_frame)
        self.versions_tree.heading("#0", text=self.locale.get("versions_tree", "Versioni disponibili"))
        self.versions_tree.bind("<Double-1>", self.on_select_version)
        self.versions_tree.pack(side="left", fill="both", expand=False)
    
        # Canvas PDF con scroll e zoom
        pdf_frame = ttk.Frame(center_frame)
        pdf_frame.pack(side="left", fill="both", expand=True, padx=5)
    
        zoom_controls = ttk.Frame(pdf_frame)
        zoom_controls.pack(side="top", fill="x")
    
        self.zoom_in_btn = ttk.Button(zoom_controls, text="+", command=self.zoom_in)
        self.zoom_in_btn.pack(side="left")
    
        self.zoom_out_btn = ttk.Button(zoom_controls, text="-", command=self.zoom_out)
        self.zoom_out_btn.pack(side="left")
    
        self.prev_page_btn = ttk.Button(zoom_controls, text="↑", command=self.pagina_su)
        self.prev_page_btn.pack(side="left")
    
        self.next_page_btn = ttk.Button(zoom_controls, text="↓", command=self.pagina_giu)
        self.next_page_btn.pack(side="left")
    
        canvas_frame = ttk.Frame(pdf_frame)
        canvas_frame.pack(side="top", fill="both", expand=True)
    
        self.pdf_viewer_canvas = tk.Canvas(canvas_frame, bg="white")
        self.pdf_viewer_canvas.bind("<Button-1>", lambda e: self.pdf_viewer_canvas.focus_set())
        self.pdf_viewer_canvas.grid(row=0, column=0, sticky="nsew")
    
        self.pdf_scroll_y = ttk.Scrollbar(canvas_frame, orient="vertical", command=self.pdf_viewer_canvas.yview)
        self.pdf_scroll_y.grid(row=0, column=1, sticky="ns")
        self.pdf_scroll_x = ttk.Scrollbar(canvas_frame, orient="horizontal", command=self.pdf_viewer_canvas.xview)
        self.pdf_scroll_x.grid(row=1, column=0, sticky="ew")
    
        canvas_frame.grid_rowconfigure(0, weight=1)
        canvas_frame.grid_columnconfigure(0, weight=1)
    
        self.pdf_viewer_canvas.config(yscrollcommand=self.pdf_scroll_y.set, xscrollcommand=self.pdf_scroll_x.set)
    

        # Frame dedicato al box di testo + scrollbar (colonna destra)
        right_frame = ttk.Frame(center_frame, width=250)
        right_frame.pack(side="right", fill="y", padx=(5, 0))
        
        self.text_diff_box = tk.Text(right_frame, wrap="word", width=60)
        self.text_diff_box.pack(side="left", fill="both", expand=True)
        
        scrollbar = ttk.Scrollbar(right_frame, command=self.text_diff_box.yview)
        scrollbar.pack(side="right", fill="y")
        self.text_diff_box.config(yscrollcommand=scrollbar.set)    
        self.pdf_zoom = 1.0
        self.versione_corrente_pdf = None
    
        base_path = self.save_path_var.get()
        self.carica_treeview_versioni(base_path)


    def zoom_in(self):
        if not hasattr(self, "versione_corrente_pdf") or not self.versione_corrente_pdf:
            #logging.warning("Zoom ignorato: nessun PDF selezionato.")
            logging.warning(locale.get("zoom_skipped_no_pdf_selected"))
            return
        self.pdf_zoom += 0.2
        self.visualizza_pdf(self.versione_corrente_pdf)
    
    def zoom_out(self):
        if not hasattr(self, "versione_corrente_pdf") or not self.versione_corrente_pdf:
            logging.warning("Zoom ignorato: nessun PDF selezionato.")
            return
        self.pdf_zoom = max(0.2, self.pdf_zoom - 0.2)
        self.visualizza_pdf(self.versione_corrente_pdf)


    def pagina_su(self):
        try:
            self.pdf_viewer_canvas.yview_scroll(-3, "units")  # Scrolla verso l'alto
        except Exception as e:
            logging.warning(f"Errore scroll pagina su: {e}")
    
    def pagina_giu(self):
        try:
            self.pdf_viewer_canvas.yview_scroll(3, "units")  # Scrolla verso il basso
        except Exception as e:
            logging.warning(f"Errore scroll pagina giù: {e}")


    def _on_mousewheel(self, event):
        self.pdf_viewer_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
    
    def _on_shift_mousewheel(self, event):
        self.pdf_viewer_canvas.xview_scroll(int(-1 * (event.delta / 120)), "units")


    def aggiorna_stato_versioni(self):
        try:
            base_path = self.save_path_var.get()
            build_changes_index(base_path)

            messagebox.showinfo(
                self.locale.get("update_complete", "Aggiornamento completato"),
                self.locale.get("changes_json_created", "File changes.json aggiornato.")
            )

            self.carica_treeview_versioni(base_path)

        except Exception as e:
            messagebox.showerror(self.locale.get("error_title", "Errore"), str(e))

    def carica_treeview_versioni(self, base_path):
        changes_path = os.path.join(base_path, "changes", "changes.json")
        if os.path.exists(changes_path):
            with open(changes_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.versions_tree.delete(*self.versions_tree.get_children())

            for url, info in data.items():
                country = info.get("country", "Unknown")
                versions = info.get("versions", [])

                parent = self.versions_tree.insert("", "end", text=f"{country} - {url}")

                for version in sorted(versions, key=lambda v: v["timestamp"]):
                    label = datetime.fromisoformat(version["timestamp"]).strftime("%Y-%m-%d %H:%M")
                    self.versions_tree.insert(
                        parent,
                        "end",
                        text=label,
                        values=(version["pdf_path"], version["txt_path"])
                    )
                self.versions_tree.item(parent, open=True)

    def on_select_version(self, event):
        selected = self.versions_tree.selection()
        if not selected:
            return
        item_id = selected[0]
        parent_id = self.versions_tree.parent(item_id)
    
        if parent_id:
            relative_pdf_path = self.versions_tree.item(item_id, "values")[0]
            relative_txt_path = self.versions_tree.item(item_id, "values")[1]
    
            self.versione_corrente = relative_txt_path
            self.versione_corrente_pdf = relative_pdf_path
            self.visualizza_pdf(relative_pdf_path)
    
            base_dir = self.save_path_var.get()
            full_txt_path = os.path.join(base_dir, relative_txt_path)
    
            # Reset casella testo
            self.text_diff_box.delete("1.0", "end")
    
            # Prova a fare il diff con la versione precedente
            siblings = self.versions_tree.get_children(parent_id)
            idx = siblings.index(item_id)
            if idx > 0:
                prev_item = siblings[idx - 1]
                prev_txt = self.versions_tree.item(prev_item, "values")[1]
                try:
                    with open(os.path.join(base_dir, prev_txt), "r", encoding="utf-8") as f:
                        old_text = f.read()
                    with open(full_txt_path, "r", encoding="utf-8") as f:
                        new_text = f.read()
                    self.confronta_testi(old_text, new_text)
                    self.text_diff_box.insert("end", "\n\n--- Versione selezionata completa ---\n\n" + new_text)
                except Exception as e:
                    logging.warning(f"Errore confronto versioni: {e}")
            else:
                # Nessuna versione precedente: mostra solo testo attuale
                try:
                    with open(full_txt_path, "r", encoding="utf-8") as f:
                        new_text = f.read()
                    self.text_diff_box.insert("end", new_text)
                except Exception as e:
                    logging.warning(f"Errore caricamento versione: {e}")




    def visualizza_pdf_pagina(self, relative_path, page_number=0):
        try:
            self.pdf_viewer_canvas.delete("all")
            full_path = os.path.join(self.save_path_var.get(), relative_path)
            if not relative_path or not self.save_path_var.get():
                logging.error(locale.get("missing_base_or_relative_pdf_path"))

                return            
            doc = fitz.open(full_path)
    
            if page_number < 0:
                page_number = 0
            elif page_number >= len(doc):
                page_number = len(doc) - 1
    
            self.current_pdf_page = page_number
            self.total_pdf_pages = len(doc)
    
            zoom = self.pdf_zoom
            mat = fitz.Matrix(zoom, zoom)
            page = doc.load_page(page_number)
            pix = page.get_pixmap(matrix=mat)
            img = Image.open(io.BytesIO(pix.tobytes("png")))
    
            img_tk = ImageTk.PhotoImage(img)
            self.pdf_viewer_canvas.image = img_tk
            self.pdf_viewer_canvas.create_image(0, 0, anchor="nw", image=img_tk)
            self.pdf_viewer_canvas.config(scrollregion=(0, 0, img.width, img.height))
    
        except Exception as e:
            messagebox.showerror(self.locale.get("error_loading_pdf", "Errore caricamento PDF"), str(e))





    def confronta_testi(self, old_text, new_text):
        self.text_diff_box.delete("1.0", "end")
        diff = difflib.ndiff(old_text.splitlines(), new_text.splitlines())
        for line in diff:
            if line.startswith("  "):
                self.text_diff_box.insert("end", line[2:] + "\n", ("common",))
            elif line.startswith("- "):
                self.text_diff_box.insert("end", line[2:] + "\n", ("removed",))
            elif line.startswith("+ "):
                self.text_diff_box.insert("end", line[2:] + "\n", ("added",))
        self.text_diff_box.tag_config("common", foreground="black")
        self.text_diff_box.tag_config("removed", foreground="red")
        self.text_diff_box.tag_config("added", foreground="darkgreen")


    def visualizza_pdf(self, relative_path):
        try:
            base_path = self.save_path_var.get()
            if not base_path or not relative_path:
                logging.error("Percorso base o relativo PDF mancante.")
                return
    
            self.pdf_viewer_canvas.delete("all")
            full_path = os.path.join(base_path, relative_path)
    
            doc = fitz.open(full_path)
            zoom = self.pdf_zoom
            mat = fitz.Matrix(zoom, zoom)
    
            images = []
            total_height = 0
            max_width = 0
    
            for page in doc:
                pix = page.get_pixmap(matrix=mat)
                img = Image.open(io.BytesIO(pix.tobytes("png")))
                images.append(img)
                total_height += img.height
                max_width = max(max_width, img.width)
    
            combined = Image.new("RGB", (max_width, total_height), "white")
    
            y_offset = 0
            for img in images:
                combined.paste(img, (0, y_offset))
                y_offset += img.height
    
            img_tk = ImageTk.PhotoImage(combined)
            self.pdf_viewer_canvas.image = img_tk
            self.pdf_viewer_canvas.create_image(0, 0, anchor="nw", image=img_tk)
            self.pdf_viewer_canvas.config(scrollregion=(0, 0, max_width, total_height))
    
        except Exception as e:
            messagebox.showerror(self.locale.get("error_loading_pdf", "Errore caricamento PDF"), str(e))



def convert_pdf_to_images_fitz(pdf_path, dpi=150):
    """
    Converte ogni pagina del PDF in una immagine PNG usando PyMuPDF.
    Restituisce la lista dei file immagine generati.
    """
    image_paths = []
    try:
        doc = fitz.open(pdf_path)
        for i in range(len(doc)):
            page = doc.load_page(i)
            pix = page.get_pixmap(dpi=dpi)
            img_path = f"{os.path.splitext(pdf_path)[0]}_page{i+1}.png"
            pix.save(img_path)
            image_paths.append(img_path)
        doc.close()
        logging.info(f"[RASTER] {len(image_paths)} pagine convertite in immagini.")
        return image_paths
    except Exception as e:
        logging.error(f"[RASTER] Errore durante la conversione PDF in immagini con fitz: {e}")
        return []

def replace_pdf_with_images_fitz(pdf_path, image_paths):
    """
    Ricostruisce un nuovo PDF interamente rasterizzato da immagini.
    Sovrascrive il PDF originale.
    """
    try:
        images = [Image.open(p).convert("RGB") for p in image_paths]
        if images:
            images[0].save(pdf_path, save_all=True, append_images=images[1:])
            logging.info(f"[RASTER] PDF ricreato da immagini: {pdf_path}")
            # Rimuovi i PNG temporanei
            for img in image_paths:
                os.remove(img)
            try:
                os.chmod(pdf_path, 0o600)
            except:
                pass
        else:
            # logging.warning("[RASTER] Nessuna immagine valida, PDF originale non modificato.")
            logging.warning(locale.get("raster_no_valid_image_original_pdf_retained"))
    except Exception as e:
        logging.error(f"[RASTER] Errore durante la ricostruzione PDF da immagini: {e}")


if __name__ == "__main__":
    root = TkinterDnD.Tk()
#     root = tk.Tk()
    app = App(root)
    root.mainloop()# -*- coding: utf-8 -*-
"""
Created on Tue Nov 26 14:37:32 2024

@author: piret
"""

