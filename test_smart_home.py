"""Tests for blackroad-smart-home."""
import os, json, pytest, tempfile
from smart_home import (
    SmartHomeController, Device, DeviceGroup, Capability, Scene, Schedule, init_db
)


@pytest.fixture
def ctrl(tmp_path):
    db = str(tmp_path / "test.db")
    c = SmartHomeController(db_path=db)
    light = Device(
        id="l1", name="Lamp", type="light", room="bedroom",
        capabilities=[
            Capability("on_off"),
            Capability("brightness", 0, 100, "%"),
            Capability("color_temp", 2700, 6500, "K"),
        ]
    )
    thermo = Device(
        id="t1", name="Thermo", type="thermostat", room="bedroom",
        capabilities=[Capability("temperature", 15, 30, "°C")],
        state={"on": True, "current_temp": 20.0, "target_temp": 21.0, "mode": "heat"}
    )
    c.add_device(light)
    c.add_device(thermo)
    return c


def test_toggle_device(ctrl):
    res = ctrl.toggle_device("l1")
    assert res["on"] is True
    res2 = ctrl.toggle_device("l1")
    assert res2["on"] is False


def test_set_brightness(ctrl):
    ctrl.toggle_device("l1")
    res = ctrl.set_brightness("l1", 80)
    assert res["brightness"] == 80
    d = ctrl.get_device("l1")
    assert d.state["brightness"] == 80


def test_brightness_out_of_range(ctrl):
    with pytest.raises(ValueError, match="0–100"):
        ctrl.set_brightness("l1", 150)


def test_create_and_run_scene(ctrl):
    ctrl.create_scene("Night", {"l1": {"on": False, "brightness": 0}})
    result = ctrl.run_scene("Night")
    assert "l1" in result["applied_to"]
    d = ctrl.get_device("l1")
    assert d.state["on"] is False


def test_schedule_action(ctrl):
    sched = ctrl.schedule_action("l1", {"type": "toggle"}, "*/5 * * * *")
    assert sched.id
    assert sched.next_run is not None


def test_device_history(ctrl):
    ctrl.toggle_device("l1")
    ctrl.toggle_device("l1")
    hist = ctrl.get_device_history("l1", hours=1)
    assert len(hist) >= 2


def test_get_room_status(ctrl):
    status = ctrl.get_room_status("bedroom")
    assert status["device_count"] == 2


def test_list_devices_filter(ctrl):
    lights = ctrl.list_devices(type_filter="light")
    assert len(lights) == 1 and lights[0].id == "l1"


def test_group_toggle(ctrl):
    grp = DeviceGroup(id="g1", name="Bedroom Lights", device_ids=["l1"])
    ctrl.add_group(grp)
    results = ctrl.toggle_group("g1")
    assert len(results) == 1


def test_scene_missing_raises(ctrl):
    with pytest.raises(ValueError, match="not found"):
        ctrl.run_scene("does_not_exist")
