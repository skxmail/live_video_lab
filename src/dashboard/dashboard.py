from flask import Flask, render_template, jsonify, send_file
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
        # Intentar leer datos de la suite de análisis primero
        suite_data_file = "/app/stream_analysis/dashboard_data.json"
        if os.path.exists(suite_data_file):
            with open(suite_data_file, "r") as f:
                suite_data = json.load(f)
            
            # Determinar estado basado en health score
            health_score = suite_data.get('overall_health', 0)
            if health_score >= 0.8:
                status_class = "status-ok"
                status_text = "EXCELENTE"
            elif health_score >= 0.6:
                status_class = "status-ok"
                status_text = "BUENO"
            elif health_score >= 0.4:
                status_class = "status-warning"
                status_text = "REGULAR"
            else:
                status_class = "status-error"
                status_text = "CRÍTICO"
            
            html = f"""
            <div class="metric-card {status_class}">
                <h3>Estado del Stream - {status_text}</h3>
                <p><strong>Health Score:</strong> {health_score:.3f}</p>
                <p><strong>Última actualización:</strong> {suite_data.get('timestamp', 'N/A')}</p>
                <p><strong>Duración de sesión:</strong> {suite_data.get('session_duration', 0):.1f}s</p>
            </div>
            """
            
            # Métricas de calidad
            quality_score = suite_data.get('quality_score', 0)
            avg_bitrate = suite_data.get('avg_bitrate', 0)
            avg_ssim = suite_data.get('avg_ssim', 0)
            
            html += f"""
            <div class="metric-card status-ok">
                <h3>Métricas de Calidad</h3>
                <p><strong>Quality Score:</strong> {quality_score:.3f}</p>
                <p><strong>Bitrate promedio:</strong> {avg_bitrate/1000:.1f} kbps</p>
                <p><strong>SSIM promedio:</strong> {avg_ssim:.4f}</p>
            </div>
            """
            
            # Métricas de latencia
            latency_score = suite_data.get('latency_score', 0)
            avg_latency = suite_data.get('avg_latency_ms', 0)
            
            html += f"""
            <div class="metric-card status-ok">
                <h3>Métricas de Latencia</h3>
                <p><strong>Latency Score:</strong> {latency_score:.3f}</p>
                <p><strong>Latencia promedio:</strong> {avg_latency:.1f} ms</p>
            </div>
            """
            
            # Métricas de adaptación
            adaptation_score = suite_data.get('adaptation_score', 0)
            stability_score = suite_data.get('stability_score', 0)
            switching_events = suite_data.get('switching_events', 0)
            
            html += f"""
            <div class="metric-card status-ok">
                <h3>Métricas de Adaptación</h3>
                <p><strong>Adaptation Score:</strong> {adaptation_score:.3f}</p>
                <p><strong>Estabilidad:</strong> {stability_score:.3f}</p>
                <p><strong>Eventos de switching:</strong> {switching_events}</p>
            </div>
            """
            
            # Recomendaciones
            recommendations = suite_data.get('recommendations', [])
            if recommendations:
                rec_html = ""
                for rec in recommendations:
                    rec_html += f"<p>• {rec}</p>"
                
                html += f"""
                <div class="metric-card status-warning">
                    <h3>Recomendaciones</h3>
                    {rec_html}
                </div>
                """
            
            # Información del sistema
            # html += f"""
            # <div class="metric-card status-ok">
            #     <h3>Información del Sistema</h3>
            #     <p><strong>Dashboard:</strong> http://localhost:38881</p>
            #     <p><strong>Player:</strong> http://localhost:38880</p>
            #     <p><strong>Suite de análisis:</strong> Activa</p>
            # </div>
            # """
            
            html += """
            <div class="metric-card status-ok">
                <h3>Gráfico de Adaptación de Bitrate</h3>
                <img src="/adaptation/bitrate_adaptation.png?ts={}" alt="Bitrate Adaptation" style="max-width:100%;">
            </div>
            """.format(int(datetime.now().timestamp()))

            return jsonify({"html": html})
        
        # Fallback a datos del monitor básico
        if not os.path.exists("/app/logs/stream_quality.json"):
            return jsonify({
                "html": """
                <div class="metric-card status-warning">
                    <h3>Estado del Sistema</h3>
                    <p><strong>Estado:</strong> Esperando datos del monitor</p>
                    <p><strong>Archivo de datos:</strong> No encontrado</p>
                    <p><strong>Servicio:</strong> stream-monitor debe estar ejecutándose</p>
                    <p><strong>Sugerencia:</strong> Ejecutar suite de análisis para métricas avanzadas</p>
                </div>
                """
            })
        
        with open("/app/logs/stream_quality.json", "r") as f:
            data = json.load(f)
        
        if not data:
            return jsonify({
                "html": """
                <div class="metric-card status-warning">
                    <h3>Estado del Sistema</h3>
                    <p><strong>Estado:</strong> Sin datos de monitoreo</p>
                    <p><strong>Archivo:</strong> stream_quality.json está vacío</p>
                    <p><strong>Acción:</strong> Verificar que el stream esté activo</p>
                </div>
                """
            })
        
        latest = data[-1]
        
        # Determinar el estado basado en los datos
        status_class = "status-ok"
        status_text = "OK"
        
        if "network_info" in latest:
            network_status = latest["network_info"].get("status", "unknown")
            if network_status != "ok":
                status_class = "status-error"
                status_text = "ERROR"
        
        html = f"""
        <div class="metric-card {status_class}">
            <h3>Estado del Stream - {status_text}</h3>
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
        
        # Agregar información del sistema
        # html += f"""
        # <div class="metric-card status-ok">
        #     <h3>Información del Sistema</h3>
        #     <p><strong>Total de registros:</strong> {len(data)}</p>
        #     <p><strong>Dashboard:</strong> http://localhost:38881</p>
        #     <p><strong>Player:</strong> http://localhost:38880</p>
        #     <p><strong>Modo:</strong> Monitor básico</p>
        # </div>
        # """
        
        return jsonify({"html": html})
        
    except Exception as e:
        return jsonify({
            "html": f"""
            <div class="metric-card status-error">
                <h3>Error del Sistema</h3>
                <p><strong>Error:</strong> {str(e)}</p>
                <p><strong>Archivo:</strong> /app/logs/stream_quality.json</p>
                <p><strong>Acción:</strong> Verificar logs del contenedor</p>
            </div>
            """
        })

@app.route("/adaptation/bitrate_adaptation.png")
def adaptation_plot():
    path = "/app/stream_analysis/adaptation/bitrate_adaptation.png"
    if os.path.exists(path):
        return send_file(path, mimetype="image/png")
    return "No plot available", 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8081, debug=True) 