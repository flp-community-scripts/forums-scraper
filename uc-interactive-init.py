# setup_script.py
from IPython import start_ipython

if __name__ == "__main__":
  # Launch IPython and execute the temporary script
  start_ipython(argv=["-i", "--", "uc-ipy-init.py"])
