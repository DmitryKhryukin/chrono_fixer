import os
import shutil
import subprocess
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

SOURCE_DIR = os.path.abspath('/your/folder')
UPDATED_DIR_NAME = 'updated'
NOT_UPDATED_DIR_NAME = '_not_updated'
UPDATED_DIR = os.path.join(SOURCE_DIR, UPDATED_DIR_NAME)
NOT_UPDATED_DIR = os.path.join(SOURCE_DIR, NOT_UPDATED_DIR_NAME)
LOG_FILE = 'logs_chrono_fixer.log'

file_handler = logging.FileHandler(LOG_FILE)
console_handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

logging.basicConfig(level=logging.INFO, handlers=[file_handler, console_handler])

os.makedirs(UPDATED_DIR, exist_ok=True)
os.makedirs(NOT_UPDATED_DIR, exist_ok=True)

def is_exiftool_installed():
    result = subprocess.run(['which', 'exiftool'], stdout=subprocess.PIPE)
    return bool(result.stdout.strip())

if not is_exiftool_installed():
    raise EnvironmentError("ExifTool is not installed or not in PATH.")

def process_file(file_path):
    if any(dir_name in file_path for dir_name in [UPDATED_DIR_NAME, NOT_UPDATED_DIR_NAME]):
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
        destination_dir = NOT_UPDATED_DIR
    elif '1 image files updated' in result.stdout:
        logging.info(f'Updated and moved: {filename}')
        destination_dir = UPDATED_DIR
    else:
        logging.info(f'No DateTimeOriginal found (moved to {NOT_UPDATED_DIR_NAME}): {filename}')
        destination_dir = NOT_UPDATED_DIR

    shutil.move(file_path, os.path.join(destination_dir, filename))

def get_all_files(directory):
    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if d not in [UPDATED_DIR_NAME, NOT_UPDATED_DIR_NAME]]
        for file in files:
            yield os.path.join(root, file)

all_files = list(get_all_files(SOURCE_DIR))
with ThreadPoolExecutor() as executor:
    futures = [executor.submit(process_file, file_path) for file_path in all_files]
    for _ in tqdm(as_completed(futures), total=len(futures), desc="Processing Files"):
        pass

logging.info('Processing complete.')