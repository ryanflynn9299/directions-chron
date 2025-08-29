#!/bin/bash
# A simple management script for the traffic-monitor docker container.

# --- Configuration ---
DB_FILE="./data/traffic_data.db"
STATE_FILE="./data/study_state.json"
BACKUP_DIR="./data"

# Function to print usage
usage() {
    echo "Usage: $0 {logs|start|stop|restart|wipe|backup}"
    echo "Commands:"
    echo "  logs      Follow the container logs in real-time."
    echo "  start     Start the services in the background."
    echo "  stop      Stop and remove the services."
    echo "  restart   Restart the services."
    echo "  wipe      Stop, delete all data, and start fresh."
    echo "  backup    Create a timestamped backup of the database."
}

# --- Command Functions ---

logs() {
    echo "--> Following container logs. Press Ctrl+C to exit."
    docker-compose logs -f
}

start() {
    echo "--> Starting services in detached mode..."
    docker-compose up --build -d
}

stop() {
    echo "--> Stopping and removing services..."
    docker-compose down
}

restart() {
    echo "--> Restarting services..."
    docker-compose restart
}

wipe() {
    echo "--> WARNING: This will permanently delete all collected data."
    read -p "Are you sure you want to continue? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "--> Stopping and removing container..."
        docker-compose down

        if [ -f "$DB_FILE" ]; then
            echo "--> Deleting database file: $DB_FILE"
            rm "$DB_FILE"
        fi

        if [ -f "$STATE_FILE" ]; then
            echo "--> Deleting state file: $STATE_FILE"
            rm "$STATE_FILE"
        fi

        echo "--> Wipe complete. Starting fresh..."
        start
    else
        echo "--> Wipe aborted."
    fi
}

backup() {
    if [ -f "$DB_FILE" ]; then
        TIMESTAMP=$(date +%Y-%m-%d_%H%M%S)
        BACKUP_FILE="${BACKUP_DIR}/traffic_data_backup_${TIMESTAMP}.db"
        echo "--> Backing up database to ${BACKUP_FILE}..."
        cp "$DB_FILE" "$BACKUP_FILE"
        echo "--> Backup complete."
    else
        echo "--> Database file not found. Nothing to back up."
    fi
}


# --- Main Logic ---
COMMAND=$1
if [ -z "$COMMAND" ]; then
    usage
    exit 1
fi

case $COMMAND in
    logs) logs ;;
    start) start ;;
    stop|down) stop ;;
    restart) restart ;;
    wipe) wipe ;;
    backup) backup ;;
    *)
        echo "Error: Unknown command '$COMMAND'"
        usage
        exit 1
        ;;
esac

exit 0