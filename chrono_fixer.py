import os
import shutil
import subprocess
import logging
import sys
import multiprocessing
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
from tkinter import Tk, filedialog
from datetime import datetime

UPDATED_DIR_PREFIX = '_updated'
LOG_FILE = 'logs_chrono_fixer.log'

# --- we don't want to use all our CPU's ---
MAX_WORKERS = max(1, multiprocessing.cpu_count() // 4)

file_handler = logging.FileHandler(LOG_FILE)
console_handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

logging.basicConfig(level=logging.INFO, handlers=[file_handler, console_handler])

def select_source_directory():
    root = Tk()
    root.withdraw()
    root.update_idletasks()
    selected_dir = filedialog.askdirectory(title="Select Source Directory")
    root.destroy()
    return selected_dir if selected_dir else None

def is_exiftool_installed():
    return shutil.which('exiftool') is not None

if not is_exiftool_installed():
    raise EnvironmentError("ExifTool is not installed or not in PATH.")

def process_file(file_path, updated_file_path):
    if UPDATED_DIR_PREFIX in file_path:
        return

    if not os.path.isfile(file_path):
        return

    extension = os.path.splitext(file_path)[1].lower()
    if extension in ['.jpg', '.jpeg', '.png', '.heic']:  # images
        command = ['exiftool', '-overwrite_original', '-FileCreateDate<DateTimeOriginal', '-FileModifyDate<DateTimeOriginal', file_path]
    elif extension in ['.mp4', '.mov', '.avi', '.mkv']:  # videos
        command = ['exiftool', '-overwrite_original', '-FileModifyDate<MediaCreateDate', file_path]
    else:
        return

    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    if result.returncode != 0:
        logging.error(f"Error processing {file_path}: {result.stderr}")
    elif '1 image files updated' in result.stdout or '1 video files updated' in result.stdout:
        os.makedirs(os.path.dirname(updated_file_path), exist_ok=True)
        shutil.move(file_path, updated_file_path)

def get_all_files(directory):
    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if not d.startswith(UPDATED_DIR_PREFIX)]
        for file in files:
            yield os.path.join(root, file)

def build_updated_path(source_dir, file_path):
    relative_path = os.path.relpath(file_path, source_dir)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    updated_root = os.path.join(os.path.dirname(source_dir), f"{UPDATED_DIR_PREFIX}_{os.path.basename(source_dir)}")
    updated_file_path = os.path.join(updated_root, f"{UPDATED_DIR_PREFIX}_{timestamp}_{relative_path}")
    return updated_file_path

try:
    SOURCE_DIR = select_source_directory()
    if not SOURCE_DIR:
        logging.info("No directory selected. Exiting.")
        sys.exit()

    all_files = list(get_all_files(SOURCE_DIR))
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(process_file, file_path, build_updated_path(SOURCE_DIR, file_path)): file_path for file_path in all_files}

        with tqdm(total=len(futures), desc="Processing Files") as pbar:
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    logging.error(f"Error processing file {futures[future]}: {e}")
                finally:
                    pbar.update(1)
except KeyboardInterrupt:
    logging.info("Processing interrupted by user. Exiting gracefully...")
except Exception as e:
    logging.error(f"An unexpected error occurred: {e}")
finally:
    logging.info('Processing complete.')
