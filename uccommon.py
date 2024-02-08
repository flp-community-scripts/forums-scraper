import pickle
import re
import json
import subprocess
import os
import shutil
from dataclasses import dataclass, field, fields, asdict
from typing import Optional


@dataclass
class Author:
  user_id: str
  user_name: str


@dataclass
class ThreadPost:
  author: Author
  text: str
  content_html: str
  attachbox_html: str
  timestamp: str


@dataclass
class ForumThread:
  thread_id: int
  title: str
  posts: list


@dataclass
class VersionProcessed:
  file_name: str
  label: str
  link: str


@dataclass
class ThreadPostProcessed:
  post: ThreadPost


@dataclass
class ForumThreadProcessed:
  thread_id: int
  ft: ForumThread
  processed_posts: list
  versions: [VersionProcessed]


@dataclass
class HeaderSpecInputV3:
  title: str = field(metadata={"real_label": "Title"})
  authors: str = field(metadata={"real_label": "Author"})

  category: Optional[str] = field(default=None, metadata={"prompt": True, "real_label": "Category"})
  description: Optional[str] = field(default=None, metadata={"prompt": True, "real_label": "Description"})
  version: Optional[str] = field(default=None, metadata={"prompt": True, "real_label": "Version"})
  changelog: Optional[str] = field(default=None, metadata={"prompt": True, "real_label": "Changelog"})
  license: Optional[str] = field(default=None, metadata={"prompt": True, "real_label": "License"})

@dataclass
class ThreadVersionSummary:
  thread_id: int
  ftp: ForumThreadProcessed
  version: VersionProcessed
  headerSpecInput: HeaderSpecInputV3


# Function to serialize an object
def serialize(obj):
  return pickle.dumps(obj)


# Function to deserialize an object
def deserialize(serialized_obj):
  return pickle.loads(serialized_obj)


def store_thread(cache, ft):
  cache.set(f"thread-{str(ft.thread_id)}", serialize(ft))


def get_thread(cache, thread_id):
  v = cache.get(f"thread-{str(thread_id)}")
  return deserialize(v) if v is not None else None


def store_thread_processed(cache, ft):
  cache.set(f"pthread-{str(ft.thread_id)}", serialize(ft))


def get_thread_processed(cache, thread_id):
  v = cache.get(f"pthread-{str(thread_id)}")
  return deserialize(v) if v is not None else None


def store_thread_summary(cache, ft):
  cache.set(f"tsthread-{str(ft.thread_id)}", serialize(ft))


def get_thread_summary(cache, thread_id):
  v = cache.get(f"tsthread-{str(thread_id)}")
  return deserialize(v) if v is not None else None


def extract_thread_id_from_url(url):
  match = re.search(r't=(\d+)', url)
  if match:
    return int(match.group(1))
  else:
    return None  # or a default value or raise an error


def read_first_n_lines(file_path, n):
  """
  Reads the first n lines of a file and returns them as a string without loading the entire file into memory.

  Parameters:
  file_path (str): Path to the file to be read.
  n (int): Number of lines to read. Defaults to 200.

  Returns:
  str: The first n lines of the file as a single string.
  """
  lines = []
  with open(file_path, 'r') as file:
    for i, line in enumerate(file):
      if i < n:
        lines.append(line)
      else:
        break
  return ''.join(lines)


# Define the pattern to search for
flp_pattern = re.compile(r'"""flp.*?"""', re.DOTALL)


# Function to check if the pattern exists in the file
def check_flp_header_in_file(file_path):
  with open(file_path, 'r') as file:
    content = file.read()
    if flp_pattern.search(content):
      return True
    else:
      return False


def prepend_string_to_file(file_path, string_to_prepend):
  # Step 1: Open the original file and read its contents
  with open(file_path, 'r') as file:
    original_content = file.read()

  # Step 2 & 3: Open the file in write mode and prepend the string
  with open(file_path, 'w') as file:
    file.write(string_to_prepend + '\n' +
               original_content)  # Adding a newline for separation


def list_files_recursive(path):
  file_paths = []  # List to store file paths
  for root, _, files in os.walk(path):
    for file in files:
      file_paths.append(os.path.relpath(os.path.join(root, file), start=path))
  return file_paths

def empty_directory(dir_path):
  for item in os.listdir(dir_path):
    item_path = os.path.join(dir_path, item)
    if os.path.isfile(item_path) or os.path.islink(item_path):
      os.remove(item_path)  # Remove files and links
    elif os.path.isdir(item_path):
      shutil.rmtree(item_path)  # Remove subdirectories

def extract_flp_block_from_file(file_path) -> Optional[str]:
  with open(file_path, 'r', encoding='utf-8') as file:
    file_content = file.read()
      
  # Use regular expression to find the flp block
  flp_block_pattern = re.compile(r'"""flp(.*?)"""', re.DOTALL)
  match = flp_block_pattern.search(file_content)
  
  if match:
    return match.group(0)  # Return the matched block including the flp markers
  else:
    return None

def parse_text_to_headerinput(text):
  flp_block_pattern = re.compile(r'"""flp(.*?)"""', re.DOTALL)
  match = flp_block_pattern.search(text)
  if not match:
    return None  # No flp block found

  flp_block_content = match.group(1).strip()  # Get the content without the flp markers

  parsed_data = {}
  current_key = None

  # Create a mapping from real_label to field name
  real_label_map = {field.metadata["real_label"]: field.name for field in fields(HeaderSpecInputV3) if "real_label" in field.metadata}

  lines = flp_block_content.split("\n")

  for line in lines:
    found_key = False
    for real_label, field_name in real_label_map.items():
      if line.startswith(real_label + ":"):
        current_key = field_name
        _, _, initial_value = line.partition(": ")
        parsed_data[current_key] = initial_value.strip()
        found_key = True
        break

    if not found_key and current_key:
      # Trim leading and trailing whitespace from the line
      line_content = line.strip()
      # Only append the line if it's not empty, avoiding unnecessary newlines
      if line_content:
        # Append with a space if content already exists, otherwise just set it
        if parsed_data[current_key]:
          parsed_data[current_key] += " " + line_content
        else:
          parsed_data[current_key] = line_content

  return HeaderSpecInputV3(**{field.name: parsed_data.get(field.name, None) for field in fields(HeaderSpecInputV3)})

# def parse_text_to_headerinput(text):
#   parsed_data = {}
#   lines = text.strip().split("\n")
#   current_key = None

#   # Create a mapping from real_label to field name
#   real_label_map = {field.metadata["real_label"]: field.name for field in fields(HeaderSpecInputV3) if "real_label" in field.metadata}

#   for line in lines:
#     # Check if the line corresponds to any real_label
#     for real_label, field_name in real_label_map.items():
#       if line.startswith(real_label + ":"):
#         current_key = field_name
#         _, _, initial_value = line.partition(": ")
#         parsed_data[current_key] = initial_value.strip()
#         break
#     else:
#       if current_key in parsed_data:
#         parsed_data[current_key] += "\n" + line.strip()
#       else:
#         parsed_data[current_key] = line.strip()

  # Initialize the dataclass with parsed data, using default None for missing fields
  return HeaderSpecInputV3(**{field.name: parsed_data.get(field.name) for field in fields(HeaderSpecInputV3)})

def header_input_from_file(file_path):
  text = extract_flp_block_from_file(file_path)
  if not text:
    return None
  return parse_text_to_headerinput(text,)

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

def update_or_prepend_flp_block(file_path, header_spec_input):
  with open(file_path, 'r', encoding='utf-8') as file:
    content = file.read()

  flp_block_pattern = re.compile(r'"""flp.*?"""', re.DOTALL)
  match = flp_block_pattern.search(content)
  
  flp_header = construct_header(asdict(header_spec_input))
  
  if match:
    updated_content = flp_block_pattern.sub(flp_header, content)
  else:
    updated_content = flp_header + '\n' + content
  
  with open(file_path, 'w', encoding='utf-8') as file:
    file.write(updated_content)