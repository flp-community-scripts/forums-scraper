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
  # b = os.path.basename(f)
  
  if f in unique_check:
    print("Duplicate found: ", f)
    
  unique_check.add(f)

staging_path = "./staging"
staging_order_memo = "./staging-order-memo"

if any(os.path.isfile(os.path.join(staging_path, item)) for item in os.listdir(staging_path)):
  response = input(f'Clean "{staging_path}"? (y/n): ').lower()
  if response in ['y', 'yes']:
    empty_directory(staging_path)

archive_path = f"{staging_path}/Archive"

os.makedirs(archive_path, exist_ok=True)
for c in summary_prompts['categories']:
  os.makedirs(f"{staging_path}/{c}", exist_ok=True)

staging_order_memo_files = list_files_recursive(staging_order_memo)

category_memo = {}

for f in staging_order_memo_files:
  b = os.path.basename(f)

  if not os.path.basename(f).endswith(".pyscript") and not os.path.basename(f).endswith(".py"):
    continue
  
  if not os.path.basename(f).startswith("(archive)"):
    continue
  
  category_memo[b] = os.path.dirname(f).split(os.path.sep)[0]
  # print(category_memo[b])

for f in files:
  if not os.path.basename(f).endswith(".pyscript") and not os.path.basename(f).endswith(".py"):
    continue

  src_path = f'{input_path}/{f}'
  flp_header = header_input_from_file(src_path)
  
  # print(flp_header.changelog)
  # exit(0)

  parts = f.split(os.path.sep)
  p = os.path.sep.join(parts[1:])

  if flp_header.category and os.path.dirname(p) == '':
    dest_path = ''
    k = f'(archive) {os.path.basename(f)}'

    if k in category_memo:
      print(k, category_memo[k])
      dest_path = f'{staging_path}/{category_memo[k]}/{k}'
      shutil.copy2(src_path, dest_path)
      flp_header.category = category_memo[k]
      update_or_prepend_flp_block(dest_path, flp_header) 
    else:
      dest_path = f'{staging_path}/{flp_header.category}/{k}'
      shutil.copy2(src_path, dest_path)
      # flp_header = header_input_from_file(dest_path)
      # flp_header.category = flp_header
      # update_or_prepend_flp_block(dest_path, flp_header) 

  # p = os.path.join(*parts[1:-1])
  dest_path = f'{staging_path}/Archive/{p}'

  os.makedirs(f'{staging_path}/Archive/{os.path.dirname(p)}', exist_ok=True)
  shutil.copy2(src_path, dest_path)
  flp_header.category = 'Archive'
  update_or_prepend_flp_block(dest_path, flp_header)
