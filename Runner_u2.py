
import time
# local import
from preliminary_study.RecordUtils import RecordUtils
import uiautomator2 as u2
from uiautomator2.xpath import XPathSelector
import cv2
import os

from ScreenUtil import ScreenUtil

class Runner_u2:
    def __init__(self, app_id, pkg, no_reset=False, udid=None):
        self.apk_dir = "subject_apps"
        self.app_id = app_id
        self.apk_path = os.path.join(self.apk_dir, self.app_id[:2], f"{self.app_id}.apk")
        self.device_name = udid
        self.pkg = pkg
        self.no_reset = no_reset
        self.device = u2.connect(udid)
        self.action_interval = 2
        self.activition_interval = 5
        # check if the app is installed
        try:
            self.device.app_info(self.pkg)
        except:
            # install the apk
            self.device.app_install(self.apk_path)
            
        try:
            self.device.app_info(pkg)
        except Exception as e:
            print(f'{pkg} is not installed, exiting...')
            exit(1)

        if no_reset:
            self.restart_app()
        else:
            self.device.app_clear(self.pkg)
            self.device.app_start(self.pkg)
        time.sleep(self.activition_interval)
        # check if the app is running
        running_apps = self.device.app_list_running()
        if pkg not in running_apps:
            print(f'Running apps: {running_apps}')
            print(f'{pkg} is not running, exiting...')
            exit(1)
        
    def restart_app(self):
        self.device.app_stop(self.pkg)
        time.sleep(2)
        self.device.app_start(self.pkg)
        time.sleep(self.activition_interval)

    def perform_actions(self, action_list, require_wait=False, reset=True, cgp=None):
        num_candidates = 0
        if reset:
            if self.no_reset:
                self.device.app_start(self.pkg)  # don't clear app data
            else:
                # self.driver.reset() is deprecated
                self.device.app_clear(self.pkg)
                self.device.app_start(self.pkg)
        time.sleep(self.activition_interval)

        for i, action in enumerate(action_list):
            print(f'Performing action {i+1}/{len(action_list)}')
            print(action)
            time.sleep(self.action_interval)
            if action['class'] == 'SYS_EVENT':
                if action['action'][0] == 'sleep':
                    time.sleep(action['action'][1])
                elif action['action'][0] == 'KEY_BACK':
                    # press back key
                    self.device.press("back")
                elif action['action'][0] == 'restart_app':
                    self.restart_app()
                else:
                    assert False, 'Unknown SYS_EVENT'
                continue

            if action['class'] == 'EMPTY_EVENT':
                continue
            if action['class'] == 'DELETE_LAST_CHAR':
                # to undo unnecessary "enter"
                print('Deleting last character')
                self.device.press("del")
                continue

            if action['action'][0].startswith('wait_until'):
                wait_time, selector_type, selector = action['action'][1:]
                locator = None
                if selector_type == 'xpath':
                    locator_func = lambda: self.device.xpath(selector)
                elif selector_type == 'content-desc':
                    locator_func = lambda: self.device(description=selector)
                elif selector_type == 'id':
                    locator_func = lambda: self.device(resourceId=selector)
                elif selector_type == 'text':
                    locator_func = lambda: self.device(text=selector)
                else:
                    assert locator, "Unknown selector type"
                def wait_for_presence():
                    start_time = time.time()
                    while time.time() - start_time < wait_time:
                        if locator_func().exists:
                            return True
                        time.sleep(0.5)
                    return False

                def wait_for_invisibility():
                    start_time = time.time()
                    while time.time() - start_time < wait_time:
                        if not locator_func().exists:
                            return True
                        time.sleep(0.5)
                    return False
                
                try:
                    if action['action'][0].endswith('presence'):
                        # assert wait_for_presence(), "Element not present within the wait time"
                        if not wait_for_presence() and self.pkg == "com.android.chrome":
                            self.device.click(500, 1000)
                            assert wait_for_presence(), "Element not present within the wait time"
                        if not wait_for_presence() and self.pkg == "com.superproductivity.superproductivity":
                            self.restart_app()
                            time.sleep(self.activition_interval)
                            assert wait_for_presence(), "Element not present within the wait time"
                        assert wait_for_presence(), "Element not present within the wait time"
                    elif action['action'][0].endswith('invisible'):
                        if not wait_for_invisibility():
                            print('Element not invisible within the wait time')
                    else:
                        raise ValueError("Unknown WAIT_UNTIL action")
                except Exception as ex:
                    print('Exception in wait_until')
                    print(ex)
                    print(action)
                    print(self.device.dump_hierarchy())
                    raise AssertionError("Failed WAIT_UNTIL action")
                continue

            # action performed on the selected element
            ele = self.get_element(action)
            if not ele:
                # print page source
                print(self.device.dump_hierarchy())
                # wait for 10 seconds and try again
                print(f'element not found, waiting for 2*{self.activition_interval} sec and trying again')
                time.sleep(2*self.activition_interval)
                self.get_page_source()
                ele = self.get_element(action)
            if not ele:
                print('Perhaps the page hierarchy is not fully loaded, awakening it by clicking the screen')
                # click any non-interactive area
                if self.pkg == "com.opera.mini.native":
                    self.device.click(500, 1000)
                elif self.pkg == "info.plateaukao.einkbro":
                    self.device.click(500, 150)
                elif self.pkg == "com.microsoft.office.outlook":
                    self.device.click(500, 1000)
                time.sleep(self.action_interval)
                self.get_page_source()
                ele = self.get_element(action)   
            if not ele:
                print('element still not found, the page source is:')
                print(self.get_page_source())
                # raise an exception
                raise AssertionError("Element not found")
            
            if ele:
                print(f'element Info: {ele.info}')
                page_source = self.get_page_source()
                num_candidates = len(RecordUtils.get_interactable_widgets(page_source))
                try:
                    if action['action'][0] == 'click':
                        ele.click()
                    elif 'send_keys' in action['action'][0]:
                        value_for_input = action['action'][1]
                        # all possible cases: 'clear_and_send_keys', 'clear_and_send_keys_and_hide_keyboard',
                        # 'send_keys_and_hide_keyboard', 'send_keys_and_enter', 'send_keys'
                        if action['action'][0].startswith('clear'):
                            pass
                        ele.set_text(value_for_input)
                        ele.set_text(value_for_input)
                        if 'enter' in action['action'][0]:
                            self.device.press("enter")
                    elif action['action'][0] == 'swipe_right':
                        rect = ele.info['bounds']
                        width = rect['right'] - rect['left']
                        height = rect['bottom'] - rect['top']
                        start_x, start_y, end_x, end_y = rect['left'] + width / 4, rect['top'] + height / 2, \
                                                        rect['left'] + width * 3 / 4, rect['top'] + height / 2
                        # self.driver.swipe(start_x, start_y, end_x, end_y, duration=0.5)
                        self.device.swipe(start_x, start_y, end_x, end_y, duration=0.2)
                    elif action['action'][0] == 'swipe_left':
                        rect = ele.info['bounds']
                        width = rect['right'] - rect['left']
                        height = rect['bottom'] - rect['top']
                        start_x, start_y, end_x, end_y = rect['left'] + width * 3 / 4, rect['top'] + height / 2, \
                                                        rect['left'] + width / 4, rect['top'] + height / 2
                        self.device.swipe(start_x, start_y, end_x, end_y, duration=0.2)
                    elif action['action'][0] == 'swipe_up':
                        rect = ele.info['bounds']
                        width = rect['right'] - rect['left']
                        height = rect['bottom'] - rect['top']
                        start_x, start_y, end_x, end_y = rect['left'] + width / 2, rect['top'] + height * 3 / 4, \
                                                        rect['left'] + width / 2, rect['top'] + height / 4
                        self.device.swipe(start_x, start_y, end_x, end_y, duration=0.2)
                    elif action['action'][0] == 'swipe_down':
                        rect = ele.info['bounds']
                        width = rect['right'] - rect['left']
                        height = rect['bottom'] - rect['top']
                        start_x, start_y, end_x, end_y = rect['left'] + width / 2, rect['top'] + height / 4, \
                                                        rect['left'] + width / 2, rect['top'] + height * 3 / 4
                        self.device.swipe(start_x, start_y, end_x, end_y, duration=0.2)
                    elif action['action'][0] == 'long_press':
                        # self.driver.tap([(ele.location['x'], ele.location['y'])], duration=1000)
                        ele.long_click(duration=2)
                    else:
                        assert False, "Unknown action to be performed"
                except Exception as ex:
                    print('Exception in perform_actions')
                    print(ex)
                    print(action)
                    print(self.device.dump_hierarchy())
                    raise AssertionError("Failed to perform action")

        if require_wait:
            time.sleep(self.action_interval*2)
        else:
            # time.sleep(self.action_interval/2)
            time.sleep(self.action_interval)
            
        return num_candidates

    def get_element(self, action):
        ele = None
        xpath = None
        try:
            if action.get('xpath'):
                ele = self.device.xpath(action['xpath'])
            if action.get('resource-id'):
                print(f'rid: {action["resource-id"]}')
                # If there's a prefix, add it to the resource-id
                rid = action['id-prefix'] + action['resource-id'] if 'id-prefix' in action and '/' not in action['resource-id'] else action['resource-id']
                # Try to locate by resource-id
                ele = self.device(resourceId=rid)
                if not ele.exists:
                    # Construct xpath with resource-id
                    xpath = f'//{action["class"]}[@resource-id="{rid}"]'
                    ele = self.device.xpath(xpath)
                # Additional filtering by text or content-desc if multiple elements are found
                # ele_count = ele.count if no crash, otherwise, ele_count = 0

                if ele.exists and (action.get('text') or action.get('content-desc')):
                    if action.get('text') and self.get_ele_count(ele) > 1:
                        ele = self.device(resourceId=rid, text=action['text'])
                    elif action.get('content-desc') and self.get_ele_count(ele) > 1:
                        ele = self.device(resourceId=rid, description=action['content-desc'])
            elif action.get('content-desc'):
                # Find element by content description
                ele = self.device(description=action['content-desc'])
                if not ele.exists:
                    xpath = f'//{action["class"]}[@content-desc="{action["content-desc"]}"]'
                    ele = self.device.xpath(xpath)

            elif action.get('text'):
                # Find element by text
                ele = self.device(text=action['text'])
                if not ele.exists:
                    xpath = f'//{action["class"]}[@text="{action["text"]}"]'
                    ele = self.device.xpath(xpath)

            elif action.get('class'):
                # Find element by class name
                ele = self.device(className=action['class'])
                
            elif action.get('naf') == 'true':
                # NAF attribute case
                xpath = f'//{action["class"]}[@NAF="true"]'
                ele = self.device.xpath(xpath)

            # if still multiple elements are found, try to filter by bounds
            if ele and self.get_ele_count(ele) > 1 and action.get('bounds'):
                # print the elements attributes
                print('Multiple elements found, filtering by bounds')
                for e in ele:
                    print("Element info:")
                    print(e.info)
                # action['bounds']: 'bounds': '[0,136][1080,2213]', get the number, not the string
                bounds_str = action['bounds'].strip('[]').split('][')
                bounds = [int(coord) for pair in bounds_str for coord in pair.split(',')]
                left, top, right, bottom = bounds
                for e in ele:
                    e_bounds = e.info.get('bounds', {})
                    e_left, e_top = e_bounds.get('left'), e_bounds.get('top')
                    e_right, e_bottom = e_bounds.get('right'), e_bounds.get('bottom')

                    if (e_left, e_top, e_right, e_bottom) == (left, top, right, bottom):
                        ele = e
                        print('Element found by bounds')
                        print(ele.info)
                        break
                
            if not ele or not ele.exists:
                return None

        except Exception as ex:
            print('Exception in get_ui_element')
            print(ex)
            # print the whole traceback
            import traceback
            traceback.print_exc()
            print(action)
            if xpath:
                print(xpath)
            return None
        
        return ele if ele.exists else None

    def get_ele_count(self, ele):
        ele_count = 0
        try:
            if ele and isinstance(ele, u2.UiObject):
                ele_count = ele.count
            elif ele and isinstance(ele, XPathSelector):
                ele_count = len(ele.all())
        except Exception as ex:
            ele_count = 1
        return ele_count
    
    def get_screenshot_as_file(self, filename):
        return self.device.screenshot(filename)
    
    def get_page_source(self):
        return self.device.dump_hierarchy()
    
    def annotate_screenshot(self, screenshot_path, output_path, bounds):
        img = cv2.imread(screenshot_path)
        left, top, right, bottom = ScreenUtil.parse_bounds(bounds)
        cv2.rectangle(img, (left, top), (right, bottom), (0, 0, 255), 3)
        cv2.imwrite(output_path, img)
        return output_path
    
    def get_current_activity(self):
        return self.device.app_current()['activity']
    
    def get_current_package(self):
        return self.device.app_current()['package']
    
    def stop_server(self):
        # To avoid default browser conflict
        if self.app_id.startswith('a1'):
            self.device.app_uninstall(self.pkg)
        self.device.app_stop(self.pkg)
        return
    
    def check_app_foreground(self):
        is_foreground = self.device.app_current()['package'] == self.pkg
        # if not, but the app is running, switch to the app
        if not is_foreground:
            self.device.app_start(self.pkg)
            time.sleep(self.activition_interval)
    def set_default_browser(self):
        self.device.shell("settings put secure browser_default com.android.chrome")
        return

if __name__ == '__main__':
    runner = Runner_u2("a1", "com.android.chrome")
    time.sleep(5)
    while True:
        time.sleep(2)
        runner.device.clear_text()