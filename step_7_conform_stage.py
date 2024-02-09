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

input_path = "./staging"

files = list_files_recursive(input_path)

for f in files:
  if not os.path.basename(f).endswith(".pyscript") and not os.path.basename(f).endswith(".py"):
    continue

  cat_real = os.path.dirname(f).split(os.path.sep)[0]

  if not (os.path.basename(f).startswith("(archive)") or cat_real == 'Archive') \
    or cat_real == 'Packages':
    continue
  
  src_path = f'{input_path}/{f}'

  flp_header = header_input_from_file(src_path)
  
  if cat_real != flp_header.category:
    flp_header.category = cat_real
    print(f"Conforming: {src_path}")
    
  # flp_header.description = fill_preserving_newlines(flp_header.description, 80)

  # if flp_header.changelog:
  #   # flp_header.changelog = flp_header.changelog.replace(' - ', '\n- ')

  #   pattern = r'(\d{4}-\d{2}-\d{2})'
  #   replaced_text = re.sub(pattern, r'\n\1', flp_header.changelog)
    
  #   flp_header.changelog = replaced_text

  #   flp_header.changelog = re.sub(pattern, r'\n\n\1', flp_header.changelog)

  update_or_prepend_flp_block(src_path, flp_header)
  