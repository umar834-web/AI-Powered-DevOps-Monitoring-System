
import time
import psutil
import requests
from prometheus_client import start_http_server, Gauge

# Existing Prometheus metrics — names preserved
cpu_usage = Gauge(
    "windows_cpu_usage_percent",
    "Current CPU usage percentage"
)

memory_usage = Gauge(
    "windows_memory_usage_percent",
    "Current virtual memory usage percentage"
)

memory_available_bytes = Gauge(
    "windows_memory_available_bytes",
    "Available physical memory in bytes"
)

disk_usage = Gauge(
    "windows_disk_usage_percent",
    "Used percentage of the system drive"
)

disk_free_bytes = Gauge(
    "windows_disk_free_bytes",
    "Free space on the system drive in bytes"
)

network_sent_bytes = Gauge(
    "windows_network_sent_bytes_total",
    "Bytes sent over network interfaces"
)

network_received_bytes = Gauge(
    "windows_network_received_bytes_total",
    "Bytes received over network interfaces"
)

system_uptime_seconds = Gauge(
    "windows_system_uptime_seconds",
    "Seconds since system boot"
)

# Alert configuration
ALERT_URL = "http://localhost:8001/api/alerts"

THRESHOLDS = {
    "cpu": 80.0,
    "memory": 85.0,
    "disk": 90.0,
}

# Tracks whether each threshold is currently breached.
# One alert is sent on entering a breach; another can be sent
# after the metric recovers and breaches again.
alert_active = {
    "cpu": False,
    "memory": False,
    "disk": False,
}

def check_and_send_alert(component, value):
    threshold = THRESHOLDS[component]
    breached = value > threshold

    if not breached:
        alert_active[component] = False
        return

    if alert_active[component]:
        return

    alert_name = {
        "cpu": "HighCPUUsage",
        "memory": "HighMemoryUsage",
        "disk": "HighDiskUsage",
    }[component]

    payload = {
        "alerts": [
            {
                "status": "firing",
                "labels": {
                    "alertname": alert_name,
                    "severity": "warning",
                    "component": component,
                    "instance": "localhost",
                },
                "annotations": {
                    "summary": f"High {component} usage detected",
                    "description": (
                        f"{component.upper()} usage is {value:.1f}%, "
                        f"above the configured threshold of "
                        f"{threshold:.1f}%."
                    ),
                },
                "values": {
                    "A": value,
                },
            }
        ]
    }

    try:
        response = requests.post(
            ALERT_URL,
            json=payload,
            timeout=5,
        )
        response.raise_for_status()

        alert_active[component] = True
        print(
            f"ALERT SENT: {component.upper()} "
            f"{value:.1f}% > {threshold:.1f}%"
        )

    except requests.RequestException as error:
        print(
            f"Alert delivery failed for {component}: {error}"
        )


# Start Prometheus metrics endpoint
start_http_server(8000)

boot_time = psutil.boot_time()

print("Windows Multi-Metric Monitoring Agent started.")
print("Metrics: http://localhost:8000/metrics")
print(f"Alert receiver: {ALERT_URL}")

while True:
    try:
        # CPU
        cpu = psutil.cpu_percent(interval=1)
        cpu_usage.set(cpu)

        # Memory
        memory = psutil.virtual_memory()
        memory_usage.set(memory.percent)
        memory_available_bytes.set(memory.available)

        # Disk
        disk = psutil.disk_usage("C:\\")
        disk_usage.set(disk.percent)
        disk_free_bytes.set(disk.free)

        # Network
        network = psutil.net_io_counters()
        network_sent_bytes.set(network.bytes_sent)
        network_received_bytes.set(network.bytes_recv)

        # Uptime
        system_uptime_seconds.set(time.time() - boot_time)

        print(
            f"CPU: {cpu:.1f}% | "
            f"Memory: {memory.percent:.1f}% | "
            f"Disk: {disk.percent:.1f}%"
        )

        # Deliver alerts to FastAPI
        check_and_send_alert("cpu", cpu)
        check_and_send_alert("memory", memory.percent)
        check_and_send_alert("disk", disk.percent)

    except Exception as error:
        print(f"Monitoring error: {error}")

    time.sleep(5)
