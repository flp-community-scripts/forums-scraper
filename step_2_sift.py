from bs4 import BeautifulSoup
from rich.console import Console
from rich.table import Table
from uccommon import *

import pickle
import diskcache as dc
import re


# Function to serialize an object
def serialize(obj):
  return pickle.dumps(obj)


# Function to deserialize an object
def deserialize(serialized_obj):
  return pickle.loads(serialized_obj)


def store_thread_processed(cache, ft):
  cache.set(f"pthread-{str(ft.thread_id)}", serialize(ft))


def get_thread_processed(cache, thread_id):
  v = cache.get(f"pthread-{str(thread_id)}")
  return deserialize(v) if v is not None else None


def grep_An_Bk(pattern, lines, n, k, should_join=True, multi_list=False):
  # Compile the regular expression pattern
  regex = re.compile(pattern)
  lstr = []
  ml = []

  for i, line in enumerate(lines):
    # Search for the pattern in the line
    if regex.search(line):
      start = max(0, i - k)
      end = min(len(lines), i + n + 1)
      for j in range(start, end):
        lstr.append(lines[j].rstrip())
      if multi_list:
        ml.append([x for x in lstr])
        lstr.clear()

  if multi_list:
    return ml
  if should_join:
    return '\n'.join(lstr)
  return lstr


def sift_versions(input_lists):
  base_url = "https://forum.image-line.com"
  versions = []

  # Regex to capture the download link and file base name (ignoring extensions and version numbers)
  link_regex = re.compile(r'.*(/download/file\.php\?id=\d+).*')
  label_regex = re.compile(r'\s*([^\.<>"]+?(?:v\d+(\.\d+)?)?)(?=\.\w+$)')

  # label_regex = re.compile(r'\s*([^\.<>"]+?(?:\.\d+)*)')

  for item in input_lists:
    # Extracting the link
    link_match = link_regex.match(item[0])
    if link_match:
      full_link = f"{base_url}{link_match.group(1)}"

      # Extracting the label
      label_match = label_regex.match(item[1])
      if label_match:
        label = label_match.group(1).strip()

        versions.append(
            VersionProcessed(label=label,
                             link=full_link,
                             file_name=item[1].strip()))

  return versions


def step_2_sift():
  cache = dc.Cache('./cache.db')
  i = 0
  # ft: ForumThread = deserialize(cache.get('thread-310304'))
  # print(ft)

  console = Console()

  # Create a table
  t1 = Table(show_header=True, header_style="bold magenta")
  t1.add_column("Matched", style="dim", width=90)
  t1.add_column("Author", style="dim", width=12)

  for k in cache.iterkeys():
    # print(k)
    if not k.startswith('thread'):
      continue

    ft: ForumThread = deserialize(cache.get(k))
    st = ft.title.lower()

    title_ignore_patterns = [
        'request', 'req', 'demo', 'meme', 'question', 'to all', '\sme\s',
        'GoldenPond'
    ]

    ignore_authors = [
        'BinaryBorn',
        'cableerector',
    ]

    if any([re.search(p.lower(), st) for p in title_ignore_patterns]):
      continue

    if any(
        [re.search(p, ft.posts[0].author.user_name) for p in ignore_authors]):
      continue

    # print(ft.posts[0].author.user_name)
    # print(ft.title)

    valid_html_patterns = [
        # '<code>',
        '\.zip',
        '\.rar',
        '\.tar',
        '\.pyscript'
    ]

    merged_html = ft.posts[0].content_html + \
      (ft.posts[0].attachbox_html if ft.posts[0].attachbox_html is not None else '')

    if not any([re.search(p, merged_html) for p in valid_html_patterns]):
      continue

    html = merged_html

    soup = BeautifulSoup(html, "html.parser")

    for video_tag in soup.find_all('video'):
      video_tag.extract()

    for img_tag in soup.find_all('img'):
      img_tag.extract()

    for img_tag in soup.find_all('svg'):
      img_tag.extract()

    elements_to_remove = soup.find_all(
        attrs={
            "style":
            lambda x: x and
            'width: 100%; height: 100%; background-image: url("data:image/png;base64'
            in x
        })

    # Remove those elements
    for element in elements_to_remove:
      element.extract()

    text = soup.prettify()
    # print(ft.thread_id)

    files = []

    for p in valid_html_patterns:
      files.extend(grep_An_Bk(p, text.split('\n'), 1, 1, multi_list=True))

    tpp0 = ThreadPostProcessed(post=ft.posts[0])

    # print(files)
    # print(files)
    versions = sift_versions(files)

    ftp = ForumThreadProcessed(thread_id=ft.thread_id,
                               versions=versions,
                               ft=ft,
                               processed_posts=[tpp0])

    store_thread_processed(cache, ftp)
    # print(get_thread_processed(cache, ftp.thread_id))
    print(ft.thread_id, versions)

    i += 1

    # console.print(t1)
  # print(tabulate(t1, headers="firstrow", tablefmt="pretty"))

  print(f'Total: {i}')
  # open('test.html', 'w').write(ft.posts[0].html)

  cache.close()


if __name__ == '__main__':
  step_2_sift()
