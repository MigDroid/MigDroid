# Note: The openai-python library support for Azure OpenAI is in preview.
import openai
import os
import re
import base64

app_category = ["Browser", "To Do List", "Shopping", "Email", "Tip Calculator"]


class LLMUtil:
    """
    This class provides utility functions for calling Large Language Model.
    """
    @staticmethod
    def encode_image(image_path):
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")

    @staticmethod
    def call_qwen(text, image_path=None, model_name="qwen-vl-plus"):
        client = openai.OpenAI(
            api_key=os.getenv("YOUR_API_KEY"),
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
        if image_path:
            base64_image = LLMUtil.encode_image(image_path)
            image_type = f"image/{image_path.split('.')[-1]}"
            msg = [
                {"type": "text", "text": text},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{image_type};base64,{base64_image}", "detail": "high"},
                },
            ]
        else:
            msg = text
        response = client.chat.completions.create(
            model=model_name, 
            messages=[{"role": "user", "content": msg}]
        )
        return response.choices[0].message.content

    @staticmethod
    def call_gpt(text, image_path=None, model_name="gpt-4o-mini"):
        print("Start calling gpt...")
        client = openai.OpenAI(
            api_key=os.getenv("YOUR_API_KEY")
        )
        if image_path:
            base64_image = LLMUtil.encode_image(image_path)
            image_type = f"image/{image_path.split('.')[-1]}"
            msg = [
                {"type": "text", "text": text},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{image_type};base64,{base64_image}", "detail": "high"},
                },
            ]
        else:
            msg = text
        response = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": msg}],
            temperature=0,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0,
            seed=0,
            stop=None,
        )
        return response.choices[0].message.content
    
    @staticmethod
    def query_with_retry(text, image_path=None, model_name="gpt-4o-mini", retry=3):
        if "gpt" in model_name.lower():
            call_llm = LLMUtil.call_gpt
        elif "qwen" in model_name.lower():
            call_llm = LLMUtil.call_qwen
        else:
            raise Exception("Error: model not supported, check your model name.")

        print("Start Querying...")
        for i in range(retry):
            answer = call_llm(text, image_path, model_name)
            if answer:
                break
        if answer is None:
            print("Query failed!")
            for i in range(retry):
                answer = call_llm(text, image_path, model_name)
                if answer:
                    break
        print("Finish Querying...")
        print("Answer:", answer)
        return answer

    @staticmethod
    def extract_answer_components(answer, answer_type):
        if answer_type == "stage1_test_desc":
            is_part = re.split(r"interaction steps:", answer, flags=re.IGNORECASE)[1]
            interaction_steps = re.split(r"stop condition:", is_part, flags=re.IGNORECASE)[0].strip()
            stop_condition = re.split(r"stop condition:", is_part, flags=re.IGNORECASE)[1]
            stop_condition = re.split(r"functionality under test:", stop_condition, flags=re.IGNORECASE)[0].strip()
            functionality_under_test = re.split(r"functionality under test:", is_part, flags=re.IGNORECASE)[1].strip()
            return interaction_steps, stop_condition, functionality_under_test
        elif answer_type == "grouped_stage1_test_desc":
            map_from_interaction_to_semantic = []
            ss_part = re.split(r"semantic steps:", answer, flags=re.IGNORECASE)[1]
            semantic_steps = re.split(r"stop condition:", ss_part, flags=re.IGNORECASE)[0].strip()
            stop_condition = re.split(r"stop condition:", ss_part, flags=re.IGNORECASE)[1]
            stop_condition = re.split(r"functionality under test:", stop_condition, flags=re.IGNORECASE)[0].strip()
            functionality_under_test = re.split(r"functionality under test:", ss_part, flags=re.IGNORECASE)[1].strip()
            # extract the mapping from semantic steps to interaction steps
            # split the semantic steps into lines
            ss_lines = semantic_steps.split("\n")
            ss_desc = ''
            for line in ss_lines:
                # delete all * in the line
                test_line = re.sub(r"\*", "", line).strip()
                print(test_line)
                if not test_line:
                    continue
                step_desc = re.split(r"this step is grouped from", line, flags=re.IGNORECASE)[0].strip()
                ss_desc += step_desc + "\n"
                interaction_step_map = re.split(r"this step is grouped from", line, flags=re.IGNORECASE)[1].strip()
                # get the digits in the interaction step map, and make them into a list of integers
                interaction_step_map = [int(s) for s in re.findall(r"\b\d+\b", interaction_step_map)]
                map_from_interaction_to_semantic.append(interaction_step_map)
            return ss_desc, stop_condition, functionality_under_test, map_from_interaction_to_semantic
        elif answer_type == "key_test_desc":
            steps_part = re.split(r"new semantic steps:", answer, flags=re.IGNORECASE)[1]
            steps_part = re.split(r"key step analysis:", steps_part, flags=re.IGNORECASE)[0].strip()
            key_id_part = re.split(r"key step ids:", answer, flags=re.IGNORECASE)[1]
            key_id_part = re.split(r"peripheral step ids:", key_id_part, flags=re.IGNORECASE)[0].strip()
            # get the numbers in the key id part, and make them into a list of integers
            key_ids = [int(s) for s in re.findall(r"\b\d+\b", key_id_part)]
            peripheral_id_part = re.split(r"peripheral step ids:", answer, flags=re.IGNORECASE)[1]
            peripheral_id_part = re.split(r"stop condition:", peripheral_id_part, flags=re.IGNORECASE)[0].strip()
            # get the numbers in the peripheral id part, and make them into a list of integers
            peripheral_ids = [int(s) for s in re.findall(r"\b\d+\b", peripheral_id_part)]
            steps = steps_part.split("\n")
            for i, step in enumerate(steps):
                # delete the leading number and the dot like "1. ", only delete the first one, and only delete it if it starts with a number
                step = step.strip()
                step = re.sub(r"^\d+\.\s", "", step)
                
                if i+1 in key_ids:
                    steps[i] = f"{i+1}. Key Step: {step}"
                elif i+1 in peripheral_ids:
                    steps[i] = f"{i+1}. Peripheral Step: {step}"
                else:
                    raise Exception("Error: step id not found in key or peripheral step ids.")
            classified_steps = "\n".join(steps)
                
            stop_condition = re.split(r"stop condition:", answer, flags=re.IGNORECASE)[1]
            stop_condition = re.split(r"functionality under test:", stop_condition, flags=re.IGNORECASE)[0].strip()
            functionality_under_test = re.split(r"functionality under test:", answer, flags=re.IGNORECASE)[1].strip()
            return classified_steps, stop_condition, functionality_under_test
        elif answer_type == "ag":
            # Extract widget ID
            # Use case-insensitive splitting for "widget id" and "selected action"
            widget_id_part = re.split(r"widget id:", answer, flags=re.IGNORECASE)[1]
            widget_id_part = re.split(r"selected action:", widget_id_part, flags=re.IGNORECASE)[0].strip()
            widget_id = int(re.sub(r"\D+", "", widget_id_part))

            # Extract action
            action_part = re.split(r"selected action:", answer, flags=re.IGNORECASE)[1]
            action_part = re.split(r"input value:", action_part, flags=re.IGNORECASE)[0].strip()
            action = re.sub(r"^\W+|\W+$", "", action_part.split("\n")[0])

            # Extract input value
            input_value = re.split(r"input value:", answer, flags=re.IGNORECASE)[1].strip().split("\n")[0]
            if input_value.startswith("[") and input_value.endswith("]"):
                input_value = input_value[1:-1]
            event_info = [widget_id, action, input_value]
            return event_info
        elif answer_type == "ag_feedback":
            # extract things after Skeleton step completeness analysis:, and before "Completed/Achieved Steps:"
            skeleton_completeness = re.split(r"Skeleton step completeness analysis:", answer, flags=re.IGNORECASE)[1]
            skeleton_completeness = re.split(r"Completed/Achieved Steps:", skeleton_completeness, flags=re.IGNORECASE)[0].strip()
            step_status = "Step in progress:" + re.split(r"Step in progress:", answer, flags=re.IGNORECASE)[1]
            step_status = re.split(r"Interaction Reasoning:", step_status, flags=re.IGNORECASE)[0].strip()
            feed_context = [skeleton_completeness, step_status]
            return feed_context
        elif answer_type == "cc":
            stop_flag = False
            extra_step_tip = None
            answer = answer.lower()
            remain_steps = re.split(r"remaining steps:", answer, flags=re.IGNORECASE)[1].strip()
            remain_steps = re.split(r"stop condition:", remain_steps, flags=re.IGNORECASE)[0].strip()
            # if any(word in remain_steps for word in ["type", "input", "enter"]):
            #     return False
            completeness = answer.split("time to check stop condition:")[1].strip()
            if 'yes' in completeness:
                stop_flag = True
            extra_step = re.split(r"Extra Steps Needed to Go to Anchor GUI Page:", answer, flags=re.IGNORECASE)[1].strip()
            extra_step = re.split(r"time to check stop condition:", extra_step, flags=re.IGNORECASE)[0].strip()
            if not 'no' in extra_step:
                stop_flag = False
                extra_step_tip = "We have triggered the target functionality successfully, now we need to go to the anchor page so that the anchor widget corresponding to the stop condition can be checked. Tell me how to go to the anchor page."
            return stop_flag, extra_step_tip
        elif answer_type == "feedback":
            # Extract Step Description
            step_desc = re.split(r"interaction description:", answer, flags=re.IGNORECASE)[1].strip().split("\n")[0]
            flag_accept = re.split(r"whether to accept:", answer, flags=re.IGNORECASE)[1].strip().split("\n")[0]
            if 'yes' in flag_accept.lower():
                flag_accept = True
            else:
                flag_accept = False
            reject_reason = None
            if not flag_accept:
                reject_reason = re.split(r"Reject Reasoning:", answer, flags=re.IGNORECASE)[1].strip().split("\n")[0]
            return step_desc, flag_accept, reject_reason
        elif answer_type == "feedback_suggestion":
            suggestion = re.split(r"Interaction Suggestions:", answer, flags=re.IGNORECASE)[1].strip()
            return suggestion
        elif answer_type == "reflection":
            wrong_step = re.split(r"Earliest wrong interaction:", answer, flags=re.IGNORECASE)[1].strip().split("\n")[0]
            wrong_step_id = int(re.sub(r"\D+", "", wrong_step))
            return wrong_step_id
        elif answer_type == "oracle_presence":
            widget_id = re.split(r"Anchor Widget ID:", answer, flags=re.IGNORECASE)[1].strip().split("\n")[0]
            widget_id = int(re.sub(r"\D+", "", widget_id))
            return widget_id
        else:
            raise Exception("Error: answer type not supported, check your answer type.")