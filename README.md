# Commute Data Logger

A simple, containerized Python application for continuously collecting and storing real-world traffic data for a specific commute.

---
### Motivation

This project was built to move beyond generic estimates and gather high-resolution, empirical data about my daily commute. The goal is to collect raw travel time information over several weeks to analyze patterns, identify the true "rush hours," and make data-driven decisions on the best times to travel.

---
### Features

* **Continuous Monitoring**: Runs 24/7 in a Docker container to log data over long periods.
* **Dynamic Scheduling**: Automatically reduces polling frequency during off-peak hours (e.g., overnight) to save resources and API calls.
* **Bidirectional Collection**: Can be configured to collect data for both legs of a commute (e.g., Home -> Work and Work -> Home).
* **Modern API**: Uses Google's efficient Routes API for accurate, real-time traffic data.
* **Persistent Storage**: Saves all collected data to a local SQLite database that persists across container restarts.
* **Easy Management**: Includes a simple shell script to view logs, back up the database, or reset the study.

---
### Tech Stack

* **Backend**: Python 3.10
* **Containerization**: Docker, Docker Compose
* **Database**: SQLite
* **Key Libraries**:
    * **SQLAlchemy**: For robust ORM-based database interaction.
    * **Schedule**: For managing the dynamic peak/off-peak job scheduling.
    * **Requests**: For communicating with the Google Routes API.
* **External API**: Google Cloud Routes API

---
### ## Getting Started

#### **1. Prerequisites**

* Docker and Docker Compose must be installed on your system.
* A Google Cloud Platform project with the **Routes API** enabled.
* A Google Maps API key.

#### **2. Configuration**

1.  Clone or download this repository.
2.  Rename the `.env.example` file to `.env`.
3.  Open the `.env` file and fill in the required values:

```ini
# .env

# Your Google Maps API key
GOOGLE_MAPS_API_KEY="YOUR_GOOGLE_MAPS_API_KEY_HERE"

# The start and end points of your commute
START_POINT="123 Main St, Anytown, USA"
END_POINT="456 Business Rd, Workville, USA"

# Set to "true" to collect data for the return trip as well
COLLECT_RETURN_TRIP="true"

# The interval for data collection during peak hours
COLLECTION_INTERVAL_MINUTES=5
```

3. Running the Application

Open a terminal in the project's root directory and run the following command to build the image and start the service in the background:

```Bash
docker-compose up --build -d
```
The application will now start collecting data according to the schedule defined in the code.

### Managing the Service

A simple management script is included for common operations.

- View live logs:

```Bash
./manage.sh logs
```
- Stop the service:

```Bash
./manage.sh stop
```
- Create a timestamped backup of the database:

```bash
./manage.sh backup
```
- Wipe all data and start a new study:

```bash
./manage.sh wipe
```
### Accessing the Data

All collected data is stored in the data/traffic_data.db file. You can access this file using any standard SQLite database viewer (like DB Browser for SQLite) to query and analyze the results.