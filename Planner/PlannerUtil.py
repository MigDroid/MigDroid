from copy import deepcopy
import re

from LLMUtil import LLMUtil
from ScreenUtil import ScreenUtil
from const import CATEGORY_MAP, SEMANTIC_ATTRS


class PlannerUtil:
    """
    This class is a utility class for the MLLM planner, which is activated when the matcher fails to find a match.
    """

    @staticmethod
    def query_action_v2(prompt_components, screenshot_path, query_save_path, model_name="gpt-4o-mini"):
        prompt_template_file = "Planner/prompt_ag.txt"
        with open(prompt_template_file, "r") as f:
            prompt = f.read()
        category_name = CATEGORY_MAP[prompt_components["tgt_app_id"][:2]]
        prompt = prompt.replace("$$$category$$$", category_name)
        prompt = prompt.replace("$$$func$$$", prompt_components["functionality_under_test"])
        prompt = prompt.replace("$$$src_test_desc$$$", prompt_components["src_test_desc"])
        if prompt_components["event_history_desc"]:
            prompt = prompt.replace("$$$event_history_desc$$$", f"I have opened te app and executed the following interactions:\n {prompt_components['event_history_desc']}. ")
        else:
            prompt = prompt.replace("$$$event_history_desc$$$", "I have just opened the app and haven't executed any interactions. ")
        prompt = prompt.replace("$$$page_desc$$$", prompt_components["page_desc"])

        candidate_prompt = ''
        candidates = []
        for candidate in prompt_components["candidates"]:
            # preserve only the semantic attributes
            new_candidate = ScreenUtil.extract_semantic_attrs(candidate)
            candidates.append(deepcopy(new_candidate))
        for i, candidate in enumerate(candidates):
            candidate_prompt += f"{i+1}. {candidate}\n"
        prompt = prompt.replace("$$$candidates$$$", candidate_prompt)
        # get input values
        input_values = []
        for src_event in prompt_components["src_test"]:
            if 'send_keys' in src_event['action'][0]:
                input_values.append(src_event['action'][1])
        input_values = ', '.join(input_values)
        prompt = prompt.replace("$$$input_values$$$", input_values)
        if prompt_components["feedback_tip"]:
            prompt += f"\nExtra tips:\n"
            for i, tip in enumerate(prompt_components["feedback_tip"]):
                prompt += f"{i+1}. {tip}\n"
        if prompt_components["extra_step_tip"]:
            prompt += f"\nThe most important tip:{prompt_components['extra_step_tip']}"
        if prompt_components["rejected_actions"]:
            prompt += f"\nThese actions have been proven to be ineffective, they are not recommended:\n"
            for i, action in enumerate(prompt_components["rejected_actions"]):
                prompt += f"{i+1}. {action}\n"
        prompt += f"\n{prompt_components['reflection_tip']}"
        answer = LLMUtil.query_with_retry(prompt, screenshot_path, model_name=model_name)
        with open(query_save_path, "a") as f:
            f.write("\n--------------------Action Prompt-------------------\n")
            f.write(prompt)
            f.write("\n--------------------End of Action Prompt-------------------\n")
            f.write("\n--------------------Action Answer-------------------\n")
            f.write(answer)
            f.write("\n--------------------End of Action Answer-------------------\n")
        try:
            event_info = LLMUtil.extract_answer_components(answer, "ag")
            feedback_context = LLMUtil.extract_answer_components(answer, "ag_feedback")
        except:
            format = prompt.split("strictly follow this format:")[1]
            refomat_prompt_file = "Planner/reformat.txt"
            with open(refomat_prompt_file, "r") as f:
                refomat_prompt = f.read()
            refomat_prompt = refomat_prompt.replace("$$$answer$$$", answer)
            refomat_prompt = refomat_prompt.replace("$$$format$$$", format)
            new_answer = LLMUtil.query_with_retry(refomat_prompt, None, model_name=model_name)
            try:
                event_info = LLMUtil.extract_answer_components(new_answer, "ag")
                feedback_context = LLMUtil.extract_answer_components(new_answer, "ag_feedback")
            except:
                event_info = None
                feedback_context = None
        return event_info, feedback_context
    
    @staticmethod
    def completenesss_check(prompt_components, screenshot_path, query_save_path, model_name="gpt-4o-mini"):
        prompt_template_file = "Planner/prompt_cc.txt"
        with open(prompt_template_file, "r") as f:
            prompt = f.read()
        category_name = CATEGORY_MAP[prompt_components["tgt_app_id"][:2]]
        prompt = prompt.replace("$$$category$$$", category_name)
        prompt = prompt.replace("$$$func$$$", prompt_components["functionality_under_test"])
        prompt = prompt.replace("$$$src_test_desc$$$", prompt_components["src_test_desc"])
        prompt = prompt.replace("$$$stop_condition$$$", prompt_components["stop_condition"])
        prompt = prompt.replace("$$$event_history_desc$$$", prompt_components["event_history_desc"])
        prompt = prompt.replace("$$$page_desc$$$", prompt_components["page_desc"])
        answer = LLMUtil.query_with_retry(prompt, screenshot_path, model_name=model_name)
        with open(query_save_path, "a") as f:
            f.write("\n--------------------CC Prompt-------------------\n")
            f.write(prompt)
            f.write("\n--------------------End of CC Prompt-------------------\n")
            f.write("\n--------------------CC Answer-------------------\n")
            f.write(answer)
            f.write("\n--------------------End of CC Answer-------------------\n")
            
        completeness, extra_step_tip = LLMUtil.extract_answer_components(answer, "cc")
        return completeness, extra_step_tip
    
    @staticmethod
    def seek_oracle_widget(src_oracle_event, all_widgets, target_pkg, target_act):
        action = src_oracle_event["action"]
        executable_event = {}
        if "wait_until_text_presence" in action:
            # search for the widget with the same "text" in page layout
            for widget in all_widgets:
                if widget["text"] == src_oracle_event["text"]:
                    executable_event['class'] = widget['class']
                    executable_event['resource-id'] = widget['resource-id']
                    executable_event['text'] = widget['text']
                    executable_event['content-desc'] = widget['content-desc']
                    executable_event['clickable'] = widget['clickable']
                    executable_event['password'] = widget.get('password', 'false')
                    executable_event['package'] = target_pkg
                    executable_event['activity'] = target_act
                    executable_event['ignorable'] = 'false'
                    executable_event['event_type'] = 'oracle'
                    executable_event['bounds'] = widget['bounds']
                    executable_event['action'] = action
                    executable_event['action'][3] = widget['text']
                    break
            if not executable_event:
                # use fuzzy matching
                for widget in all_widgets:
                    if widget["text"] and (src_oracle_event["text"] in widget["text"] or widget["text"] in src_oracle_event["text"]):
                        executable_event['class'] = widget['class']
                        executable_event['resource-id'] = widget['resource-id']
                        executable_event['text'] = widget['text']
                        executable_event['content-desc'] = widget['content-desc']
                        executable_event['clickable'] = widget['clickable']
                        executable_event['password'] = widget.get('password', 'false')
                        executable_event['package'] = target_pkg
                        executable_event['activity'] = target_act
                        executable_event['ignorable'] = 'false'
                        executable_event['event_type'] = 'oracle'
                        executable_event['action'] = action
                        executable_event['action'][3] = widget['text']
                        executable_event['bounds'] = widget['bounds']
                        break
                        
        elif "wait_until_element_presence" in action:
            signal_attr = action[2]
            second_signal_attr = None
            if signal_attr == 'xpath':
                if "@content-desc" in action[3]:
                    signal_attr = 'content-desc'
                if "@text" in action[3]:
                    signal_attr = 'text'
            if not signal_attr:
                second_signal_attr = 'bounds'
                # deal with LLM-generated signal attribute
                if 'text' in src_oracle_event and src_oracle_event['text']:
                    signal_attr = 'text'
                elif 'content-desc' in src_oracle_event and src_oracle_event['content-desc']:
                    signal_attr = 'content-desc'
                elif 'resource-id' in src_oracle_event and src_oracle_event['resource-id']:
                    signal_attr = 'resource-id'
            for widget in all_widgets:
                if signal_attr in widget and src_oracle_event[signal_attr] == widget[signal_attr]:
                    if second_signal_attr == 'bounds' and 'bounds' in widget and src_oracle_event['bounds'] != widget['bounds']:
                        continue
                    executable_event['class'] = widget['class']
                    executable_event['resource-id'] = widget['resource-id']
                    executable_event['text'] = widget['text']
                    executable_event['content-desc'] = widget['content-desc']
                    executable_event['clickable'] = widget['clickable']
                    executable_event['password'] = widget.get('password', 'false')
                    executable_event['package'] = target_pkg
                    executable_event['activity'] = target_act
                    executable_event['ignorable'] = 'false'
                    executable_event['event_type'] = 'oracle'
                    executable_event['action'] = [action[0], action[1], signal_attr, widget[signal_attr]]
                    executable_event['bounds'] = widget['bounds']
            if not executable_event:
                # use fuzzy matching
                for widget in all_widgets:
                    if signal_attr in widget and widget[signal_attr] and (src_oracle_event[signal_attr] in widget[signal_attr] or widget[signal_attr] in src_oracle_event[signal_attr]):
                        executable_event['class'] = widget['class']
                        executable_event['resource-id'] = widget['resource-id']
                        executable_event['text'] = widget['text']
                        executable_event['content-desc'] = widget['content-desc']
                        executable_event['clickable'] = widget['clickable']
                        executable_event['password'] = widget.get('password', 'false')
                        executable_event['package'] = target_pkg
                        executable_event['activity'] = target_act
                        executable_event['ignorable'] = 'false'
                        executable_event['event_type'] = 'oracle'
                        executable_event['action'] = [action[0], action[1], signal_attr, widget[signal_attr]]
                        executable_event['bounds'] = widget['bounds']
        elif "wait_until_text_invisible" in action:
            executable_event['class'] = ""
            executable_event['resource-id'] = ""
            executable_event['text'] = src_oracle_event['text']
            executable_event['content-desc'] = ""
            executable_event['clickable'] = ""
            executable_event['password'] = 'false'
            executable_event['action'] = action
            executable_event['package'] = target_pkg
            executable_event['activity'] = target_act
            executable_event['ignorable'] = 'false'
            executable_event['event_type'] = 'oracle'
            executable_event['action'] = action
        return executable_event
    
    @staticmethod
    def query_oracle(prompt_components, merged_screen_save_path, leaf_widgets, query_save_path, model_name="gpt-4o-mini"):
        prompt_template_file = "Planner/prompt_oracle_presence.txt"
        with open(prompt_template_file, "r") as f:
            prompt = f.read()
        category_name = CATEGORY_MAP[prompt_components["tgt_app_id"][:2]]
        prompt = prompt.replace("$$$category$$$", category_name)
        prompt = prompt.replace("$$$func$$$", prompt_components["functionality_under_test"])
        prompt = prompt.replace("$$$src_test_desc$$$", prompt_components["src_test_desc"])
        prompt = prompt.replace("$$$stop_condition$$$", prompt_components["stop_condition"])
        candidate_prompt = ''
        candidates = []
        for candidate in leaf_widgets:
            # preserve only the semantic attributes
            new_candidate = ScreenUtil.extract_semantic_attrs(candidate)
            candidates.append(deepcopy(new_candidate))
        for i, candidate in enumerate(candidates):
            candidate_prompt += f"{i+1}. {candidate}\n"
        prompt = prompt.replace("$$$candidates$$$", candidate_prompt)
        answer = LLMUtil.query_with_retry(prompt, merged_screen_save_path, model_name=model_name)
        with open(query_save_path, "a") as f:
            f.write("\n--------------------Oracle Prompt-------------------\n")
            f.write(prompt)
            f.write("\n--------------------End of Oracle Prompt-------------------\n")
            f.write("\n--------------------Oracle Answer-------------------\n")
            f.write(answer)
            f.write("\n--------------------End of Oracle Answer-------------------\n")
            
        try:
            widget_id = LLMUtil.extract_answer_components(answer, "oracle")
        except:
            format = prompt.split("strictly follow this format:")[1]
            refomat_prompt_file = "Planner/reformat.txt"
            with open(refomat_prompt_file, "r") as f:
                refomat_prompt = f.read()
            refomat_prompt = refomat_prompt.replace("$$$answer$$$", answer)
            refomat_prompt = refomat_prompt.replace("$$$format$$$", format)
            new_answer = LLMUtil.query_with_retry(refomat_prompt, None, model_name=model_name)
            widget_id = LLMUtil.extract_answer_components(new_answer, "oracle_presence")
        return widget_id
    
    @staticmethod
    def get_step_desc(prompt_components, feedback_context, feedback_screenshot_path, query_save_path, model_name="gpt-4o-mini"):
        prompt_template_file = "Planner/prompt_feedback.txt"
        with open(prompt_template_file, "r") as f:
            prompt = f.read()
        category_name = CATEGORY_MAP[prompt_components["tgt_app_id"][:2]]
        prompt = prompt.replace("$$$category$$$", category_name)
        prompt = prompt.replace("$$$func$$$", prompt_components["functionality_under_test"])
        prompt = prompt.replace("$$$src_test_desc$$$", prompt_components["src_test_desc"])
        if prompt_components["event_history_desc"]:
            prompt = prompt.replace("$$$event_history_desc$$$", f"I have opened te app and executed the following interactions:\n {prompt_components['event_history_desc']}. ")
        else:
            prompt = prompt.replace("$$$event_history_desc$$$", "I have just opened the app and haven't executed any interactions. ")
        prompt = prompt.replace("$$$skeleton_completeness$$$", feedback_context[0])
        prompt = prompt.replace("$$$step_status$$$", feedback_context[1])
        current_interaction = {}
        current_interaction = ScreenUtil.extract_semantic_attrs(prompt_components["current_interaction"])
        prompt = prompt.replace("$$$current_interaction$$$", str(current_interaction))

        # get input values
        answer = LLMUtil.query_with_retry(prompt, feedback_screenshot_path, model_name=model_name)
        with open(query_save_path, "a") as f:
            f.write("\n--------------------Feedback Prompt-------------------\n")
            f.write(prompt)
            f.write("\n--------------------End of Feedback Prompt-------------------\n")
            f.write("\n--------------------Feedback Answer-------------------\n")
            f.write(answer)
            f.write("\n--------------------End of Feedback Answer-------------------\n")
        try:
            step_desc, flag_accept, reject_reason = LLMUtil.extract_answer_components(answer, "feedback")
        except:
            format = prompt.split("strictly follow this format:")[1]
            refomat_prompt_file = "Planner/reformat.txt"
            with open(refomat_prompt_file, "r") as f:
                refomat_prompt = f.read()
            refomat_prompt = refomat_prompt.replace("$$$answer$$$", answer)
            refomat_prompt = refomat_prompt.replace("$$$format$$$", format)
            new_answer = LLMUtil.query_with_retry(refomat_prompt, None, model_name=model_name)
            with open(query_save_path, "a") as f:
                f.write("\n--------------------Reformat Feedback Prompt-------------------\n")
                f.write(refomat_prompt)
                f.write("\n--------------------End of Reformat Feedback Prompt-------------------\n")
                f.write("\n--------------------Reformat Feedback Answer-------------------\n")
                f.write(new_answer)
                f.write("\n--------------------End of Reformat Feedback Answer----------------\n")
            try:
                step_desc, flag_accept, reject_reason= LLMUtil.extract_answer_components(new_answer, "feedback")
            except:
                step_desc, flag_accept, reject_reason= None, None, None
        return step_desc
        
    @staticmethod
    def get_feedback(prompt_components, feedback_context, feedback_screenshot_path, query_save_path, model_name="gpt-4o-mini"):
        prompt_template_file = "Planner/prompt_feedback.txt"
        with open(prompt_template_file, "r") as f:
            prompt = f.read()
        category_name = CATEGORY_MAP[prompt_components["tgt_app_id"][:2]]
        prompt = prompt.replace("$$$category$$$", category_name)
        prompt = prompt.replace("$$$func$$$", prompt_components["functionality_under_test"])
        prompt = prompt.replace("$$$src_test_desc$$$", prompt_components["src_test_desc"])
        if prompt_components["event_history_desc"]:
            prompt = prompt.replace("$$$event_history_desc$$$", f"I have opened te app and executed the following interactions:\n {prompt_components['event_history_desc']}. ")
        else:
            prompt = prompt.replace("$$$event_history_desc$$$", "I have just opened the app and haven't executed any interactions. ")
        prompt = prompt.replace("$$$skeleton_completeness$$$", feedback_context[0])
        prompt = prompt.replace("$$$step_status$$$", feedback_context[1])
        current_interaction = {}
        current_interaction = ScreenUtil.extract_semantic_attrs(prompt_components["current_interaction"])
        prompt = prompt.replace("$$$current_interaction$$$", str(current_interaction))

        # get input values
        answer = LLMUtil.query_with_retry(prompt, feedback_screenshot_path, model_name=model_name)
        with open(query_save_path, "a") as f:
            f.write("\n--------------------Feedback Prompt-------------------\n")
            f.write(prompt)
            f.write("\n--------------------End of Feedback Prompt-------------------\n")
            f.write("\n--------------------Feedback Answer-------------------\n")
            f.write(answer)
            f.write("\n--------------------End of Feedback Answer-------------------\n")
        try:
            step_desc, flag_accept, reject_reason = LLMUtil.extract_answer_components(answer, "feedback")
        except:
            format = prompt.split("strictly follow this format:")[1]
            refomat_prompt_file = "Planner/reformat.txt"
            with open(refomat_prompt_file, "r") as f:
                refomat_prompt = f.read()
            refomat_prompt = refomat_prompt.replace("$$$answer$$$", answer)
            refomat_prompt = refomat_prompt.replace("$$$format$$$", format)
            new_answer = LLMUtil.query_with_retry(refomat_prompt, None, model_name=model_name)
            with open(query_save_path, "a") as f:
                f.write("\n--------------------Reformat Feedback Prompt-------------------\n")
                f.write(refomat_prompt)
                f.write("\n--------------------End of Reformat Feedback Prompt-------------------\n")
                f.write("\n--------------------Reformat Feedback Answer-------------------\n")
                f.write(new_answer)
                f.write("\n--------------------End of Reformat Feedback Answer----------------\n")
            try:
                step_desc, flag_accept, reject_reason= LLMUtil.extract_answer_components(new_answer, "feedback")
            except:
                step_desc, flag_accept, reject_reason= None, None, None
        suggestion = None
        if flag_accept == False:
            # query again for suggestions
            prompt_template_file = "Planner/prompt_feedback_suggestion.txt"
            screen_before_path = feedback_screenshot_path.replace("_feedback", "").replace("feedback_", "")
            with open(prompt_template_file, "r") as f:
                prompt = f.read()
            category_name = CATEGORY_MAP[prompt_components["tgt_app_id"][:2]]
            prompt = prompt.replace("$$$category$$$", category_name)
            prompt = prompt.replace("$$$func$$$", prompt_components["functionality_under_test"])
            prompt = prompt.replace("$$$src_test_desc$$$", prompt_components["src_test_desc"])
            if prompt_components["event_history_desc"]:
                prompt = prompt.replace("$$$event_history_desc$$$", f"I have opened te app and executed the following interactions:\n {prompt_components['event_history_desc']}. ")
            else:
                prompt = prompt.replace("$$$event_history_desc$$$", "I have just opened the app and haven't executed any interactions. ")
            prompt = prompt.replace("$$$skeleton_completeness$$$", feedback_context[0])
            prompt = prompt.replace("$$$step_status$$$", feedback_context[1])
            current_interaction = {}
            current_interaction = ScreenUtil.extract_semantic_attrs(prompt_components["current_interaction"])
            prompt = prompt.replace("$$$current_interaction$$$", str(current_interaction))
            prompt = prompt.replace("$$$reject_reason$$$", reject_reason)
            suggestion_answer = LLMUtil.query_with_retry(prompt, screen_before_path, model_name=model_name)
            suggestion = LLMUtil.extract_answer_components(suggestion_answer, "feedback_suggestion")
            with open(query_save_path, "a") as f:
                f.write("\n--------------------Feedback Suggestion Answer-------------------\n")
                f.write(suggestion_answer)
                f.write("\n--------------------End of Feedback Suggestion Answer-------------------\n")
                
        return step_desc, flag_accept, suggestion
    
    @staticmethod
    def get_feedback_wo_vision(prompt_components, feedback_context, feedback_screenshot_path, query_save_path, model_name="gpt-4o-mini"):
        prompt_template_file = "Planner/prompt_feedback.txt"
        with open(prompt_template_file, "r") as f:
            prompt = f.read()
        category_name = CATEGORY_MAP[prompt_components["tgt_app_id"][:2]]
        prompt = prompt.replace("$$$category$$$", category_name)
        prompt = prompt.replace("$$$func$$$", prompt_components["functionality_under_test"])
        prompt = prompt.replace("$$$src_test_desc$$$", prompt_components["src_test_desc"])
        if prompt_components["event_history_desc"]:
            prompt = prompt.replace("$$$event_history_desc$$$", f"I have opened te app and executed the following interactions:\n {prompt_components['event_history_desc']}. ")
        else:
            prompt = prompt.replace("$$$event_history_desc$$$", "I have just opened the app and haven't executed any interactions. ")
        prompt = prompt.replace("$$$skeleton_completeness$$$", feedback_context[0])
        prompt = prompt.replace("$$$step_status$$$", feedback_context[1])
        current_interaction = {}
        current_interaction = ScreenUtil.extract_semantic_attrs(prompt_components["current_interaction"])
        prompt = prompt.replace("$$$current_interaction$$$", str(current_interaction))

        # get input values
        answer = LLMUtil.query_with_retry(prompt, feedback_screenshot_path, model_name=model_name)
        with open(query_save_path, "a") as f:
            f.write("\n--------------------Feedback Prompt-------------------\n")
            f.write(prompt)
            f.write("\n--------------------End of Feedback Prompt-------------------\n")
            f.write("\n--------------------Feedback Answer-------------------\n")
            f.write(answer)
            f.write("\n--------------------End of Feedback Answer-------------------\n")
        try:
            step_desc, flag_accept, reject_reason = LLMUtil.extract_answer_components(answer, "feedback")
        except:
            format = prompt.split("strictly follow this format:")[1]
            refomat_prompt_file = "Planner/reformat.txt"
            with open(refomat_prompt_file, "r") as f:
                refomat_prompt = f.read()
            refomat_prompt = refomat_prompt.replace("$$$answer$$$", answer)
            refomat_prompt = refomat_prompt.replace("$$$format$$$", format)
            new_answer = LLMUtil.query_with_retry(refomat_prompt, None, model_name=model_name)
            with open(query_save_path, "a") as f:
                f.write("\n--------------------Reformat Feedback Prompt-------------------\n")
                f.write(refomat_prompt)
                f.write("\n--------------------End of Reformat Feedback Prompt-------------------\n")
                f.write("\n--------------------Reformat Feedback Answer-------------------\n")
                f.write(new_answer)
                f.write("\n--------------------End of Reformat Feedback Answer----------------\n")
            try:
                step_desc, flag_accept, reject_reason= LLMUtil.extract_answer_components(new_answer, "feedback")
            except:
                step_desc, flag_accept, reject_reason= None, None, None
        suggestion = None
        if flag_accept == False:
            # query again for suggestions
            prompt_template_file = "Planner/prompt_feedback_suggestion.txt"
            screen_before_path = None
            with open(prompt_template_file, "r") as f:
                prompt = f.read()
            category_name = CATEGORY_MAP[prompt_components["tgt_app_id"][:2]]
            prompt = prompt.replace("$$$category$$$", category_name)
            prompt = prompt.replace("$$$func$$$", prompt_components["functionality_under_test"])
            prompt = prompt.replace("$$$src_test_desc$$$", prompt_components["src_test_desc"])
            if prompt_components["event_history_desc"]:
                prompt = prompt.replace("$$$event_history_desc$$$", f"I have opened te app and executed the following interactions:\n {prompt_components['event_history_desc']}. ")
            else:
                prompt = prompt.replace("$$$event_history_desc$$$", "I have just opened the app and haven't executed any interactions. ")
            prompt = prompt.replace("$$$skeleton_completeness$$$", feedback_context[0])
            prompt = prompt.replace("$$$step_status$$$", feedback_context[1])
            current_interaction = {}
            current_interaction = ScreenUtil.extract_semantic_attrs(prompt_components["current_interaction"])
            prompt = prompt.replace("$$$current_interaction$$$", str(current_interaction))
            prompt = prompt.replace("$$$reject_reason$$$", reject_reason)
            suggestion_answer = LLMUtil.query_with_retry(prompt, screen_before_path, model_name=model_name)
            suggestion = LLMUtil.extract_answer_components(suggestion_answer, "feedback_suggestion")
            with open(query_save_path, "a") as f:
                f.write("\n--------------------Feedback Suggestion Answer-------------------\n")
                f.write(suggestion_answer)
                f.write("\n--------------------End of Feedback Suggestion Answer-------------------\n")
                
        return step_desc, flag_accept, suggestion
    
    @staticmethod
    def get_reflection(prompt_components, screenshot_path, correct_events, query_save_path, model_name="gpt-4o-mini"):
        prompt_template_file = "Planner/prompt_reflection.txt"
        with open(prompt_template_file, "r") as f:
            prompt = f.read()
        category_name = CATEGORY_MAP[prompt_components["tgt_app_id"][:2]]
        prompt = prompt.replace("$$$category$$$", category_name)
        prompt = prompt.replace("$$$func$$$", prompt_components["functionality_under_test"])
        prompt = prompt.replace("$$$src_test_desc$$$", prompt_components["src_test_desc"])
        prompt = prompt.replace("$$$event_history_desc$$$", prompt_components['event_history_desc'])
        if correct_events:
            prompt += "The following interactions are correct, do not choose any of them as the Late Earlest Interaction:\n"
            prompt += "\n".join([f"Interaction {str(event)}" for event in correct_events])
        answer = LLMUtil.query_with_retry(prompt, screenshot_path, model_name=model_name)
        with open(query_save_path, "a") as f:
            f.write("\n--------------------Reflection Prompt-------------------\n")
            f.write(prompt)
            f.write("\n--------------------End of Reflection Prompt-------------------\n")
            f.write("\n--------------------Reflection Answer-------------------\n")
            f.write(answer)
            f.write("\n--------------------End of Reflection Answer-------------------\n")
        try:
            wrong_step_id = LLMUtil.extract_answer_components(answer, "reflection")
        except:
            format = prompt.split("strictly follow this format:")[1]
            refomat_prompt_file = "Planner/reformat.txt"
            with open(refomat_prompt_file, "r") as f:
                refomat_prompt = f.read()
            refomat_prompt = refomat_prompt.replace("$$$answer$$$", answer)
            refomat_prompt = refomat_prompt.replace("$$$format$$$", format)
            new_answer = LLMUtil.query_with_retry(refomat_prompt, None, model_name=model_name)
            try:
                wrong_step_id = LLMUtil.extract_answer_components(new_answer, "reflection")
            except:
                wrong_step_id = None
        return wrong_step_id
    
    @staticmethod
    def get_routine_reflection(prompt_components, screenshot_path, correct_events, query_save_path, model_name="gpt-4o-mini"):
        prompt_template_file = "Planner/prompt_routine_reflection.txt"
        with open(prompt_template_file, "r") as f:
            prompt = f.read()
        category_name = CATEGORY_MAP[prompt_components["tgt_app_id"][:2]]
        prompt = prompt.replace("$$$category$$$", category_name)
        prompt = prompt.replace("$$$func$$$", prompt_components["functionality_under_test"])
        prompt = prompt.replace("$$$src_test_desc$$$", prompt_components["src_test_desc"])
        prompt = prompt.replace("$$$event_history_desc$$$", prompt_components['event_history_desc'])
        if correct_events:
            prompt += "The following interactions are correct, do not choose any of them as the Late Earlest Interaction:\n"
            prompt += "\n".join([f"Interaction {str(event)}" for event in correct_events])
        answer = LLMUtil.query_with_retry(prompt, screenshot_path, model_name=model_name)
        with open(query_save_path, "a") as f:
            f.write("\n--------------------Reflection Prompt-------------------\n")
            f.write(prompt)
            f.write("\n--------------------End of Reflection Prompt-------------------\n")
            f.write("\n--------------------Reflection Answer-------------------\n")
            f.write(answer)
            f.write("\n--------------------End of Reflection Answer-------------------\n")
        try:
            wrong_step_id = LLMUtil.extract_answer_components(answer, "reflection")
        except:
            format = prompt.split("strictly follow this format:")[1]
            refomat_prompt_file = "Planner/reformat.txt"
            with open(refomat_prompt_file, "r") as f:
                refomat_prompt = f.read()
            refomat_prompt = refomat_prompt.replace("$$$answer$$$", answer)
            refomat_prompt = refomat_prompt.replace("$$$format$$$", format)
            new_answer = LLMUtil.query_with_retry(refomat_prompt, None, model_name=model_name)
            try:
                wrong_step_id = LLMUtil.extract_answer_components(new_answer, "reflection")
            except:
                wrong_step_id = None
        return wrong_step_id