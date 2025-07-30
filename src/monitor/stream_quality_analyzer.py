#!/usr/bin/env python3
"""
Stream Quality Analyzer - Analiza la calidad de streams DASH/HLS en tiempo real
Uso: python3 stream_quality_analyzer.py <manifest_url> [options]
"""

import argparse
import json
import time
import subprocess
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from urllib.parse import urljoin, urlparse
import threading
import queue
import os
import traceback

import stream_analisys_common as common

class StreamQualityAnalyzer:
    def __init__(self, manifest_url, output_dir="./stream_analysis", interval=30):
        self.manifest_url = manifest_url
        self.output_dir = output_dir
        self.interval = interval
        self.running = False
        self.analysis_queue = queue.Queue()
        
        # Crear directorio de salida
        os.makedirs(output_dir, exist_ok=True)
        
        # Archivos de salida
        self.quality_log = os.path.join(output_dir, "stream_quality_analysis.json")
        self.report_file = os.path.join(output_dir, "quality_report.txt")
        
        # Inicializar datos
        self.quality_data = []
        
    def fetch_manifest(self):
        """Obtiene y parsea el manifest DASH"""
        try:
            # Descargar y parsear el manifest
            root, namespace = common.fetch_mpd_root(self.manifest_url)

            # Extraer información básica
            period = root.find('.//mpd:Period', namespace)
            adaptations = period.findall('.//mpd:AdaptationSet', namespace) if period else []
            
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
                if content_type == 'video':
                    manifest_info['video_streams'] += 1
                    # Extraer bitrates y resoluciones
                    representations = adaptation.findall('.//mpd:Representation', namespace)
                    for rep in representations:
                        bitrate = rep.get('bandwidth')
                        if bitrate:
                            manifest_info['bitrates'].append(int(bitrate))
                        
                        width = rep.get('width')
                        height = rep.get('height')
                        if width and height:
                            manifest_info['resolutions'].append(f"{width}x{height}")
                        
                        codec = rep.get('codecs')
                        if codec:
                            manifest_info['codecs'].append(codec)
                            
                elif content_type == 'audio':
                    manifest_info['audio_streams'] += 1
                elif content_type == 'text':
                    manifest_info['subtitle_streams'] += 1
            
            return manifest_info
            
        except Exception as e:
            print(f"Error obteniendo manifest: {e}")
            return None
    
    def analyze_segment_quality(self, segment_url):
        """Analiza la calidad de un segmento usando FFmpeg"""
        try:
            # Comando FFmpeg para análisis rápido
            cmd = [
                'ffprobe', '-v', 'quiet', '-print_format', 'json',
                '-show_format', '-show_streams', '-show_frames',
                '-select_streams', 'v:0',  # Solo video
                segment_url
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            
            if result.returncode == 0:
                data = json.loads(result.stdout)
                
                # Extraer métricas de calidad
                video_stream = next((s for s in data.get('streams', []) if s.get('codec_type') == 'video'), None)
                format_info = data.get('format', {})
                
                if video_stream:
                    quality_metrics = {
                        'bitrate': int(format_info.get('bit_rate', 0)),
                        'duration': float(format_info.get('duration', 0)),
                        'codec': video_stream.get('codec_name', 'unknown'),
                        'width': video_stream.get('width', 0),
                        'height': video_stream.get('height', 0),
                        'fps': eval(video_stream.get('r_frame_rate', '0/1')),
                        'pixel_format': video_stream.get('pix_fmt', 'unknown'),
                        'frame_count': len(data.get('frames', []))
                    }
                    
                    # Análisis SSIM si es posible
                    # ssim_result = self.analyze_ssim(segment_url)
                    # if ssim_result:
                    #     quality_metrics['ssim'] = ssim_result
                    
                    return quality_metrics
            
        except Exception as e:
            print(f"Error analizando segmento: {e}")
        
        return None
    
    def analyze_ssim(self, segment_url):
        """Analiza SSIM del segmento"""
        try:
            # Crear archivo temporal para SSIM
            ssim_file = f"/tmp/ssim_{int(time.time())}.log"
            
            cmd = [
                'ffmpeg', '-i', segment_url,
                '-vf', f'ssim=stats_file={ssim_file}',
                '-f', 'null', '-'
            ]
            
            result = subprocess.run(cmd, capture_output=True, timeout=30)
            
            if result.returncode == 0 and os.path.exists(ssim_file):
                # Buscar el valor SSIM global en stderr
                stderr_str = result.stderr.decode() if isinstance(result.stderr, bytes) else result.stderr
                match = re.search(r'All:([0-9.]+)', stderr_str)
                if match:
                    return float(match.group(1))
                # (Opcional) limpiar el archivo temporal
                if os.path.exists(ssim_file):
                    os.remove(ssim_file)
                
                os.remove(ssim_file)
                
        except Exception as e:
            print(f"Error en análisis SSIM: {e}")
        
        return None
    
    def analyze_ssim_between_segments(self, segment1_path, segment2_path):
        """Calcula el SSIM entre dos archivos de segmento"""
        import re
        try:
            ssim_file = f"/tmp/ssim_{int(time.time())}.log"
            cmd = [
                'ffmpeg', '-i', segment1_path, '-i', segment2_path,
                '-lavfi', f'ssim=stats_file={ssim_file}',
                '-f', 'null', '-'
            ]
            result = subprocess.run(cmd, capture_output=True, timeout=30)
            # Buscar el valor SSIM global en stderr
            stderr_str = result.stderr.decode() if isinstance(result.stderr, bytes) else result.stderr
            match = re.search(r'All:([0-9.]+)', stderr_str)
            if match:
                return float(match.group(1))
            # (Opcional) limpiar el archivo temporal
            if os.path.exists(ssim_file):
                os.remove(ssim_file)
        except Exception as e:
            print(f"Error en análisis SSIM entre segmentos: {e}")
        return None
    
    def download_segment(self, segment_url, output_path):
        """Descarga un segmento para análisis"""
        try:
            response = requests.get(segment_url, timeout=30)
            response.raise_for_status()
            
            with open(output_path, 'wb') as f:
                f.write(response.content)
            return True
        except Exception as e:
            print(f"Error descargando segmento: {e}")
            return False
    
    def get_segment_urls(self, manifest_info):
        """Obtiene URLs de inicialización y de los dos primeros segmentos de video del manifest"""
        try:
            response = requests.get(self.manifest_url, timeout=10)
            response.raise_for_status()
            
            root = ET.fromstring(response.content)
            namespace = {'mpd': 'urn:mpeg:dash:schema:mpd:2011'}
            
            segment_info_list = []
            
            # Buscar AdaptationSet de video
            adaptations = root.findall('.//mpd:AdaptationSet', namespace)
            for adaptation in adaptations:
                if adaptation.get('contentType') == 'video':
                    representations = adaptation.findall('.//mpd:Representation', namespace)
                    for rep in representations:
                        segment_template = rep.find('.//mpd:SegmentTemplate', namespace)
                        if segment_template is not None:
                            media = segment_template.get('media')
                            initialization = segment_template.get('initialization')
                            start_number = int(segment_template.get('startNumber', '1'))
                            if media and initialization:
                                # Obtener SegmentTimeline
                                timeline = segment_template.find('.//mpd:SegmentTimeline', namespace)
                                segment_numbers = []
                                if timeline is not None:
                                    current_number = start_number
                                    for s in timeline.findall('mpd:S', namespace):
                                        repeat = int(s.get('r', '0'))
                                        count = repeat + 1
                                        for _ in range(count):
                                            segment_numbers.append(current_number)
                                            current_number += 1
                                            if len(segment_numbers) >= 5:
                                                break
                                        if len(segment_numbers) >= 5:
                                            break
                                else:
                                    # Si no hay timeline, usar start_number y el siguiente
                                    segment_numbers = [start_number, start_number + 1]
                                # Construir URLs de los dos primeros segmentos
                                for seg_num in segment_numbers:
                                    segment_url = urljoin(self.manifest_url, media.replace('$Number$', str(seg_num)))
                                    init_url = urljoin(self.manifest_url, initialization)
                                    segment_info_list.append((init_url, segment_url))
                                break  # Solo la primera representación de video
                    break  # Solo el primer AdaptationSet de video
            return segment_info_list[:5]  # Solo los dos primeros segmentos
            # return segment_info_list  # Solo los dos primeros segmentos
        except Exception as e:
            print(f"Error obteniendo URLs de segmentos: {e}")
            return []
    
    def run_analysis(self):
        """Ejecuta el análisis completo"""
        print(f"=== Análisis de Calidad de Stream ===")
        print(f"Manifest: {self.manifest_url}")
        print(f"Intervalo: {self.interval} segundos")
        print(f"Directorio de salida: {self.output_dir}")
        print()
        
        while self.running:
            try:
                timestamp = datetime.now().isoformat()
                print(f"[{timestamp}] Analizando stream...")
                
                # 1. Obtener información del manifest
                manifest_info = self.fetch_manifest()
                if not manifest_info:
                    print("Error: No se pudo obtener información del manifest")
                    time.sleep(self.interval)
                    continue
                
                # 2. Obtener URLs de segmentos y de inicialización
                segment_info_list = self.get_segment_urls(manifest_info)
                if not segment_info_list:
                    print("Error: No se encontraron segmentos para analizar")
                    time.sleep(self.interval)
                    continue
                
                # 3. Analizar calidad de segmentos
                quality_results = []
                concat_files = []  # Para guardar los archivos concatenados
                for i, (init_url, segment_url) in enumerate(segment_info_list):
                    print(f"  Analizando segmento {i+1}/{len(segment_info_list)}...")
                    
                    # Descargar init y segmento temporalmente
                    temp_init = f"/tmp/init_{i}_{int(time.time())}.mp4"
                    temp_segment = f"/tmp/segment_{i}_{int(time.time())}.m4s"
                    temp_concat = f"/tmp/concat_{i}_{int(time.time())}.mp4"
                    if self.download_segment(init_url, temp_init) and self.download_segment(segment_url, temp_segment):
                        # Concatenar init + segmento
                        with open(temp_concat, 'wb') as wfd:
                            for f in [temp_init, temp_segment]:
                                with open(f, 'rb') as fd:
                                    wfd.write(fd.read())
                        # Analizar el archivo concatenado
                        quality_metrics = self.analyze_segment_quality(temp_concat)
                        if quality_metrics:
                            quality_results.append(quality_metrics)
                        concat_files.append(temp_concat)
                        # Limpiar archivos temporales si lo deseas
                        os.remove(temp_init)
                        os.remove(temp_segment)
                        # No borres temp_concat aún, lo usamos para SSIM entre segmentos
                # Calcular SSIM entre primer y segundo segmento si existen
                ssim_between = None
                if len(concat_files) >= 2:
                    ssim_between = self.analyze_ssim_between_segments(concat_files[0], concat_files[-1])
                    quality_metrics['ssim'] = ssim_between
                    print(f"  ✓ SSIM entre primer y segundo segmento: {ssim_between if ssim_between is not None else 'N/A'}")
                # Limpiar archivos concatenados
                for f in concat_files:
                    os.remove(f)
                
                # 4. Calcular métricas agregadas
                if quality_results:
                    avg_bitrate = sum(r['bitrate'] for r in quality_results) / len(quality_results)
                    ssim_values = [r.get('ssim') for r in quality_results if r.get('ssim') is not None]
                    if ssim_values:
                        avg_ssim = sum(ssim_values) / len(ssim_values)
                    else:
                        avg_ssim = None  # No hay SSIM disponible
                    
                    analysis_result = {
                        'timestamp': timestamp,
                        'manifest_info': manifest_info,
                        'segment_analysis': quality_results,
                        'aggregate_metrics': {
                            'avg_bitrate': avg_bitrate,
                            'avg_ssim': avg_ssim,
                            'ssim_between_segments': ssim_between,
                            'segments_analyzed': len(quality_results)
                        }
                    }
                    
                    # Guardar resultado
                    self.quality_data.append(analysis_result)
                    self.save_results()
                    
                    # Mostrar resumen
                    print(f"  ✓ Bitrate promedio: {avg_bitrate/1000:.1f} kbps")
                    if avg_ssim is not None:
                        print(f"  ✓ SSIM promedio: {avg_ssim:.4f}")
                    else:
                        print(f"  ✓ SSIM promedio: N/A")
                    print(f"  ✓ Segmentos analizados: {len(quality_results)}")
                
                print(f"  Esperando {self.interval} segundos...")
                time.sleep(self.interval)
                
            except KeyboardInterrupt:
                print("\nDetención solicitada por el usuario")
                break
            except Exception as e:
                print(f"Error en análisis: {e}")
                traceback.print_exc()
                time.sleep(self.interval)
    

    def save_results(self):
        """Guarda los resultados en archivos"""
        common.save_results(self.quality_data, self.quality_log)
      
        # Generar reporte de texto
        self.generate_report()
    
    def generate_report(self):
        """Genera reporte de texto"""
        with open(self.report_file, 'w') as f:
            f.write("=== REPORTE DE CALIDAD DE STREAM ===\n")
            f.write(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Manifest: {self.manifest_url}\n")
            f.write(f"Total de análisis: {len(self.quality_data)}\n\n")
            
            if self.quality_data:
                latest = self.quality_data[-1]
                manifest = latest['manifest_info']
                metrics = latest['aggregate_metrics']
                
                f.write("--- INFORMACIÓN DEL MANIFEST ---\n")
                f.write(f"Tipo: {manifest['type']}\n")
                f.write(f"Adaptation Sets: {manifest['adaptation_sets']}\n")
                f.write(f"Streams de video: {manifest['video_streams']}\n")
                f.write(f"Streams de audio: {manifest['audio_streams']}\n")
                f.write(f"Codecs: {', '.join(manifest['codecs'])}\n\n")
                
                f.write("--- MÉTRICAS DE CALIDAD ---\n")
                f.write(f"Bitrate promedio: {metrics['avg_bitrate']/1000:.1f} kbps\n")
                if metrics['avg_ssim'] is not None:
                    f.write(f"SSIM promedio: {metrics['avg_ssim']:.4f}\n")
                else:
                    f.write("SSIM promedio: N/A\n")
                if 'ssim_between_segments' in metrics:
                    if metrics['ssim_between_segments'] is not None:
                        f.write(f"SSIM entre primer y segundo segmento: {metrics['ssim_between_segments']:.4f}\n")
                    else:
                        f.write("SSIM entre primer y segundo segmento: N/A\n")
                f.write(f"Segmentos analizados: {metrics['segments_analyzed']}\n\n")
                
                f.write("--- HISTORIAL DE ANÁLISIS ---\n")
                for i, analysis in enumerate(self.quality_data[-10:], 1):  # Últimos 10
                    f.write(f"{i}. {analysis['timestamp']} - Bitrate: {analysis['aggregate_metrics']['avg_bitrate']/1000:.1f} kbps")
                    if 'ssim_between_segments' in analysis['aggregate_metrics']:
                        ssim_val = analysis['aggregate_metrics']['ssim_between_segments']
                        if ssim_val is not None:
                            f.write(f", SSIM entre segmentos: {ssim_val:.4f}\n")
                        else:
                            f.write(", SSIM entre segmentos: N/A\n")
                    else:
                        f.write("\n")
    
    def start(self):
        """Inicia el análisis"""
        self.running = True
        self.run_analysis()
    
    def stop(self):
        """Detiene el análisis"""
        self.running = False

def main():
    parser = argparse.ArgumentParser(description='Analiza la calidad de streams DASH/HLS en tiempo real')
    parser.add_argument('manifest_url', help='URL del manifest DASH/HLS')
    parser.add_argument('-o', '--output', default='./stream_analysis', help='Directorio de salida')
    parser.add_argument('-i', '--interval', type=int, default=30, help='Intervalo de análisis en segundos')
    
    args = parser.parse_args()
    
    analyzer = StreamQualityAnalyzer(args.manifest_url, args.output, args.interval)
    
    try:
        analyzer.start()
    except KeyboardInterrupt:
        print("\nDeteniendo análisis...")
        analyzer.stop()

if __name__ == "__main__":
    main() 