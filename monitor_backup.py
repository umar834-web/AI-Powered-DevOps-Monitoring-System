
import time
import psutil
from prometheus_client import start_http_server, Gauge

# Keep the existing CPU metric name for Grafana compatibility
cpu_usage = Gauge(
    "windows_cpu_usage_percent",
    "Current CPU usage percentage"
)

# Memory metrics
memory_usage = Gauge(
    "windows_memory_usage_percent",
    "Current virtual memory usage percentage"
)

memory_available_bytes = Gauge(
    "windows_memory_available_bytes",
    "Available physical memory in bytes"
)

# Disk metrics
disk_usage = Gauge(
    "windows_disk_usage_percent",
    "Used percentage of the system drive"
)

disk_free_bytes = Gauge(
    "windows_disk_free_bytes",
    "Free space on the system drive in bytes"
)

# Network metrics: cumulative bytes since system/network counter start
network_sent_bytes = Gauge(
    "windows_network_sent_bytes_total",
    "Bytes sent over network interfaces"
)

network_received_bytes = Gauge(
    "windows_network_received_bytes_total",
    "Bytes received over network interfaces"
)

# System availability
system_uptime_seconds = Gauge(
    "windows_system_uptime_seconds",
    "Seconds since system boot"
)

# Expose metrics to Prometheus
start_http_server(8000)

# Record the boot time once
boot_time = psutil.boot_time()

print("Windows Multi-Metric Monitoring Agent started...")
print("Prometheus metrics: http://localhost:8000/metrics")

while True:
    try:
        # CPU
        cpu = psutil.cpu_percent(interval=1)
        cpu_usage.set(cpu)

        # Memory
        memory = psutil.virtual_memory()
        memory_usage.set(memory.percent)
        memory_available_bytes.set(memory.available)

        # Disk: use the Windows system drive
        disk = psutil.disk_usage("C:\\")
        disk_usage.set(disk.percent)
        disk_free_bytes.set(disk.free)

        # Network: aggregate counters across interfaces
        network = psutil.net_io_counters()
        network_sent_bytes.set(network.bytes_sent)
        network_received_bytes.set(network.bytes_recv)

        # Uptime
        system_uptime_seconds.set(time.time() - boot_time)

        print(
            f"CPU: {cpu:.1f}% | "
            f"Memory: {memory.percent:.1f}% | "
            f"Disk: {disk.percent:.1f}% | "
            f"Network sent: {network.bytes_sent} bytes | "
            f"Network received: {network.bytes_recv} bytes"
        )

    except Exception as error:
        print(f"Monitoring error: {error}")

    time.sleep(5)
