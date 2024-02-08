import pickle
import re
from dataclasses import dataclass, field
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
  title: str
  authors: str

  category: Optional[str] = field(default=None, metadata={"prompt": True})
  description: Optional[str] = field(default=None, metadata={"prompt": True})
  version: Optional[str] = field(default=None, metadata={"prompt": True})
  changelog: Optional[str] = field(default=None, metadata={"prompt": True})
  license: Optional[str] = field(default=None, metadata={"prompt": True})


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
