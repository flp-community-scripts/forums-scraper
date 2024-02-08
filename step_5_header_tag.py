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

from dotenv import dotenv_values

dotenv_config = dotenv_values(".env")
client = OpenAI(api_key=dotenv_config["OPENAI_API_KEY"])

with open('summary-prompts.yaml', 'r') as file:
  summary_prompts = yaml.safe_load(file)

header_template_path = './header-spec.go.tmpl'


def construct_header(data):
  tmpjson = './.tmp.json'

  # Convert the data to JSON because gomplate can easily parse JSON
  data_json = json.dumps(data)

  with open(tmpjson, 'w') as writer:
    writer.write(data_json)

  # Call gomplate with the data and template
  result = subprocess.run(
      ['gomplate', '-f', header_template_path, '-c', f'.={tmpjson}'],
      capture_output=True,
      text=True)

  if result.returncode != 0:
    raise Exception("Error processing template: " + result.stderr)

  return result.stdout


def list_files_recursive(path):
  file_paths = []  # List to store file paths
  for root, _, files in os.walk(path):
    for file in files:
      file_paths.append(os.path.relpath(os.path.join(root, file), start=path))
  return file_paths


def version_label_from_file(f, label):
  label_regex = re.compile(r'\s*([^\.<>"]+?(?:v\d+(\.\d+)?)?)(?=\.\w+$)')
  basename = os.path.basename(f)
  label_match = label_regex.match(basename)
  if label_match:
    return label_match.group(1)
  else:
    return label


def pick_version_label(f, v, d=' / '):
  l = version_label_from_file(f, None)
  if l and l != v.label:
    return f'{v.label}{d}{l}'
  else:
    return v.label


def prompt_all(header_spec_input, **kwargs):

  for field in fields(header_spec_input):
    if field.metadata.get(
        "prompt", False):  # Check if this field is flagged for prompting
      attribute_name = field.name
      prompt_function_name = f"prompt_{attribute_name}"
      if hasattr(llm, prompt_function_name):
        prompt_function = getattr(llm, prompt_function_name)
        # Call the function, pass header_spec_input and other kwargs as needed
        result = prompt_function(header_spec_input=header_spec_input, **kwargs)
        setattr(header_spec_input, attribute_name, result)


def step_5_header_tag():
  cache = dc.Cache('./cache.db')

  for k in cache.iterkeys():
    if not k.startswith('pthread'):
      continue

    ftp: ForumThreadProcessed = deserialize(cache.get(k))

    vbasepath = './versions'
    # print('---- k')
    for v in ftp.versions:
      vpath = f'{vbasepath}/{v.label}'
      # print('-- v')

      labels = [(pick_version_label(f, v, d=' / '), f)
                for f in list_files_recursive(vpath)]

      for normalized_label, file_path in labels:
        print(normalized_label)
        fpath = f'{vpath}/{file_path}'

        if check_flp_header_in_file(fpath):
          continue

        header_spec_input = HeaderSpecInputV3(
            title=normalized_label,
            authors=ftp.ft.posts[0].author.user_name,
        )

        code_slice = read_first_n_lines(fpath, n=200)

        prompt_all(header_spec_input=header_spec_input,
                   ftp=ftp,
                   code_slice=code_slice,
                   labels=labels)

        flpheader = construct_header(asdict(header_spec_input))

        prepend_string_to_file(fpath, flpheader)
        # print(flpheader)

        # exit(0)

        # original_post = ftp.ft.posts[0].content_html
        # soup = BeautifulSoup(original_post, "html.parser")

        # header_input = {
        #   "title": normalized_label,
        #   "authors": ftp.ft.posts[0].author.user_name
        # }

        # header_input.version = derive_version(normalized_label, ftp,)
        # header_input.description = derive_description(normalized_label, ftp,)
        # header_input.license = get_license_if_any(normalized_label)
        # header_input.category = guess_category(normalized_label)

        # print(construct_header(header_input))

        # print(soup.get_text())

  cache.close()


if __name__ == '__main__':
  step_5_header_tag()
