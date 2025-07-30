#!/usr/bin/env python3
"""
Stream Latency Analyzer - Analiza latencia y buffering de streams DASH/HLS
Uso: python3 stream_latency_analyzer.py <manifest_url> [options]
"""

import argparse
import json
import time
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from urllib.parse import urljoin
import threading
import os

import stream_analisys_common as common

class StreamLatencyAnalyzer:
    def __init__(self, manifest_url, output_dir="./latency_analysis", interval=5):
        self.manifest_url = manifest_url
        self.output_dir = output_dir
        self.interval = interval
        self.running = False
        
        # Crear directorio de salida
        os.makedirs(output_dir, exist_ok=True)
        
        # Archivos de salida
        self.latency_log = os.path.join(output_dir, "latency_analysis.json")
        self.report_file = os.path.join(output_dir, "latency_report.txt")
        
        # Inicializar datos
        self.latency_data = []
        self.session_start = datetime.now()
        
    def measure_manifest_latency(self):
        """Mide la latencia de respuesta del manifest"""
        start_time = time.time()
        try:
            response = requests.get(self.manifest_url, timeout=10)
            end_time = time.time()
            
            latency = (end_time - start_time) * 1000  # Convertir a ms
            
            return {
                'status': 'success',
                'latency_ms': latency,
                'http_status': response.status_code,
                'content_length': len(response.content),
                'timestamp': datetime.now().isoformat()
            }
        except requests.exceptions.Timeout:
            return {
                'status': 'timeout',
                'latency_ms': None,
                'error': 'Timeout al obtener manifest',
                'timestamp': datetime.now().isoformat()
            }
        except requests.exceptions.RequestException as e:
            return {
                'status': 'error',
                'latency_ms': None,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def analyze_segment_availability(self):
        """Analiza la disponibilidad de segmentos"""
        try:
            # Descargar y parsear el manifest
           
            root, namespace = common.fetch_mpd_root(self.manifest_url)

            # Extraer información de segmentos
            period = root.find('.//mpd:Period', namespace)
            if not period:
                return None
            
            # Buscar información de segmentación
            segment_info = {}
            
            adaptations = period.findall('.//mpd:AdaptationSet', namespace)
            for adaptation in adaptations:
                content_type = adaptation.get('contentType', '')
                if content_type == 'video':
                    representations = adaptation.findall('.//mpd:Representation', namespace)
                    for rep in representations:
                        segment_template = rep.find('.//mpd:SegmentTemplate', namespace)
                        if segment_template:
                            # Extraer información de segmentación
                            segment_duration = segment_template.get('duration')
                            timescale = segment_template.get('timescale', '1')
                            start_number = segment_template.get('startNumber', '1')
                            
                            if segment_duration:
                                segment_info = {
                                    'segment_duration': float(segment_duration) / float(timescale),
                                    'timescale': int(timescale),
                                    'start_number': int(start_number),
                                    'content_type': content_type
                                }
                                break
            
            return segment_info
            
        except Exception as e:
            print(f"Error analizando segmentos: {e}")
            return None
    
    def measure_segment_download_latency(self, segment_url):
        """Mide la latencia de descarga de un segmento"""
        start_time = time.time()
        try:
            response = requests.get(segment_url, timeout=30)
            end_time = time.time()
            
            latency = (end_time - start_time) * 1000  # Convertir a ms
            
            return {
                'status': 'success',
                'latency_ms': latency,
                'http_status': response.status_code,
                'content_length': len(response.content),
                'segment_url': segment_url,
                'timestamp': datetime.now().isoformat()
            }
        except requests.exceptions.Timeout:
            return {
                'status': 'timeout',
                'latency_ms': None,
                'error': 'Timeout al descargar segmento',
                'segment_url': segment_url,
                'timestamp': datetime.now().isoformat()
            }
        except requests.exceptions.RequestException as e:
            return {
                'status': 'error',
                'latency_ms': None,
                'error': str(e),
                'segment_url': segment_url,
                'timestamp': datetime.now().isoformat()
            }
    
    def get_segment_urls(self):
        """Obtiene URLs de segmentos del manifest"""
        try:
            response = requests.get(self.manifest_url, timeout=10)
            response.raise_for_status()
            
            root = ET.fromstring(response.content)
            namespace = {'mpd': 'urn:mpeg:dash:schema:mpd:2011'}
            
            segment_urls = []
            
            # Buscar segmentos de video
            adaptations = root.findall('.//mpd:AdaptationSet', namespace)
            for adaptation in adaptations:
                if adaptation.get('contentType') == 'video':
                    representations = adaptation.findall('.//mpd:Representation', namespace)
                    for rep in representations:
                        # Obtener el primer segmento como muestra
                        segment_template = rep.find('.//mpd:SegmentTemplate', namespace)
                        if segment_template:
                            media = segment_template.get('media')
                            if media:
                                # Construir URL del primer segmento
                                segment_url = urljoin(self.manifest_url, media.replace('$Number$', '1'))
                                segment_urls.append(segment_url)
                                break
            
            return segment_urls[:2]  # Limitar a 2 segmentos para análisis
            
        except Exception as e:
            print(f"Error obteniendo URLs de segmentos: {e}")
            return []
    
    def calculate_buffering_metrics(self, latency_history):
        """Calcula métricas de buffering basadas en latencia"""
        if not latency_history:
            return {}
        
        successful_latencies = [l['latency_ms'] for l in latency_history if l.get('latency_ms') is not None]
        
        if not successful_latencies:
            return {
                'avg_latency_ms': None,
                'min_latency_ms': None,
                'max_latency_ms': None,
                'latency_variance': None,
                'timeout_rate': 1.0,
                'error_rate': 1.0
            }
        
        avg_latency = sum(successful_latencies) / len(successful_latencies)
        min_latency = min(successful_latencies)
        max_latency = max(successful_latencies)
        
        # Calcular varianza
        variance = sum((x - avg_latency) ** 2 for x in successful_latencies) / len(successful_latencies)
        
        # Calcular tasas de error
        timeouts = len([l for l in latency_history if l.get('status') == 'timeout'])
        errors = len([l for l in latency_history if l.get('status') == 'error'])
        total = len(latency_history)
        
        timeout_rate = timeouts / total if total > 0 else 0
        error_rate = errors / total if total > 0 else 0
        
        return {
            'avg_latency_ms': avg_latency,
            'min_latency_ms': min_latency,
            'max_latency_ms': max_latency,
            'latency_variance': variance,
            'timeout_rate': timeout_rate,
            'error_rate': error_rate,
            'total_measurements': total,
            'successful_measurements': len(successful_latencies)
        }
    
    def run_analysis(self):
        """Ejecuta el análisis de latencia"""
        print(f"=== Análisis de Latencia de Stream ===")
        print(f"Manifest: {self.manifest_url}")
        print(f"Intervalo: {self.interval} segundos")
        print(f"Directorio de salida: {self.output_dir}")
        print()
        
        manifest_latency_history = []
        segment_latency_history = []
        
        while self.running:
            try:
                timestamp = datetime.now().isoformat()
                print(f"[{timestamp}] Analizando latencia...")
                
                # 1. Medir latencia del manifest
                manifest_result = self.measure_manifest_latency()
                manifest_latency_history.append(manifest_result)
                
                if manifest_result['status'] == 'success':
                    print(f"  ✓ Latencia manifest: {manifest_result['latency_ms']:.1f} ms")
                else:
                    print(f"  ✗ Error manifest: {manifest_result.get('error', 'Unknown')}")
                
                # 2. Analizar disponibilidad de segmentos
                segment_info = self.analyze_segment_availability()
                
                # 3. Medir latencia de segmentos
                segment_urls = self.get_segment_urls()
                segment_results = []
                
                for i, segment_url in enumerate(segment_urls):
                    segment_result = self.measure_segment_download_latency(segment_url)
                    segment_results.append(segment_result)
                    segment_latency_history.append(segment_result)
                    
                    if segment_result['status'] == 'success':
                        print(f"  ✓ Latencia segmento {i+1}: {segment_result['latency_ms']:.1f} ms")
                    else:
                        print(f"  ✗ Error segmento {i+1}: {segment_result.get('error', 'Unknown')}")
                
                # 4. Calcular métricas agregadas
                manifest_metrics = self.calculate_buffering_metrics(manifest_latency_history[-50:])  # Últimos 50
                segment_metrics = self.calculate_buffering_metrics(segment_latency_history[-50:])   # Últimos 50
                
                # 5. Crear resultado del análisis
                analysis_result = {
                    'timestamp': timestamp,
                    'manifest_latency': manifest_result,
                    'segment_latencies': segment_results,
                    'segment_info': segment_info,
                    'manifest_metrics': manifest_metrics,
                    'segment_metrics': segment_metrics,
                    'session_duration': (datetime.now() - self.session_start).total_seconds()
                }
                
                # Guardar resultado
                self.latency_data.append(analysis_result)
                self.save_results()
                
                # Mostrar resumen
                if manifest_metrics['avg_latency_ms']:
                    print(f"  📊 Latencia promedio manifest: {manifest_metrics['avg_latency_ms']:.1f} ms")
                if segment_metrics['avg_latency_ms']:
                    print(f"  📊 Latencia promedio segmentos: {segment_metrics['avg_latency_ms']:.1f} ms")
                
                print(f"  Esperando {self.interval} segundos...")
                time.sleep(self.interval)
                
            except KeyboardInterrupt:
                print("\nDetención solicitada por el usuario")
                break
            except Exception as e:
                print(f"Error en análisis: {e}")
                time.sleep(self.interval)
    
    # def flatten_dict(self, d, parent_key='', sep='.'):
    #     items = []
    #     for k, v in d.items():
    #         new_key = f"{parent_key}{sep}{k}" if parent_key else k
    #         if isinstance(v, dict):
    #             items.extend(self.flatten_dict(v, new_key, sep=sep).items())
    #         elif isinstance(v, list):
    #             items.append((new_key, str(v)))
    #         else:
    #             items.append((new_key, v))
    #     return dict(items)

    # def save_tabular_log(self, data, path):
    #     import csv
    #     if not data:
    #         return
    #     flat_entries = [self.flatten_dict(entry) for entry in data]
    #     all_keys = sorted({k for entry in flat_entries for k in entry})
    #     with open(path, 'w', newline='') as f:
    #         writer = csv.DictWriter(f, fieldnames=all_keys)
    #         writer.writeheader()
    #         for entry in flat_entries:
    #             writer.writerow(entry)

    def save_results(self):
        """Guarda los resultados en archivos"""
        common.save_results(self.latency_data, self.latency_log)

        # Generar reporte de texto
        self.generate_report()
    
    def generate_report(self):
        """Genera reporte de texto"""
        with open(self.report_file, 'w') as f:
            f.write("=== REPORTE DE LATENCIA DE STREAM ===\n")
            f.write(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Manifest: {self.manifest_url}\n")
            f.write(f"Duración de sesión: {self.session_duration:.1f} segundos\n")
            f.write(f"Total de análisis: {len(self.latency_data)}\n\n")
            
            if self.latency_data:
                latest = self.latency_data[-1]
                manifest_metrics = latest['manifest_metrics']
                segment_metrics = latest['segment_metrics']
                
                f.write("--- MÉTRICAS DE LATENCIA DEL MANIFEST ---\n")
                if manifest_metrics['avg_latency_ms']:
                    f.write(f"Latencia promedio: {manifest_metrics['avg_latency_ms']:.1f} ms\n")
                    f.write(f"Latencia mínima: {manifest_metrics['min_latency_ms']:.1f} ms\n")
                    f.write(f"Latencia máxima: {manifest_metrics['max_latency_ms']:.1f} ms\n")
                    f.write(f"Varianza: {manifest_metrics['latency_variance']:.2f}\n")
                f.write(f"Tasa de timeout: {manifest_metrics['timeout_rate']:.2%}\n")
                f.write(f"Tasa de error: {manifest_metrics['error_rate']:.2%}\n\n")
                
                f.write("--- MÉTRICAS DE LATENCIA DE SEGMENTOS ---\n")
                if segment_metrics['avg_latency_ms']:
                    f.write(f"Latencia promedio: {segment_metrics['avg_latency_ms']:.1f} ms\n")
                    f.write(f"Latencia mínima: {segment_metrics['min_latency_ms']:.1f} ms\n")
                    f.write(f"Latencia máxima: {segment_metrics['max_latency_ms']:.1f} ms\n")
                    f.write(f"Varianza: {segment_metrics['latency_variance']:.2f}\n")
                f.write(f"Tasa de timeout: {segment_metrics['timeout_rate']:.2%}\n")
                f.write(f"Tasa de error: {segment_metrics['error_rate']:.2%}\n\n")
                
                f.write("--- RECOMENDACIONES ---\n")
                if manifest_metrics['avg_latency_ms'] and manifest_metrics['avg_latency_ms'] > 1000:
                    f.write("⚠️  Latencia del manifest muy alta (>1s)\n")
                if segment_metrics['avg_latency_ms'] and segment_metrics['avg_latency_ms'] > 5000:
                    f.write("⚠️  Latencia de segmentos muy alta (>5s)\n")
                if manifest_metrics['timeout_rate'] > 0.1:
                    f.write("⚠️  Muchos timeouts en manifest (>10%)\n")
                if segment_metrics['timeout_rate'] > 0.1:
                    f.write("⚠️  Muchos timeouts en segmentos (>10%)\n")
                
                f.write("\n--- HISTORIAL DE LATENCIA ---\n")
                for i, analysis in enumerate(self.latency_data[-10:], 1):  # Últimos 10
                    manifest_lat = analysis['manifest_latency'].get('latency_ms', 'N/A')
                    if manifest_lat != 'N/A':
                        f.write(f"{i}. {analysis['timestamp']} - Manifest: {manifest_lat:.1f} ms\n")
    
    def start(self):
        """Inicia el análisis"""
        self.running = True
        self.run_analysis()
    
    def stop(self):
        """Detiene el análisis"""
        self.running = False
    
    @property
    def session_duration(self):
        return (datetime.now() - self.session_start).total_seconds()

def main():
    parser = argparse.ArgumentParser(description='Analiza latencia y buffering de streams DASH/HLS')
    parser.add_argument('manifest_url', help='URL del manifest DASH/HLS')
    parser.add_argument('-o', '--output', default='./latency_analysis', help='Directorio de salida')
    parser.add_argument('-i', '--interval', type=int, default=5, help='Intervalo de análisis en segundos')
    
    args = parser.parse_args()
    
    analyzer = StreamLatencyAnalyzer(args.manifest_url, args.output, args.interval)
    
    try:
        analyzer.start()
    except KeyboardInterrupt:
        print("\nDeteniendo análisis...")
        analyzer.stop()

if __name__ == "__main__":
    main() 