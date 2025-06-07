import json
import os
from copy import deepcopy
import re
# from numpy import dot
# from numpy.linalg import norm

from const import TEST_REPO, SRC_SCREENSHOT_FOLDER


class FileUtil:
    """
    file operations, including saving and loading events
    """
    @staticmethod
    def load_events(config_id, target):
        print(f"config_id: {config_id}")
        # target: 'generated', 'base_from', 'base_to'
        # e.g., a41a-a42a-b41 -> [FileUtil.TEST_REPO, 'a4', 'b41', 'base', 'a41a.json']
        fpath = [TEST_REPO, config_id[:2], config_id.split('-')[-1]]
        sub_dir = ''
        if target == 'generated':
            fpath += ['generated', sub_dir, config_id + '.json']
        elif target == '0-step':
            fpath += ['generated', '0-step', sub_dir, config_id + '.json']
        elif target == '1-step':
            fpath += ['generated', '1-step', sub_dir, config_id + '.json']
        elif target == '2-step':
            fpath += ['generated', '2-step', sub_dir, config_id + '.json']
        elif target == 'base_from':
            fpath += ['base', config_id.split('-')[0] + '.json']
        elif target == 'base_to':
            fpath += ['base', config_id.split('-')[1] + '.json']
        else:
            assert False, "Wrong target"
        fpath = os.path.join(*fpath)
        assert os.path.exists(fpath), f"Invalid file path: {fpath}"
        act_list = []
        with open(fpath, 'r', encoding='utf-8') as f:
            acts = json.load(f)
        for act in acts:
            if "affix" not in act:
                act_list.append(act)
        return act_list

    @staticmethod
    def load_prefix_events(config_id, target):
        # target: 'generated', 'base_from', 'base_to'
        # e.g., a41a-a42a-b41 -> [FileUtil.TEST_REPO, 'a4', 'b41', 'base', 'a41a.json']
        fpath = [TEST_REPO, config_id[:2], config_id.split('-')[-1]]
        sub_dir = ''
        if target == 'base_to':
            fpath += ['base', config_id.split('-')[1] + '.json']
        else:
            assert False, "Wrong target"
        fpath = os.path.join(*fpath)
        assert os.path.exists(fpath), f"Invalid file path: {fpath}"
        act_list = []
        with open(fpath, 'r', encoding='utf-8') as f:
            acts = json.load(f)
        for act in acts:
            if "affix" in act and "prefix" in act["affix"]:
                act_list.append(act)
        return act_list
    
    @staticmethod
    def load_postfix_events(config_id, target):
        # target: 'generated', 'base_from', 'base_to'
        # e.g., a41a-a42a-b41 -> [FileUtil.TEST_REPO, 'a4', 'b41', 'base', 'a41a.json']
        fpath = [TEST_REPO, config_id[:2], config_id.split('-')[-1]]
        sub_dir = ''
        if target == 'base_to':
            fpath += ['base', config_id.split('-')[1] + '.json']
        else:
            assert False, "Wrong target"
        fpath = os.path.join(*fpath)
        assert os.path.exists(fpath), f"Invalid file path: {fpath}"
        act_list = []
        with open(fpath, 'r', encoding='utf-8') as f:
            acts = json.load(f)
        for act in acts:
            if "affix" in act and "postfix" in act["affix"]:
                act_list.append(act)
        return act_list

    @staticmethod
    def load_oracle_screen_path(config_id):
        src_screen_dir = SRC_SCREENSHOT_FOLDER
        src_screen_dir = os.path.join(src_screen_dir, config_id[:2], config_id.split('-')[-1], 'base', f'{config_id.split("-")[0]}_screens')
        files = [f for f in os.listdir(src_screen_dir) if f.endswith('.png') and not f.endswith('ed.png')]
        files_sorted = sorted(files, key=lambda x: int(os.path.splitext(x)[0]))
        # Get the last file (which would be the highest number)
        last_file = files_sorted[-1] if files_sorted else None
        return os.path.join(src_screen_dir, last_file)
    
    @staticmethod
    def process_model_name_for_dir(model_name):
        model_name = model_name.replace("/", "_")
        model_name = model_name.replace("-", "_")
        model_name = model_name.replace(" ", "_")
        model_name = model_name.replace(".", "")
        return model_name
    
    @staticmethod
    def generate_result_save_dir(parent_dir, config_id, model_name):
        model_name = FileUtil.process_model_name_for_dir(model_name)
        # e.g., a41a-a42a-b41
        # folder = 'success' if is_success else 'failed'
        # fpath = [TEST_REPO, config_id[:2], config_id.split('-')[-1], 'generated', folder, config_id + '.json']
        new_save_dir = os.path.join(parent_dir, config_id[:2], config_id.split('-')[-1], f'generated_{model_name}', config_id)
        return new_save_dir
    
    @staticmethod
    def save_events(save_dir, actions):
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
        fpath = os.path.join(save_dir, "events.json")
        new_actions = [deepcopy(a) for a in actions]
        for a in new_actions:
            if a['class'] in ['EMPTY_EVENT', 'SYS_EVENT']:
                continue
            if 'id-prefix' in a:
                a['resource-id'] = a['id-prefix'] + a['resource-id']
                a.pop('id-prefix', "")
        with open(fpath, 'w') as f:
            json.dump(new_actions, f, indent=4)
            
    @staticmethod
    def sort_filename_by_num(dir):
        # some filenames has numbers in them, sort them by the number
        num_list = []
        for filename in os.listdir(dir):
            match = re.search(r'\d+', filename)
            num_list.append(int(match.group()))
        return sorted(num_list)
    
    @staticmethod
    def clear_folder(folder):
        # delete all files and subfolders recursively in the folder
        for root, dirs, files in os.walk(folder):
            for file in files:
                os.remove(os.path.join(root, file))
            for dir in dirs:
                os.rmdir(os.path.join(root, dir))