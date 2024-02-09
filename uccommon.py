import pickle
import re
import json
import subprocess
import os
import shutil
import textwrap
import chardet
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

  thread_link: Optional[str] = field(default=None, metadata={"real_label": "Thread Link"})

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

def read_first_n_lines(file_path, n=200):
  """
  Reads the first n lines of a file, assuming UTF-8 encoding, and returns them as a string.
  Unknown characters are replaced with '?'.

  Parameters:
  file_path (str): Path to the file to be read.
  n (int): Number of lines to read. Defaults to 200.

  Returns:
  str: The first n lines of the file as a single string.
  """
  lines = []
  with open(file_path, 'r', encoding='utf-8', errors='replace') as file:
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
  with open(file_path, 'r', errors='replace') as file:
    content = file.read()
    if flp_pattern.search(content):
      return True
    else:
      return False


def prepend_string_to_file(file_path, string_to_prepend):
  # Step 1: Open the original file and read its contents
  with open(file_path, 'r', errors='replace') as file:
    original_content = file.read()

  # Step 2 & 3: Open the file in write mode and prepend the string
  with open(file_path, 'w', errors='replace') as file:
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
  real_label_map = {field.metadata["real_label"]: field.name for field in fields(HeaderSpecInputV3) if "real_label" in field.metadata}

  lines = flp_block_content.split("\n")

  for line in lines:
    if line.strip() == "":  # Detecting paragraph breaks
      if current_key:
        parsed_data[current_key] += "\n"
      continue

    # Detect field labels and assign them as current keys
    label_detected = False
    for real_label, field_name in real_label_map.items():
      if line.startswith(real_label + ":"):
        current_key = field_name
        parsed_data[current_key] = line[len(real_label) + 1:].strip()  # Skip label and colon, then trim
        label_detected = True
        break

    if not label_detected and current_key:
      # Append the line to the current field, maintaining paragraph structure
      if parsed_data[current_key]:  # If there's already content, prepend with a newline
        parsed_data[current_key] += "\n" + line
      else:
        parsed_data[current_key] = line

  # Ensure each field ends without excessive newlines
  for key in parsed_data:
    parsed_data[key] = parsed_data[key].strip()

  return HeaderSpecInputV3(**{field.name: parsed_data.get(field.name, None) for field in fields(HeaderSpecInputV3)})

# def parse_text_to_headerinput(text):
#   flp_block_pattern = re.compile(r'"""flp(.*?)"""', re.DOTALL)
#   match = flp_block_pattern.search(text)
#   if not match:
#     return None  # No flp block found

#   flp_block_content = match.group(1).strip()  # Get the content without the flp markers

#   parsed_data = {}
#   current_key = None

#   # Create a mapping from real_label to field name
#   real_label_map = {field.metadata["real_label"]: field.name for field in fields(HeaderSpecInputV3) if "real_label" in field.metadata}

#   lines = flp_block_content.split("\n")

#   for line in lines:
#     found_key = False
#     for real_label, field_name in real_label_map.items():
#       if line.startswith(real_label + ":"):
#         current_key = field_name
#         _, _, initial_value = line.partition(": ")
#         parsed_data[current_key] = initial_value.strip()
#         found_key = True
#         break

#     if not found_key and current_key:
#       # Trim leading and trailing whitespace from the line
#       line_content = line.strip()
#       # Only append the line if it's not empty, avoiding unnecessary newlines
#       if line_content:
#         # Append with a space if content already exists, otherwise just set it
#         if parsed_data[current_key]:
#           parsed_data[current_key] += "\n" + line_content
#         else:
#           parsed_data[current_key] = line_content

#   return HeaderSpecInputV3(**{field.name: parsed_data.get(field.name, None) for field in fields(HeaderSpecInputV3)})

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

# def version_label_from_file(f, label):
#   label_regex = re.compile(r'\s*([^\.<>"]+?(?:v\d+(\.\d+)?)?)(?=\.\w+$)')
#   basename = os.path.basename(f)
#   label_match = label_regex.match(basename)
#   if label_match:
#     return label_match.group(1)
#   else:
#     return label

# def version_label_from_file(f, default_label):
#   # Updated regex to capture more complex filename structures, including version numbers and descriptive text
#   label_regex = re.compile(r'\s*(.*?)\s*(v\d+(\.\d+)?\s*(.*?))?(?=\.\w+$)')
#   basename = os.path.basename(f)
#   label_match = label_regex.match(basename)
#   if label_match:
#     # Concatenate the base name and version number if present, including any additional descriptive text
#     base_name = label_match.group(1).strip()
#     version = label_match.group(2) if label_match.group(2) else ""
#     additional_text = label_match.group(4).strip() if label_match.group(4) else ""
#     full_label = f"{base_name} {version} {additional_text}".strip()
#     return full_label
#   else:
#     return default_label

def version_label_from_file(f, default_label):
  # Improved regex to exclude multiple file extensions using negative lookahead to preserve version numbers
  label_regex = re.compile(r'''
    ^                               # Start of the string
    (.+?)                           # Non-greedy capture of the initial part of the filename, potentially including version
    ((?:\.\d+)+)?                   # Optionally capturing version numbers as '.number'
    (?=                             # Start of positive lookahead for file extension(s)
      (?:\.\w+)+                  # Non-capturing group for one or more '.word' sequences at the end
      $                           # End of the string
    )
  ''', re.VERBOSE)

  basename = os.path.basename(f)  # Extract the basename
  label_match = label_regex.match(basename)
  
  if label_match:
    # Concatenate base name and version number, if present
    full_label = f"{label_match.group(1)}{label_match.group(2) or ''}".strip()
    return full_label
  else:
    # If regex match fails, fallback to using the default label without change
    return default_label

def fill_preserving_newlines(text, width=80):
  """Wrap text with preservation of existing newlines."""
  lines = text.split('\n')  # Split the text into lines
  wrapped_lines = [textwrap.fill(line, width=width) for line in lines]  # Wrap each line
  return '\n'.join(wrapped_lines)  # Combine wrapped lines, preserving original newlines

