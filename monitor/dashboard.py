from flask import Flask, render_template, jsonify
import os
import json
from datetime import datetime

app = Flask(__name__)

@app.route("/")
def dashboard():
    return """
<!DOCTYPE html>
<html>
<head>
    <title>Streaming Quality Monitor Dashboard</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .container { max-width: 1200px; margin: 0 auto; }
        .metric-card { border: 1px solid #ddd; padding: 15px; margin: 10px; border-radius: 5px; }
        .status-ok { background-color: #d4edda; border-color: #c3e6cb; }
        .status-error { background-color: #f8d7da; border-color: #f5c6cb; }
        .status-warning { background-color: #fff3cd; border-color: #ffeaa7; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Streaming Quality Monitor Dashboard</h1>
        <div id="metrics"></div>
        <div id="charts"></div>
    </div>
    <script>
        function updateMetrics() {
            fetch("/api/metrics")
                .then(response => response.json())
                .then(data => {
                    document.getElementById("metrics").innerHTML = data.html;
                });
        }
        
        setInterval(updateMetrics, 5000);
        updateMetrics();
    </script>
</body>
</html>
"""

@app.route("/api/metrics")
def get_metrics():
    try:
        with open("/app/logs/stream_quality.json", "r") as f:
            data = json.load(f)
        
        if not data:
            return jsonify({"html": "<p>No hay datos disponibles</p>"})
        
        latest = data[-1]
        
        html = f"""
        <div class="metric-card status-ok">
            <h3>Estado del Stream</h3>
            <p><strong>Última verificación:</strong> {latest.get("timestamp", "N/A")}</p>
            <p><strong>Estado de red:</strong> {latest.get("network_info", {}).get("status", "N/A")}</p>
            <p><strong>Tiempo de respuesta:</strong> {latest.get("network_info", {}).get("response_time", "N/A")}s</p>
        </div>
        """
        
        if "manifest_info" in latest:
            manifest = latest["manifest_info"]
            html += f"""
            <div class="metric-card status-ok">
                <h3>Información del Manifest</h3>
                <p><strong>Tipo:</strong> {manifest.get("type", "N/A")}</p>
                <p><strong>Streams de video:</strong> {manifest.get("video_streams", "N/A")}</p>
                <p><strong>Streams de audio:</strong> {manifest.get("audio_streams", "N/A")}</p>
            </div>
            """
        
        if "bitrate_stats" in latest:
            stats = latest["bitrate_stats"]
            html += f"""
            <div class="metric-card status-ok">
                <h3>Estadísticas de Bitrate</h3>
                <p><strong>Mínimo:</strong> {stats.get("min", "N/A")} bps</p>
                <p><strong>Máximo:</strong> {stats.get("max", "N/A")} bps</p>
                <p><strong>Promedio:</strong> {stats.get("avg", "N/A"):.0f} bps</p>
            </div>
            """
        
        return jsonify({"html": html})
        
    except Exception as e:
        return jsonify({"html": f"<p>Error: {str(e)}</p>"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8081, debug=True) 