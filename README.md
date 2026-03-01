# blackroad-smart-home

> **Production-grade smart home controller** — part of the [BlackRoad OS](https://github.com/BlackRoad-Hardware) IoT & hardware intelligence platform.

---

## Table of Contents

1. [Overview](#overview)
2. [BlackRoad OS Ecosystem](#blackroad-os-ecosystem)
3. [Features](#features)
4. [Requirements](#requirements)
5. [Installation](#installation)
6. [Quick Start](#quick-start)
7. [API Reference](#api-reference)
   - [Devices](#devices)
   - [Device Groups](#device-groups)
   - [Scenes](#scenes)
   - [Scheduling](#scheduling)
   - [History & Reporting](#history--reporting)
8. [Architecture](#architecture)
9. [Database Schema](#database-schema)
10. [Stripe Integration](#stripe-integration)
11. [Testing](#testing)
    - [Unit Tests](#unit-tests)
    - [End-to-End Tests](#end-to-end-tests)
12. [Contributing](#contributing)
13. [License](#license)

---

## Overview

`blackroad-smart-home` is the device-control core of the BlackRoad OS platform. It provides a thread-safe, SQLite-backed Python library for managing smart home devices, rooms, groups, scenes, and cron-based schedules — all with full event history.

It is published as a standalone **PyPI package** and integrates with the BlackRoad billing layer via **Stripe** for subscription-gated feature access.

---

## BlackRoad OS Ecosystem

| Repository | Description |
|---|---|
| **blackroad-smart-home** | Smart home controller: devices, groups, scenes, scheduling, history |
| blackroad-sensor-network | IoT sensor aggregator with Z-score anomaly detection |
| blackroad-automation-hub | Rules engine: triggers, conditions, actions |
| blackroad-energy-optimizer | Energy tracking, peak analysis, CO₂ equivalent |
| blackroad-fleet-tracker | Fleet GPS tracking, geofencing, idle detection |

---

## Features

- **Device management** — add, retrieve, list, and update any smart home device (lights, thermostats, locks, plugs, sensors)
- **Device groups** — batch-control multiple devices as a single unit
- **Scenes** — save and instantly replay named device-state snapshots (e.g. *Movie Night*, *Good Morning*)
- **Cron scheduling** — schedule device actions using standard cron expressions, with automatic next-run computation
- **Event history** — every state change is written to a tamper-evident SQLite event log, queryable by device and time window
- **Room reporting** — aggregate on/off status and device inventory by room
- **Thread-safe** — all writes are protected by a module-level lock; safe for concurrent WSGI/ASGI use
- **WAL-mode SQLite** — high-concurrency reads with minimal write contention
- **Zero external services** — runs entirely offline; integrates with cloud services via optional Stripe billing layer

---

## Requirements

- Python 3.10 or higher
- `croniter >= 2.0.0`

---

## Installation

### pip (recommended)

```bash
pip install blackroad-smart-home
```

### From source

```bash
git clone https://github.com/BlackRoad-Hardware/blackroad-smart-home.git
cd blackroad-smart-home
pip install -e ".[dev]"
```

### Legacy requirements file

```bash
pip install -r requirements.txt
```

---

## Quick Start

```python
from smart_home import SmartHomeController, Device, Capability

ctrl = SmartHomeController()          # self-initialises SQLite DB

# Register a device
ctrl.add_device(Device(
    id="light-001",
    name="Living Room Main",
    type="light",
    room="living_room",
    capabilities=[
        Capability("on_off"),
        Capability("brightness", 0, 100, "%"),
        Capability("color_temp", 2700, 6500, "K"),
    ]
))

# Control it
ctrl.toggle_device("light-001")
ctrl.set_brightness("light-001", 75)
ctrl.set_color_temp("light-001", 3000)

# Create and activate a scene
ctrl.create_scene(
    "Movie Night",
    {"light-001": {"on": True, "brightness": 20, "color_temp": 2700}},
    description="Dim warm lights for movies",
    icon="🎬",
)
ctrl.run_scene("Movie Night")

# Schedule lights on at 07:00 every day
ctrl.schedule_action(
    "light-001",
    {"type": "brightness", "level": 100},
    "0 7 * * *",
)
```

Run the bundled demo:

```bash
python smart_home.py
```

---

## API Reference

### Devices

| Method | Signature | Description |
|---|---|---|
| `add_device` | `(device: Device) → Device` | Register or replace a device |
| `get_device` | `(device_id: str) → Device \| None` | Fetch a single device |
| `list_devices` | `(room=None, type_filter=None) → List[Device]` | List devices with optional filters |
| `toggle_device` | `(device_id: str) → dict` | Flip on/off state |
| `set_brightness` | `(device_id: str, level: int) → dict` | Set brightness 0–100 |
| `set_color_temp` | `(device_id: str, kelvin: int) → dict` | Set colour temperature 2700–6500 K |
| `set_thermostat` | `(device_id, target_temp, mode) → dict` | Set thermostat target and mode |
| `get_room_status` | `(room: str) → dict` | Aggregate status for a room |
| `get_all_rooms` | `() → List[str]` | List all known rooms |

### Device Groups

| Method | Signature | Description |
|---|---|---|
| `add_group` | `(group: DeviceGroup) → DeviceGroup` | Register or replace a group |
| `get_group` | `(group_id: str) → DeviceGroup \| None` | Fetch a group |
| `toggle_group` | `(group_id: str) → List[dict]` | Toggle every device in a group |

### Scenes

| Method | Signature | Description |
|---|---|---|
| `create_scene` | `(name, device_states, description, icon) → Scene` | Save a named scene |
| `run_scene` | `(scene_name: str) → dict` | Apply a scene to all target devices |
| `list_scenes` | `() → List[Scene]` | Enumerate all saved scenes |

### Scheduling

| Method | Signature | Description |
|---|---|---|
| `schedule_action` | `(device_id, action, cron_expr) → Schedule` | Register a recurring schedule |
| `get_due_schedules` | `() → List[Schedule]` | Fetch all schedules due now |
| `run_due_schedules` | `() → List[dict]` | Execute all due schedules |
| `start_scheduler` | `(poll_seconds=30)` | Start background scheduler thread |
| `stop_scheduler` | `()` | Stop the background scheduler |

### History & Reporting

| Method | Signature | Description |
|---|---|---|
| `get_device_history` | `(device_id, hours=24) → List[dict]` | Event log for a device |

---

## Architecture

- **Pure Python** — no framework dependency; embeds in any Python application
- **SQLite with WAL mode** — high-concurrency reads, atomic writes, zero configuration
- **Dataclass domain model** — `Device`, `DeviceGroup`, `Scene`, `Schedule`, `Capability`
- **Thread-safe writes** — module-level `threading.Lock` guards all `INSERT`/`UPDATE` operations
- **Self-initialising** — `SmartHomeController.__init__` calls `init_db()` on first run; no migration tooling required
- **Scheduler daemon** — optional background thread polls due schedules every *N* seconds (default 30)

---

## Database Schema

```
devices          – id, name, type, room, state (JSON), capabilities (JSON),
                   online, firmware, created_at
device_groups    – id, name, device_ids (JSON), description
scenes           – name (PK), device_states (JSON), description, icon, created_at
schedules        – id, device_id, action (JSON), cron_expr, enabled,
                   last_run, next_run, created_at
events           – id (auto), device_id, event_type, payload (JSON), ts
                   INDEX: idx_events_device (device_id, ts)
```

---

## Stripe Integration

Subscription and billing management for BlackRoad OS is handled via [Stripe](https://stripe.com). The smart-home library is gated behind the **BlackRoad Pro** plan.

**Configuration**

Set the following environment variables before starting your application:

```bash
export STRIPE_SECRET_KEY="sk_live_..."
export STRIPE_WEBHOOK_SECRET="whsec_..."
export BLACKROAD_PLAN_ID="price_..."
```

**Subscription flow**

1. Customer checks out via the BlackRoad billing portal (powered by Stripe Checkout).
2. Stripe sends a `customer.subscription.created` webhook to your endpoint.
3. Your webhook handler enables the `blackroad-smart-home` feature flag for the customer.
4. On subsequent requests the application verifies the active subscription before invoking `SmartHomeController`.

**Webhook verification example**

```python
import stripe

def handle_webhook(payload: bytes, sig_header: str) -> None:
    event = stripe.Webhook.construct_event(
        payload, sig_header, STRIPE_WEBHOOK_SECRET
    )
    if event["type"] == "customer.subscription.created":
        activate_smart_home_for(event["data"]["object"]["customer"])
```

Refer to the [Stripe documentation](https://stripe.com/docs/webhooks) for full webhook integration guidance.

---

## Testing

### Unit Tests

All unit tests are written with **pytest** and use an isolated in-memory SQLite database per test.

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run the full test suite
pytest test_smart_home.py -v
```

Expected output (10 tests, 0 failures):

```
test_smart_home.py::test_toggle_device            PASSED
test_smart_home.py::test_set_brightness           PASSED
test_smart_home.py::test_brightness_out_of_range  PASSED
test_smart_home.py::test_create_and_run_scene     PASSED
test_smart_home.py::test_schedule_action          PASSED
test_smart_home.py::test_device_history           PASSED
test_smart_home.py::test_get_room_status          PASSED
test_smart_home.py::test_list_devices_filter      PASSED
test_smart_home.py::test_group_toggle             PASSED
test_smart_home.py::test_scene_missing_raises     PASSED

10 passed in 0.xx s
```

### End-to-End Tests

The end-to-end flow exercises the full stack from device registration through scene activation to history retrieval:

```bash
python smart_home.py        # executes the built-in demo scenario
```

The demo script:
1. Creates a SQLite database from scratch
2. Registers two devices (smart light + thermostat)
3. Toggles and dims the light, changes colour temperature
4. Creates and activates the *Movie Night* scene
5. Schedules a morning brightness action (cron `0 7 * * *`)
6. Reads back the event history and room status

A clean run with no exceptions and correct printed output confirms the E2E path is healthy.

---

## Contributing

1. Fork the repository and create a feature branch.
2. Write or update tests for your changes.
3. Ensure `pytest test_smart_home.py -v` passes with zero failures.
4. Open a pull request against `main` with a clear description.

---

## License

© BlackRoad OS, Inc. All rights reserved.

