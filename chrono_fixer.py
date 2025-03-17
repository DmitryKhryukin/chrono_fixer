import os
import shutil
import subprocess
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import multiprocessing

SOURCE_DIR = os.path.abspath('/your/folder')
UPDATED_DIR_NAME = '_updated'
LOG_FILE = 'logs_chrono_fixer.log'

# --- we don't want to use all our cpu's ---
MAX_WORKERS = max(1, multiprocessing.cpu_count() // 2)

file_handler = logging.FileHandler(LOG_FILE)
console_handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

logging.basicConfig(level=logging.INFO, handlers=[file_handler, console_handler])

def is_exiftool_installed():
    result = subprocess.run(['which', 'exiftool'], stdout=subprocess.PIPE)
    return bool(result.stdout.strip())

if not is_exiftool_installed():
    raise EnvironmentError("ExifTool is not installed or not in PATH.")

def process_file(file_path, updated_dir):
    if UPDATED_DIR_NAME in file_path:
        return

    if not os.path.isfile(file_path):
        return

    result = subprocess.run(
        ['exiftool', '-overwrite_original', '-FileCreateDate<DateTimeOriginal', '-FileModifyDate<DateTimeOriginal', file_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    filename = os.path.basename(file_path)
    if result.returncode != 0:
        logging.error(f"Error processing {filename}: {result.stderr}")
    elif '1 image files updated' in result.stdout:
        shutil.move(file_path, os.path.join(updated_dir, filename))

def get_all_files(directory):
    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if d != UPDATED_DIR_NAME]
        for file in files:
            yield os.path.join(root, file)

def prepare_dirs(root):
    updated_dir = os.path.join(root, UPDATED_DIR_NAME)
    os.makedirs(updated_dir, exist_ok=True)
    return updated_dir

try:
    all_files = list(get_all_files(SOURCE_DIR))
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = []
        for file_path in all_files:
            root = os.path.dirname(file_path)
            updated_dir = prepare_dirs(root)
            futures.append(executor.submit(process_file, file_path, updated_dir))
        
        for _ in tqdm(as_completed(futures), total=len(futures), desc="Processing Files"):
            pass
except KeyboardInterrupt:
    logging.info("Processing interrupted by user. Exiting gracefully...")
except Exception as e:
    logging.error(f"An unexpected error occurred: {e}")
finally:
    logging.info('Processing complete.')
