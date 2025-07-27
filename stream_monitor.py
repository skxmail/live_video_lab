#!/usr/bin/env python3
"""
Monitor de calidad de streaming DASH/HLS en tiempo real
Monitorea bitrate, buffer, errores, y calidad de reproducción
"""

import requests
import time
import json
import argparse
import logging
from datetime import datetime
from urllib.parse import urljoin, urlparse
import xml.etree.ElementTree as ET

class StreamMonitor:
    def __init__(self, manifest_url, output_file=None):
        self.manifest_url = manifest_url
        self.output_file = output_file or f"stream_quality_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        self.session = requests.Session()
        self.metrics = []
        
        # Configurar logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(f"stream_monitor_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def analyze_manifest(self):
        """Analiza el manifest DASH o HLS"""
        try:
            response = self.session.get(self.manifest_url, timeout=10)
            response.raise_for_status()
            
            content_type = response.headers.get('content-type', '')
            
            if 'mpd' in content_type or self.manifest_url.endswith('.mpd'):
                return self.analyze_dash_manifest(response.text)
            elif 'm3u8' in content_type or self.manifest_url.endswith('.m3u8'):
                return self.analyze_hls_manifest(response.text)
            else:
                self.logger.warning(f"Tipo de manifest no reconocido: {content_type}")
                return None
                
        except requests.RequestException as e:
            self.logger.error(f"Error al obtener manifest: {e}")
            return None
    
    def analyze_dash_manifest(self, manifest_content):
        """Analiza manifest DASH"""
        try:
            root = ET.fromstring(manifest_content)
            namespace = {'dash': 'urn:mpeg:dash:schema:mpd:2011'}
            
            # Extraer información básica
            period = root.find('.//dash:Period', namespace)
            adaptations = period.findall('.//dash:AdaptationSet', namespace) if period else []
            
            manifest_info = {
                'type': 'DASH',
                'adaptation_sets': len(adaptations),
                'video_streams': 0,
                'audio_streams': 0,
                'subtitle_streams': 0,
                'bitrates': [],
                'resolutions': [],
                'codecs': []
            }
            
            for adaptation in adaptations:
                content_type = adaptation.get('contentType', '')
                representations = adaptation.findall('.//dash:Representation', namespace)
                
                if content_type == 'video':
                    manifest_info['video_streams'] = len(representations)
                    for rep in representations:
                        bitrate = rep.get('bandwidth')
                        if bitrate:
                            manifest_info['bitrates'].append(int(bitrate))
                        
                        # Extraer resolución si está disponible
                        width = rep.get('width')
                        height = rep.get('height')
                        if width and height:
                            manifest_info['resolutions'].append(f"{width}x{height}")
                        
                        # Extraer codec
                        codec = rep.get('codecs')
                        if codec:
                            manifest_info['codecs'].append(codec)
                            
                elif content_type == 'audio':
                    manifest_info['audio_streams'] = len(representations)
                    
                elif content_type == 'text':
                    manifest_info['subtitle_streams'] = len(representations)
            
            return manifest_info
            
        except ET.ParseError as e:
            self.logger.error(f"Error al parsear manifest DASH: {e}")
            return None
    
    def analyze_hls_manifest(self, manifest_content):
        """Analiza manifest HLS"""
        lines = manifest_content.split('\n')
        manifest_info = {
            'type': 'HLS',
            'variants': 0,
            'bitrates': [],
            'resolutions': [],
            'codecs': []
        }
        
        for line in lines:
            line = line.strip()
            if line.startswith('#EXT-X-STREAM-INF'):
                manifest_info['variants'] += 1
                # Extraer bitrate
                if 'BANDWIDTH=' in line:
                    bitrate = line.split('BANDWIDTH=')[1].split(',')[0]
                    manifest_info['bitrates'].append(int(bitrate))
                # Extraer resolución
                if 'RESOLUTION=' in line:
                    resolution = line.split('RESOLUTION=')[1].split(',')[0]
                    manifest_info['resolutions'].append(resolution)
                # Extraer codec
                if 'CODECS=' in line:
                    codec = line.split('CODECS=')[1].split(',')[0].strip('"')
                    manifest_info['codecs'].append(codec)
        
        return manifest_info
    
    def check_segment_accessibility(self, segment_urls, max_checks=5):
        """Verifica la accesibilidad de los segmentos"""
        results = {
            'accessible_segments': 0,
            'failed_segments': 0,
            'response_times': [],
            'errors': []
        }
        
        for i, url in enumerate(segment_urls[:max_checks]):
            try:
                start_time = time.time()
                response = self.session.head(url, timeout=5)
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    results['accessible_segments'] += 1
                    results['response_times'].append(response_time)
                else:
                    results['failed_segments'] += 1
                    results['errors'].append(f"HTTP {response.status_code}: {url}")
                    
            except requests.RequestException as e:
                results['failed_segments'] += 1
                results['errors'].append(f"Error: {e}")
        
        if results['response_times']:
            results['avg_response_time'] = sum(results['response_times']) / len(results['response_times'])
        
        return results
    
    def collect_metrics(self):
        """Recolecta métricas del stream"""
        timestamp = datetime.now().isoformat()
        
        # Analizar manifest
        manifest_info = self.analyze_manifest()
        
        if not manifest_info:
            return None
        
        # Métricas básicas
        metrics = {
            'timestamp': timestamp,
            'manifest_url': self.manifest_url,
            'manifest_info': manifest_info,
            'network_info': {
                'status': 'unknown',
                'response_time': None,
                'error': None
            }
        }
        
        # Verificar conectividad
        try:
            start_time = time.time()
            response = self.session.get(self.manifest_url, timeout=10)
            response_time = time.time() - start_time
            
            metrics['network_info']['status'] = 'ok' if response.status_code == 200 else 'error'
            metrics['network_info']['response_time'] = response_time
            metrics['network_info']['http_status'] = response.status_code
            
        except requests.RequestException as e:
            metrics['network_info']['status'] = 'error'
            metrics['network_info']['error'] = str(e)
        
        # Calcular estadísticas de bitrate
        if manifest_info['bitrates']:
            metrics['bitrate_stats'] = {
                'min': min(manifest_info['bitrates']),
                'max': max(manifest_info['bitrates']),
                'avg': sum(manifest_info['bitrates']) / len(manifest_info['bitrates']),
                'count': len(manifest_info['bitrates'])
            }
        
        return metrics
    
    def monitor_stream(self, interval=30, duration=None):
        """Monitorea el stream continuamente"""
        self.logger.info(f"Iniciando monitoreo de: {self.manifest_url}")
        self.logger.info(f"Intervalo: {interval} segundos")
        if duration:
            self.logger.info(f"Duración: {duration} segundos")
        
        start_time = time.time()
        iteration = 0
        
        try:
            while True:
                iteration += 1
                self.logger.info(f"Iteración {iteration}: Recolectando métricas...")
                
                metrics = self.collect_metrics()
                if metrics:
                    self.metrics.append(metrics)
                    self.logger.info(f"Métricas recolectadas: {len(self.metrics)} total")
                    
                    # Guardar en archivo
                    with open(self.output_file, 'w') as f:
                        json.dump(self.metrics, f, indent=2)
                    
                    # Mostrar resumen
                    self.print_summary(metrics)
                
                # Verificar si debemos parar
                if duration and (time.time() - start_time) >= duration:
                    self.logger.info("Duración de monitoreo alcanzada")
                    break
                
                time.sleep(interval)
                
        except KeyboardInterrupt:
            self.logger.info("Monitoreo interrumpido por el usuario")
        
        self.logger.info(f"Monitoreo finalizado. Total de métricas: {len(self.metrics)}")
        self.generate_final_report()
    
    def print_summary(self, metrics):
        """Imprime un resumen de las métricas actuales"""
        print(f"\n=== RESUMEN {metrics['timestamp']} ===")
        print(f"Tipo: {metrics['manifest_info']['type']}")
        print(f"Estado red: {metrics['network_info']['status']}")
        
        if metrics['network_info']['response_time']:
            print(f"Tiempo respuesta: {metrics['network_info']['response_time']:.3f}s")
        
        if 'bitrate_stats' in metrics:
            stats = metrics['bitrate_stats']
            print(f"Bitrates: {stats['min']}-{stats['max']} kbps (avg: {stats['avg']:.0f})")
        
        if metrics['manifest_info']['resolutions']:
            print(f"Resoluciones: {', '.join(set(metrics['manifest_info']['resolutions']))}")
    
    def generate_final_report(self):
        """Genera un reporte final del monitoreo"""
        if not self.metrics:
            return
        
        report = {
            'summary': {
                'total_checks': len(self.metrics),
                'start_time': self.metrics[0]['timestamp'],
                'end_time': self.metrics[-1]['timestamp'],
                'manifest_url': self.manifest_url
            },
            'statistics': {}
        }
        
        # Estadísticas de red
        network_statuses = [m['network_info']['status'] for m in self.metrics]
        report['statistics']['network'] = {
            'success_rate': network_statuses.count('ok') / len(network_statuses) * 100,
            'total_errors': network_statuses.count('error')
        }
        
        # Estadísticas de bitrate
        bitrate_stats = [m['bitrate_stats'] for m in self.metrics if 'bitrate_stats' in m]
        if bitrate_stats:
            all_bitrates = []
            for stats in bitrate_stats:
                all_bitrates.extend([stats['min'], stats['max'], stats['avg']])
            
            report['statistics']['bitrate'] = {
                'min': min(all_bitrates),
                'max': max(all_bitrates),
                'avg': sum(all_bitrates) / len(all_bitrates)
            }
        
        # Guardar reporte final
        report_file = f"final_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        self.logger.info(f"Reporte final guardado en: {report_file}")
        print(f"\n=== REPORTE FINAL ===")
        print(f"Total de verificaciones: {report['summary']['total_checks']}")
        print(f"Tasa de éxito de red: {report['statistics']['network']['success_rate']:.1f}%")
        print(f"Errores totales: {report['statistics']['network']['total_errors']}")

def main():
    parser = argparse.ArgumentParser(description='Monitor de calidad de streaming DASH/HLS')
    parser.add_argument('manifest_url', help='URL del manifest DASH (.mpd) o HLS (.m3u8)')
    parser.add_argument('-i', '--interval', type=int, default=30, help='Intervalo de monitoreo en segundos (default: 30)')
    parser.add_argument('-d', '--duration', type=int, help='Duración total del monitoreo en segundos')
    parser.add_argument('-o', '--output', help='Archivo de salida para las métricas')
    
    args = parser.parse_args()
    
    monitor = StreamMonitor(args.manifest_url, args.output)
    monitor.monitor_stream(args.interval, args.duration)

if __name__ == '__main__':
    main() 