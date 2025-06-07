from csv import DictReader
import json
import time
import os
import sys
import traceback

# local import

from Runner_u2 import Runner_u2
from const import TEST_REPO

# test_id = 'a56b51'

attrs_to_repair = {"clickable"}
attrs_to_add = {"bounds"}
# get test_id from the args in the command line
test_id = sys.argv[1]
udid = sys.argv[2]
app_id = test_id[:3]
task_id = test_id[-3:]

category = app_id[:2]
configfile = f'{TEST_REPO}/{category}/{category}.config'
testfile = f'{TEST_REPO}/{category}/{task_id}/base/{app_id}.json'
temp_screen_save_dir = f'TestAugmenter/src_screens_annoted/{category}/{task_id}/base/{app_id}_screens'
pkg, act, no_reset = '', '', False

repaired_testfile = f'test_repo/{category}/{task_id}/base/{app_id}.json'

# if os.path.exists(temp_screen_save_dir):
#     print("Directory already exists, skipping...")
#     sys.exit()
# else:
#     os.makedirs(temp_screen_save_dir)

if not os.path.exists(temp_screen_save_dir):
    os.makedirs(temp_screen_save_dir)

print("test_file: ", testfile)

with open(configfile, newline='') as cf:
    reader = DictReader(cf)
    for row in reader:
        if row['aid'] == app_id:
            pkg, act = row['package'], row['activity']
            # check if row has reset field
            if 'reset' in row:
                no_reset = (row['reset'] != 'true')
            else:
                no_reset = False
            break


# read the test events
with open(testfile, 'r') as f:
    test_events = json.load(f)

print("pkg: ", pkg)
print("act: ", act)
print("no_reset: ", no_reset)

runner = Runner_u2(app_id, pkg, udid=udid, no_reset=no_reset)
time.sleep(5)

i = 0
index_non_affix = 0
element_info_to_save = None
for event in test_events:
    i += 1
    event["tid"] = app_id
    if "affix" not in event:
        index_non_affix += 1
    print("Action Number: ", i)
    print("act: ", act)
    print(event)
    try:
        if "affix" not in event:
            if i == 1 or ("affix" in test_events[i-2] and test_events[i-2]["affix"] == "prefix"):
                runner.get_screenshot_as_file(os.path.join(temp_screen_save_dir, "0.png"))
        if event["event_type"] == "gui":
            element = runner.get_element(event)
            if element:
                event["clickable"] = str(element.info["clickable"]) if "clickable" in element.info else "false"
                event["long_clickable"] = str(element.info["longClickable"]) if "longClickable" in element.info else "false"
                if "bounds" not in event:
                    event["bounds"] = element.info["bounds"] if "bounds" in element.info else None
        
        if event["event_type"] == "gui" and "bounds" in event:
            screen_path = os.path.join(temp_screen_save_dir, f"{index_non_affix-1}.png")
            output_path = screen_path.replace('.png', '_annotated.png')
            runner.annotate_screenshot(screen_path, output_path, event['bounds'])
        
        # save invisibel element in advance
        # for index_invisible in range(i, len(test_events)):
        #     if "invisible" in test_events[index_invisible]["action"][0]:
        #         element_to_save = runner.get_element(test_events[index_invisible])
        #         if element_to_save:
        #             element_info_to_save = element_to_save.info
        #             print("element_info_to_save: ", element_info_to_save)
        #         break
            
        runner.perform_actions([event], reset=False)
        time.sleep(2)
        
        if "affix" not in event:
            screen_path = os.path.join(temp_screen_save_dir, f"{index_non_affix}.png")
            runner.get_screenshot_as_file(screen_path)
        # uodate change made by the last action, so that it looks instant
        if event["event_type"] == "oracle":
            screen_path = os.path.join(temp_screen_save_dir, f"{index_non_affix-1}.png")
            runner.get_screenshot_as_file(screen_path)
        
        if "presence" in event["action"][0]:
            element = runner.get_element(event)
            print("presence element: ", element.info)
            if element:
                event["clickable"] = str(element.info["clickable"]) if "clickable" in element.info else "false"
                event["long_clickable"] = str(element.info["longClickable"]) if "longClickable" in element.info else "false"
                if "bounds" not in event:
                    event["bounds"] = element.info["bounds"] if "bounds" in element.info else None
            if "bounds" in event:
                screen_path = os.path.join(temp_screen_save_dir, f"{index_non_affix}.png")
                output_path = os.path.join(temp_screen_save_dir, f"{index_non_affix-1}_annotated.png")
                runner.annotate_screenshot(screen_path, output_path, event['bounds'])
        # if "invisible" in event["action"][0]:
        #     print("invisible event: ", event)
        #     if element_info_to_save:
        #         event["clickable"] = str(element_info_to_save["clickable"]) if "clickable" in element_info_to_save else "false"
        #         event["long_clickable"] = str(element_info_to_save["longClickable"]) if "longClickable" in element_info_to_save else "false"
        #         if "bounds" not in event:
        #             event["bounds"] = element_info_to_save["bounds"] if "bounds" in element_info_to_save else None
        #     if "bounds" in event:
        #         screen_path = os.path.join(temp_screen_save_dir, f"{index_non_affix-2}.png")
        #         output_path = os.path.join(temp_screen_save_dir, f"{index_non_affix-1}_annotated.png")
        #         runner.annotate_screenshot(screen_path, output_path, event['bounds'])
    except Exception as e:
        print("Exception: ", e)
        # print the stack trace of the exception
        traceback.print_exc()
        # print the line number of the error
        print("Line Number: ", sys.exc_info()[-1].tb_lineno)
        continue

if not os.path.exists(os.path.dirname(repaired_testfile)):
    os.makedirs(os.path.dirname(repaired_testfile))
with open(repaired_testfile, 'w') as f:
    print("repaired_testfile: ", repaired_testfile)
    json.dump(test_events, f, indent=4)
runner.device.app_stop(pkg)