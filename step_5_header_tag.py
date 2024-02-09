from dataclasses import asdict, fields
from uccommon import *

import yaml
import diskcache as dc
import re
import os
import subprocess
import json
from openai import OpenAI
import llm
import textwrap

from dotenv import dotenv_values

dotenv_config = dotenv_values(".env")
client = OpenAI(api_key=dotenv_config["OPENAI_API_KEY"])

with open('summary-prompts.yaml', 'r') as file:
  summary_prompts = yaml.safe_load(file)

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
    for v in ftp.versions:
      vpath = f'{vbasepath}/{v.label}'

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
          thread_link=f"https://forum.image-line.com/viewtopic.php?t={ftp.thread_id}"
        )

        code_slice = read_first_n_lines(fpath, n=200)
        
        prompt_all(header_spec_input=header_spec_input,
                   ftp=ftp,
                   code_slice=code_slice,
                   labels=labels)
        
        if header_spec_input.description:
          header_spec_input.description = fill_preserving_newlines(
            header_spec_input.description, 80)

        if header_spec_input.changelog:
          header_spec_input.changelog = fill_preserving_newlines(
            header_spec_input.changelog, 80)
          
        if not header_spec_input.license:
          header_spec_input.license = "Unknown"

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
