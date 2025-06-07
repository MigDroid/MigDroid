# MigDroid

This is the implementation of MigDroid.
# Prerequisites

* Python 3.9.16 with the packages in `requirements.txt` installed
* [Appium v2.5.4](https://appium.io/docs/en/2.5/quickstart/install/)
* Android Studio Giraffe | 2022.3.1 Patch 1
* Nexus 5X Emulator API 23 (ARM64 image)
* Pixel 5 Emulator API 34 (ARM64 image)
* Subject apks from [here](https://drive.google.com/file/d/1XNBWXIxvpOerz2xJ2GLoueYC8Imzh-3Q/view?usp=sharing)
* API keys for calling GPT-4o and Qwen-VL-Max

# Getting Started
1. Install subject apps on the emulators, we recommend installing a*1~a*5 to emulator API 23 and a*6~a*9, a*0 to emulator API 34
2. Start the emulators; Start appium
3. Set the API keys in `LLMs/LLMUtil.py`

## Augmenting the source test
1. Run scripts/run_gt_test.sh to run the tests and collect screenshots
2. Run TestAugmenter/get_test_desc_stage1.py to summarize the source test accompanied with screenshots

## Getting test skeleton
1. Run TestAnalyzer/group_stage1_test_desc.py to group operations into subsequences, so that each subsequence achieves a complete intention
2. Run TestAnalyzer/extract_key_steps.py to keep key operations and remove auxiliary operations

## Starting migration
Run Planner/Planner.py with arguments: 
```
python3 Planner/Planner.py ${TRANSFER_ID} ${APPIUM_PORT} ${EMULATOR}
```
TRANSFER_ID is the transfer id, APPIUM_PORT is the port used by Appium-Desktop (4723 by default), EMULATOR is the name of the emulator, e.g., 
```
python3 Planner/Planner.py a21-a22-b21 4723 emulator-5554
```
It will start transferring the test case of `a21-Minimal` to `a22-Clear` List for the b21-Add task function. 

The source test cases are under test-repo_migdroid/[CATEGORY]/[FUNCTIONALITY]/base/[APP_ID].json, e.g., `test-repo_migdroid/a2/b21/base/a21.json`. The generated test cases for the target app is under generated/[APP_FROM]-/[APP_TO]-[FUNCTIONALITY].json, e.g., `test-repo_migdroid/a2/b21/generated/a21-a22-b21.json`

## Result
Run Evaluator.py to get the similarity between the generated test cases and ground truth.

# Acknowledgements
This tool reuses the code from [CraftDroid](https://github.com/seal-hub/CraftDroid).
Many thanks to the CraftDroid team for their great work and contributions.