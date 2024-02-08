from playwright.sync_api import sync_playwright

with sync_playwright() as p:
  browser = p.chromium.launch(
      headless=False)  # Set headless=True to run in headless mode
  page = browser.new_page()
  page.goto("https://example.com")
  print(page.title())
  browser.close()
