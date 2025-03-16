import os
import shutil
import subprocess
import logging
from concurrent.futures import ThreadPoolExecutor

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

def process_file(filename):
    if filename in {UPDATED_DIR_NAME, NOT_UPDATED_DIR_NAME}:
        return

    source_file = os.path.join(SOURCE_DIR, filename)
    if not os.path.isfile(source_file):
        return

    result = subprocess.run(
        ['exiftool', '-overwrite_original', '-FileCreateDate<DateTimeOriginal', '-FileModifyDate<DateTimeOriginal', source_file],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    if result.returncode != 0:
        logging.error(f"Error processing {filename}: {result.stderr}")
        destination_dir = NOT_UPDATED_DIR
    elif '1 image files updated' in result.stdout:
        logging.info(f'Updated and moved: {filename}')
        destination_dir = UPDATED_DIR
    else:
        logging.info(f'No DateTimeOriginal found (moved to {NOT_UPDATED_DIR_NAME}): {filename}')
        destination_dir = NOT_UPDATED_DIR

    shutil.move(source_file, os.path.join(destination_dir, filename))

with ThreadPoolExecutor() as executor:
    executor.map(process_file, os.listdir(SOURCE_DIR))

logging.info('Processing complete.')
