import copy
import re
import json
import os

from LLMUtil import LLMUtil
from FileUtil import FileUtil
from ScreenUtil import ScreenUtil
from const import SRC_SCREENSHOT_FOLDER, CATEGORY_MAP, TEST_DESC_STAGE1_FOLDER, TEST_DESC_GROUPED_FOLDER, TEST_DESC_KEY_FOLDER, TEST_DESC_KEY_IMAGE_FOLDER, TEST_DESC_STAGE1_FOLDER_WO_VISION, TEST_DESC_GROUPED_FOLDER_WO_VISION, TEST_DESC_KEY_FOLDER_WO_VISION


class AnalyzerUtil:
    """
    This class contains utility functions for the feature extractor, including functions for extracting descriptions of tests, pages and widgets.
    """

    @staticmethod
    def get_stage1_test_desc_from_file(config_id, model_name="gpt-4o"):
        desc_dir = TEST_DESC_STAGE1_FOLDER.replace("model_name", model_name)
        category = config_id[:2]
        src_app_id = config_id[:3]
        task_id = config_id[-3:]
        desc_file = f"{desc_dir}/{category}/{task_id}/base/{src_app_id}.txt"
        f = open(desc_file, "r")
        desc = f.read()
        fut_part = re.split(r"functionality under test:", desc, flags=re.IGNORECASE)[1]
        functionality_under_test = re.split(r"interaction steps:", fut_part, flags=re.IGNORECASE)[0].strip()
        interaction_steps = re.split(r"interaction steps:", fut_part, flags=re.IGNORECASE)[1]
        interaction_steps = re.split(r"stop condition:", interaction_steps, flags=re.IGNORECASE)[0].strip()
        stop_condition = re.split(r"stop condition:", fut_part, flags=re.IGNORECASE)[1].strip()
        return interaction_steps, stop_condition, functionality_under_test
    
    def get_stage1_test_desc_from_file_wo_vision(config_id, model_name="gpt-4o"):
        desc_dir = TEST_DESC_STAGE1_FOLDER_WO_VISION.replace("model_name", model_name)
        category = config_id[:2]
        src_app_id = config_id[:3]
        task_id = config_id[-3:]
        desc_file = f"{desc_dir}/{category}/{task_id}/base/{src_app_id}.txt"
        f = open(desc_file, "r")
        desc = f.read()
        fut_part = re.split(r"functionality under test:", desc, flags=re.IGNORECASE)[1]
        functionality_under_test = re.split(r"interaction steps:", fut_part, flags=re.IGNORECASE)[0].strip()
        interaction_steps = re.split(r"interaction steps:", fut_part, flags=re.IGNORECASE)[1]
        interaction_steps = re.split(r"stop condition:", interaction_steps, flags=re.IGNORECASE)[0].strip()
        stop_condition = re.split(r"stop condition:", fut_part, flags=re.IGNORECASE)[1].strip()
        return interaction_steps, stop_condition, functionality_under_test
    
    @staticmethod
    def get_grouped_test_desc_from_file(config_id, model_name="gpt-4o"):
        desc_dir = TEST_DESC_GROUPED_FOLDER.replace("model_name", model_name)
        category = config_id[:2]
        src_app_id = config_id[:3]
        task_id = config_id[-3:]
        desc_file = f"{desc_dir}/{category}/{task_id}/base/{src_app_id}.txt"
        map_file = desc_file.replace(".txt", "_map.json")
        f = open(desc_file, "r")
        desc = f.read()
        # interaction_steps = desc.split("Interaction steps:")[1].split("Stop condition:")[0]
        # functionality_under_test = desc.split("Functionality under test:")[1].split("Test Steps:")[0]
        # stop_condition = desc.split("Stop condition:")[1]
        fut_part = re.split(r"functionality under test:", desc, flags=re.IGNORECASE)[1]
        functionality_under_test = re.split(r"test steps", fut_part, flags=re.IGNORECASE)[0].strip()
        semantic_steps = re.split(r"test steps", fut_part, flags=re.IGNORECASE)[1]
        semantic_steps = re.split(r"stop condition:", semantic_steps, flags=re.IGNORECASE)[0].strip()
        stop_condition = re.split(r"stop condition:", fut_part, flags=re.IGNORECASE)[1].strip()
        map_from_interaction_to_semantic = json.load(open(map_file, "r"))
        return semantic_steps, stop_condition, functionality_under_test, map_from_interaction_to_semantic
    
    @staticmethod
    def get_grouped_test_desc_from_file_wo_vision(config_id, model_name="gpt-4o"):
        desc_dir = TEST_DESC_GROUPED_FOLDER_WO_VISION.replace("model_name", model_name)
        category = config_id[:2]
        src_app_id = config_id[:3]
        task_id = config_id[-3:]
        desc_file = f"{desc_dir}/{category}/{task_id}/base/{src_app_id}.txt"
        map_file = desc_file.replace(".txt", "_map.json")
        f = open(desc_file, "r")
        desc = f.read()
        # interaction_steps = desc.split("Interaction steps:")[1].split("Stop condition:")[0]
        # functionality_under_test = desc.split("Functionality under test:")[1].split("Test Steps:")[0]
        # stop_condition = desc.split("Stop condition:")[1]
        fut_part = re.split(r"functionality under test:", desc, flags=re.IGNORECASE)[1]
        functionality_under_test = re.split(r"test steps", fut_part, flags=re.IGNORECASE)[0].strip()
        semantic_steps = re.split(r"test steps", fut_part, flags=re.IGNORECASE)[1]
        semantic_steps = re.split(r"stop condition:", semantic_steps, flags=re.IGNORECASE)[0].strip()
        stop_condition = re.split(r"stop condition:", fut_part, flags=re.IGNORECASE)[1].strip()
        map_from_interaction_to_semantic = json.load(open(map_file, "r"))
        return semantic_steps, stop_condition, functionality_under_test, map_from_interaction_to_semantic
    
    @staticmethod
    def get_key_test_desc_from_file(config_id, model_name="gpt-4o"):
        desc_dir = TEST_DESC_KEY_FOLDER.replace("model_name", model_name)
        category = config_id[:2]
        src_app_id = config_id[:3]
        task_id = config_id[-3:]
        desc_file = f"{desc_dir}/{category}/{task_id}/base/{src_app_id}.txt"
        f = open(desc_file, "r")
        desc = f.read()
        fut_part = re.split(r"functionality under test:", desc, flags=re.IGNORECASE)[1]
        functionality_under_test = re.split(r"semantic steps:", fut_part, flags=re.IGNORECASE)[0].strip()
        semantic_steps = re.split(r"semantic steps:", fut_part, flags=re.IGNORECASE)[1]
        semantic_steps = re.split(r"stop condition:", semantic_steps, flags=re.IGNORECASE)[0].strip()
        stop_condition = re.split(r"stop condition:", fut_part, flags=re.IGNORECASE)[1].strip()
        # split interaction steps using the newline character
        semantic_steps = semantic_steps.split("\n")
        key_steps = ""
        key_step_id = 0
        for semantic_step in semantic_steps:
            if "Key Step:" in semantic_step:
                key_step_id += 1
                key_step = re.split(r"Key Step:", semantic_step, flags=re.IGNORECASE)[1]
                key_steps += f"{key_step_id}. {key_step}\n"
                
        return key_steps, stop_condition, functionality_under_test
    
    @staticmethod
    def get_key_test_desc_from_file_wo_vision(config_id, model_name="gpt-4o"):
        desc_dir = TEST_DESC_KEY_FOLDER_WO_VISION.replace("model_name", model_name)
        category = config_id[:2]
        src_app_id = config_id[:3]
        task_id = config_id[-3:]
        desc_file = f"{desc_dir}/{category}/{task_id}/base/{src_app_id}.txt"
        f = open(desc_file, "r")
        desc = f.read()
        fut_part = re.split(r"functionality under test:", desc, flags=re.IGNORECASE)[1]
        functionality_under_test = re.split(r"semantic steps:", fut_part, flags=re.IGNORECASE)[0].strip()
        semantic_steps = re.split(r"semantic steps:", fut_part, flags=re.IGNORECASE)[1]
        semantic_steps = re.split(r"stop condition:", semantic_steps, flags=re.IGNORECASE)[0].strip()
        stop_condition = re.split(r"stop condition:", fut_part, flags=re.IGNORECASE)[1].strip()
        # split interaction steps using the newline character
        semantic_steps = semantic_steps.split("\n")
        key_steps = ""
        key_step_id = 0
        for semantic_step in semantic_steps:
            if "Key Step:" in semantic_step:
                key_step_id += 1
                key_step = re.split(r"Key Step:", semantic_step, flags=re.IGNORECASE)[1]
                key_steps += f"{key_step_id}. {key_step}\n"
                
        return key_steps, stop_condition, functionality_under_test
    
    @staticmethod
    def get_stage1_test_desc(config_id, test, image_path, model_name="gpt-4o"):
        app_id = config_id[:3]
        test_without_oracle = []
        # ignore oracle events and affix events from the test
        for event in test:
            if "affix" not in event and event["event_type"] != "oracle":
                test_without_oracle.append(copy.deepcopy(event))
        
        # find the last oracle event in the test and assign it to final_oracle
        final_oracle = None
        for event in reversed(test):
            if event["event_type"] == "oracle":
                final_oracle = copy.deepcopy(event)
                break
        final_oracle["event_type"] = "stop_checking"
        for event in test_without_oracle:
            new_action = event["action"][0].replace("and_hide_keyboard", "")
            new_action = new_action.replace("clear_and_", "")
            event["action"][0] = new_action
                
        prompt_file = "TestAnalyzer/prompts_test_desc_stage1.txt"
        with open(prompt_file, "r") as f:
            prompt = f.read()
        category_name = CATEGORY_MAP[app_id[:2]]
        prompt = prompt.replace("$$$category$$$", category_name)
        prompt = prompt.replace("$$$actions$$$", str(test_without_oracle))
        prompt = prompt.replace("$$$stop_checking_event$$$", str(final_oracle))
        print(prompt)
        answer = LLMUtil.query_with_retry(prompt, image_path, model_name=model_name)
        interaction_steps, stop_condition, functionality_under_test = LLMUtil.extract_answer_components(answer, "stage1_test_desc")
        return interaction_steps, stop_condition, functionality_under_test
    
    @staticmethod
    def get_stage1_test_desc_wo_vision(config_id, test, image_path, model_name="gpt-4o"):
        app_id = config_id[:3]
        test_without_oracle = []
        # ignore oracle events and affix events from the test
        for event in test:
            if "affix" not in event and event["event_type"] != "oracle":
                test_without_oracle.append(copy.deepcopy(event))
        
        # find the last oracle event in the test and assign it to final_oracle
        final_oracle = None
        for event in reversed(test):
            if event["event_type"] == "oracle":
                final_oracle = copy.deepcopy(event)
                break
        final_oracle["event_type"] = "stop_checking"
        for event in test_without_oracle:
            new_action = event["action"][0].replace("and_hide_keyboard", "")
            new_action = new_action.replace("clear_and_", "")
            event["action"][0] = new_action
                
        prompt_file = "TestAnalyzer/prompts_test_desc_stage1.txt"
        with open(prompt_file, "r") as f:
            prompt = f.read()
        category_name = CATEGORY_MAP[app_id[:2]]
        prompt = prompt.replace("$$$category$$$", category_name)
        prompt = prompt.replace("$$$actions$$$", str(test_without_oracle))
        prompt = prompt.replace("$$$stop_checking_event$$$", str(final_oracle))
        print(prompt)
        answer = LLMUtil.query_with_retry(prompt, None, model_name=model_name)
        interaction_steps, stop_condition, functionality_under_test = LLMUtil.extract_answer_components(answer, "stage1_test_desc")
        return interaction_steps, stop_condition, functionality_under_test

    @staticmethod
    def group_interaction_steps(config_id, image_path, model_name="gpt-4o-mini"):
        prompt_file = "TestAnalyzer/prompt_group_steps.txt"
        category_name = CATEGORY_MAP[config_id[:2]]
        interaction_steps, stop_condition, functionality_under_test = AnalyzerUtil.get_stage1_test_desc_from_file(config_id, model_name=model_name)
        with open(prompt_file, "r") as f:
            prompt = f.read()
        prompt = prompt.replace("$$$category$$$", category_name)
        prompt = prompt.replace("$$$fut$$$", functionality_under_test)
        prompt = prompt.replace("$$$interaction_steps$$$", interaction_steps)
        prompt = prompt.replace("$$$stop_condition$$$", stop_condition)
        answer = LLMUtil.query_with_retry(prompt, image_path, model_name=model_name)
        sub_string = "(Each step should be semantically atomic, that means each step should hold a complete meaning, but each of its sub-step does not. Use no more than 20 words for each step, for input actions, you should include the exact input content in the step)"
        if sub_string in answer:
            answer = answer.replace(sub_string, "")
        # interaction_steps, stop_condition, functionality_under_test = AnalyzerUtil.extract_test_desc_from_answer(answer)
        semantic_steps, stop_condition, functionality_under_test, map_from_interaction_to_semantic = LLMUtil.extract_answer_components(answer, "grouped_stage1_test_desc")
        # return interaction_steps, stop_condition, functionality_under_test
        return semantic_steps, stop_condition, functionality_under_test, map_from_interaction_to_semantic
    
    @staticmethod
    def group_interaction_steps_wo_vision(config_id, image_path, model_name="gpt-4o-mini"):
        prompt_file = "TestAnalyzer/prompt_group_steps.txt"
        category_name = CATEGORY_MAP[config_id[:2]]
        interaction_steps, stop_condition, functionality_under_test = AnalyzerUtil.get_stage1_test_desc_from_file_wo_vision(config_id, model_name=model_name)
        with open(prompt_file, "r") as f:
            prompt = f.read()
        prompt = prompt.replace("$$$category$$$", category_name)
        prompt = prompt.replace("$$$fut$$$", functionality_under_test)
        prompt = prompt.replace("$$$interaction_steps$$$", interaction_steps)
        prompt = prompt.replace("$$$stop_condition$$$", stop_condition)
        answer = LLMUtil.query_with_retry(prompt, None, model_name=model_name)
        sub_string = "(Each step should be semantically atomic, that means each step should hold a complete meaning, but each of its sub-step does not. Use no more than 20 words for each step, for input actions, you should include the exact input content in the step)"
        if sub_string in answer:
            answer = answer.replace(sub_string, "")
        # interaction_steps, stop_condition, functionality_under_test = AnalyzerUtil.extract_test_desc_from_answer(answer)
        semantic_steps, stop_condition, functionality_under_test, map_from_interaction_to_semantic = LLMUtil.extract_answer_components(answer, "grouped_stage1_test_desc")
        # return interaction_steps, stop_condition, functionality_under_test
        return semantic_steps, stop_condition, functionality_under_test, map_from_interaction_to_semantic
    
    @staticmethod    
    def extract_key_steps(config_id, model_name="gpt-4o"):
        semantic_steps, stop_condition, functionality_under_test, map_from_interaction_to_semantic = AnalyzerUtil.get_grouped_test_desc_from_file(config_id, model_name=model_name)
        prompt_dir = "TestAnalyzer/prompt_extract_key_steps.txt"
        with open(prompt_dir, "r") as f:
            prompt = f.read()
        category_name = CATEGORY_MAP[config_id[:2]]
        prompt = prompt.replace("$$$category$$$", category_name)
        prompt = prompt.replace("$$$fut$$$", functionality_under_test)
        prompt = prompt.replace("$$$semantic_steps$$$", semantic_steps)
        prompt = prompt.replace("$$$stop_condition$$$", stop_condition)
        
        # align image_id with semantic steps
        screen_paths = AnalyzerUtil.match_screenshot_with_semantic_steps(config_id, map_from_interaction_to_semantic, model_name)
        titles = []
        for i, _ in enumerate(screen_paths):
            titles.append(f"Step {i+1}")
        # get screen_paths[0]'s parent directory
        merged_screen_path = ScreenUtil.synthesize_image(titles, screen_paths, os.path.join(os.path.dirname(screen_paths[0]), "merged.png"))
        answer = LLMUtil.query_with_retry(prompt, merged_screen_path, model_name="gpt-4o")
        classified_steps, stop_condition, functionality_under_test = LLMUtil.extract_answer_components(answer, "key_test_desc")
        return classified_steps, stop_condition, functionality_under_test
    
    @staticmethod    
    def extract_key_steps_wo_vision(config_id, model_name="gpt-4o"):
        semantic_steps, stop_condition, functionality_under_test, map_from_interaction_to_semantic = AnalyzerUtil.get_grouped_test_desc_from_file_wo_vision(config_id, model_name=model_name)
        prompt_dir = "TestAnalyzer/prompt_extract_key_steps.txt"
        with open(prompt_dir, "r") as f:
            prompt = f.read()
        category_name = CATEGORY_MAP[config_id[:2]]
        prompt = prompt.replace("$$$category$$$", category_name)
        prompt = prompt.replace("$$$fut$$$", functionality_under_test)
        prompt = prompt.replace("$$$semantic_steps$$$", semantic_steps)
        prompt = prompt.replace("$$$stop_condition$$$", stop_condition)
        
        # align image_id with semantic steps
        screen_paths = AnalyzerUtil.match_screenshot_with_semantic_steps(config_id, map_from_interaction_to_semantic, model_name)
        titles = []
        for i, _ in enumerate(screen_paths):
            titles.append(f"Step {i+1}")
        # get screen_paths[0]'s parent directory
        merged_screen_path = ScreenUtil.synthesize_image(titles, screen_paths, os.path.join(os.path.dirname(screen_paths[0]), "merged.png"))
        answer = LLMUtil.query_with_retry(prompt, None, model_name="gpt-4o")
        try:
            classified_steps, stop_condition, functionality_under_test = LLMUtil.extract_answer_components(answer, "key_test_desc")
        except:
            format = prompt.split("strictly follow this format:")[1]
            refomat_prompt_file = "Planner/reformat.txt"
            with open(refomat_prompt_file, "r") as f:
                refomat_prompt = f.read()
            refomat_prompt = refomat_prompt.replace("$$$answer$$$", answer)
            refomat_prompt = refomat_prompt.replace("$$$format$$$", format)
            print("refomat_prompt:", refomat_prompt)
            new_answer = LLMUtil.query_with_retry(refomat_prompt, None, model_name=model_name)
            print("new answer:", new_answer)
            classified_steps, stop_condition, functionality_under_test = LLMUtil.extract_answer_components(new_answer, "key_test_desc")
        return classified_steps, stop_condition, functionality_under_test
    
    @staticmethod
    def match_screenshot_with_semantic_steps(config_id, map_from_interaction_to_semantic, model_name="gpt-4o-mini"):
        screen_dir = os.path.join(SRC_SCREENSHOT_FOLDER, config_id[:2], config_id[-3:], "base", f"{config_id.split('-')[0]}_screens")
        # load test script
        test_script = FileUtil.load_events(config_id, "base_from")
        landmark = 0
        map_from_script_to_interaction = []
        for event in test_script:
            landmark += 1
            if event["event_type"] != "oracle":
                map_from_script_to_interaction.append(landmark)
        print("map_from_script_to_interaction:", map_from_script_to_interaction)
        semantic_step_id = 0
        merged_screen_paths = []
        for semantic_step_map in map_from_interaction_to_semantic:
            semantic_step_id += 1
            start_interaction_step = min(semantic_step_map)
            print("start_interaction_step:", start_interaction_step)
            end_interaction_step = max(semantic_step_map)
            print("end_interaction_step:", end_interaction_step)
            print("map_from_script_to_interaction:", map_from_script_to_interaction)
            start_script_step = map_from_script_to_interaction[start_interaction_step-1]
            end_script_step = map_from_script_to_interaction[end_interaction_step-1]
            start_screen_path = os.path.join(screen_dir, f"{start_script_step-1}.png")
            end_screen_path = os.path.join(screen_dir, f"{end_script_step}.png")
            screen_titles = ["Before the step", "After the step"]
            screen_paths = [start_screen_path, end_screen_path]
            key_image_dir = TEST_DESC_KEY_IMAGE_FOLDER.replace("model_name", model_name)
            merged_screen_path = os.path.join(screen_dir.replace(SRC_SCREENSHOT_FOLDER, key_image_dir), f"{semantic_step_id}.png")
            if not os.path.exists(os.path.dirname(merged_screen_path)):
                os.makedirs(os.path.dirname(merged_screen_path))
            merged_screen_path = ScreenUtil.synthesize_image(screen_titles, screen_paths, merged_screen_path)
            merged_screen_paths.append(merged_screen_path)
        return merged_screen_paths
            

            
            
            