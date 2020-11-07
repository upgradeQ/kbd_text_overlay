__author__ = "upgradeQ"
__version__ = "0.1.0"
__licence__ = "MPL-2.0"

import obspython as obs
import os
from itertools import cycle
from functools import partial
from contextlib import contextmanager
from pathlib import Path
from datetime import datetime


# auto release context managers
@contextmanager
def source_ar(source_name):
    source = obs.obs_get_source_by_name(source_name)
    try:
        yield source
    finally:
        obs.obs_source_release(source)


@contextmanager
def source_create_ar(id, source_name, settings):
    try:
        _source = obs.obs_source_create(id, source_name, settings, None)
        yield _source
    finally:
        obs.obs_source_release(_source)


@contextmanager
def scene_create_ar(name):
    try:
        _scene = obs.obs_scene_create(name)
        yield _scene
    finally:
        obs.obs_scene_release(_scene)


@contextmanager
def data_ar(source_settings=None):
    if not source_settings:
        settings = obs.obs_data_create()
    if source_settings:
        settings = obs.obs_source_get_settings(source_settings)
    try:
        yield settings
    finally:
        obs.obs_data_release(settings)


@contextmanager
def p_data_ar(data_type, field):
    settings = obs.obs_get_private_data()
    get = getattr(obs, f"obs_data_get_{data_type}")
    try:
        yield get(settings, field)
    finally:
        obs.obs_data_release(settings)


@contextmanager
def scene_from_source_ar(source):
    source = obs.obs_scene_from_source(source)
    try:
        yield source
    finally:
        obs.obs_scene_release(source)


class Hotkey:
    def __init__(self, callback, obs_settings, _id):
        self.obs_data = obs_settings
        self.hotkey_id = obs.OBS_INVALID_HOTKEY_ID
        self.hotkey_saved_key = None
        self.callback = callback
        self._id = _id

        self.load_hotkey()
        self.register_hotkey()
        self.save_hotkey()

    def register_hotkey(self):
        description = "Htk " + str(self._id)
        self.hotkey_id = obs.obs_hotkey_register_frontend(
            "htk_id" + str(self._id), description, self.callback
        )
        obs.obs_hotkey_load(self.hotkey_id, self.hotkey_saved_key)

    def load_hotkey(self):
        self.hotkey_saved_key = obs.obs_data_get_array(
            self.obs_data, "htk_id" + str(self._id)
        )
        obs.obs_data_array_release(self.hotkey_saved_key)

    def save_hotkey(self):
        self.hotkey_saved_key = obs.obs_hotkey_save(self.hotkey_id)
        obs.obs_data_set_array(
            self.obs_data, "htk_id" + str(self._id), self.hotkey_saved_key
        )
        obs.obs_data_array_release(self.hotkey_saved_key)

    @staticmethod
    def send_hotkey(obs_htk_id, key_modifiers=None):
        if key_modifiers:
            shift = key_modifiers.get("shift")
            control = key_modifiers.get("control")
            alt = key_modifiers.get("alt")
            command = key_modifiers.get("command")
        else:
            shift = control = alt = command = 0
        modifiers = 0

        if shift:
            modifiers |= obs.INTERACT_SHIFT_KEY
        if control:
            modifiers |= obs.INTERACT_CONTROL_KEY
        if alt:
            modifiers |= obs.INTERACT_ALT_KEY
        if command:
            modifiers |= obs.INTERACT_COMMAND_KEY

        combo = obs.obs_key_combination()
        combo.modifiers = modifiers
        combo.key = obs.obs_key_from_name(obs_htk_id)

        if not modifiers and (
            # obs.OBS_KEY_NONE = 0 ?
            combo.key == 0
            or combo.key >= obs.OBS_KEY_LAST_VALUE
        ):
            raise Exception("invalid key-modifier combination")

        obs.obs_hotkey_inject_event(combo, False)
        obs.obs_hotkey_inject_event(combo, True)
        obs.obs_hotkey_inject_event(combo, False)

    @staticmethod
    def hook(obs_htk_id, htk_id, callback):
        json_data = '{"%s":[{"key":"%s"}]}' % (htk_id, obs_htk_id)
        s = obs.obs_data_create_from_json(json_data)

        a = obs.obs_data_get_array(s, htk_id)
        h = obs.obs_hotkey_register_frontend(htk_id, obs_htk_id, callback)
        obs.obs_hotkey_load(h, a)

        obs.obs_data_array_release(a)
        obs.obs_data_release(s)


# ---------------------------
class TextElement:
    def __init__(self, name, text):
        self.name = name
        self.text = text
        self.x = 0
        self.y = 0


def set_text_source_settings(settings, text_data):
    with data_ar() as font_settings:
        obs.obs_data_set_string(font_settings, "face", DEFAULT_FONT)
        obs.obs_data_set_int(font_settings, "size", 80)
        obs.obs_data_set_obj(settings, "font", font_settings)
        obs.obs_data_set_string(settings, "text", text_data)


def add_text_to_scene(scene, text_element):
    """Places text source into some location within scene
    returns width and height to align next scene items later """

    with data_ar() as settings:
        set_text_source_settings(settings, text_element.text)
        with source_create_ar("text_ft2_source", text_element.name, settings) as source:
            pos = obs.vec2()
            pos.x = text_element.x
            pos.y = text_element.y
            scene_item = obs.obs_scene_add(scene, source)
            obs.obs_sceneitem_set_pos(scene_item, pos)
            height = obs.obs_source_get_height(source)
            width = obs.obs_source_get_width(source)
            return width, height


def place_row(scene, text_element, height_ruler):
    text_element.y += height_ruler
    width, height = add_text_to_scene(scene, text_element)
    status = TextElement(text_element.name + "_status", " empty")
    spacing = 80
    status.x = width + spacing
    status.y = text_element.y
    add_text_to_scene(scene, status)
    return height


def crete_text_scene_source(panels, menus):
    "Adds scene with text sources to current scene"

    current_scene_source = obs.obs_frontend_get_current_scene()
    with scene_from_source_ar(current_scene_source) as scene_source:
        with scene_create_ar("_scene") as _scene:
            py_scene_source = obs.obs_scene_get_source(_scene)

            with scene_from_source_ar(py_scene_source) as scene:
                height_ruler = 0
                for i in panels:
                    sn, ds = i.source_name, i.description
                    height_ruler += place_row(scene, TextElement(sn, ds), height_ruler)

                height_ruler += 30
                for i in menus:
                    i = i.text_obs_obj
                    sn, ds = i.source_name, i.description
                    height_ruler += place_row(scene, TextElement(sn, ds), height_ruler)

            # add created scene to current scene ( nested scene)
            _scene_source = obs.obs_scene_get_source(scene)
            obs.obs_scene_add(scene_source, _scene_source)


# ---------------------------
class MenuController:
    def __init__(self, menu_items):
        self.index = 0
        self.selection = menu_items[self.index]
        self.text_obs_obj = self.selection.text_obs_obj
        self.submenus = menu_items
        self.max_index = len(menu_items) - 1
        self.menu_item_select = True
        self.submenu_item_select = False
        self.action_item_active = False

    def update_index(self, i):
        if i > 0:
            self.index += 1
        else:
            self.index -= 1

        if self.index > self.max_index:
            self.index = 0
        if self.index < 0:
            self.index = self.max_index

    def on_left(self):
        self.menu_item_select = True
        self.action_item_active = False
        self.submenu_item_select = False
        self.selection = self.submenus[self.index]

        for i, _ in enumerate(self.submenus):
            with source_ar(f"menu_{i}_status") as source, data_ar() as settings:
                obs.obs_data_set_string(settings, "text", " ")
                obs.obs_source_update(source, settings)

    def on_right(self):
        if self.submenu_item_select:
            self.selection = self.submenus[self.index]
            if self.action_item_active:
                self.selection.activate()
            self.action_item_active = True
        else:
            source_name = f"menu_{self.index}_status"
            with source_ar(source_name) as source, data_ar() as settings:
                obs.obs_data_set_string(settings, "text", ">")
                obs.obs_source_update(source, settings)
            self.submenu_item_select = True

    def on_up(self):
        if self.submenu_item_select:
            self.selection.get_next()
        else:
            self.update_index(-1)
            self.selection = self.submenus[self.index]

            self.selection.text_obs_obj.redraw(
                self.selection.description, self.max_index + 1
            )

    def on_down(self):
        if self.submenu_item_select:
            self.selection.get_previous()
        else:
            self.update_index(1)
            self.selection = self.submenus[self.index]
            self.selection.text_obs_obj.redraw(
                self.selection.description, self.max_index + 1
            )


class SubMenuItem(MenuController):
    def __init__(self, text_obs_obj, action_list):
        self.description = text_obs_obj.description
        self.text_obs_obj = text_obs_obj
        self.index = 0
        self.max_index = len(action_list) - 1
        self.selection = action_list[self.index]
        self.action_list = action_list

    def get_next(self):
        self.update_index(1)
        self.selection.text_obs_obj.redraw(self.action_list[self.index].description)

    def get_previous(self):
        self.update_index(-1)
        self.selection.text_obs_obj.redraw(self.action_list[self.index].description)

    def activate(self):
        self.action_list[self.index].activate()


class ActionItem:
    def __init__(self, text_obs_obj, callback):
        self.description = text_obs_obj.description
        self.text_obs_obj = text_obs_obj
        self.callback = callback

    def activate(self):
        self.callback()


# ------------------------


class TextObsObj:
    def __init__(self, description, source_name):
        self.description = description
        self.source_name = source_name

    def set_text(self, source_name, text):
        with source_ar(source_name) as source, data_ar() as settings:
            obs.obs_data_set_string(settings, "text", text)
            obs.obs_source_update(source, settings)

    def get_text(self, source_name):
        with source_ar(source_name) as source, data_ar(source) as settings:
            return obs.obs_data_get_string(settings, "text")

    def clear_text(self, index):
        s = self.get_text(f"menu_{index}")
        if "[" in s:
            self.set_text(f"menu_{index}", s[1:-1])

    def redraw(self, text, menu_max=0):
        if "status" not in self.source_name:
            index = int(self.source_name[-1])
            for i in range(menu_max):
                if i == index:
                    continue
                self.clear_text(i)

            self.set_text(self.source_name, f"[{text}]")
        else:
            self.set_text(self.source_name, text)


DEFAULT_FONT = "Arial"


def set_default_font():
    global DEFAULT_FONT
    if os.name == "nt":
        DEFAULT_FONT = "Arial"
    else:
        DEFAULT_FONT = "Sans Serif"


set_default_font()

# ------------------------
test_items = [
    ActionItem(TextObsObj(f" sound {i}", "menu_0_status"), lambda: ...)
    for i in range(9)
]

# -o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o


def scene_item(arg):
    print(f"toggle scene item # {arg}")


test_item2 = ActionItem(TextObsObj("item 2 ", "menu_1_status"), lambda: scene_item(2))
test_item3 = ActionItem(TextObsObj("item 3 ", "menu_1_status"), lambda: scene_item(3))
test_item4 = ActionItem(TextObsObj("item 4 ", "menu_1_status"), lambda: scene_item(4))


# -o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o


def _send_hotkey(number):
    Hotkey.send_hotkey(f"OBS_KEY_{number}")


test_items2 = [
    ActionItem(
        TextObsObj(f" hotkey {i}", "menu_2_status"), partial(_send_hotkey,i)
    )
    for i in range(9)
]

# -o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o
def doubler(n):
    print(n * 2)


test_items3 = [
    ActionItem(TextObsObj(f" double {i}", "menu_3_status"), partial(doubler, n=i))
    for i in range(9)
]

# -o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o

sub_item = SubMenuItem(TextObsObj("Play sound", "menu_0"), test_items)

sub_item1 = SubMenuItem(
    TextObsObj("Activated scene item", "menu_1"), [test_item2, test_item3, test_item4],
)
sub_item2 = SubMenuItem(TextObsObj("Send hotkey", "menu_2"), test_items2)
sub_item3 = SubMenuItem(TextObsObj("Send double", "menu_3"), test_items3)

menu_items = [sub_item, sub_item1, sub_item2, sub_item3]


menu = MenuController(menu_items)


# ---------------------------


class MultipleStatusUpdater:
    lock = True
    interval = 1000 // 2  # ms

    def __init__(self, status_update_functions):
        self.status_update_functions = status_update_functions

    def update_all(self):
        for f in self.status_update_functions:
            f()
        if self.lock:
            obs.remove_current_callback()


def update_status(index, text):
    with source_ar(f"panel_{index}_status") as source, data_ar() as settings:
        obs.obs_data_set_string(settings, "text", str(text))
        obs.obs_source_update(source, settings)


def update_time():
    time = str(datetime.now())
    update_status(0, time)


def update_scene_name():
    current_scene_source = obs.obs_frontend_get_current_scene()
    name = obs.obs_source_get_name(current_scene_source)
    update_status(1, name)
    obs.obs_source_release(current_scene_source)


def update_mic_status():
    with p_data_ar("string", "__muted__") as value:
        update_status(2, value)


panel_items = [
    TextObsObj("Time: ", "panel_0"),
    TextObsObj("Current scene: ", "panel_1"),
    TextObsObj("Mute: ", "panel_2"),
]

status = MultipleStatusUpdater([update_time, update_scene_name, update_mic_status])

# ------------------------------


def add_nested():
    crete_text_scene_source(panel_items, menu_items)


def launcher(pressed):
    if pressed:
        if status.lock:
            obs.timer_add(status.update_all, status.interval)
            status.lock = False
        elif not status.lock:
            status.lock = True


Hotkey.hook("OBS_KEY_LEFT", "left_id", lambda h: menu.on_left() if h else 0)
Hotkey.hook("OBS_KEY_RIGHT", "right_id", lambda h: menu.on_right() if h else 0)
Hotkey.hook("OBS_KEY_UP", "up_id", lambda h: menu.on_up() if h else 0)
Hotkey.hook("OBS_KEY_DOWN", "down_id", lambda h: menu.on_down() if h else 0)

Hotkey.hook("OBS_KEY_0", "0_id", launcher)


def callback(*p):
    add_nested()


def script_properties():
    props = obs.obs_properties_create()
    obs.obs_properties_add_button(props, "button1", "add to current scene", callback)
    return props
