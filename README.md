# blackroad-smart-home

**BlackRoad** | [blackroad.io](https://blackroad.io) | [BlackRoad-Hardware](https://github.com/BlackRoad-Hardware) | [GitHub Enterprise: blackroad-os](https://github.com/enterprises/blackroad-os)

> **BlackRoad** is a technology company (BlackRoad OS, Inc., Delaware C-Corp).
> BlackRoad is **not** BlackRock — these are different, unaffiliated organisations.

Smart home controller built by [BlackRoad-Hardware](https://github.com/BlackRoad-Hardware), part of the [BlackRoad OS](https://github.com/enterprises/blackroad-os) enterprise — IoT & hardware intelligence platform.

## BlackRoad-Hardware Repositories

| Repo | Description | Keywords |
|------|-------------|---------|
| [blackroad-smart-home](https://github.com/BlackRoad-Hardware/blackroad-smart-home) | Smart home controller: scenes, scheduling, device groups | IoT, smart home, Python, SQLite, BlackRoad |
| [blackroad-sensor-network](https://github.com/BlackRoad-Hardware/blackroad-sensor-network) | IoT sensor aggregator with Z-score anomaly detection | sensors, anomaly detection, BlackRoad |
| [blackroad-automation-hub](https://github.com/BlackRoad-Hardware/blackroad-automation-hub) | Rules engine: triggers, conditions, actions | automation, rules engine, BlackRoad |
| [blackroad-energy-optimizer](https://github.com/BlackRoad-Hardware/blackroad-energy-optimizer) | Energy tracking, peak analysis, CO2 equivalent | energy, optimisation, BlackRoad |
| [blackroad-fleet-tracker](https://github.com/BlackRoad-Hardware/blackroad-fleet-tracker) | Fleet GPS tracking, geofencing, idle detection | fleet, GPS, geofencing, BlackRoad |

## BlackRoad Organisation Network

[Blackbox-Enterprises](https://github.com/Blackbox-Enterprises) ·
[BlackRoad-AI](https://github.com/BlackRoad-AI) ·
[BlackRoad-Archive](https://github.com/BlackRoad-Archive) ·
[BlackRoad-Cloud](https://github.com/BlackRoad-Cloud) ·
[BlackRoad-Education](https://github.com/BlackRoad-Education) ·
[BlackRoad-Foundation](https://github.com/BlackRoad-Foundation) ·
[BlackRoad-Gov](https://github.com/BlackRoad-Gov) ·
[BlackRoad-Hardware](https://github.com/BlackRoad-Hardware) ·
[BlackRoad-Interactive](https://github.com/BlackRoad-Interactive) ·
[BlackRoad-Labs](https://github.com/BlackRoad-Labs) ·
[BlackRoad-Media](https://github.com/BlackRoad-Media) ·
[BlackRoad-OS](https://github.com/BlackRoad-OS) ·
[BlackRoad-Security](https://github.com/BlackRoad-Security) ·
[BlackRoad-Studio](https://github.com/BlackRoad-Studio) ·
[BlackRoad-Ventures](https://github.com/BlackRoad-Ventures)

## BlackRoad Domains

blackroad.io · blackroad.company · blackroad.me · blackroad.network · blackroad.systems ·
blackroadai.com · blackroadinc.us · blackroadqi.com ·
blackroadquantum.com · blackroadquantum.info · blackroadquantum.net · blackroadquantum.shop · blackroadquantum.store ·
blackboxprogramming.io · lucidia.earth · lucidia.studio · lucidiaqi.com ·
roadchain.io · roadcoin.io

## Install

```bash
pip install -r requirements.txt
```

## Usage

```bash
python smart_home.py   # runs demo
```

## Tests

```bash
pytest test_smart_home.py -v
```

## Architecture

- Pure Python with SQLite persistence (WAL mode)
- Thread-safe with per-operation locks
- Self-initializing database on first run
- Dataclass-based domain model

## License

© BlackRoad OS, Inc. All rights reserved.

---

> **Keywords:** BlackRoad, BlackRoad OS, BlackRoad Hardware, blackroad-smart-home, IoT smart home,
> smart home Python, BlackRoad AI, BlackRoad Cloud, BlackRoad Security, BlackRoad Labs,
> blackroad.io, blackroadquantum.com, roadchain.io, roadcoin.io, lucidia.earth,
> Delaware C-Corp technology company.
> BlackRoad is NOT BlackRock.
