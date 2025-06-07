import time
import sys
import os
from datetime import datetime
import copy
import traceback
import json
# local import
from FileUtil import FileUtil
from Configuration import Configuration
from Runner_u2 import Runner_u2
from TestAnalyzer.AnalyzerUtil import AnalyzerUtil
from PlannerUtil import PlannerUtil
from ScreenUtil import ScreenUtil
from FileUtil import FileUtil
from const import RESULT_SAVE_FOLDER

class Planner:
    def __init__(self, save_dir, model_name, config_id, udid=None):
        self.save_dir = save_dir
        self.model_name = model_name
        self.config_id = config_id
        self.target_app_id = config_id.split("-")[1]
        self.config = Configuration(config_id)
        print(f"NO_RESET: {self.config.no_reset}")
        self.runner = Runner_u2(
            self.target_app_id,
            self.config.pkg_to,
            self.config.no_reset,
            udid,
        )
        self.src_events = FileUtil.load_events(self.config.id, "base_from")
        self.src_oracle_screen_path = FileUtil.load_oracle_screen_path(self.config.id)
        self.tgt_prefix_events = FileUtil.load_prefix_events(self.config.id, "base_to")
        self.tgt_postfix_events = FileUtil.load_postfix_events(self.config.id, "base_to")
        self.gt_tgt_events = FileUtil.load_events(self.config.id, "base_to")
        self.gt_length = len(self.gt_tgt_events)
        self.tid = self.config.id
        self.tgt_events = []
        self.tgt_events_desc = []
        # self.is_rerun_required = True
        self.src_app_id = self.config.id.split("-")[0]
        self.tgt_app_id = self.config.id.split("-")[1]
        self.extra_step_tip = None
        
        self.t_start = None
        self.step = 0
        self.time_limit = 1800
        self.time_wait_load = 5
        # model_name_path = self.model_name.replace("/", "-").replace(" ", "_").replace("-", "_").replace(".", "")
        self.screen_save_dir = os.path.join(self.save_dir, "screens")
        self.annotated_screen_save_dir = os.path.join(self.save_dir, "annotated_screens")
        self.feedback_screen_save_dir = os.path.join(self.save_dir, "feedback_screens")
        self.page_layout_save_dir = os.path.join(self.save_dir, "page_layouts")
        self.query_save_path = os.path.join(self.save_dir, "queries.txt")
        self.log_file = self.save_dir + "/log.txt"
        os.makedirs(self.screen_save_dir) if not os.path.exists(self.screen_save_dir) else FileUtil.clear_folder(self.screen_save_dir)
        os.makedirs(self.annotated_screen_save_dir) if not os.path.exists(self.annotated_screen_save_dir) else FileUtil.clear_folder(self.annotated_screen_save_dir)
        os.makedirs(self.page_layout_save_dir) if not os.path.exists(self.page_layout_save_dir) else FileUtil.clear_folder(self.page_layout_save_dir)
        os.makedirs(self.feedback_screen_save_dir) if not os.path.exists(self.feedback_screen_save_dir) else FileUtil.clear_folder(self.feedback_screen_save_dir)
        with open(self.query_save_path, "w") as f:
            f.write("")

    def reorder_candidates(self, candidates):
        num_digit_text = sum(1 for c in candidates if c.get('text', '').isdigit())
        num_digit_content_desc = sum(1 for c in candidates if c.get('content-desc', '').isdigit())
        if num_digit_text < 4 and num_digit_content_desc < 4:
            return candidates
        if num_digit_text >= 4:
            attr = 'text'
        else:
            attr = 'content-desc'
        digit_candidates = []
        non_digit_candidates = []
        zero_candidates = []
        for c in candidates:
            text = c.get(attr, '')
            if text.isdigit():
                digit = int(text)
                if digit == 0:
                    zero_candidates.append(c)
                else:
                    digit_candidates.append(c)
            else:
                non_digit_candidates.append(c)
        
        digit_candidates_sorted = sorted(digit_candidates, key=lambda x: int(x[attr]))
        
        max_index = max(int(c[attr]) for c in digit_candidates_sorted) - 1
        new_length = max(len(candidates), max_index + 1)
        new_candidates = [None] * new_length
        
        used_indices = set()
        for c in digit_candidates_sorted:
            digit = int(c[attr])
            idx = digit - 1
            if 0 <= idx < new_length and idx not in used_indices:
                new_candidates[idx] = c
                used_indices.add(idx)
        
        current = 0
        for i in range(new_length):
            if new_candidates[i] is None and current < len(non_digit_candidates):
                new_candidates[i] = non_digit_candidates[current]
                current += 1
        
        new_candidates += zero_candidates
        
        new_candidates = [c for c in new_candidates if c is not None]
        return new_candidates

    def get_candidates(self):
        candidates = []
        wait_round = 0
        # get candidates
        while not candidates and wait_round < 3:
            wait_round += 1
            time.sleep(self.time_wait_load)
            page_layout = self.runner.get_page_source()
            page_layout_path = os.path.join(self.page_layout_save_dir, f"{self.step-1}.xml")
            with open(page_layout_path, "w") as f:
                f.write(page_layout)
            # get interactable widgets
            candidates = ScreenUtil.get_interactable_widgets(page_layout)
            for candidate in candidates:
                # candidate['activity'] = self.runner.get_current_activity() if candidate['package'] == self.config.pkg_to else ''
                candidate['activity'] = ''
        candidates = self.reorder_candidates(candidates)
        return page_layout, candidates
    
    def generate_oracle(self, page_layout, screenshot_path, prompt_components):
        merged_screen_save_path = os.path.join(self.screen_save_dir, f"{self.step-1}_merged.png")
        titles = ["Source App Final Screen", "Target App Current Screen"]
        screen_paths = [self.src_oracle_screen_path, screenshot_path]
        ScreenUtil.synthesize_image(titles, screen_paths, merged_screen_save_path)
        completeness, self.extra_step_tip = PlannerUtil.completenesss_check(prompt_components, merged_screen_save_path, model_name=self.model_name, query_save_path=self.query_save_path)
        if completeness:
            self.is_done = True
            all_widgets = ScreenUtil.extract_widgets_from_xml(page_layout)
            src_oracle_event = self.src_events[-1]
            oracle = PlannerUtil.seek_oracle_widget(src_oracle_event, all_widgets, self.config.pkg_to, self.config.act_to)
            if oracle:
                print(f"Oracle event found by hard-coded rules:\n{oracle}")
                return oracle
            else:
                # update the page layout and one more chance
                new_page_layout = self.runner.get_page_source()
                if new_page_layout != page_layout:
                    page_layout_path = os.path.join(self.page_layout_save_dir, f"{self.step-1}.xml")
                    with open(page_layout_path, "w") as f:
                        f.write(new_page_layout)
                    all_widgets = ScreenUtil.extract_widgets_from_xml(new_page_layout)
                    oracle = PlannerUtil.seek_oracle_widget(src_oracle_event, all_widgets, self.config.pkg_to, self.config.act_to)
                    if oracle:
                        print(f"Oracle event found by hard-coded rules:\n{oracle}")
                        return oracle
            
            page_layout = self.runner.get_page_source()
            leaf_widgets = ScreenUtil.get_leaf_widgets(page_layout)
            oracle_widget_id = PlannerUtil.query_oracle(prompt_components, merged_screen_save_path, leaf_widgets, model_name=self.model_name, query_save_path=self.query_save_path)
            oracle_widget = leaf_widgets[oracle_widget_id-1]
            oracle_widget['event_type'] = 'oracle'
            
            oracle_widget['action'] = [src_oracle_event['action'][0], src_oracle_event['action'][1], '', '']
            if src_oracle_event['action'][0] == 'wait_until_text_presence' and oracle_widget['text']:
                oracle_widget['action'] = ['wait_until_text_presence', src_oracle_event['action'][1], 'text', oracle_widget['text']]
            elif src_oracle_event['action'][0] == 'wait_until_element_presence' or (src_oracle_event['action'][0] == 'wait_until_text_presence' and not oracle_widget['text']):
                if oracle_widget['resource-id']:
                    oracle_widget['action'] = ['wait_until_element_presence', src_oracle_event['action'][1], 'id', oracle_widget['resource-id']]
                elif oracle_widget['text']:
                    oracle_widget['action'] = ['wait_until_element_presence', src_oracle_event['action'][1], 'text', oracle_widget['text']]
                elif oracle_widget['content-desc']:
                    oracle_widget['action'] = ['wait_until_element_presence', src_oracle_event['action'][1], 'content-desc', oracle_widget['content-desc']]
                elif oracle_widget['bounds']:
                    oracle_widget['action'] = ['wait_until_element_presence', src_oracle_event['action'][1], 'bounds', oracle_widget['bounds']]
            print(f"Oracle Widget To Be Found:\n{oracle_widget}")
            oracle = PlannerUtil.seek_oracle_widget(oracle_widget, all_widgets, self.config.pkg_to, self.config.act_to)
            print(f"Oracle event found by LLMs:\n{oracle}")
            return oracle
        return None
        
    def generate_routine_reflection(self, prompt_components):
        correct_event_ids = []
        for i, reflection_event in enumerate(self.reflection_events):
            if len(self.tgt_events) >= self.reflection_event_ids[i]-1 and ScreenUtil.widget_equal(reflection_event, self.tgt_events[self.reflection_event_ids[i]-1]):
                correct_event_ids.append(i+1)
        # activate self-reflection mechanism
        reflection_prompt_components = copy.deepcopy(prompt_components)
        image_titles = ["Open Screen"]
        open_screen_path = os.path.join(self.screen_save_dir, "0.png")
        screenshot_paths = [open_screen_path]
        for i, _ in enumerate(self.tgt_events):
            image_titles.append(f"After Interaction {i+1}")
            screenshot_paths.append(os.path.join(self.screen_save_dir, f"{i}.png"))
        reflection_screen_path = os.path.join(self.screen_save_dir, f"reflection_{self.num_reflection}.png")
        ScreenUtil.synthesize_image(image_titles, screenshot_paths, reflection_screen_path)
        wrong_event_id = PlannerUtil.get_routine_reflection(reflection_prompt_components, reflection_screen_path, correct_event_ids, model_name=self.model_name, query_save_path=self.query_save_path)
        return wrong_event_id    
        
    def generate_self_reflection(self, prompt_components):
        correct_event_ids = []
        for i, reflection_event in enumerate(self.reflection_events):
            if len(self.tgt_events) >= self.reflection_event_ids[i]-1 and ScreenUtil.widget_equal(reflection_event, self.tgt_events[self.reflection_event_ids[i]-1]):
                correct_event_ids.append(i+1)
        # activate self-reflection mechanism
        reflection_prompt_components = copy.deepcopy(prompt_components)
        image_titles = ["Open Screen"]
        open_screen_path = os.path.join(self.screen_save_dir, "0.png")
        screenshot_paths = [open_screen_path]
        for i, _ in enumerate(self.tgt_events):
            image_titles.append(f"After Interaction {i+1}")
            screenshot_paths.append(os.path.join(self.screen_save_dir, f"{i}.png"))
        reflection_screen_path = os.path.join(self.screen_save_dir, f"reflection_{self.num_reflection}.png")
        ScreenUtil.synthesize_image(image_titles, screenshot_paths, reflection_screen_path)
        wrong_event_id = PlannerUtil.get_reflection(reflection_prompt_components, reflection_screen_path, correct_event_ids, model_name=self.model_name, query_save_path=self.query_save_path)
        return wrong_event_id
    
    def cancel_stepping_event(self):
        # delete the last event in the tgt_events if it is a stepping event
        if len(self.tgt_events) > 0 and 'stepping' in self.tgt_events[-1]:
            self.tgt_events = self.tgt_events[:-1]
            self.tgt_events_desc = self.tgt_events_desc[:-1]
            self.step -= 1
            current_result = self.tgt_prefix_events + self.tgt_events
            FileUtil.save_events(self.save_dir, current_result)
    
    def run(self):
        print(f"Save directory: {result_save_path}")
        print("Start exploring the target app")
        print("Timestamp:", datetime.now())
        # executing the prefix events for target app
        if self.tgt_prefix_events:
            print("Performing prefix events for target app:", self.tgt_prefix_events)
            self.runner.perform_actions(self.tgt_prefix_events, reset=True)
        self.tgt_events = []
        self.is_done = False
        self.step = 0
        self.num_reflection = 0
        # get source test description
        src_test_desc, stop_condition, functionality_under_test = AnalyzerUtil.get_key_test_desc_from_file(self.config_id, self.model_name)
        feedback_tip = []
        rejected_actions = []
        self.reflection_events = []
        self.reflection_event_ids = []
        prompt_components = {}
        num_iteration = 0
        while not self.is_done and time.time() - self.t_start < self.time_limit and num_iteration < 10*self.gt_length and self.step < 2*self.gt_length:
            num_iteration += 1
            self.step += 1
            self.stepping = False
            flag_reflection = False
            event_history_desc = ''
            # events history description
            for desc_id, desc in enumerate(self.tgt_events_desc):
                event_history_desc += f"Interaction {desc_id + 1}: {desc}\n"
            prompt_components["event_history_desc"] = event_history_desc
            if (num_iteration-1) % 100 == 0 and num_iteration > 1:
                # activate routine reflection mechanism
                reflection_event_id = self.generate_routine_reflection(prompt_components)
                if reflection_event_id <= len(self.tgt_events) and reflection_event_id > 0:
                    flag_reflection = True
                    reflection_event = self.tgt_events[reflection_event_id-1]
                    self.tgt_events = self.tgt_events[:reflection_event_id-1]
                    self.tgt_events_desc = self.tgt_events_desc[:reflection_event_id-1]
                    self.step = reflection_event_id
                    self.reflection_events.append(reflection_event)
                    self.reflection_event_ids.append(reflection_event_id)
                    self.runner.perform_actions(self.tgt_prefix_events + self.tgt_events, reset=True)
                
            if len(feedback_tip) >= 3:
                feedback_tip = []
                # activate self-reflection mechanism
                reflection_event_id = self.generate_self_reflection(prompt_components)
                if reflection_event_id <= len(self.tgt_events) and reflection_event_id > 0:
                    flag_reflection = True
                    reflection_event = self.tgt_events[reflection_event_id-1]
                    self.tgt_events = self.tgt_events[:reflection_event_id-1]
                    self.tgt_events_desc = self.tgt_events_desc[:reflection_event_id-1]
                    self.step = reflection_event_id
                    self.reflection_events.append(reflection_event)
                    self.reflection_event_ids.append(reflection_event_id)
                    self.runner.perform_actions(self.tgt_prefix_events + self.tgt_events, reset=True)
                
            
            print(f"Step {self.step}")
            time.sleep(self.time_wait_load)
            print("Curernt Target Event Sequence:")
            for tgt_event in self.tgt_events:
                print(tgt_event)
            # check loop
            if len(self.tgt_events) > 4 and str(self.tgt_events[-1]) == str(self.tgt_events[-2]) == str(self.tgt_events[-3]) == str(self.tgt_events[-4]):
                print("Stuck in loop, exploration terminated.")
                break
            # check if the app has accidentally closed
            if self.config.pkg_to not in self.runner.device.app_list_running():
                print("App is not running. Restart the app and perform previous events.")
                self.runner.perform_actions(self.tgt_prefix_events + self.tgt_events, reset=True)
            
            page_layout, candidates = self.get_candidates()
            print("Candidates: ", candidates)
            reflection_tip = ''
            if flag_reflection:
                print("Wrong event: ", reflection_event)
                print("Candidates: ", candidates)
                # match the wrong event with the candidates
                for i, candidate in enumerate(candidates):
                    if ScreenUtil.widget_equal(candidate, reflection_event):
                        print("Matched candidate: ", candidate)
                        wrong_candidate_id = i+1
                        wrong_action = reflection_event['action']
                        if wrong_action == ['click']:
                            wrong_action = 'tap'
                        reflection_tip = f"Forbidden action(you must not choose this one since it is definitely wrong):\n Widget ID: {wrong_candidate_id}\n Action: {wrong_action}"
            # get screenshot
            screenshot_path = os.path.join(self.screen_save_dir, f"{self.step-1}.png")
            self.runner.get_screenshot_as_file(screenshot_path)
            # annotate the screenshot with the candidates
            annotated_screenshot_path = os.path.join(self.annotated_screen_save_dir, f"{self.step-1}.png")
            ScreenUtil.annotate_screen(screenshot_path, annotated_screenshot_path, candidates)
            # page description
            page_desc = ScreenUtil.get_page_desc(
                self.tgt_app_id,
                screenshot_path,
                self.tgt_events,
                model_name=self.model_name,
            )
            event_history_desc = ''
            # events history description
            for desc_id, desc in enumerate(self.tgt_events_desc):
                event_history_desc += f"Interaction {desc_id + 1}: {desc}\n"
            prompt_components["event_history_desc"] = event_history_desc
            prompt_components = {
                "functionality_under_test": functionality_under_test,
                "stop_condition": stop_condition,
                "src_test": self.src_events,
                "src_test_desc": src_test_desc,
                "page_desc": page_desc,
                "event_history_desc": event_history_desc,
                "src_app_id": self.src_app_id,
                "tgt_app_id": self.tgt_app_id,
                "candidates": candidates,
                "feedback_tip": feedback_tip,
                "rejected_actions": rejected_actions,
                "reflection_tip": reflection_tip,
                "extra_step_tip": self.extra_step_tip
            }
            
            # only when the last action is accepted, check the completeness
            if len(self.tgt_events) > 0 and feedback_tip == []:
                oracle = self.generate_oracle(page_layout, screenshot_path, prompt_components)
                if oracle:
                    self.tgt_events.append(oracle)
                    break
                
            # get next action
            event_info, feedback_context = PlannerUtil.query_action_v2(
                prompt_components, annotated_screenshot_path, model_name=self.model_name, query_save_path=self.query_save_path
            )
            executable_event = {}
            # ensure the app is still open 
            if self.config.pkg_to not in self.runner.device.app_list_running():
                print("App is not running. Restart the app and perform previous events.")
                self.runner.perform_actions(self.tgt_prefix_events + self.tgt_events, reset=True)
            stepping_event = None
            widget = candidates[event_info[0]-1]
            action = event_info[1].lower()
                    
            if 'tap' in action:
                action = ['click']
            elif 'input' in action:
                action = ['send_keys_and_enter', event_info[2]]
            elif 'back' in action:
                action = ['KEY_BACK']
                executable_event = {
                    "class": "SYS_EVENT",
                    "action": action,
                    "event_type": "SYS_EVENT"
                }
            elif 'long_press' in action or 'long_click' in action:
                action = ['long_press']
            else:
                action = [action]
            if not executable_event:
                executable_event = copy.deepcopy(widget)
                executable_event['package'] = self.config.pkg_to
                executable_event['activity'] = self.runner.get_current_activity()
                executable_event['ignorable'] = 'false'
                executable_event['event_type'] = 'gui'
                executable_event['action'] = action
                executable_event['bounds'] = widget['bounds']
            # click input field before sending keys
            if 'send_keys' in action[0]:
                if self.tgt_events and ScreenUtil.is_same_widget(widget, self.tgt_events[-1]) and 'click' in self.tgt_events[-1]['action']:
                    pass
                elif widget['focused'] == 'true':
                    pass
                else:
                    stepping_event = copy.deepcopy(executable_event)
                    stepping_event['action'] = ['click']
                    print(f"Stepping event for this step:\n{stepping_event}")
                    self.runner.perform_actions([stepping_event], reset=False)
                    screenshot_path = os.path.join(self.screen_save_dir, f"{self.step-1}.png")
                    interaction_screenshot_path = screenshot_path.replace(".png", "_interaction.png")
                    ScreenUtil.annotate_screen(screenshot_path, interaction_screenshot_path, [widget], enable_number=False)
                    stepping_event["stepping"] = "yes"
                    print(f"Executable event learned for this step:\n{stepping_event}")
                    self.tgt_events.append(stepping_event)
                    stepping_event_desc = f"Tap the input field {stepping_event} to activate it."
                    self.tgt_events_desc.append(stepping_event_desc)
                    current_result = self.tgt_prefix_events + self.tgt_events
                    FileUtil.save_events(self.save_dir, current_result)
                    self.step += 1
                    self.stepping = True
                    
                    # hopefully the box is focused, start inputting
                    page_layout = self.runner.get_page_source()
                    candidates = ScreenUtil.get_interactable_widgets(page_layout)
                    executable_event = copy.deepcopy(widget)
                    executable_event['package'] = self.config.pkg_to
                    executable_event['activity'] = self.runner.get_current_activity()
                    executable_event['ignorable'] = 'false'
                    executable_event['event_type'] = 'gui'
                    executable_event['action'] = ['send_keys_and_enter', event_info[2]]
                    executable_event['bounds'] = widget['bounds']
                    screenshot_path = os.path.join(self.screen_save_dir, f"{self.step-1}.png")
                    self.runner.get_screenshot_as_file(screenshot_path)

            try:
                self.runner.perform_actions([executable_event], reset=False)
                if 'send_keys' in action[0]:
                    # get page layout after sending keys
                    interested_input_box = copy.deepcopy(executable_event)
                    interested_input_box['text'] = ''
                    ele = self.runner.get_element(interested_input_box)
                    if ele and ele.info['text'] == event_info[2] + '\n':
                        interested_input_box['class'] = 'DELETE_LAST_CHAR'
                        self.runner.perform_actions([interested_input_box], reset=False)
                screenshot_path = os.path.join(self.screen_save_dir, f"{self.step-1}.png")
                interaction_screenshot_path = screenshot_path.replace(".png", "_interaction.png")
                ScreenUtil.annotate_screen(screenshot_path, interaction_screenshot_path, [widget], enable_number=False)
            except Exception as excep:
                print(f"Error when performing the action\n{excep}")
                # print whole traceback
                traceback.print_exc()
                print(executable_event)
                # get new page layout and start over
                new_page_layout = self.runner.get_page_source()
                new_candidates = ScreenUtil.get_interactable_widgets(new_page_layout)
                layout_changed = False
                for new_widget in new_candidates:
                    if not any([ScreenUtil.widget_equal(new_widget, w) for w in candidates]):
                        layout_changed = True
                        break
                for widget in candidates:
                    if not any([ScreenUtil.widget_equal(widget, w) for w in new_candidates]):
                        layout_changed = True
                        break
                if layout_changed:
                    print("Page layout has been updated and the action is not performed, starting this step over.")
                    self.step -= 1
                    continue
                else:
                    print("Page layout has not been updated and the action is not performed, starting this step over.")
                    forbidden_action = {"Widget ID": event_info[0], "Action": event_info[1]}
                    rejected_actions.append(forbidden_action)
                    prompt_event = ScreenUtil.extract_semantic_attrs(executable_event)
                    feedback_tip.append(f"The action {prompt_event} cannot be performed. Please do not choose this action.")
                    self.step -= 1
                    continue
            
            # feedback mechanism when the action is successfully performed
            prompt_components["current_interaction"] = executable_event
            screenshot_path = os.path.join(self.screen_save_dir, f"{self.step-1}.png")
            interaction_screenshot_path = screenshot_path.replace(".png", "_interaction.png")
            time.sleep(self.time_wait_load)
            new_screen_path = os.path.join(self.screen_save_dir, f"{self.step}.png")
            titles = ["App Screen Before New Step", "App Screen After New Step"]
            time.sleep(self.time_wait_load)
            self.runner.get_screenshot_as_file(new_screen_path)
            feedback_screen_save_path = os.path.join(self.feedback_screen_save_dir, f"{self.step-1}_feedback.png")
            ScreenUtil.synthesize_image(titles, [interaction_screenshot_path, new_screen_path], feedback_screen_save_path)
            step_desc, flag_accept, suggestion = PlannerUtil.get_feedback(prompt_components, feedback_context, feedback_screen_save_path, self.query_save_path, model_name=self.model_name)
            if flag_accept:
                self.tgt_events.append(executable_event)
                self.tgt_events_desc.append(step_desc)
            else:
                print(f"The action is rejected by the user.")
                prompt_event = ScreenUtil.extract_semantic_attrs(executable_event)
                forbidden_action = {"Widget ID": event_info[0], "Action": event_info[1]}
                rejected_actions.append(forbidden_action)
                feedback_tip.append(f"A Suggestion on the next interaction: {suggestion}")
                self.step -= 1
                # if there is a stepping event, cancel it
                if self.stepping:
                    self.cancel_stepping_event()
                # restart the app, clear data, perform prefix events
                self.runner.perform_actions(self.tgt_prefix_events + self.tgt_events, reset=True)
                continue
            
            feedback_tip = []
            rejected_actions = []
            current_result = self.tgt_prefix_events + self.tgt_events
            FileUtil.save_events(self.save_dir, current_result)
        if self.is_done:
            return True, 0
        else:
            return False, self.step

    @staticmethod
    def generate_empty_event(event_type):
        return {"class": "EMPTY_EVENT", "skey": 0, "event_type": event_type}

    # MigDroid_Runner class contains 'socket' object and cannot be pickled
    def __getstate__(self):
        state = self.__dict__.copy()
        del state["runner"]
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        self.runner = None


if __name__ == "__main__":
    save_dir = RESULT_SAVE_FOLDER
    if len(sys.argv) > 1:
        config_id = sys.argv[1]
        appium_port = sys.argv[2]
        udid = sys.argv[3]
        model_name = sys.argv[4]
    else:
        config_id = "a33-a35-b31"
        appium_port = "5723"
        udid = "emulator-5556"
        model_name = "gpt-4o-mini"

    result_save_path = FileUtil.generate_result_save_dir(save_dir, config_id, model_name)
    planner = Planner(result_save_path, model_name, config_id, udid)
    planner.t_start = time.time()
    is_done, failed_step = False, 1
    is_done, failed_step = planner.run()
    if is_done:
        print('Finished. Learned actions')
        results = planner.tgt_events
        for a in results:
            print(a)
        print(f'Transfer time in sec: {time.time() - planner.t_start}')
        
    elif time.time() - planner.t_start > planner.time_limit:
        print(f'Time limit {planner.time_limit}s exceeded. Stop the exploration.')
        results = planner.tgt_events
        timeout_event = Planner.generate_empty_event('Timeout') # to indicate timeout
        results.append(timeout_event)
    else:
        print(f'Failed transfer at step {failed_step}')
        print(f'Transfer time in sec: {time.time() - planner.t_start}')
        results = planner.tgt_events
    
    t_start = time.time()
    results = planner.tgt_prefix_events + results + planner.tgt_postfix_events
    FileUtil.save_events(result_save_path, results)
    
    print(f'Start testing learned actions')
    # execute post-fix events
    if planner.tgt_postfix_events:
        print("Performing postfix events for target app:", planner.tgt_postfix_events)
        try:
            planner.runner.perform_actions(planner.tgt_postfix_events, reset=True)
        except:
            print("Error when performing postfix events")
    
    planner.runner.stop_server()
    