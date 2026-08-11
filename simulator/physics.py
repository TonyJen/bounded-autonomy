import random

LED_COLORS = {
    "off": {"r": 0, "g": 0, "b": 0}, "red": {"r": 255, "g": 0, "b": 0},
    "green": {"r": 0, "g": 255, "b": 0}, "blue": {"r": 0, "g": 0, "b": 255},
    "white": {"r": 255, "g": 255, "b": 255}, "amber": {"r": 255, "g": 191, "b": 0},
}


class RoomModel:
    """Virtual room: sinusoidal day drift + noise + actuator feedback."""

    def __init__(self) -> None:
        self.temp_c: float | None = 22.0
        self.humidity_pct: float | None = 45.0
        self.light: int = 800
        self.motion: bool = False
        self.fan: bool = False
        self.servo_deg: int = 0
        self.led: dict = dict(LED_COLORS["off"])
        self.buzzer: bool = False
        self.oled: list[str] = ["GrokGuardian", "sim"]
        self._elapsed = 0.0
        self._scenario: dict | None = None
        self._fired: set[int] = set()
        self._rng = random.Random(42)

    def apply_scenario(self, scenario: dict) -> None:
        self._scenario = scenario
        self._elapsed = 0.0
        self._fired: set[int] = set()

    def force(self, **kwargs) -> None:
        for k, v in kwargs.items():
            if hasattr(self, k):
                setattr(self, k, v)

    def tick(self, dt_s: float) -> None:
        self._elapsed += dt_s
        # scripted overrides: fire each keyframe once when its time is reached
        # (index-tracked so at_s=0 fires on the first tick and large dt
        # doesn't skip frames; after firing, physics drifts naturally)
        if self._scenario:
            for i, frame in enumerate(self._scenario.get("script", [])):
                if i not in self._fired and frame["at_s"] <= self._elapsed:
                    self.force(**frame.get("set", {}))
                    self._fired.add(i)
        # day-cycle drift + noise
        if self.temp_c is not None:
            self.temp_c += self._rng.uniform(-0.05, 0.05) * dt_s
            # actuator feedback: fan pulls toward 22°C at ~0.5°C/min
            if self.fan and self.temp_c > 22.0:
                self.temp_c = max(22.0, self.temp_c - (0.5 / 60.0) * dt_s)
        # humidity inversely coupled to temperature
        if self.humidity_pct is not None and self.temp_c is not None:
            self.humidity_pct = min(100.0, max(0.0,
                self.humidity_pct - (self.temp_c - 22.0) * 0.001 * dt_s
                + self._rng.uniform(-0.02, 0.02) * dt_s))

    def set_actuator(self, action: str, args: dict) -> None:
        if action == "set_fan":
            self.fan = bool(args.get("on"))
        elif action == "set_servo":
            self.servo_deg = max(0, min(90, int(args.get("angle", 0))))
        elif action == "set_led":
            self.led = dict(LED_COLORS.get(args.get("color", "off"),
                                           LED_COLORS["off"]))
        elif action == "buzzer":
            self.buzzer = True  # sim marks the event; pattern timing not modeled
        elif action == "display_text":
            self.oled = [str(args.get("line1", ""))[:16],
                         str(args.get("line2", ""))[:16]]

    def snapshot(self) -> dict:
        return {
            "temp_c": round(self.temp_c, 1) if self.temp_c is not None else None,
            "humidity_pct": (round(self.humidity_pct, 1)
                             if self.humidity_pct is not None else None),
            "light": int(self.light),
            "motion": bool(self.motion),
        }
