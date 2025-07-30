#!/usr/bin/env python3
"""
Stream Analysis Suite - Suite completa de análisis de streams DASH/HLS
Integra todas las herramientas de análisis en una sola interfaz
Uso: python3 stream_analysis_suite.py <manifest_url> [options]
"""

import argparse
import json
import time
import threading
import os
import sys
from datetime import datetime
import subprocess

# Importar los analizadores
from stream_quality_analyzer import StreamQualityAnalyzer
from stream_latency_analyzer import StreamLatencyAnalyzer
from stream_adaptation_analyzer import StreamAdaptationAnalyzer

class StreamAnalysisSuite:
    def __init__(self, manifest_url, output_dir="./stream_analysis", interval=30):
        self.manifest_url = manifest_url
        self.output_dir = output_dir
        self.interval = interval
        self.running = False
        
        # Crear directorio principal
        os.makedirs(output_dir, exist_ok=True)
        
        # Subdirectorios para cada tipo de análisis
        self.quality_dir = os.path.join(output_dir, "quality")
        self.latency_dir = os.path.join(output_dir, "latency")
        self.adaptation_dir = os.path.join(output_dir, "adaptation")
        
        # Crear subdirectorios
        os.makedirs(self.quality_dir, exist_ok=True)
        os.makedirs(self.latency_dir, exist_ok=True)
        os.makedirs(self.adaptation_dir, exist_ok=True)
        
        # Archivos de salida
        self.suite_log = os.path.join(output_dir, "analysis_suite.json")
        self.suite_report = os.path.join(output_dir, "comprehensive_report.txt")
        self.dashboard_data = os.path.join(output_dir, "dashboard_data.json")
        
        # Inicializar analizadores
        self.quality_analyzer = StreamQualityAnalyzer(manifest_url, self.quality_dir, interval)
        self.latency_analyzer = StreamLatencyAnalyzer(manifest_url, self.latency_dir, interval//6)  # Más frecuente
        self.adaptation_analyzer = StreamAdaptationAnalyzer(manifest_url, self.adaptation_dir, interval//3)
        
        # Datos agregados
        self.suite_data = []
        self.session_start = datetime.now()
        
    def start_analyzers(self):
        """Inicia todos los analizadores en hilos separados"""
        print("Iniciando analizadores...")
        
        # Hilo para análisis de calidad
        self.quality_thread = threading.Thread(target=self.quality_analyzer.start)
        self.quality_thread.daemon = True
        self.quality_thread.start()
        
        # Hilo para análisis de latencia
        self.latency_thread = threading.Thread(target=self.latency_analyzer.start)
        self.latency_thread.daemon = True
        self.latency_thread.start()
        
        # Hilo para análisis de adaptación
        self.adaptation_thread = threading.Thread(target=self.adaptation_analyzer.start)
        self.adaptation_thread.daemon = True
        self.adaptation_thread.start()
        
        print("✓ Todos los analizadores iniciados")
    
    def stop_analyzers(self):
        """Detiene todos los analizadores"""
        print("Deteniendo analizadores...")
        
        self.quality_analyzer.stop()
        self.latency_analyzer.stop()
        self.adaptation_analyzer.stop()
        
        # Esperar a que terminen los hilos
        if hasattr(self, 'quality_thread'):
            self.quality_thread.join(timeout=5)
        if hasattr(self, 'latency_thread'):
            self.latency_thread.join(timeout=5)
        if hasattr(self, 'adaptation_thread'):
            self.adaptation_thread.join(timeout=5)
        
        print("✓ Todos los analizadores detenidos")
    
    def aggregate_results(self):
        """Agrega resultados de todos los analizadores"""
        try:
            # Leer datos de cada analizador
            quality_data = []
            latency_data = []
            adaptation_data = []
            
            # Calidad
            quality_file = os.path.join(self.quality_dir, "stream_quality_analysis.json")
            if os.path.exists(quality_file):
                with open(quality_file, 'r') as f:
                    quality_data = json.load(f)
            
            # Latencia
            latency_file = os.path.join(self.latency_dir, "latency_analysis.json")
            if os.path.exists(latency_file):
                with open(latency_file, 'r') as f:
                    latency_data = json.load(f)
            
            # Adaptación
            adaptation_file = os.path.join(self.adaptation_dir, "adaptation_analysis.json")
            if os.path.exists(adaptation_file):
                with open(adaptation_file, 'r') as f:
                    adaptation_data = json.load(f)
            
            # Crear resumen agregado
            aggregated_result = {
                'timestamp': datetime.now().isoformat(),
                'session_duration': (datetime.now() - self.session_start).total_seconds(),
                'quality_analysis': {
                    'total_analyses': len(quality_data),
                    'latest_analysis': quality_data[-1] if quality_data else None
                },
                'latency_analysis': {
                    'total_analyses': len(latency_data),
                    'latest_analysis': latency_data[-1] if latency_data else None
                },
                'adaptation_analysis': {
                    'total_analyses': len(adaptation_data),
                    'latest_analysis': adaptation_data[-1] if adaptation_data else None
                }
            }
            
            # Calcular métricas agregadas
            aggregated_result['overall_metrics'] = self.calculate_overall_metrics(
                quality_data, latency_data, adaptation_data
            )
            
            return aggregated_result
            
        except Exception as e:
            print(f"Error agregando resultados: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def calculate_overall_metrics(self, quality_data, latency_data, adaptation_data):
        """Calcula métricas generales del sistema"""
        overall_metrics = {
            'stream_health_score': 0.0,
            'quality_score': 0.0,
            'latency_score': 0.0,
            'adaptation_score': 0.0,
            'recommendations': []
        }
        
        # Calcular score de calidad
        if quality_data:
            latest_quality = quality_data[-1]
            if latest_quality.get('aggregate_metrics'):
                avg_ssim = latest_quality['aggregate_metrics'].get('avg_ssim', 0)
                if avg_ssim:
                    val = avg_ssim
                else:
                    val = 0.0
                overall_metrics['quality_score'] = min(1.0, avg_ssim)
        
        # Calcular score de latencia
        if latency_data:
            latest_latency = latency_data[-1]
            if latest_latency.get('manifest_metrics'):
                avg_latency = latest_latency['manifest_metrics'].get('avg_latency_ms', 0)
                if avg_latency:
                    # Score basado en latencia (menor es mejor)
                    overall_metrics['latency_score'] = max(0.0, 1.0 - (avg_latency / 1000))
        
        # Calcular score de adaptación
        if adaptation_data:
            latest_adaptation = adaptation_data[-1]
            if latest_adaptation.get('aggregate_metrics'):
                stability = latest_adaptation['aggregate_metrics'].get('stability_score', 0)
                overall_metrics['adaptation_score'] = stability
        
        # Calcular score general
        scores = [
            overall_metrics['quality_score'],
            overall_metrics['latency_score'],
            overall_metrics['adaptation_score']
        ]
        overall_metrics['stream_health_score'] = sum(scores) / len(scores)
        
        # Generar recomendaciones
        if overall_metrics['quality_score'] < 0.7:
            overall_metrics['recommendations'].append("Calidad de video baja - revisar configuración de codificación")
        
        if overall_metrics['latency_score'] < 0.8:
            overall_metrics['recommendations'].append("Latencia alta - optimizar red o servidor")
        
        if overall_metrics['adaptation_score'] < 0.6:
            overall_metrics['recommendations'].append("Inestabilidad en adaptación - revisar configuración de bitrates")
        
        return overall_metrics
    
    def generate_dashboard_data(self):
        """Genera datos para el dashboard"""
        aggregated_result = self.aggregate_results()
        if not aggregated_result:
            return
        
        # Formato simplificado para el dashboard
        dashboard_data = {
            'timestamp': aggregated_result['timestamp'],
            'overall_health': aggregated_result['overall_metrics']['stream_health_score'],
            'quality_score': aggregated_result['overall_metrics']['quality_score'],
            'latency_score': aggregated_result['overall_metrics']['latency_score'],
            'adaptation_score': aggregated_result['overall_metrics']['adaptation_score'],
            'recommendations': aggregated_result['overall_metrics']['recommendations'],
            'session_duration': aggregated_result['session_duration']
        }
        
        # Agregar métricas específicas si están disponibles
        if aggregated_result['quality_analysis']['latest_analysis']:
            quality = aggregated_result['quality_analysis']['latest_analysis']
            if quality.get('aggregate_metrics'):
                dashboard_data['avg_bitrate'] = quality['aggregate_metrics'].get('avg_bitrate', 0)
                dashboard_data['avg_ssim'] = quality['aggregate_metrics'].get('avg_ssim', 0)
        
        if aggregated_result['latency_analysis']['latest_analysis']:
            latency = aggregated_result['latency_analysis']['latest_analysis']
            if latency.get('manifest_metrics'):
                dashboard_data['avg_latency_ms'] = latency['manifest_metrics'].get('avg_latency_ms', 0)
        
        if aggregated_result['adaptation_analysis']['latest_analysis']:
            adaptation = aggregated_result['adaptation_analysis']['latest_analysis']
            if adaptation.get('aggregate_metrics'):
                dashboard_data['stability_score'] = adaptation['aggregate_metrics'].get('stability_score', 0)
                dashboard_data['switching_events'] = adaptation['aggregate_metrics'].get('total_switching_events', 0)
        
        # Guardar datos del dashboard
        with open(self.dashboard_data, 'w') as f:
            json.dump(dashboard_data, f, indent=2)
        
        return dashboard_data
    
    def run_suite(self):
        """Ejecuta la suite completa de análisis"""
        print(f"=== Stream Analysis Suite ===")
        print(f"Manifest: {self.manifest_url}")
        print(f"Directorio de salida: {self.output_dir}")
        print(f"Intervalo principal: {self.interval} segundos")
        print()
        
        # Iniciar analizadores
        self.start_analyzers()
        
        # Bucle principal
        while self.running:
            try:
                timestamp = datetime.now().isoformat()
                print(f"[{timestamp}] Ejecutando análisis completo...")
                
                # Agregar resultados
                aggregated_result = self.aggregate_results()
                if aggregated_result:
                    self.suite_data.append(aggregated_result)
                    
                    # Generar datos del dashboard
                    dashboard_data = self.generate_dashboard_data()
                    
                    # Mostrar resumen
                    metrics = aggregated_result['overall_metrics']
                    print(f"  📊 Health Score: {metrics['stream_health_score']:.3f}")
                    print(f"  📊 Quality: {metrics['quality_score']:.3f}")
                    print(f"  📊 Latency: {metrics['latency_score']:.3f}")
                    print(f"  📊 Adaptation: {metrics['adaptation_score']:.3f}")
                    
                    if metrics['recommendations']:
                        print(f"  ⚠️  Recomendaciones: {len(metrics['recommendations'])}")
                
                # Guardar resultados
                self.save_results()
                
                print(f"  Esperando {self.interval} segundos...")
                time.sleep(self.interval)
                
            except KeyboardInterrupt:
                print("\nDetención solicitada por el usuario")
                break
            except Exception as e:
                print(f"Error en suite: {e}")
                time.sleep(self.interval)
    
    def flatten_dict(self, d, parent_key='', sep='.'):
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self.flatten_dict(v, new_key, sep=sep).items())
            elif isinstance(v, list):
                items.append((new_key, str(v)))
            else:
                items.append((new_key, v))
        return dict(items)

    def save_tabular_log(self, data, path):
        import csv
        if not data:
            return
        flat_entries = [self.flatten_dict(entry) for entry in data]
        all_keys = sorted({k for entry in flat_entries for k in entry})
        with open(path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=all_keys)
            writer.writeheader()
            for entry in flat_entries:
                writer.writerow(entry)

    def save_results(self):
        """Guarda los resultados de la suite"""
        # Guardar datos JSON
        with open(self.suite_log, 'w') as f:
            json.dump(self.suite_data, f, indent=2)
        
        self.save_tabular_log(self.suite_data, self.suite_log.replace('.json', '.csv'))
        # Generar reporte
        self.generate_comprehensive_report()
    
    def generate_comprehensive_report(self):
        """Genera reporte comprehensivo"""
        with open(self.suite_report, 'w') as f:
            f.write("=== REPORTE COMPREHENSIVO DE STREAM ===\n")
            f.write(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Manifest: {self.manifest_url}\n")
            f.write(f"Duración de sesión: {self.session_duration:.1f} segundos\n")
            f.write(f"Total de análisis: {len(self.suite_data)}\n\n")
            
            if self.suite_data:
                latest = self.suite_data[-1]
                metrics = latest['overall_metrics']
                
                f.write("--- PUNTUACIONES GENERALES ---\n")
                f.write(f"Health Score: {metrics['stream_health_score']:.3f}\n")
                f.write(f"Quality Score: {metrics['quality_score']:.3f}\n")
                f.write(f"Latency Score: {metrics['latency_score']:.3f}\n")
                f.write(f"Adaptation Score: {metrics['adaptation_score']:.3f}\n\n")
                
                f.write("--- RECOMENDACIONES ---\n")
                for rec in metrics['recommendations']:
                    f.write(f"• {rec}\n")
                
                f.write("\n--- RESUMEN DE ANÁLISIS ---\n")
                f.write(f"Análisis de calidad: {latest['quality_analysis']['total_analyses']}\n")
                f.write(f"Análisis de latencia: {latest['latency_analysis']['total_analyses']}\n")
                f.write(f"Análisis de adaptación: {latest['adaptation_analysis']['total_analyses']}\n")
                
    
    def start(self):
        """Inicia la suite de análisis"""
        self.running = True
        self.run_suite()
    
    def stop(self):
        """Detiene la suite de análisis"""
        self.running = False
        self.stop_analyzers()
    
    @property
    def session_duration(self):
        return (datetime.now() - self.session_start).total_seconds()

def main():
    parser = argparse.ArgumentParser(description='Suite completa de análisis de streams DASH/HLS')
    parser.add_argument('manifest_url', help='URL del manifest DASH/HLS')
    parser.add_argument('-o', '--output', default='./stream_analysis', help='Directorio de salida')
    parser.add_argument('-i', '--interval', type=int, default=30, help='Intervalo de análisis en segundos')
    parser.add_argument('--quality-only', action='store_true', help='Solo análisis de calidad')
    parser.add_argument('--latency-only', action='store_true', help='Solo análisis de latencia')
    parser.add_argument('--adaptation-only', action='store_true', help='Solo análisis de adaptación')
    
    args = parser.parse_args()
    
    if args.quality_only:
        print("Ejecutando solo análisis de calidad...")
        analyzer = StreamQualityAnalyzer(args.manifest_url, args.output, args.interval)
        try:
            analyzer.start()
        except KeyboardInterrupt:
            analyzer.stop()
    elif args.latency_only:
        print("Ejecutando solo análisis de latencia...")
        analyzer = StreamLatencyAnalyzer(args.manifest_url, args.output, args.interval//6)
        try:
            analyzer.start()
        except KeyboardInterrupt:
            analyzer.stop()
    elif args.adaptation_only:
        print("Ejecutando solo análisis de adaptación...")
        analyzer = StreamAdaptationAnalyzer(args.manifest_url, args.output, args.interval//3)
        try:
            analyzer.start()
        except KeyboardInterrupt:
            analyzer.stop()
    else:
        print("Ejecutando suite completa de análisis...")
        suite = StreamAnalysisSuite(args.manifest_url, args.output, args.interval)
        try:
            suite.start()
        except KeyboardInterrupt:
            print("\nDeteniendo suite...")
            suite.stop()

if __name__ == "__main__":
    main() 