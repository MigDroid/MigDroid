import os
import json
from copy import deepcopy

from TestAnalyzer.AnalyzerUtil import AnalyzerUtil
from ScreenUtil import ScreenUtil
from const import SRC_SCREENSHOT_FOLDER, TEST_DESC_STAGE1_FOLDER, TEST_REPO, TEST_DESC_STAGE1_IMAGE_FOLDER, TEST_DESC_GROUPED_FOLDER

model_name = "gpt-4o-mini"
test_dir = TEST_REPO
stage1_desc_dir = TEST_DESC_STAGE1_FOLDER.replace("model_name", model_name)
save_dir = TEST_DESC_GROUPED_FOLDER.replace("model_name", model_name)
image_save_dir = TEST_DESC_STAGE1_IMAGE_FOLDER
screen_dir = SRC_SCREENSHOT_FOLDER

# traverse all the subdirectories in the test directory, and find all the files with "base" in their parent directory names
for subdir, dirs, files in os.walk(stage1_desc_dir):
    for file in files:
        if not ".txt" in file:
            continue
        # get the app_id from the file name
        app_id = file.split(".")[0]
        # get task_id and category from the parent directory name
        task_id = subdir.split("/")[-2]
        category = subdir.split("/")[-3]
        desc_file = os.path.join(subdir, file)
        print(f"Desc path: {desc_file}")
        with open(desc_file, 'r') as f:
            test_desc = f.read()
        test_file = desc_file.replace(stage1_desc_dir, test_dir).replace(".txt", ".json")
        print(f"Desc path: {desc_file}")
        print(f"Test file path: {test_file}")
        save_file = desc_file.replace(stage1_desc_dir, save_dir)
        map_save_file = save_file.replace(".txt", "_map.json")
        if os.path.exists(save_file) and os.path.exists(map_save_file):
                print(f"File {save_file} already exists, skipping...")
                continue
        config_id = f"{app_id}-{app_id}-{task_id}"
        
         # get screen shots for the test
        titles = ["Before", "After"]
        app_screen_dir = test_file.replace(test_dir, screen_dir).replace(".json", "_screens")
        merged_screen_save_path = test_file.replace(test_dir, image_save_dir).replace(".json", ".png")
        
        # interaction_steps, stop_condition, functionality_under_test = AnalyzerUtil.group_interaction_steps(test_desc, model_name=model_name)
        semantic_steps, stop_condition, functionality_under_test, map_from_interaction_to_semantic = AnalyzerUtil.group_interaction_steps(config_id, merged_screen_save_path, model_name=model_name)        
        # save the grouped test steps
        if not os.path.exists(os.path.dirname(save_file)):
            os.makedirs(os.path.dirname(save_file))
        print(f"Save path: {save_file}")
        with open(save_file, 'w') as f:
            f.write("Functionality Under Test: " + functionality_under_test + "\n")
            f.write("Test Steps: \n" + semantic_steps + "\n")
            f.write("Stop Condition: " + stop_condition + "\n")
        with open(map_save_file, 'w') as f:
            json.dump(map_from_interaction_to_semantic, f)
        print(f"Grouped test steps for {config_id} saved to {save_file}")
