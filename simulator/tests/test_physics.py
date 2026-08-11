from simulator.physics import RoomModel


def test_idle_room_drifts_naturally():
    room = RoomModel()
    t0 = room.temp_c
    room.tick(60)
    assert abs(room.temp_c - t0) < 1.0  # no scenario → small drift only


def test_fan_cools_room():
    room = RoomModel()
    room.force(temp_c=30.0)
    room.set_actuator("set_fan", {"on": True})
    for _ in range(10):
        room.tick(60)  # 10 minutes
    assert room.temp_c < 30.0
    assert room.fan is True


def test_heat_spike_scenario():
    room = RoomModel()
    room.apply_scenario({"duration_s": 600, "script": [
        {"at_s": 0, "set": {"temp_c": 35.0}}]})
    room.tick(1)
    assert room.temp_c >= 34.9


def test_snapshot_shape():
    room = RoomModel()
    snap = room.snapshot()
    assert set(snap) == {"temp_c", "humidity_pct", "light", "motion"}
    assert isinstance(snap["light"], int)


def test_servo_and_led():
    room = RoomModel()
    room.set_actuator("set_servo", {"angle": 45})
    room.set_actuator("set_led", {"color": "red"})
    assert room.servo_deg == 45
    assert room.led == {"r": 255, "g": 0, "b": 0}
