from concurrent.futures import thread
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from dataclasses import dataclass, asdict
from selenium.webdriver.support.ui import WebDriverWait
from bs4 import BeautifulSoup
from rich.console import Console
from rich.table import Table
from uccommon import *

import random
import time
import pickle
import diskcache as dc
import re
import os
import shutil
import patoolib


def step_4_unpack():
  cache = dc.Cache('./cache.db')

  for k in cache.iterkeys():
    if not k.startswith('pthread'):
      continue

    ftp: ForumThreadProcessed = deserialize(cache.get(k))

    vbasepath = './versions'
    abasepath = './archives'
    dbasepath = './downloads'

    os.makedirs(vbasepath, exist_ok=True)
    os.makedirs(abasepath, exist_ok=True)

    for v in ftp.versions:
      # Archives
      apath = f'{abasepath}/{v.label}'
      os.makedirs(apath, exist_ok=True)

      afpath = f'{apath}/{v.file_name}'

      shutil.copy2(f'{dbasepath}/{v.file_name}', afpath)

      # Extract

      vpath = f'{vbasepath}/{v.label}/'
      os.makedirs(vpath, exist_ok=True)

      patoolib.extract_archive(afpath, outdir=vpath)

  cache.close()


if __name__ == '__main__':

  step_4_unpack()
