# Commute Data Logger

A dynamic, containerized Python application for continuously collecting, tracking, and analyzing real-world traffic data via the Google Maps Routes API.

---
## Motivation

This project was built to move beyond generic Google Maps estimates by gathering high-resolution, empirical commute data. By fetching and storing highly specific travel times over weeks or months, the data can be analyzed to identify true "rush hours," track seasonal variants, and make data-driven decisions on when to travel or move to new locations.

---
## Core Features

* **Dynamic REST API**: Fully rebuilt on FastAPI, allowing users to query routes synchronously or push complex background jobs into an event loop.
* **Smart Event Scheduler**: Rather than pulling manually, users can submit background jobs handling fixed intervals, exact times, or intelligent `peak_off_peak` strategies that automatically reduce polling frequency overnight to save API costs.
* **Multi-Destination & Bidirectional**: Service logic supports fanning out a single source to up to 100 destinations via flat JSON arrays. It automatically flips the query to capture the return trip by default.
* **Persistent Aliasing and Tracking**: Uses an embedded SQLite database (via SQLAlchemy) padded with hashing tools to stamp database rows with custom UUIDs, `job_id`s, and custom group `alias` names, making analytical multi-route grouping queries trivial.
* **Cascading Configuration**: Implements a clean hierarchy where hardcoded fallbacks are overridden by `config.yaml` defaults, which can in turn be selectively overridden by local `.env` values.
* **Container Ready**: Shipped with Docker and Docker Compose files to instantly boot the environment and let the background queues run seamlessly 24/7.

---
## Tech Stack

* **Backend**: Python 3.10+, FastAPI
* **Data Validations**: Pydantic
* **Database & ORM**: SQLite, SQLAlchemy
* **Testing**: Pytest (89%+ coverage)
* **Job Scheduler**: `schedule`, UUID memory management
* **Containerization**: Docker, Docker Compose
* **External Integrations**: Google Cloud Routes API

---
## Initialization & Configuration

### 1. Prerequisites
* Docker and Docker Compose configured on your system.
* A Google Cloud Platform project with the **Routes API** enabled and an active API Key.

### 2. Configuration Setup
The project uses a cascading config system (`config.yaml` -> `.env`).
1. Make a copy of `.env.example` named `.env`.
2. Insert your Google Maps Key.
```ini
# .env
GOOGLE_MAPS_API_KEY="AIzaSyYourKeyHere..."
```

*(Optional)* You can alter system-wide schedule cadence defaults by editing `config.yaml` directly:
```yaml
schedule:
  peak_interval_minutes: 5
  off_peak_interval_minutes: 30
  off_peak_start_time: "21:00"
  off_peak_end_time: "04:00"
```

### 3. Running the Application
Open a terminal in the project's root directory and run the following command to build the image and start the FastAPI service:
```Bash
docker-compose up --build -d
```
The application will boot, bind to port `8000`, and initialize the SQLite database within the `data/` volume.

---
## API Reference & Usage

The Commute Logger operates entirely via its REST API (default `http://localhost:8000`).

### 1. Manage Destination Batches
**`POST /destinations/batch`**
Instead of repeating large arrays of commute destinations, you can save a reusable set of destinations as a "batch alias".

**Example Payload:**
```json
{
  "alias": "routine",
  "destinations": ["Work", "Gym", "Groceries"]
}
```
*You can also fetch all saved destination batches via `GET /destinations/batch`, retrieve a specific batch via `GET /destinations/batch/{alias}`, or clear one using `DELETE /destinations/batch/{alias}`.*

### 2. Execute Immediate Query
**`POST /routes/query`**
Executes routing queries immediately against Google Maps, persists the data, and returns the results. It supports bulk arrays and automatic reverse-trip gathering.

**Example Payload:**
```json
{
  "routes": [
    {
      "source": "123 Main St, Boston, MA",
      "destinations": ["456 Market St, Boston", "789 Broad St, Boston"],
      "bidirectional": true,
      "alias": "morning_evals"
    },
    {
      "source": "Home",
      "destination_batch_alias": "routine"
    }
  ]
}
```
*Note: The array expands multiplicatively. For example, 1 source mapping to 2 destinations with bidirectional set to `true` will execute 4 discrete route fetches and return 4 result objects. Alternatively, passing `destination_batch_alias` auto-expands into all destinations registered under that batch alias. Additionally, providing an `alias` label alongside an explicitly defined route will idempotently save or update that configuration in your database for future shorthand use! The API will append a creation receipt object to your response to confirm it was saved.*

### 3. Schedule Background Jobs
**`POST /routes/schedule`**
Kicks off background jobs for the requested routes based on a customized schedule. Limits cap active jobs at 10.

**Example Payload (Intelligent Peak Tracking):**
```json
{
  "routes": [
    {
      "source": "Downtown Office",
      "destination": "Home Suburbs",
      "alias": "daily_commute"
    }
  ],
  "schedule": {
    "schedule_type": "peak_off_peak",
    "peak_interval_minutes": 5,
    "off_peak_interval_minutes": 30,
    "peak_start_time": "06:00",
    "peak_stop_time": "19:00"
  }
}
```

### 4. Retrieve Active Schedules
**`GET /routes/schedule`**
Returns metadata about all active tracking jobs currently spinning in the event loop.

```json
{
  "active_jobs_count": 1,
  "max_jobs_allowed": 10,
  "jobs": [
    {
      "job_id": "job-a1b2c3d4",
      "schedule_type": "peak_off_peak",
      "routes_count": 1,
      "next_run": "See internal logs - trackably managed"
    }
  ]
}
```

---
## Managing Data & Reports

All traffic interactions, whether manual or scheduled, are persistently logged to `data/traffic_data.db`. Because the application actively stamps `route_group_id` hashes and payload `alias` elements into the SQLAlchemy schema during execution, extracting complex longitudinal reports out of standard SQLite viewers (like DB Browser) requires minimal SQL knowledge.

*Example Data-Warehouse Strategy:*
```sql
SELECT timestamp, duration_seconds 
FROM traffic_data 
WHERE alias = 'morning_evals';
```

*(Note: Data retention is persistent through Docker volumes; tearing down the container will not wipe the historical collection database).*