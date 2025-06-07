import os
import json
from copy import deepcopy

from TestAnalyzer.AnalyzerUtil import AnalyzerUtil
from const import SRC_SCREENSHOT_FOLDER, TEST_DESC_STAGE1_FOLDER, TEST_DESC_KEY_FOLDER

model_name = "v3-gpt-4o-mini-2024-07-18"
stage1_desc_dir = TEST_DESC_STAGE1_FOLDER.replace("model_name", model_name)
save_dir = TEST_DESC_KEY_FOLDER.replace("model_name", model_name)
category_map = {"a1": "Browser", "a2": "ToDo List", "a4": "Mail Client", "a5": "Tip Calculator"}
print(f"Stage 1 description directory: {stage1_desc_dir}")

# traverse all the subdirectories in the test directory, and find all the files with "base" in their parent directory names
for subdir, dirs, files in os.walk(stage1_desc_dir):
    for file in files:
        if "a13" in file or "a17" in file:
            continue
        if not ".txt" in file:
            continue
            
        app_id = file.split(".")[0]
        # get task_id and category from the parent directory name
        task_id = subdir.split("/")[-2]
        category = subdir.split("/")[-3]
        config_id = f"{app_id}-{app_id}-{task_id}"
        desc_file = os.path.join(subdir, file)
        save_file = desc_file.replace(stage1_desc_dir, save_dir)

        # if already processed, skip
        if os.path.exists(save_file):
            print(f"Classified test steps for {config_id} already exists at {save_file}")
            continue
        
        print(f"File path: {desc_file}")
        classified_steps, stop_condition, functionality_under_test = AnalyzerUtil.extract_key_steps(config_id, model_name)

        # save the key test steps
        if not os.path.exists(os.path.dirname(save_file)):
            os.makedirs(os.path.dirname(save_file))
        print(f"Save path: {save_file}")
        with open(save_file, 'w') as f:
            f.write("Functionality under test: " + functionality_under_test + "\n")
            f.write("Semantic steps: \n" + classified_steps + "\n")
            f.write("Stop condition: " + stop_condition + "\n")
        print(f"Classified test steps for {config_id} saved to {save_file}")
