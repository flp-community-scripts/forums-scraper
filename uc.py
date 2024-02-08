import undetected_chromedriver as uc
from selenium.common import WebDriverException
import os
import asyncio
from asyncio import Queue

from dotenv import dotenv_values

dotenv_config = dotenv_values(".env")


async def wait_for_browser_to_close(driver, task_queue: Queue):
  try:
    while True:
      await asyncio.sleep(1)
      try:
        driver.current_url
      except WebDriverException:
        print("Browser is closed.")
        break
  except Exception as e:
    print(f"Error during execution: {e}")
  finally:
    await task_queue.put(None)  # Signal that browser has closed


async def worker(task_queue: Queue):
  while True:
    task_func = await task_queue.get()
    if task_func is None:  # Check for the termination signal
      task_queue.task_done()
      break
    await task_func()
    task_queue.task_done()


def get_driver():
  options = uc.ChromeOptions()

  options.add_argument("--disable-notifications")

  prefs = {
      "download.default_directory": os.path.join(os.getcwd(), "./downloads"),
      "download.prompt_for_download":
      False,  # To automatically download the file without asking
      "download.directory_upgrade": True,
      "plugins.always_open_pdf_externally":
      True  # It will not show PDF directly in chrome
  }
  options.add_experimental_option("prefs", prefs)

  driver = uc.Chrome(
      options=options,
      # user_data_dir='./.chrome-user-data',
      user_data_dir=dotenv_config["CHROMIUM_USER_DATA_DIR"],
      headless=False,
      driver_executable_path=dotenv_config["CHROMEDRIVER_EXEC_PATH"],
      browser_executable_path=dotenv_config["CHROMIUM_BROWSER_EXEC_PATH"])

  return driver


async def main():
  # options = uc.ChromeOptions(user_data_dir='./.chrome-user-data')

  driver = uc.Chrome(
      # user_data_dir='./.chrome-user-data',
      user_data_dir=dotenv_config["CHROMIUM_USER_DATA_DIR"],
      headless=False,
      driver_executable_path=dotenv_config["CHROMEDRIVER_EXEC_PATH"],
      browser_executable_path=dotenv_config["CHROMIUM_BROWSER_EXEC_PATH"])

  driver.get("https://forum.image-line.com/viewforum.php?f=2008")

  task_queue = Queue()

  workers = []

  # Queue initial tasks
  await task_queue.put(wait_for_browser_to_close(driver, task_queue))
  # await task_queue.put(some_other_async_task)

  # Wait for the task queue to be empty
  await task_queue.join()

  # Cleanup: signal all workers to exit
  # for _ in workers:
  #     await task_queue.put(None)

  # Wait for all workers to finish
  await asyncio.gather(*workers)

  print("All tasks completed. Quitting driver.")
  driver.quit()
  # Clean up: ensure driver termination (optional, as the browser might be closed manually)
  driver.quit()


# Run the async main function

if __name__ == "__main__":
  asyncio.run(main())
