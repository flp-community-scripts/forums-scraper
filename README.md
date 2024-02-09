# Community Scraper

**Will take all old posts in fl piano roll forums and attempt to reindex them with some basic filtering logic and gpt as well**

install 3.8.10 python with pyenv & pyenv-virtualenv or something, and run all commands under that env. I did ```pyenv virtualenv 3.8.10 flp-archive-uc``` and then ```pyenv shell flp-archive-uc``` on each shell

```pip3 install -r requirements.txt``` or manually

```python3 uc-interactive-init.py```

go to image line

go to forums

login

in interactive prompt type:

```ucations.step_1_log_forum_threads(driver)<Enter>```

after that open up second terminal:

```python3 step_2_sift.py```

(Heavy post filtering happens here)

then back in interactive shell:

```ucactions.step_3_download_versions(driver)```

then:

```python3 step_4_unpack.py```

```python3 step_5_header_tag.py```

now everything is labelled and stored in versions folder.

mirroring to flp-community-repo:

```python3 step_6_stage.py```

> Copy over to so called staging folder that will look similar to `flp-community-repo`

(Since some files will be incorrectly categorised, simply take copy-paste folders from `flp-community-repo` to `staging-order-memo/`)

If you wanna reorder some scripts manually, place then in respective folder and then run: `step_7_conform_stage.py`

And lastly just copy over back the contents of staging folder to `flp-community-repo`, yeah for now it's manual