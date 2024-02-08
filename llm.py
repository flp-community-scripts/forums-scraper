from calendar import c
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
import tiktoken
from openai import OpenAI

from dotenv import dotenv_values

dotenv_config = dotenv_values(".env")
client = OpenAI(api_key=dotenv_config["OPENAI_API_KEY"])

with open('summary-prompts.yaml', 'r') as file:
  summary_prompts = yaml.safe_load(file)

smaller_model = "gpt-3.5-turbo"
smaller_model_limit = 4096
larger_model = "gpt-3.5-turbo-16k"
conditionally_use_larger_model = True

tiktokenizer = tiktoken.encoding_for_model(smaller_model)


def count_small_model_tokens(t):
  return len(tiktokenizer.encode(t))


def process_prompt_oneshot(input: str, system_prompt: str, temperature=0):
  model = smaller_model

  if conditionally_use_larger_model:
    tokens = count_small_model_tokens(system_prompt + input) + 12

    if tokens > smaller_model_limit:
      model = larger_model

  response = client.chat.completions.create(
      model=model,  # Replace with your desired model
      messages=[{
          "role": "system",
          "content": system_prompt
      }, {
          "role": "user",
          "content": input
      }],
      temperature=temperature)
  response = response.choices[0].message.content

  return response


def prompt_version(ftp: ForumThreadProcessed,
                   header_spec_input: HeaderSpecInputV3, labels: [str],
                   **kwargs):

  original_post = ftp.ft.posts[0].content_html
  soup = BeautifulSoup(original_post, "html.parser")

  othernames = "\n".join([f"- {l}" for l in labels])

  vreply = process_prompt_oneshot(
      f"""
|currentfilebegin|{header_spec_input.title}|currentfileend|
                                
|othernamesbegin|
{othernames}
|othernamesend|

|postbegin|
{soup.get_text()}
|postend|
                                
""", summary_prompts['version'])

  if "no-version" in vreply:
    return None

  if "version: " in vreply:
    return vreply.split("version: ")[-1]

  return None


def prompt_description(ftp: ForumThreadProcessed,
                       header_spec_input: HeaderSpecInputV3, **kwargs):

  original_post = ftp.ft.posts[0].content_html
  soup = BeautifulSoup(original_post, "html.parser")

  return process_prompt_oneshot(soup.get_text(),
                                summary_prompts['description'])


def prompt_changelog(ftp: ForumThreadProcessed,
                     header_spec_input: HeaderSpecInputV3, **kwargs):

  original_post = ftp.ft.posts[0].content_html
  soup = BeautifulSoup(original_post, "html.parser")

  return process_prompt_oneshot(soup.get_text(), summary_prompts['changelog'])


def prompt_category(ftp: ForumThreadProcessed,
                    header_spec_input: HeaderSpecInputV3, code_slice: str,
                    **kwargs):

  original_post = ftp.ft.posts[0].content_html
  soup = BeautifulSoup(original_post, "html.parser")

  categories = "\n".join([f'- {c}' for c in summary_prompts['categories']])

  creply = process_prompt_oneshot(
      f"""
|currentfilebegin|{header_spec_input.title}|currentfileend|
                                
|availablecategoriesbegin|
{categories}
|availablecategoriesend|
                                  
|codebegin|
{code_slice}
|codeend|

|postbegin|
{soup.get_text()}
|postend|
                                
""", summary_prompts['category'])

  if "no-category" in creply:
    return None

  if "category: " in creply:
    return creply.split("category: ")[-1]

  return None


def prompt_license(ftp: ForumThreadProcessed,
                   header_spec_input: HeaderSpecInputV3, code_slice: str,
                   **kwargs):

  original_post = ftp.ft.posts[0].content_html
  soup = BeautifulSoup(original_post, "html.parser")

  creply = process_prompt_oneshot(
      f"""
|codebegin|
{code_slice}
|codeend|

|postbegin|
{soup.get_text()}
|postend|
""", summary_prompts['license'])

  if "no-license" in creply:
    return None

  if "license: " in creply:
    return creply.split("license: ")[-1]

  return None
