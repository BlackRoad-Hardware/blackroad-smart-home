"""
blackroad-smart-home — Smart Home Controller
Production implementation: devices, groups, scenes, scheduling, history.
"""

from __future__ import annotations
import sqlite3
import json
import hashlib
import threading
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable
from croniter import croniter  # pip install croniter
import logging

logger = logging.getLogger(__name__)

DB_PATH = "smart_home.db"
_LOCK = threading.Lock()


# ─────────────────────────── Dataclasses ────────────────────────────

@dataclass
class Capability:
    name: str          # e.g. "brightness", "color_temp", "on_off"
    min_val: float = 0.0
    max_val: float = 100.0
    unit: str = ""


@dataclass
class Device:
    id: str
    name: str
    type: str           # light / thermostat / lock / plug / sensor
    room: str
    state: Dict[str, Any] = field(default_factory=lambda: {"on": False})
    capabilities: List[Capability] = field(default_factory=list)
    online: bool = True
    firmware: str = "1.0.0"
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def has_capability(self, name: str) -> bool:
        return any(c.name == name for c in self.capabilities)

    def to_dict(self) -> dict:
        d = asdict(self)
        return d


@dataclass
class DeviceGroup:
    id: str
    name: str
    device_ids: List[str] = field(default_factory=list)
    description: str = ""

    def add_device(self, device_id: str) -> None:
        if device_id not in self.device_ids:
            self.device_ids.append(device_id)

    def remove_device(self, device_id: str) -> None:
        self.device_ids = [d for d in self.device_ids if d != device_id]


@dataclass
class Scene:
    name: str
    device_states: Dict[str, Dict[str, Any]]  # device_id -> state dict
    description: str = ""
    icon: str = "🏠"
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class Schedule:
    id: str
    device_id: str
    action: Dict[str, Any]
    cron_expr: str
    enabled: bool = True
    last_run: Optional[str] = None
    next_run: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def compute_next_run(self, base: Optional[datetime] = None) -> datetime:
        base = base or datetime.utcnow()
        return croniter(self.cron_expr, base).get_next(datetime)


# ─────────────────────────── Database ───────────────────────────────

def _get_conn(db_path: str = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db(db_path: str = DB_PATH) -> None:
    with _get_conn(db_path) as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS devices (
            id          TEXT PRIMARY KEY,
            name        TEXT NOT NULL,
            type        TEXT NOT NULL,
            room        TEXT NOT NULL,
            state       TEXT NOT NULL DEFAULT '{}',
            capabilities TEXT NOT NULL DEFAULT '[]',
            online      INTEGER NOT NULL DEFAULT 1,
            firmware    TEXT NOT NULL DEFAULT '1.0.0',
            created_at  TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS device_groups (
            id          TEXT PRIMARY KEY,
            name        TEXT NOT NULL,
            device_ids  TEXT NOT NULL DEFAULT '[]',
            description TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS events (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id   TEXT NOT NULL,
            event_type  TEXT NOT NULL,
            payload     TEXT NOT NULL DEFAULT '{}',
            ts          TEXT NOT NULL,
            FOREIGN KEY(device_id) REFERENCES devices(id)
        );
        CREATE INDEX IF NOT EXISTS idx_events_device ON events(device_id, ts);
        CREATE TABLE IF NOT EXISTS scenes (
            name            TEXT PRIMARY KEY,
            device_states   TEXT NOT NULL DEFAULT '{}',
            description     TEXT NOT NULL DEFAULT '',
            icon            TEXT NOT NULL DEFAULT '🏠',
            created_at      TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS schedules (
            id          TEXT PRIMARY KEY,
            device_id   TEXT NOT NULL,
            action      TEXT NOT NULL,
            cron_expr   TEXT NOT NULL,
            enabled     INTEGER NOT NULL DEFAULT 1,
            last_run    TEXT,
            next_run    TEXT,
            created_at  TEXT NOT NULL,
            FOREIGN KEY(device_id) REFERENCES devices(id)
        );
        """)
    logger.info("smart_home DB initialised at %s", db_path)


# ─────────────────────────── Controller ─────────────────────────────

class SmartHomeController:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        init_db(db_path)
        self._scheduler_thread: Optional[threading.Thread] = None
        self._running = False

    # ── Device CRUD ──────────────────────────────────────────────────

    def add_device(self, device: Device) -> Device:
        with _LOCK, _get_conn(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO devices VALUES (?,?,?,?,?,?,?,?,?)",
                (device.id, device.name, device.type, device.room,
                 json.dumps(device.state),
                 json.dumps([asdict(c) for c in device.capabilities]),
                 int(device.online), device.firmware, device.created_at)
            )
        self._log_event(device.id, "device_added", {"name": device.name})
        return device

    def get_device(self, device_id: str) -> Optional[Device]:
        with _get_conn(self.db_path) as conn:
            row = conn.execute(
                "SELECT * FROM devices WHERE id=?", (device_id,)
            ).fetchone()
        if not row:
            return None
        caps = [Capability(**c) for c in json.loads(row["capabilities"])]
        return Device(
            id=row["id"], name=row["name"], type=row["type"],
            room=row["room"], state=json.loads(row["state"]),
            capabilities=caps, online=bool(row["online"]),
            firmware=row["firmware"], created_at=row["created_at"]
        )

    def list_devices(self, room: Optional[str] = None, type_filter: Optional[str] = None) -> List[Device]:
        query = "SELECT * FROM devices WHERE 1=1"
        params: list = []
        if room:
            query += " AND room=?"
            params.append(room)
        if type_filter:
            query += " AND type=?"
            params.append(type_filter)
        with _get_conn(self.db_path) as conn:
            rows = conn.execute(query, params).fetchall()
        result = []
        for row in rows:
            caps = [Capability(**c) for c in json.loads(row["capabilities"])]
            result.append(Device(
                id=row["id"], name=row["name"], type=row["type"],
                room=row["room"], state=json.loads(row["state"]),
                capabilities=caps, online=bool(row["online"]),
                firmware=row["firmware"], created_at=row["created_at"]
            ))
        return result

    def _update_state(self, device_id: str, updates: Dict[str, Any]) -> Device:
        device = self.get_device(device_id)
        if not device:
            raise ValueError(f"Device {device_id!r} not found")
        device.state.update(updates)
        with _LOCK, _get_conn(self.db_path) as conn:
            conn.execute(
                "UPDATE devices SET state=? WHERE id=?",
                (json.dumps(device.state), device_id)
            )
        return device

    # ── Actions ───────────────────────────────────────────────────────

    def toggle_device(self, device_id: str) -> Dict[str, Any]:
        device = self.get_device(device_id)
        if not device:
            raise ValueError(f"Device {device_id!r} not found")
        new_on = not device.state.get("on", False)
        device = self._update_state(device_id, {"on": new_on})
        self._log_event(device_id, "toggle", {"on": new_on})
        return {"device_id": device_id, "on": new_on, "ts": datetime.utcnow().isoformat()}

    def set_brightness(self, device_id: str, level: int) -> Dict[str, Any]:
        if not 0 <= level <= 100:
            raise ValueError("Brightness must be 0–100")
        device = self.get_device(device_id)
        if not device:
            raise ValueError(f"Device {device_id!r} not found")
        if not device.has_capability("brightness"):
            raise ValueError(f"Device {device_id!r} does not support brightness")
        self._update_state(device_id, {"brightness": level, "on": level > 0})
        self._log_event(device_id, "set_brightness", {"level": level})
        return {"device_id": device_id, "brightness": level}

    def set_color_temp(self, device_id: str, kelvin: int) -> Dict[str, Any]:
        if not 2700 <= kelvin <= 6500:
            raise ValueError("Color temp must be 2700K–6500K")
        device = self.get_device(device_id)
        if not device:
            raise ValueError(f"Device {device_id!r} not found")
        self._update_state(device_id, {"color_temp": kelvin})
        self._log_event(device_id, "set_color_temp", {"kelvin": kelvin})
        return {"device_id": device_id, "color_temp": kelvin}

    def set_thermostat(self, device_id: str, target_temp: float, mode: str = "heat") -> Dict[str, Any]:
        if mode not in ("heat", "cool", "auto", "off"):
            raise ValueError(f"Unknown thermostat mode: {mode}")
        device = self.get_device(device_id)
        if not device:
            raise ValueError(f"Device {device_id!r} not found")
        self._update_state(device_id, {"target_temp": target_temp, "mode": mode})
        self._log_event(device_id, "set_thermostat", {"target_temp": target_temp, "mode": mode})
        return {"device_id": device_id, "target_temp": target_temp, "mode": mode}

    # ── Groups ────────────────────────────────────────────────────────

    def add_group(self, group: DeviceGroup) -> DeviceGroup:
        with _LOCK, _get_conn(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO device_groups VALUES (?,?,?,?)",
                (group.id, group.name, json.dumps(group.device_ids), group.description)
            )
        return group

    def get_group(self, group_id: str) -> Optional[DeviceGroup]:
        with _get_conn(self.db_path) as conn:
            row = conn.execute(
                "SELECT * FROM device_groups WHERE id=?", (group_id,)
            ).fetchone()
        if not row:
            return None
        return DeviceGroup(
            id=row["id"], name=row["name"],
            device_ids=json.loads(row["device_ids"]),
            description=row["description"]
        )

    def toggle_group(self, group_id: str) -> List[Dict[str, Any]]:
        group = self.get_group(group_id)
        if not group:
            raise ValueError(f"Group {group_id!r} not found")
        return [self.toggle_device(did) for did in group.device_ids]

    # ── Scenes ────────────────────────────────────────────────────────

    def create_scene(self, name: str, device_states: Dict[str, Dict[str, Any]],
                     description: str = "", icon: str = "🏠") -> Scene:
        scene = Scene(name=name, device_states=device_states,
                      description=description, icon=icon)
        with _LOCK, _get_conn(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO scenes VALUES (?,?,?,?,?)",
                (name, json.dumps(device_states), description, icon, scene.created_at)
            )
        return scene

    def run_scene(self, scene_name: str) -> Dict[str, Any]:
        with _get_conn(self.db_path) as conn:
            row = conn.execute(
                "SELECT * FROM scenes WHERE name=?", (scene_name,)
            ).fetchone()
        if not row:
            raise ValueError(f"Scene {scene_name!r} not found")
        device_states = json.loads(row["device_states"])
        results = []
        errors = []
        for device_id, state in device_states.items():
            try:
                self._update_state(device_id, state)
                self._log_event(device_id, "scene_applied", {"scene": scene_name})
                results.append(device_id)
            except Exception as e:
                errors.append({"device_id": device_id, "error": str(e)})
        return {
            "scene": scene_name,
            "applied_to": results,
            "errors": errors,
            "ts": datetime.utcnow().isoformat()
        }

    def list_scenes(self) -> List[Scene]:
        with _get_conn(self.db_path) as conn:
            rows = conn.execute("SELECT * FROM scenes").fetchall()
        return [
            Scene(name=r["name"], device_states=json.loads(r["device_states"]),
                  description=r["description"], icon=r["icon"],
                  created_at=r["created_at"])
            for r in rows
        ]

    # ── Scheduling ────────────────────────────────────────────────────

    def schedule_action(self, device_id: str, action: Dict[str, Any],
                        cron_expr: str) -> Schedule:
        sched_id = hashlib.sha256(
            f"{device_id}{cron_expr}{json.dumps(action)}".encode()
        ).hexdigest()[:16]
        sched = Schedule(
            id=sched_id, device_id=device_id,
            action=action, cron_expr=cron_expr
        )
        sched.next_run = sched.compute_next_run().isoformat()
        with _LOCK, _get_conn(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO schedules VALUES (?,?,?,?,?,?,?,?)",
                (sched.id, device_id, json.dumps(action), cron_expr,
                 int(sched.enabled), sched.last_run, sched.next_run,
                 sched.created_at)
            )
        return sched

    def get_due_schedules(self) -> List[Schedule]:
        now = datetime.utcnow().isoformat()
        with _get_conn(self.db_path) as conn:
            rows = conn.execute(
                "SELECT * FROM schedules WHERE enabled=1 AND next_run<=?", (now,)
            ).fetchall()
        return [
            Schedule(
                id=r["id"], device_id=r["device_id"],
                action=json.loads(r["action"]), cron_expr=r["cron_expr"],
                enabled=bool(r["enabled"]), last_run=r["last_run"],
                next_run=r["next_run"], created_at=r["created_at"]
            )
            for r in rows
        ]

    def run_due_schedules(self) -> List[Dict[str, Any]]:
        due = self.get_due_schedules()
        results = []
        for sched in due:
            try:
                self._apply_action(sched.device_id, sched.action)
                next_run = sched.compute_next_run().isoformat()
                with _LOCK, _get_conn(self.db_path) as conn:
                    conn.execute(
                        "UPDATE schedules SET last_run=?, next_run=? WHERE id=?",
                        (datetime.utcnow().isoformat(), next_run, sched.id)
                    )
                results.append({"schedule_id": sched.id, "status": "ok"})
            except Exception as e:
                results.append({"schedule_id": sched.id, "error": str(e)})
        return results

    def _apply_action(self, device_id: str, action: Dict[str, Any]) -> None:
        action_type = action.get("type", "state_update")
        if action_type == "toggle":
            self.toggle_device(device_id)
        elif action_type == "brightness":
            self.set_brightness(device_id, action["level"])
        elif action_type == "state_update":
            self._update_state(device_id, action.get("state", {}))
        else:
            raise ValueError(f"Unknown action type: {action_type}")

    # ── History ───────────────────────────────────────────────────────

    def _log_event(self, device_id: str, event_type: str,
                   payload: Dict[str, Any]) -> None:
        ts = datetime.utcnow().isoformat()
        with _LOCK, _get_conn(self.db_path) as conn:
            conn.execute(
                "INSERT INTO events (device_id, event_type, payload, ts) VALUES (?,?,?,?)",
                (device_id, event_type, json.dumps(payload), ts)
            )

    def get_device_history(self, device_id: str, hours: int = 24) -> List[Dict[str, Any]]:
        since = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
        with _get_conn(self.db_path) as conn:
            rows = conn.execute(
                "SELECT * FROM events WHERE device_id=? AND ts>=? ORDER BY ts DESC",
                (device_id, since)
            ).fetchall()
        return [
            {"id": r["id"], "device_id": r["device_id"],
             "event_type": r["event_type"],
             "payload": json.loads(r["payload"]), "ts": r["ts"]}
            for r in rows
        ]

    def get_room_status(self, room: str) -> Dict[str, Any]:
        devices = self.list_devices(room=room)
        on_count = sum(1 for d in devices if d.state.get("on", False))
        return {
            "room": room,
            "device_count": len(devices),
            "on_count": on_count,
            "devices": [
                {"id": d.id, "name": d.name, "type": d.type,
                 "state": d.state, "online": d.online}
                for d in devices
            ]
        }

    def get_all_rooms(self) -> List[str]:
        with _get_conn(self.db_path) as conn:
            rows = conn.execute(
                "SELECT DISTINCT room FROM devices ORDER BY room"
            ).fetchall()
        return [r["room"] for r in rows]

    # ── Scheduler daemon ─────────────────────────────────────────────

    def start_scheduler(self, poll_seconds: int = 30) -> None:
        self._running = True
        def _loop():
            while self._running:
                try:
                    self.run_due_schedules()
                except Exception as e:
                    logger.error("Scheduler error: %s", e)
                time.sleep(poll_seconds)
        self._scheduler_thread = threading.Thread(target=_loop, daemon=True)
        self._scheduler_thread.start()

    def stop_scheduler(self) -> None:
        self._running = False


# ──────────────────────────── CLI ───────────────────────────────────

def demo() -> None:
    import os; os.remove(DB_PATH) if os.path.exists(DB_PATH) else None
    ctrl = SmartHomeController()

    # Add devices
    living_light = Device(
        id="light-001", name="Living Room Main", type="light", room="living_room",
        capabilities=[
            Capability("on_off"), Capability("brightness", 0, 100, "%"),
            Capability("color_temp", 2700, 6500, "K")
        ]
    )
    ctrl.add_device(living_light)

    thermostat = Device(
        id="thermo-001", name="Nest Thermostat", type="thermostat",
        room="living_room",
        capabilities=[Capability("on_off"), Capability("temperature", 15, 30, "°C")],
        state={"on": True, "current_temp": 20.5, "target_temp": 21.0, "mode": "auto"}
    )
    ctrl.add_device(thermostat)

    # Toggle & brightness
    print(ctrl.toggle_device("light-001"))
    print(ctrl.set_brightness("light-001", 75))
    print(ctrl.set_color_temp("light-001", 3000))

    # Scene
    ctrl.create_scene(
        "Movie Night",
        {"light-001": {"on": True, "brightness": 20, "color_temp": 2700}},
        description="Dim warm lights for movies", icon="🎬"
    )
    print(ctrl.run_scene("Movie Night"))

    # Schedule
    sched = ctrl.schedule_action(
        "light-001",
        {"type": "brightness", "level": 100},
        "0 7 * * *"   # every day at 07:00
    )
    print(f"Scheduled: {sched.id}, next={sched.next_run}")

    # History
    hist = ctrl.get_device_history("light-001", hours=1)
    print(f"Events in last 1h: {len(hist)}")

    # Room status
    print(ctrl.get_room_status("living_room"))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    demo()
