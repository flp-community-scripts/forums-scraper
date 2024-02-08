from concurrent.futures import thread
from distutils.cygwinccompiler import get_versions

from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from dataclasses import dataclass, asdict
from selenium.webdriver.support.ui import WebDriverWait
from bs4 import BeautifulSoup
from rich.console import Console
from rich.table import Table
from uccommon import *

import yaml
import random
import time
import pickle
import diskcache as dc
import re
import os
import shutil
import patoolib
import subprocess
import json
from openai import OpenAI
import llm

with open('summary-prompts.yaml', 'r') as file:
  summary_prompts = yaml.safe_load(file)

input_path = "./versions"

files = list_files_recursive(input_path)

unique_check = set()

for f in files:
  b = os.path.basename(f)
  
  if b in unique_check:
    print("Duplicate found: ", f)
    exit(1)
    
  unique_check.add(b)

staging_path = "./staging"

# if any(os.path.isfile(os.path.join(staging_path, item)) for item in os.listdir(staging_path)):
#   response = input(f'Clean "{staging_path}"? (y/n): ').lower()
#   if response in ['y', 'yes']:
#     empty_directory(staging_path)

archive_path = f"{staging_path}/Archive"

os.makedirs(archive_path, exist_ok=True)
for c in summary_prompts['categories']:
  os.makedirs(f"{staging_path}/{c}", exist_ok=True)

for f in files:
  src_path = f'{input_path}/{f}'
  flp_header = header_input_from_file(src_path)
  
  # if flp_header.category:
  #   dest_path = f'{staging_path}/{flp_header.category}/(archive) {os.path.basename(f)}'
  #   shutil.copy2(src_path, dest_path)

  dest_path = f'{staging_path}/Archive/{os.path.basename(f)}'
  shutil.copy2(src_path, dest_path)
  flp_header.category = 'Archive'
  update_or_prepend_flp_block(dest_path, flp_header)
