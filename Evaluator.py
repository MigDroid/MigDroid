import os
import json
import time
import sys
import tiktoken
import math
import logging

from ScreenUtil import ScreenUtil
from FileUtil import FileUtil

from const import TEST_REPO, RESULT_SAVE_FOLDER as RESULT_SAVE_FOLDER


class Evaluator:
    def __init__(self, result_folder, gt_folder, model_name):
        assert os.path.exists(result_folder), "Invalid config file path"
        self.result_folder = result_folder
        self.gt_folder = gt_folder
        self.model_name = model_name
        self.res = {'gui': {'tp': 0, 'fp': 0, 'tn': 0, 'fn': 0},
                    'oracle': {'tp': 0, 'fp': 0, 'tn': 0, 'fn': 0}}
        self.gui_success = False
        self.whole_success = False
        self.finished = 0
        self.model = model_name
        # self.enc = tiktoken.encoding_for_model('gpt-4o')
        self.should_calculate_cost = False
        self.setup_cost_parameters()
        self.logger = self.setup_logger()
        self.num_empty = 0
        self.total_cost = 0
        self.num_all = 0
        self.policy_violation = 0
        self.average_ned_similarity = 0
        self.average_lcs_similarity = 0
    
    def setup_cost_parameters(self):
        if self.model_name == "gpt-4o":
            self.cost_per_token_input = 2.5e-6
            self.cost_per_token_output = 1e-5
        elif self.model_name == "gpt-4o-mini":
            self.cost_per_token_input = 1.5e-7
            self.cost_per_token_output = 6e-7
        else:
            self.should_calculate_cost = False

    def setup_logger(self):
        logger = logging.getLogger('Evaluator')
        logger.setLevel(logging.INFO)
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        return logger

    def calculate_cost(self, query_file) -> float:
        try:
            if not self.should_calculate_cost:
                return 0
            input_text, output_text = self.split_input_output(query_file)
            num_input_tokens = len(self.enc.encode(input_text))
            num_output_tokens = len(self.enc.encode(output_text))
            num_image_tokens = self.calculate_image_token_from_query(query_file)
            
            cost = (
                num_input_tokens * self.cost_per_token_input
                + num_output_tokens * self.cost_per_token_output
                + num_image_tokens * self.cost_per_token_input
            )
            self.logger.info(f"Cost calculation completed: {cost}")
            return cost
        except Exception as e:
            self.logger.error(f"Error calculating cost: {str(e)}")
            return 0
    
    def split_input_output(self, filename) -> tuple[str, str]:
        with open(filename, "r") as file:
            lines = file.readlines()

        input_text = ""
        output_text = ""

        for line in lines:
            if line.endswith("Prompt-------------------\n") and not line.startswith("--------------------End"):
                # from this line, the lines below are input
                for input_line in lines[lines.index(line) + 1 :]:
                    if input_line.endswith("-------------------\n"):
                        break
                    input_text += input_line
            if line.endswith("Answer-------------------\n") and not line.startswith("--------------------End"):
                # from this line, the lines below are output
                for output_line in lines[lines.index(line) + 1 :]:
                    if output_line.endswith("-------------------\n"):
                        break
                    output_text += output_line
        return input_text.strip(), output_text.strip()

    def calculate_image_token(self, image_size: list) -> int:
        """
        Calculate the number of tokens for an image.
        """
        width, height = image_size
        # width is always less than height
        if width > height:
            width, height = height, width
        # print(f"Image size: {width}x{height}")
        if width/768 > height/2048:
            height = int((768 * height) / width)
            width = 768
            # print(f"Resized image size: {width}x{height}")
            num_tile = 2 * math.ceil(height / 512)
            # print(f"Number of tiles: {num_tile}")
        else:
            width = int((2048 * width) / height)
            height = 2048
            num_tile = 4 * math.ceil(width / 512)
        num_token = 170 * num_tile + 85
        return num_token
    
    def calculate_image_token_from_query(self, query_file: str) -> int:
        """
        Calculate the number of tokens for an image from a query file.
        """
        image_size = {}
        image_size["action"] = [1080, 1920]
        image_size["cc"] = [3060, 2440]
        image_size["feedback"] = [3060, 2020]
        image_size["oracle"] = [3060, 2020]
        num_action_query = 0
        num_cc_query = 0
        num_feedback_query = 0
        num_oracle_query = 0
        num_token = 0
        with open(query_file, "r") as file:
            lines = file.readlines()
        for line in lines:
            if line == "--------------------End of Action Prompt-------------------\n":
                num_action_query += 1
            if line == "--------------------End of CC Prompt-------------------\n":
                num_cc_query += 1
            if line == "--------------------End of Feedback Prompt-------------------\n":
                num_feedback_query += 1
            if line == "--------------------End of Oracle Prompt-------------------\n":
                num_oracle_query += 1
        num_token += num_action_query * self.calculate_image_token(image_size["action"])
        num_token += num_cc_query * self.calculate_image_token(image_size["cc"])
        num_token += num_feedback_query * self.calculate_image_token(image_size["feedback"])
        num_token += num_oracle_query * self.calculate_image_token(image_size["oracle"])
        return num_token

    def event_equal(self, result_event, gt_event):
        attrs = ['class', 'resource-id', 'content-desc', 'text', 'bounds', 'action', 'event_type']
        if ScreenUtil.widget_equal(result_event, gt_event):
            attrs = ['action', 'event_type']
        if 'children' in result_event:
            for child in result_event["children"]:
                if ScreenUtil.widget_equal(child, gt_event):
                    # print(f"Child: {child}")
                    attrs = ['action', 'event_type']
        for attr in attrs:
            if attr in result_event and attr in gt_event:
                if attr == 'action':
                    if "send_keys" in result_event[attr][0] and "send_keys" in gt_event[attr][0] and result_event[attr][1] == gt_event[attr][1]:
                        continue
                if result_event[attr] != gt_event[attr]:
                    return False
        return True
    
    def calculate_edit_distance(self, test1, test2):
        if not test1:
            return len(test2)
        if not test2:
            return len(test1)
        
        dp = [[0 for _ in range(len(test2) + 1)] for _ in range(len(test1) + 1)]
        
        for i in range(len(test1) + 1):
            dp[i][0] = i
        for j in range(len(test2) + 1):
            dp[0][j] = j
        
        for i in range(1, len(test1) + 1):
            for j in range(1, len(test2) + 1):
                if self.event_equal(test1[i-1], test2[j-1]):
                    dp[i][j] = dp[i-1][j-1]
                else:
                    delete_cost = dp[i-1][j] + 1
                    insert_cost = dp[i][j-1] + 1
                    replace_cost = dp[i-1][j-1] + 2
                    
                    dp[i][j] = min(delete_cost, insert_cost, replace_cost)
                    
                    for k in range(j+1, len(test2) + 1):
                        if k < len(test2) + 1 and self.event_equal(test1[i-1], test2[k-1]):
                            move_cost = dp[i-1][j] + 1
                            dp[i][j] = min(dp[i][j], move_cost)
                            break
        
        return dp[len(test1)][len(test2)]
    
    def calculate_ned_similarity(self, test1, test2):
        test1 = [e for e in test1 if e['event_type'] != 'oracle']
        test2 = [e for e in test2 if e['event_type'] != 'oracle']
        edit_distance = self.calculate_edit_distance(test1, test2)
        max_length = max(len(test1), len(test2))
        
        if max_length == 0:
            return 1.0 
        
        similarity = 1.0 - (edit_distance / (2 * max_length))
        return max(0.0, similarity)
    
    def calculate_lcs(self, test1, test2):
        if not test1 or not test2:
            return []
        
        dp = [[0 for _ in range(len(test2) + 1)] for _ in range(len(test1) + 1)]
        
        for i in range(1, len(test1) + 1):
            for j in range(1, len(test2) + 1):
                if self.event_equal(test1[i-1], test2[j-1]):
                    dp[i][j] = dp[i-1][j-1] + 1
                else:
                    dp[i][j] = max(dp[i-1][j], dp[i][j-1])
        
        lcs = []
        i, j = len(test1), len(test2)
        while i > 0 and j > 0:
            if self.event_equal(test1[i-1], test2[j-1]):
                lcs.append(test1[i-1])
                i -= 1
                j -= 1
            elif dp[i-1][j] > dp[i][j-1]:
                i -= 1
            else:
                j -= 1
        
        lcs.reverse()
        
        return lcs
    
    def calculate_lcs_similarity(self, result, gt):
        result_no_oracle = [e for e in result if e['event_type'] != 'oracle']
        gt_no_oracle = [e for e in gt if e['event_type'] != 'oracle']
        
        lcs = self.calculate_lcs(result_no_oracle, gt_no_oracle)
        
        max_length = len(gt_no_oracle)
        if max_length == 0:
            return 1.0 
        
        similarity = len(lcs) / max_length
        return similarity

    def evaluate_single_case(self, config_id, result_file, gt_file):
        result = json.load(open(result_file, 'r'))
        gt = json.load(open(gt_file, 'r'))
        
        if "ResponsibleAIPolicyViolation" in result[-1]:
            return
        
        self.num_all += 1
        # calculate test similarity
        ned_similarity = self.calculate_ned_similarity(result, gt)
        # print(f"ned similarity: {ned_similarity}")
        lcs_similarity = self.calculate_lcs_similarity(result, gt)
        # print(f"LCS similarity: {lcs_similarity}")
        self.average_ned_similarity += ned_similarity
        self.average_lcs_similarity += lcs_similarity
        
    def evaluate_all(self, target_category):
        # print("Result Folder: ", self.result_folder)
        # print("GT Folder: ", self.gt_folder)
        
        for root, dirs, files in os.walk(result_folder):
            for file in files:
                if self.model_name == "gpt-4o":
                    if FileUtil.process_model_name_for_dir('gpt-4o-mini') in root or FileUtil.process_model_name_for_dir('qwen-vl-max-2025-01-25') in root:
                        continue
                if self.model_name == "gpt-4o-mini":
                    if not FileUtil.process_model_name_for_dir('gpt-4o-mini') in root:
                        continue
                if self.model_name == "qwen-vl-max-2025-01-25":
                    if not FileUtil.process_model_name_for_dir('qwen-vl-max-2025-01-25') in root:
                        continue
                if target_category not in ['a1', 'a2', 'a4', 'a5']:
                    pass
                elif target_category not in root:
                    continue
                if file.endswith('.json'):
                    config_id = file.split('.')[0]
                    result_file = os.path.join(root, file)
                    gt_file = f"{self.gt_folder}/{config_id[:2]}/{config_id.split('-')[-1]}/base/{config_id.split('-')[1]}.json"
                    
                    # print("Result File: ", result_file)
                    # print("GT File: ", gt_file)
                    self.evaluate_single_case(config_id, result_file, gt_file)
                    
        self.average_ned_similarity = self.average_ned_similarity / self.num_all
        self.average_lcs_similarity = self.average_lcs_similarity / self.num_all
        print(f"Average NED similarity: {self.average_ned_similarity}")
        print(f"Average LCS similarity: {self.average_lcs_similarity}")

    def evaluate_single_case_llmigrate(self, config_id, result_file, gt_file):
        result = json.load(open(result_file, 'r'))
        gt = json.load(open(gt_file, 'r'))
        self.num_all += 1
        ned_similarity = self.calculate_ned_similarity(result, gt)
        print(f"ned similarity: {ned_similarity}")
        lcs_similarity = self.calculate_lcs_similarity(result, gt)
        print(f"LCS similarity: {lcs_similarity}")
        self.average_ned_similarity += ned_similarity
        self.average_lcs_similarity += lcs_similarity
        
    def evaluate_all_llmigrate(self, target_category):
        for root, dirs, files in os.walk(result_folder):
            for file in files:
                if target_category not in ['a1', 'a2', 'a4', 'a5']:
                    pass
                elif target_category not in root:
                    continue
                if '-u' in root:
                    continue
                if file.endswith('.json') and not 'base' in root:
                    category = root.split('/')[1]
                    config_id = f"{category}{file[1]}-{category}{file.split('-')[1][1]}-b{category[1]}{root.split('/')[-2][2]}"
                    print(config_id)
                    result_file = os.path.join(root, file)
                    gt_file = f"{self.gt_folder}/{config_id[:2]}/{config_id.split('-')[-1]}/base/{config_id.split('-')[1]}.json"
                    
                    print("Result File: ", result_file)
                    print("GT File: ", gt_file)
                    self.evaluate_single_case_llmigrate(config_id, result_file, gt_file)

        self.average_ned_similarity = self.average_ned_similarity / self.num_all
        self.average_lcs_similarity = self.average_lcs_similarity / self.num_all
        print(f"Average ned similarity: {self.average_ned_similarity}")
        print(f"Average LCS similarity: {self.average_lcs_similarity}")

    def evaluate_all_craftdroid(self, target_category):
        self.evaluate_all_llmigrate(target_category)

if __name__ == '__main__':
    # take an argument
    # target_category = sys.argv[1]
    data_folder = 'Results'
    target_tool = 'MigDroid'
    # target_tool = 'LLMigrate'
    # target_tool = 'CraftDroid'
    gt_folder = TEST_REPO
    # model_name = "qwen-vl-max-2025-01-25"
    model_name = "gpt-4o"
    ned_similarities = {}
    lcs_similarities = {}
    
    if target_tool == 'MigDroid':
        result_folder = RESULT_SAVE_FOLDER
        for target_category in ['a1', 'a2', 'a4', 'a5']:
            evaluator = Evaluator(result_folder, gt_folder, model_name)
            print(f"Category: {target_category}")
            evaluator.evaluate_all(target_category)
            ned_similarities[target_category] = evaluator.average_ned_similarity
            lcs_similarities[target_category] = evaluator.average_lcs_similarity
        evaluator = Evaluator(result_folder, gt_folder, model_name)
        print(f"Category: all")
        evaluator.evaluate_all('all')
    elif target_tool == 'LLMigrate':
        result_folder = 'test_repo_llmigrate'
        for target_category in ['a1', 'a2', 'a4', 'a5']:
            evaluator = Evaluator(result_folder, gt_folder, model_name)
            evaluator.evaluate_all_llmigrate(target_category)
            ned_similarities[target_category] = evaluator.average_ned_similarity
            lcs_similarities[target_category] = evaluator.average_lcs_similarity
        evaluator = Evaluator(result_folder, gt_folder, model_name)
        evaluator.evaluate_all_llmigrate('all')
    elif target_tool == 'CraftDroid':
        result_folder = 'test_repo_craftdroid'
        for target_category in ['a1', 'a2', 'a4', 'a5']:
            evaluator = Evaluator(result_folder, gt_folder, model_name)
            evaluator.evaluate_all_craftdroid(target_category)
            ned_similarities[target_category] = evaluator.average_ned_similarity
            lcs_similarities[target_category] = evaluator.average_lcs_similarity
        evaluator = Evaluator(result_folder, gt_folder, model_name)
        evaluator.evaluate_all_craftdroid('all')
    # for target_category in ['a1', 'a2', 'a4', 'a5']:
    #     print(f"ned similarity: {ned_similarities[target_category]}")
    #     print(f"LCS similarity: {lcs_similarities[target_category]}")
    if model_name == 'gpt-4o':
        model_name = 'GPT-4o'
    elif model_name == 'qwen-vl-max-2025-01-25':
        model_name = 'Qwen-VL-Max'
    data_save_folder = f'{data_folder}/{target_tool}-{model_name}'
    if target_tool == 'CraftDroid':
        data_save_folder = f'{data_folder}/{target_tool}'
    os.makedirs(data_save_folder, exist_ok=True)
    with open(f'{data_save_folder}/ned_similarities.json', 'w') as f:
        json.dump(ned_similarities, f, indent=4)
    with open(f'{data_save_folder}/lcs_similarities.json', 'w') as f:
        json.dump(lcs_similarities, f, indent=4)

