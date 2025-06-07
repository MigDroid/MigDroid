import os
import json
from copy import deepcopy
import re

from TestAnalyzer.AnalyzerUtil import AnalyzerUtil
from ScreenUtil import ScreenUtil
from FileUtil import FileUtil
from const import SEMANTIC_ATTRS, SRC_SCREENSHOT_FOLDER, TEST_REPO, TEST_DESC_STAGE1_FOLDER, TEST_DESC_STAGE1_IMAGE_FOLDER

model_name = 'v3-gpt-4o-mini-2024-07-18'
test_dir = TEST_REPO
screen_dir = SRC_SCREENSHOT_FOLDER
save_dir = TEST_DESC_STAGE1_FOLDER.replace("model_name", model_name)
image_save_dir = TEST_DESC_STAGE1_IMAGE_FOLDER

# traverse all the subdirectories in the test directory, and find all the files with "base" in their parent directory names
for subdir, dirs, files in os.walk(test_dir):
    for file in files:
        if "base" in subdir:
            test_file = os.path.join(subdir, file)
            print(test_file)
            app_id = file.split(".")[0]
            f = open(test_file, 'r')
            test = json.load(f)
            filtered_test = []
            for action in test:
                new_action = {}
                if "affix" not in action:
                    new_action = ScreenUtil.extract_semantic_attrs(action)
                    filtered_test.append(deepcopy(new_action))
            
            save_path = test_file.replace(test_dir, save_dir).replace(".json", ".txt")
            # if the file already exists, skip
            if os.path.exists(save_path):
                print(f"File {save_path} already exists, skipping...")
                continue
            print(f"Extracting test description for {app_id}")
            
            # get screen shots for the test
            titles = ["Before", "After"]
            app_screen_dir = test_file.replace(test_dir, screen_dir).replace(".json", "_screens")
            # use open screen and close screen as the before and after screen
            open_screen = "0.png"
            end_screen = f"{max(FileUtil.sort_filename_by_num(app_screen_dir))}.png"
            screen_paths = [os.path.join(app_screen_dir, open_screen), os.path.join(app_screen_dir, end_screen)]
            merged_screen_save_path = test_file.replace(test_dir, image_save_dir).replace(".json", ".png")
            os.makedirs(os.path.dirname(merged_screen_save_path), exist_ok=True)            
            ScreenUtil.synthesize_image(titles, screen_paths, merged_screen_save_path)
            
            interaction_steps, stop_condition, func_under_test = AnalyzerUtil.get_stage1_test_desc(app_id, filtered_test, merged_screen_save_path, model_name=model_name)
            # create the save directory if it doesn't exist
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            f = open(save_path, 'w')
            f.write(f"Functionality Under Test:\n{func_under_test}\n")
            f.write(f"Interaction Steps:\n{interaction_steps}\n")
            f.write(f"Stop Condition:\n{stop_condition}\n")
            f.close()
