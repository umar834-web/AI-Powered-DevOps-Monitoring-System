
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import time
import requests

app = FastAPI(title="AI DevOps Alert Receiver")


# ==================================================
# CONFIGURATION
# ==================================================

METRICS_URL = "http://localhost:8000/metrics"
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.2"

# Keep the existing React frontend origin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================================================
# IN-MEMORY STORAGE
# ==================================================

alerts = []

# Used to calculate network throughput between requests.
_previous_network = None
_previous_network_time = None


# ==================================================
# HEALTH CHECK
# ==================================================

@app.get("/")
def home():
    return {
        "status": "Alert receiver is running"
    }


# ==================================================
# RECEIVE ALERTS
# Supports Grafana and Python-generated alerts.
# ==================================================

@app.post("/api/alerts")
async def receive_alert(alert: dict):
    incident = {
        "received_at": datetime.now().isoformat(),
        "alert": alert
    }

    alerts.append(incident)

    print("\n" + "=" * 60)
    print("🚨 ALERT RECEIVED")
    print("=" * 60)
    print(alert)
    print("=" * 60 + "\n")

    return {
        "status": "received",
        "message": "Alert received successfully",
        "count": len(alerts)
    }


# ==================================================
# GET ALERT HISTORY
# ==================================================

@app.get("/api/alerts")
def get_alerts():
    return {
        "count": len(alerts),
        "alerts": alerts
    }


# ==================================================
# LIVE SYSTEM METRICS
# Reads metrics exported by monitor.py.
# ==================================================

@app.get("/api/metrics")
def get_live_metrics():
    global _previous_network, _previous_network_time

    try:
        response = requests.get(
            METRICS_URL,
            timeout=3
        )
        response.raise_for_status()

        # Prometheus metric name -> API response field.
        metric_names = {
            "windows_cpu_usage_percent": "cpu_percent",
            "windows_memory_usage_percent": "memory_percent",
            "windows_memory_available_bytes": "memory_available_bytes",
            "windows_disk_usage_percent": "disk_percent",
            "windows_disk_free_bytes": "disk_free_bytes",
            "windows_network_sent_bytes_total": "network_sent_bytes",
            "windows_network_received_bytes_total": "network_received_bytes",
            "windows_system_uptime_seconds": "uptime_seconds",
        }

        metrics = {}

        for line in response.text.splitlines():
            if not line or line.startswith("#"):
                continue

            parts = line.split()

            if len(parts) < 2:
                continue

            metric_name = parts[0]

            if metric_name not in metric_names:
                continue

            try:
                metrics[metric_names[metric_name]] = float(parts[1])
            except ValueError:
                continue

        # Verify that the essential metrics exist.
        required_metrics = [
            "cpu_percent",
            "memory_percent",
            "disk_percent",
        ]

        missing = [
            name for name in required_metrics
            if name not in metrics
        ]

        if missing:
            return {
                "status": "error",
                "message": "Missing metrics: " + ", ".join(missing),
                "metrics": metrics,
            }

        # Calculate network throughput from counter changes.
        now = time.time()

        sent = metrics.get("network_sent_bytes", 0.0)
        received = metrics.get("network_received_bytes", 0.0)

        sent_rate = 0.0
        received_rate = 0.0

        if _previous_network is not None:
            previous_sent, previous_received = _previous_network
            elapsed = now - _previous_network_time

            if elapsed > 0:
                # Handle counter resets/reboots without negative rates.
                sent_rate = max(0.0, sent - previous_sent) / elapsed
                received_rate = max(
                    0.0, received - previous_received
                ) / elapsed

        _previous_network = (sent, received)
        _previous_network_time = now

        metrics["network_sent_bytes_per_second"] = round(
            sent_rate, 2
        )
        metrics["network_received_bytes_per_second"] = round(
            received_rate, 2
        )

        metrics["status"] = "online"
        metrics["timestamp"] = datetime.now().isoformat()

        return metrics

    except requests.exceptions.RequestException as error:
        return {
            "status": "offline",
            "message": (
                "Could not read metrics from the monitoring agent. "
                "Check that monitor.py is running on port 8000."
            ),
            "detail": str(error),
        }


# ==================================================
# AI INCIDENT ANALYSIS
# ==================================================

@app.post("/api/analyze")
async def analyze_incident(incident: dict):
    try:
        # Accept either a stored incident or a raw alert payload.
        alert = incident.get("alert", incident)

        first_alert = {}

        if alert.get("alerts"):
            first_alert = alert["alerts"][0]

        labels = (
            first_alert.get("labels")
            or alert.get("commonLabels")
            or {}
        )

        annotations = (
            first_alert.get("annotations")
            or alert.get("commonAnnotations")
            or {}
        )

        values = first_alert.get("values") or {}

        alert_name = labels.get(
            "alertname", "Unknown alert"
        )

        severity = labels.get(
            "severity", "unknown"
        )

        component = labels.get(
            "component", "unknown"
        ).lower()

        instance = labels.get(
            "instance", "unknown"
        )

        summary = annotations.get(
            "summary", "No summary provided"
        )

        description = annotations.get(
            "description", "No description provided"
        )

        # The Grafana A value represents the alert query result.
        # It is not necessarily a CPU value.
        metric_value = values.get("A")

        if metric_value is None:
            metric_value = values.get("value")

        metric_label = {
            "cpu": "CPU usage",
            "memory": "Memory usage",
            "disk": "Disk usage",
            "network": "Network activity",
            "uptime": "System uptime",
        }.get(component, f"{component.capitalize()} metric")

        # Use OS-specific and component-specific guidance.
        component_guidance = {
            "cpu": (
                "For Windows, inspect Task Manager and Resource Monitor "
                "to identify processes consuming CPU."
            ),
            "memory": (
                "For Windows, inspect Task Manager and Resource Monitor. "
                "Check memory usage by process and available physical memory. "
                "Do not assume a memory leak without evidence."
            ),
            "disk": (
                "Check the affected drive's free space and identify large "
                "files or logs. Do not recommend deleting system files."
            ),
            "network": (
                "Inspect network throughput, interface status, and relevant "
                "connection or application logs."
            ),
        }.get(
            component,
            "Use relevant operating-system monitoring tools and logs."
        )

        prompt = f"""
You are an AI DevOps incident analysis assistant.

Analyze the monitoring incident below.

STRICT RULES:
1. Do not invent facts or claim a root cause has been confirmed.
2. Separate observed facts from possible causes.
3. Do not assume a specific process, application, Java/JVM,
   garbage collector, or Linux utility is installed.
4. Tailor recommendations to the reported component and Windows
   operating system when applicable.
5. The metric value is not necessarily CPU usage. Label it using
   the actual component.
6. Do not treat a warning as automatically critical.
7. Give practical, safe troubleshooting steps.
8. Do not recommend deleting system files or disabling security tools.
9. If information is missing, state what should be collected next.

OBSERVED INCIDENT:

Alert: {alert_name}
Severity: {severity}
Component: {component}
Server: {instance}
Metric: {metric_label}
Metric value: {
    metric_value if metric_value is not None else "Not provided"
}
Summary: {summary}
Description: {description}

Component-specific guidance:
{component_guidance}

Return exactly these sections:

INCIDENT SUMMARY
Briefly explain the alert.

OBSERVED FACTS
List only facts provided above.

POSSIBLE CAUSES
Give 3-5 relevant possibilities. Do not present them as confirmed.

RECOMMENDED ACTIONS
List safe troubleshooting steps in priority order.

SEVERITY ASSESSMENT
Assess Low, Medium, High, or Critical based on the supplied evidence.
Explain any uncertainty.

NEXT STEPS
Give the single most useful immediate investigation.
"""

        payload = {
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
        }

        response = requests.post(
            OLLAMA_URL,
            json=payload,
            timeout=120,
        )

        response.raise_for_status()

        result = response.json()

        analysis = result.get(
            "response",
            "No analysis returned by Ollama."
        )

        print("\n" + "=" * 60)
        print("🤖 AI INCIDENT ANALYSIS")
        print("=" * 60)
        print(f"Alert: {alert_name}")
        print(f"Component: {component}")
        print(analysis)
        print("=" * 60 + "\n")

        return {
            "status": "success",
            "analysis": analysis,
            "model": OLLAMA_MODEL,
            "alertname": alert_name,
            "component": component,
            "metric_value": metric_value,
        }

    except requests.exceptions.ConnectionError:
        return {
            "status": "error",
            "analysis": (
                "Ollama is not running or cannot be reached at "
                "http://localhost:11434. Start Ollama and ensure "
                "the configured model is available."
            ),
        }

    except requests.exceptions.Timeout:
        return {
            "status": "error",
            "analysis": (
                "The AI analysis timed out. Please try again."
            ),
        }

    except requests.exceptions.HTTPError as error:
        return {
            "status": "error",
            "analysis": f"Ollama returned an HTTP error: {error}",
        }

    except Exception as error:
        print(
            f"⚠️ AI analysis error: "
            f"{type(error).__name__}: {error}"
        )

        return {
            "status": "error",
            "analysis": "Unable to generate AI analysis.",
        }
