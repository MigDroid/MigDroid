import cv2
from xml.etree import ElementTree as ET
import numpy as np

from const import CATEGORY_MAP, PROGRAM_ATTRS, SEMANTIC_ATTRS
from LLMUtil import LLMUtil


class ScreenUtil:
    attrs_interactable = ["clickable", "long-clickable", "scrollable"]
    """
    A utility class for screen layout and widget processing
    """

    # Parse the bounds from the form "[left,top][right,bottom]" into a tuple of integers
    @staticmethod
    def parse_bounds(bounds_str):
        bounds_str = bounds_str.replace("[", "").replace("]", ",")
        bounds = list(map(int, bounds_str.split(",")[:-1]))
        return (
            bounds[0],
            bounds[1],
            bounds[2],
            bounds[3],
        )  # (left, top, right, bottom)

    @staticmethod
    def widget_equal(widget1, widget2, attrs=None):
        if not attrs:
            must_equal = [
                "resource-id",
                "text",
                "content-desc",
                "package",
            ]
        else:
            must_equal = attrs
        bounds1 = widget1["bounds"] if "bounds" in widget1 else None
        bounds2 = widget2["bounds"] if "bounds" in widget2 else None
        # check if they are both strings
        if bounds1 and bounds2:
            if not isinstance(bounds1, str):
                widget1["bounds"] = (
                    f"[{bounds1['left']},{bounds1['top']}][{bounds1['right']},{bounds1['bottom']}]"
                )
            if not isinstance(bounds2, str):
                widget2["bounds"] = (
                    f"[{bounds2['left']},{bounds2['top']}][{bounds2['right']},{bounds2['bottom']}]"
                )
        else:
            widget1["bounds"] = widget2["bounds"] = None
        if widget1["bounds"] and widget2["bounds"] and widget1["bounds"] == widget2["bounds"]:
            return True
        for attr in must_equal:
            if attr in widget1 and attr in widget2 and widget1[attr] != widget2[attr]:
                return False
        # check if the bounds overlap
        if not widget1["bounds"] or not widget2["bounds"]:
            return True
        else:
            bounds1 = ScreenUtil.parse_bounds(widget1["bounds"])
            bounds2 = ScreenUtil.parse_bounds(widget2["bounds"])
            if bounds1[0] <= bounds2[2] and bounds1[2] >= bounds2[0] and bounds1[1] <= bounds2[3] and bounds1[3] >= bounds2[1]:
                return True
        return False

    @staticmethod
    def widget_in_list(widget, widget_list, attrs=None):
        for w in widget_list:
            if ScreenUtil.widget_equal(widget, w, attrs):
                return w
        return False

    @staticmethod
    def group_children(node, attributes):
        # in-place revision of the attributes dictionary to include the children of the node
        if "children" not in attributes and len(node) > 0:
            attributes["children"] = []
        # iterate through the children of the child, and add them to the children attribute
        for child in node:
            child_attributes = {}
            for attr in PROGRAM_ATTRS:
                if attr in ["event_type", "action"]:
                    continue
                child_attributes[attr] = child.attrib.get(attr, "")
            # iterate through the children of the child
            ScreenUtil.group_children(child, child_attributes)
            attributes["children"].append(child_attributes)

    @staticmethod
    def get_interactable_widgets(page_layout):
        if page_layout is None:
            print("No page layout found")
            return None
        root = ET.fromstring(page_layout)
        interactable_widgets = []

        def find_interactable_widgets(node):
            node_interactable = []
            node_attributes = {}
            # if any of the interactable attributes is "true", then the widget is interactable
            if any(
                node.attrib.get(attr, "false") == "true"
                for attr in ScreenUtil.attrs_interactable
            ):
                if (
                    node.attrib.get("package", "") != "com.android.systemui"
                    and node.attrib.get("package", "")
                    != "com.google.android.inputmethod.latin"
                ):
                    node_attributes = {}
                    for attr in PROGRAM_ATTRS:
                        if attr in ["event_type", "action"]:
                            continue
                        node_attributes[attr] = node.attrib.get(attr, "")
                    interactable_widgets.append(node_attributes)
                    node_interactable.append(node_attributes)
            # only if an interactable node has children, it's possible to group them
            flag_group = True if node_attributes and len(node) > 0 else False
            for child in node:
                child_interactable = []
                child_interactable.extend(find_interactable_widgets(child))
                node_interactable.extend(child_interactable)
                if child_interactable:
                    flag_group = False
            # if all children are not interactable, then group them under their parent
            if flag_group:
                ScreenUtil.group_children(node, node_attributes)
            return node_interactable

        find_interactable_widgets(root)
        return interactable_widgets

    @staticmethod
    def get_leaf_widgets(page_layout):
        if page_layout is None:
            print("No page layout found")
            return None
        root = ET.fromstring(page_layout)
        leaf_widgets = []

        def find_leaf_widgets(node):
            node_leaf = []
            if (node.attrib.get("package", "") != "com.android.systemui" and node.attrib.get("package", "") != "com.google.android.inputmethod.latin"):
                if len(node) == 0:
                    node_attributes = {}
                    for attr in PROGRAM_ATTRS:
                        if attr in ["event_type", "action"]:
                            continue
                        node_attributes[attr] = node.attrib.get(attr, "")
                    node_leaf.append(node_attributes)
                    return node_leaf
                for child in node:
                    node_leaf.extend(find_leaf_widgets(child))
            return node_leaf
        leaf_widgets = find_leaf_widgets(root)
        return leaf_widgets
        
    @staticmethod
    def annotate_screen(screenshotpath, outputpath, widget_list, enable_number=True):
        # print(widget_list)
        screen = cv2.imread(screenshotpath)
        widget_id = 0
        text_points = []
        for widget in widget_list:
            widget_id += 1
            bounds = ScreenUtil.parse_bounds(widget["bounds"])
            left, top, right, bottom = bounds
            text_left, text_top, text_right, text_bottom = bounds
            num_overlap = 0
            box_color = [0, 0, 0]
            for text_point in text_points:
                if abs(text_point[0] + text_point[1] - left - top) < 30:
                    num_overlap += 1
                    
            text_left = (left + num_overlap * right) / (num_overlap + 1)
            top = top - 10*num_overlap
            # if no overlap, use red
            box_color[(num_overlap-1)%3] = 255

            cv2.rectangle(
                screen,
                (int(left), int(top)),
                (int(right), int(bottom)),
                box_color,
                thickness=3,
            )
            # put a number on the rectangle
            if enable_number:
                # pass
                # a filled box to put the number
                if widget_id < 10:
                    width = 30
                else:
                    width = 40
                cv2.rectangle(
                    screen,
                    (int(text_left), int(top)),
                    (int(text_left + width), int(top + width)),
                    box_color,
                    thickness=cv2.FILLED,
                )

                cv2.putText(
                    screen,
                    str(widget_id),
                    (int(text_left), int(top + 25)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1,
                    (255, 255, 255),
                    4,
                )

            text_points.append((left, top))
        cv2.imwrite(outputpath, screen)
        return outputpath

    @staticmethod
    def extract_widgets_from_xml(xml_content):
        root = ET.fromstring(xml_content)

        # Define a list of container widgets that should be ignored
        container_widgets = [
            "FrameLayout",
            "LinearLayout",
            "RelativeLayout",
            "ConstraintLayout",
            "CoordinatorLayout",
            "DrawerLayout",
            "ViewGroup",
            "hierarchy",
        ]

        widgets = []
        for elem in root.iter():
            # Extract class attribute to identify the widget type
            widget_class = elem.attrib.get("class", "")
            # Check if the widget is not a container
            if not any(container in widget_class for container in container_widgets):
                if (
                    elem.attrib.get("package", "") != "com.android.systemui"
                    and elem.attrib.get("package", "")
                    != "com.google.android.inputmethod.latin"
                ):
                    widget_info = {
                        "class": widget_class,
                        "resource-id": elem.attrib.get("resource-id", ""),
                        "text": elem.attrib.get("text", ""),
                        "content-desc": elem.attrib.get("content-desc", ""),
                        "clickable": elem.attrib.get("clickable", "false"),
                        "password": elem.attrib.get("password", "false"),
                        "bounds": elem.attrib.get("bounds", ""),
                        "package": elem.attrib.get("package", ""),
                    }
                    widgets.append(widget_info)
        return widgets

    @staticmethod
    def is_same_widget(widget1, widget2):
        for attr in ["class", "resource-id", "text", "content-desc", "package"]:
            if widget1[attr] != widget2[attr]:
                return False
        return True

    @staticmethod
    def get_page_desc(app_id, screenshot_path, event_history, model_name="gpt-4o-mini"):
        prompt_file = "TestAnalyzer/prompt_page_desc.txt"
        with open(prompt_file, "r") as f:
            prompt = f.read()

        category_name = CATEGORY_MAP[app_id[:2]]
        prompt = prompt.replace("$$$category$$$", category_name)

        if event_history:
            prompt += "After opening the app and executing these actions:\n"
            prompt += str(event_history) + "\n"
            prompt += "The app has come to this page shown in the screenshot. Please describe the page with no more than 50 words.\n"
        else:
            prompt += "The app is opened as shown in the screenshot, please describe the open page with no more than 50 words.\n"
        try:
            answer = LLMUtil.query_with_retry(
                prompt, screenshot_path, model_name=model_name
            )
        except Exception as e:
            print("Exception during acquiring page desc:", e)
            return None
        return answer

    @staticmethod
    def synthesize_image(titles, image_paths, save_path="Temp/synthesized_image.png"):
        print("Synthesizing images...")
        # list the images in the order of the titles, and concatenate them horizontally, with the titles on top
        images = []
        for path in image_paths:
            print(f"Loading image from {path}")
            img = cv2.imread(path)
            images.append(img)
        # Calculate the height and width for the concatenated image
        max_height = max(img.shape[0] for img in images)
        total_width = (
            sum(img.shape[1] for img in images) + (len(images) - 1) * 500 + 400
        )  # Include 500px gap
        # Create a blank canvas with white background for titles and images
        title_height = 100  # Space for the titles on top of images
        canvas = (
            np.ones((max_height + title_height, total_width, 3), dtype=np.uint8) * 255
        )

        # Position the images on the canvas with titles on top
        x_offset = 200  # Initial x position
        for i, img in enumerate(images):
            # Add title text above each image
            cv2.putText(
                canvas,
                titles[i],
                (x_offset + int(img.shape[1] / 5), 60),
                cv2.FONT_HERSHEY_SIMPLEX,
                2.2,
                (0, 0, 0),
                6,
            )

            # Place image below title
            canvas[
                title_height : title_height + img.shape[0],
                x_offset : x_offset + img.shape[1],
            ] = img
            # use red rectangle to highlight the image
            top_left = (x_offset, title_height)
            bottom_right = (x_offset + img.shape[1], title_height + img.shape[0])
            cv2.rectangle(canvas, top_left, bottom_right, (0, 0, 255), 3)
            x_offset += img.shape[1] + 500  # Move to the next position with a 500px gap

        cv2.imwrite(save_path, canvas)
        return save_path

    @staticmethod
    def extract_semantic_attrs(widget):
        new_widget = {}
        for attr in SEMANTIC_ATTRS:
            if attr in widget:
                new_widget[attr] = widget[attr]
        if "children" in widget:
            new_widget["children"] = []
            for child in widget["children"]:
                new_child = ScreenUtil.extract_semantic_attrs(child)
                new_widget["children"].append(new_child)
        return new_widget
