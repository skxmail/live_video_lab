#!/usr/bin/env python3
"""
Stream Adaptation Analyzer - Analiza adaptación de bitrate y switching en streams DASH
Uso: python3 stream_adaptation_analyzer.py <manifest_url> [options]
"""

import argparse
import json
import time
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from urllib.parse import urljoin
import os
import matplotlib.pyplot as plt
import numpy as np

import stream_analisys_common as common

class StreamAdaptationAnalyzer:
    def __init__(self, manifest_url, output_dir="./adaptation_analysis", interval=10):
        self.manifest_url = manifest_url
        self.output_dir = output_dir
        self.interval = interval
        self.running = False
        
        # Crear directorio de salida
        os.makedirs(output_dir, exist_ok=True)
        
        # Archivos de salida
        self.adaptation_log = os.path.join(output_dir, "adaptation_analysis.json")
        self.report_file = os.path.join(output_dir, "adaptation_report.txt")
        self.chart_file = os.path.join(output_dir, "bitrate_adaptation.png")
        
        # Inicializar datos
        self.adaptation_data = []
        self.session_start = datetime.now()
        
        # Historial de bitrates
        self.bitrate_history = []
        self.switching_events = []
        
    def fetch_manifest_info(self):
        """Obtiene información detallada del manifest"""
        try:
            root, namespace = common.fetch_mpd_root(self.manifest_url)
            
            manifest_info = common.extract_manifest_info(root, namespace)
            
            # Extraer información del manifest
            manifest_info = {
                'type': 'DASH',
                'profiles': root.get('profiles', ''),
                'availabilityStartTime': root.get('availabilityStartTime', ''),
                'publishTime': root.get('publishTime', ''),
                'mediaPresentationDuration': root.get('mediaPresentationDuration', ''),
                'minimumUpdatePeriod': root.get('minimumUpdatePeriod', ''),
                'adaptation_sets': []
            }
            
            # Analizar adaptation sets
            period = root.find('.//mpd:Period', namespace)
            if period:
                adaptations = period.findall('.//mpd:AdaptationSet', namespace)
                
                for adaptation in adaptations:
                    content_type = adaptation.get('contentType', '')
                    adaptation_info = {
                        'contentType': content_type,
                        'id': adaptation.get('id', ''),
                        'representations': []
                    }
                    
                    representations = adaptation.findall('.//mpd:Representation', namespace)
                    for rep in representations:
                        rep_info = {
                            'id': rep.get('id', ''),
                            'bandwidth': int(rep.get('bandwidth', 0)),
                            'width': int(rep.get('width', 0)),
                            'height': int(rep.get('height', 0)),
                            'frameRate': rep.get('frameRate', ''),
                            'codecs': rep.get('codecs', ''),
                            'mimeType': rep.get('mimeType', ''),
                            'segment_template': {}
                        }
                        
                        # Información de segmentación
                        segment_template = rep.find('.//mpd:SegmentTemplate', namespace)
                        if segment_template:
                            rep_info['segment_template'] = {
                                'media': segment_template.get('media', ''),
                                'duration': segment_template.get('duration', ''),
                                'timescale': segment_template.get('timescale', ''),
                                'startNumber': segment_template.get('startNumber', '')
                            }
                        
                        adaptation_info['representations'].append(rep_info)
                    
                    manifest_info['adaptation_sets'].append(adaptation_info)
            
            return manifest_info
            
        except Exception as e:
            print(f"Error obteniendo manifest: {e}")
            return None
    
    def get_current_segment_info(self, representation_info):
        """Obtiene información del segmento actual"""
        try:
            segment_template = representation_info['segment_template']
            if not segment_template.get('media'):
                return None
            
            # Construir URL del segmento actual
            media_template = segment_template['media']
            # Asumimos que queremos el segmento más reciente disponible
            segment = segment_template['startNumber']
            segment_url = urljoin(self.manifest_url, media_template.replace('$Number$', segment))
            
            # Obtener información del segmento
            response = requests.head(segment_url, timeout=10)
            if response.status_code == 200:
                return {
                    'url': segment_url,
                    'size_bytes': int(response.headers.get('content-length', 0)),
                    'bitrate': representation_info['bandwidth'],
                    'resolution': f"{representation_info['width']}x{representation_info['height']}",
                    'codec': representation_info['codecs']
                }
            
        except Exception as e:
            print(f"Error obteniendo información de segmento: {e}")
        
        return None
    
    def analyze_adaptation_behavior(self):
        """Analiza el comportamiento de adaptación"""
        manifest_info = self.fetch_manifest_info()
        if not manifest_info:
            return None
        
        adaptation_analysis = {
            'timestamp': datetime.now().isoformat(),
            'manifest_info': manifest_info,
            'current_segments': [],
            'adaptation_metrics': {}
        }
        
        # Analizar cada adaptation set
        for adaptation_set in manifest_info['adaptation_sets']:
            if adaptation_set['contentType'] == 'video':
                representations = adaptation_set['representations']
                
                # Ordenar por bitrate
                representations.sort(key=lambda x: x['bandwidth'])
                
                # Obtener información de segmentos actuales
                current_segments = []
                for rep in representations:
                    segment_info = self.get_current_segment_info(rep)
                    if segment_info:
                        current_segments.append(segment_info)
                
                adaptation_analysis['current_segments'] = current_segments
                
                # Calcular métricas de adaptación
                if current_segments:
                    bitrates = [seg['bitrate'] for seg in current_segments]
                    adaptation_analysis['adaptation_metrics'] = {
                        'available_bitrates': bitrates,
                        'min_bitrate': min(bitrates),
                        'max_bitrate': max(bitrates),
                        'bitrate_range': max(bitrates) - min(bitrates),
                        'bitrate_levels': len(bitrates),
                        'current_bitrate': bitrates[0],  # Asumimos el más bajo como actual
                        'resolutions': list(set([seg['resolution'] for seg in current_segments]))
                    }
        
        return adaptation_analysis
    
    def detect_switching_events(self, current_analysis):
        """Detecta eventos de cambio de bitrate"""
        if not self.bitrate_history:
            self.bitrate_history.append(current_analysis)
            return []
        
        previous_analysis = self.bitrate_history[-1]
        switching_events = []
        
        # Comparar bitrates actuales con anteriores
        current_bitrates = set()
        previous_bitrates = set()
        
        for seg in current_analysis.get('current_segments', []):
            current_bitrates.add(seg['bitrate'])
        
        for seg in previous_analysis.get('current_segments', []):
            previous_bitrates.add(seg['bitrate'])
        
        # Detectar cambios
        if current_bitrates != previous_bitrates:
            event = {
                'timestamp': current_analysis['timestamp'],
                'previous_bitrates': list(previous_bitrates),
                'current_bitrates': list(current_bitrates),
                'type': 'bitrate_switch'
            }
            
            # Determinar dirección del cambio
            if max(current_bitrates) > max(previous_bitrates):
                event['direction'] = 'upgrade'
            elif min(current_bitrates) < min(previous_bitrates):
                event['direction'] = 'downgrade'
            else:
                event['direction'] = 'mixed'
            
            switching_events.append(event)
            self.switching_events.append(event)
        
        self.bitrate_history.append(current_analysis)
        
        # Mantener solo los últimos 100 análisis
        if len(self.bitrate_history) > 100:
            self.bitrate_history = self.bitrate_history[-100:]
        
        return switching_events
    
    def calculate_adaptation_metrics(self):
        """Calcula métricas agregadas de adaptación"""
        if not self.bitrate_history:
            return {}
        
        # Extraer bitrates a lo largo del tiempo
        timestamps = []
        bitrates = []
        
        for analysis in self.bitrate_history:
            if analysis.get('adaptation_metrics'):
                timestamps.append(analysis['timestamp'])
                bitrates.append(analysis['adaptation_metrics']['current_bitrate'])
        
        if not bitrates:
            return {}
        
        # Calcular métricas
        avg_bitrate = sum(bitrates) / len(bitrates)
        bitrate_variance = sum((x - avg_bitrate) ** 2 for x in bitrates) / len(bitrates)
        
        # Contar eventos de switching
        upgrade_events = len([e for e in self.switching_events if e.get('direction') == 'upgrade'])
        downgrade_events = len([e for e in self.switching_events if e.get('direction') == 'downgrade'])
        
        return {
            'avg_bitrate': avg_bitrate,
            'bitrate_variance': bitrate_variance,
            'total_switching_events': len(self.switching_events),
            'upgrade_events': upgrade_events,
            'downgrade_events': downgrade_events,
            'switching_frequency': len(self.switching_events) / max(1, len(self.bitrate_history)),
            'stability_score': 1.0 / (1.0 + bitrate_variance / (avg_bitrate ** 2)) if avg_bitrate > 0 else 0
        }
    
    def generate_charts(self):
        """Genera gráficos de adaptación"""
        if not self.bitrate_history:
            return
        
        try:
            # Preparar datos
            timestamps = []
            bitrates = []
            
            for analysis in self.bitrate_history:
                if analysis.get('adaptation_metrics'):
                    timestamps.append(datetime.fromisoformat(analysis['timestamp']))
                    bitrates.append(analysis['adaptation_metrics']['current_bitrate'] / 1000)  # Convertir a kbps
            
            if not bitrates:
                return
            
            # Crear gráfico
            plt.figure(figsize=(12, 8))
            
            # Gráfico de bitrate a lo largo del tiempo
            plt.subplot(2, 1, 1)
            plt.plot(timestamps, bitrates, 'b-', linewidth=2, marker='o', markersize=4)
            plt.title('Adaptación de Bitrate a lo Largo del Tiempo')
            plt.ylabel('Bitrate (kbps)')
            plt.grid(True, alpha=0.3)
            
            # Marcar eventos de switching
            for event in self.switching_events[-10:]:  # Últimos 10 eventos
                event_time = datetime.fromisoformat(event['timestamp'])
                if event_time in timestamps:
                    idx = timestamps.index(event_time)
                    color = 'green' if event['direction'] == 'upgrade' else 'red'
                    plt.scatter(event_time, bitrates[idx], color=color, s=100, zorder=5)
            
            # Gráfico de distribución de bitrates
            plt.subplot(2, 1, 2)
            plt.hist(bitrates, bins=20, alpha=0.7, color='skyblue', edgecolor='black')
            plt.title('Distribución de Bitrates')
            plt.xlabel('Bitrate (kbps)')
            plt.ylabel('Frecuencia')
            plt.grid(True, alpha=0.3)
            
            plt.tight_layout()
            plt.savefig(self.chart_file, dpi=300, bbox_inches='tight')
            plt.close()
            
            print(f"✓ Gráfico guardado en {self.chart_file}")
            
        except Exception as e:
            print(f"Error generando gráfico: {e}")
    
    def run_analysis(self):
        """Ejecuta el análisis de adaptación"""
        print(f"=== Análisis de Adaptación de Stream ===")
        print(f"Manifest: {self.manifest_url}")
        print(f"Intervalo: {self.interval} segundos")
        print(f"Directorio de salida: {self.output_dir}")
        print()
        
        while self.running:
            try:
                timestamp = datetime.now().isoformat()
                print(f"[{timestamp}] Analizando adaptación...")
                
                # 1. Analizar comportamiento de adaptación
                adaptation_analysis = self.analyze_adaptation_behavior()
                if not adaptation_analysis:
                    print("Error: No se pudo analizar la adaptación")
                    time.sleep(self.interval)
                    continue
                
                # 2. Detectar eventos de switching
                switching_events = self.detect_switching_events(adaptation_analysis)
                
                # 3. Calcular métricas agregadas
                aggregate_metrics = self.calculate_adaptation_metrics()
                
                # 4. Crear resultado completo
                analysis_result = {
                    'timestamp': timestamp,
                    'adaptation_analysis': adaptation_analysis,
                    'switching_events': switching_events,
                    'aggregate_metrics': aggregate_metrics,
                    'session_duration': (datetime.now() - self.session_start).total_seconds()
                }
                
                # Guardar resultado
                self.adaptation_data.append(analysis_result)
                self.save_results()
                
                # Mostrar resumen
                if adaptation_analysis.get('adaptation_metrics'):
                    metrics = adaptation_analysis['adaptation_metrics']
                    print(f"  ✓ Bitrate actual: {metrics['current_bitrate']/1000:.1f} kbps")
                    print(f"  ✓ Rango de bitrates: {metrics['min_bitrate']/1000:.1f} - {metrics['max_bitrate']/1000:.1f} kbps")
                    print(f"  ✓ Niveles disponibles: {metrics['bitrate_levels']}")
                
                if switching_events:
                    print(f"  🔄 Eventos de switching detectados: {len(switching_events)}")
                
                if aggregate_metrics:
                    print(f"  📊 Estabilidad: {aggregate_metrics['stability_score']:.3f}")
                    print(f"  📊 Frecuencia de switching: {aggregate_metrics['switching_frequency']:.3f} eventos/intervalo")
                
                print(f"  Esperando {self.interval} segundos...")
                time.sleep(self.interval)
                
            except KeyboardInterrupt:
                print("\nDetención solicitada por el usuario")
                break
            except Exception as e:
                print(f"Error en análisis: {e}")
                time.sleep(self.interval)
    
    def save_results(self):
        """Guarda los resultados en archivos"""
        common.save_results(self.adaptation_data, self.adaptation_log)

        # Generar reporte de texto
        self.generate_report()
        
        # Generar gráficos cada 10 análisis
        if len(self.adaptation_data) % 10 == 0:
            self.generate_charts()
    
    def generate_report(self):
        """Genera reporte de texto"""
        with open(self.report_file, 'w') as f:
            f.write("=== REPORTE DE ADAPTACIÓN DE STREAM ===\n")
            f.write(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Manifest: {self.manifest_url}\n")
            f.write(f"Duración de sesión: {self.session_duration:.1f} segundos\n")
            f.write(f"Total de análisis: {len(self.adaptation_data)}\n\n")
            
            if self.adaptation_data:
                latest = self.adaptation_data[-1]
                adaptation_metrics = latest['adaptation_analysis'].get('adaptation_metrics', {})
                aggregate_metrics = latest.get('aggregate_metrics', {})
                
                f.write("--- INFORMACIÓN DE ADAPTACIÓN ---\n")
                f.write(f"Bitrate actual: {adaptation_metrics.get('current_bitrate', 0)/1000:.1f} kbps\n")
                f.write(f"Bitrate mínimo: {adaptation_metrics.get('min_bitrate', 0)/1000:.1f} kbps\n")
                f.write(f"Bitrate máximo: {adaptation_metrics.get('max_bitrate', 0)/1000:.1f} kbps\n")
                f.write(f"Niveles de bitrate: {adaptation_metrics.get('bitrate_levels', 0)}\n")
                f.write(f"Resoluciones: {', '.join(adaptation_metrics.get('resolutions', []))}\n\n")
                
                f.write("--- MÉTRICAS AGREGADAS ---\n")
                f.write(f"Bitrate promedio: {aggregate_metrics.get('avg_bitrate', 0)/1000:.1f} kbps\n")
                f.write(f"Varianza de bitrate: {aggregate_metrics.get('bitrate_variance', 0):.2f}\n")
                f.write(f"Puntuación de estabilidad: {aggregate_metrics.get('stability_score', 0):.3f}\n")
                f.write(f"Total eventos de switching: {aggregate_metrics.get('total_switching_events', 0)}\n")
                f.write(f"Eventos de upgrade: {aggregate_metrics.get('upgrade_events', 0)}\n")
                f.write(f"Eventos de downgrade: {aggregate_metrics.get('downgrade_events', 0)}\n")
                f.write(f"Frecuencia de switching: {aggregate_metrics.get('switching_frequency', 0):.3f}\n\n")
                
                f.write("--- RECOMENDACIONES ---\n")
                stability = aggregate_metrics.get('stability_score', 0)
                if stability < 0.5:
                    f.write("⚠️  Baja estabilidad de bitrate\n")
                if aggregate_metrics.get('switching_frequency', 0) > 0.5:
                    f.write("⚠️  Muchos cambios de bitrate\n")
                if aggregate_metrics.get('downgrade_events', 0) > aggregate_metrics.get('upgrade_events', 0):
                    f.write("⚠️  Más downgrades que upgrades\n")
                
                f.write("\n--- HISTORIAL DE SWITCHING ---\n")
                for i, event in enumerate(self.switching_events[-10:], 1):  # Últimos 10
                    f.write(f"{i}. {event['timestamp']} - {event['direction']} - {event['previous_bitrates']} → {event['current_bitrates']}\n")
    
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
    parser = argparse.ArgumentParser(description='Analiza adaptación de bitrate en streams DASH')
    parser.add_argument('manifest_url', help='URL del manifest DASH')
    parser.add_argument('-o', '--output', default='./adaptation_analysis', help='Directorio de salida')
    parser.add_argument('-i', '--interval', type=int, default=10, help='Intervalo de análisis en segundos')
    
    args = parser.parse_args()
    
    analyzer = StreamAdaptationAnalyzer(args.manifest_url, args.output, args.interval)
    
    try:
        analyzer.start()
    except KeyboardInterrupt:
        print("\nDeteniendo análisis...")
        analyzer.stop()

if __name__ == "__main__":
    main() 