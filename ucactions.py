from concurrent.futures import thread
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import NoSuchElementException

from bs4 import BeautifulSoup

import random
import time
import diskcache as dc
import re
from uccommon import *


def sleep_with_jitter(min_seconds, max_seconds):
  time.sleep(random.uniform(min_seconds, max_seconds))


def go_forum(driver: WebDriver):
  return driver.get("https://forum.image-line.com/viewforum.php?f=2008")


def enum_titles(driver: WebDriver):
  el = driver.find_elements(By.CLASS_NAME, "topictitle")

  for element in el:
    inner_html = element.get_attribute("innerHTML")
    print(inner_html)


class PianorollPageIterator:

  def __init__(self, page_limit=None):
    self.counter = 0
    self.page_limit = page_limit

  def __iter__(self):
    return self

  def __next__(self):
    if self.counter == 0:
      url = "https://forum.image-line.com/viewforum.php?f=2008"
    else:
      url = f"https://forum.image-line.com/viewforum.php?f=2008&start={self.counter * 50}"

    if self.page_limit is not None and self.counter >= self.page_limit:
      raise StopIteration

    self.counter += 1
    return url


def testcache():
  cache = dc.Cache('./cache.db')

  # Example object
  ft = ForumThread(title="Sample Thread",
                   posts=[
                       ThreadPost(author=Author(user_id="123",
                                                user_name="John"),
                                  text="Sample text",
                                  timestamp="2024-02-08 12:00:00")
                   ])

  cache.set("test_1", serialize(ft))
  print(deserialize(cache.get("test_1")))
  # print(cache.get("test_1", ))


def parse_user_id_from_profile_link(href):
  # Extracts the user ID from the profile link
  # This is a simplified example, adjust the parsing as necessary based on the actual URL structure
  parts = href.split("&")
  for part in parts:
    if part.startswith("u="):
      return part.split("=")[1]
  return None


def get_posts_from_current_page(driver, cache):
  posts_elements = driver.find_elements(By.CLASS_NAME, "post")
  posts = []

  for post_element in posts_elements:
    user_name_element = post_element.find_element(
        By.XPATH, ".//a[contains(@href, 'mode=viewprofile')]")
    user_name = user_name_element.text
    user_id = parse_user_id_from_profile_link(
        user_name_element.get_attribute('href'))

    # Check if author is cached
    author_key = f"author_{user_id}"
    if author_key in cache:
      author = cache[author_key]
    else:
      author = Author(user_id=user_id, user_name=user_name)
      cache.set(author_key, author)

    timestamp_element = post_element.find_element(By.CLASS_NAME, "postedTime")
    timestamp = timestamp_element.text

    content_element = post_element.find_element(By.CLASS_NAME, "content")
    html = content_element.get_attribute(
        'innerHTML'
    )  # or .text, depending on how you want to handle the content

    attachbox_elements = post_element.find_elements(By.CLASS_NAME, "attachbox")
    attachbox_html = None
    if attachbox_elements:
      attachbox_html = attachbox_elements[0].get_attribute('innerHTML')

    post = ThreadPost(author=author,
                      text=None,
                      content_html=html,
                      attachbox_html=attachbox_html,
                      timestamp=timestamp)
    posts.append(post)

  return posts


def log_forum_thread(thread_url, driver, cache):
  if driver.current_url != thread_url:
    driver.get(thread_url)
    wait_for_page_load(driver)

  thread_id = extract_thread_id_from_url(thread_url)

  title_element = driver.find_element(By.CSS_SELECTOR, "h2.topic-title a")
  thread_title = title_element.text

  all_posts = []

  all_posts.extend(get_posts_from_current_page(driver, cache))

  # Check for pagination and collect all page URLs
  pagination_links = driver.find_elements(By.CSS_SELECTOR, ".pagination a")
  page_urls = [thread_url] + [
      link.get_attribute('href') for link in pagination_links
      if link.get_attribute('href') not in thread_url
  ]

  # Remove duplicates and already visited page
  page_urls = list(dict.fromkeys(page_urls))  # Remove duplicates
  page_urls.remove(
      thread_url)  # Remove the first page URL as it's already processed

  # Iterate over each page URL
  for page_url in page_urls:
    driver.get(page_url)
    wait_for_page_load(driver)
    all_posts.extend(get_posts_from_current_page(driver, cache))

  # At this point, `all_posts` contains posts from all pages
  # print(all_posts)
  # Here you can proceed to log the posts or do further processing

  ft = ForumThread(thread_id=thread_id, title=thread_title, posts=all_posts)

  return ft


def wait_for_page_load(driver, timeout=10):
  WebDriverWait(driver, timeout).until(
      lambda d: d.execute_script('return document.readyState') == 'complete')


def test_step_1_log_forum_thread(driver: WebDriver):
  cache = dc.Cache('./cache.db')

  ft = log_forum_thread("https://forum.image-line.com/viewtopic.php?t=310058",
                        driver, cache)

  store_thread(cache, ft)

  print('test ok')

  cache.close()


def get_or_log_forum_thread(thread_url, driver, cache, jitter=False):
  cache = dc.Cache('./cache.db')

  thread_id = extract_thread_id_from_url(thread_url)
  ft: ForumThread | None = get_thread(cache, thread_id)

  if ft is None:
    if jitter:
      sleep_with_jitter(1, 4)

    ft = log_forum_thread(thread_url, driver, cache)

    store_thread(cache, ft)

  return ft


def test_step_1_snippet_acquisition(driver: WebDriver):
  cache = dc.Cache('./cache.db')

  ft = log_forum_thread('https://forum.image-line.com/viewtopic.php?t=317766',
                        driver, cache)

  store_thread(cache, ft)

  print(ft.posts[0])

  cache.close()


def test_step_1_log_forum_thread_posts_get_cache(driver: WebDriver):
  cache = dc.Cache('./cache.db')

  # test_thread_posts: [ForumThread] = deserialize(cache.get("thread-310058"))
  ft: ForumThread | None = get_thread(cache, 310058)

  if ft is None:
    print('test fail')
    return

  print(f'title: {ft.title}')
  print(f'posts: {len(ft.posts)}')

  print(f'post 1: {ft.posts[0].text}')

  print('test ok')
  cache.close()


def step_3_download_versions(driver: WebDriver):
  cache = dc.Cache('./cache.db')

  for k in cache.iterkeys():
    if not k.startswith('pthread'):
      continue

    ftp: ForumThreadProcessed = deserialize(cache.get(k))

    for v in ftp.versions:
      driver.get(v.link)
      wait_for_page_load(driver)

      sleep_with_jitter(0.5, 1)

    # pthread = get_thread_processed(cache, extra)

  cache.close()


def step_1_log_forum_threads(driver: WebDriver):
  cache = dc.Cache('./cache.db')

  for page in PianorollPageIterator(page_limit=4):
    if driver.current_url != page:
      driver.get(page)
      wait_for_page_load(driver)

    thread_links = [
        x.get_attribute("href")
        for x in driver.find_elements(By.CLASS_NAME, "topictitle")
    ]

    for thread_link in thread_links:
      try:
        get_or_log_forum_thread(thread_link, driver, cache, jitter=True)
      except Exception as e:
        print(f'Unable to log: {thread_link}')
        print(str(e))

  cache.close()

  # return driver.get("https://forum.image-line.com/viewforum.php?f=2008")
