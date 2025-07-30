import requests
import xml.etree.ElementTree as ET
import csv
from urllib.parse import urljoin

def fetch_mpd_root(manifest_url, timeout=10):
    """Descarga y parsea el manifest MPD, devolviendo el root y el namespace."""
    response = requests.get(manifest_url, timeout=timeout)
    response.raise_for_status()
    root = ET.fromstring(response.content)
    namespace = {'mpd': 'urn:mpeg:dash:schema:mpd:2011'}
    return root, namespace

def get_adaptation_sets(root, namespace):
    """Devuelve todos los AdaptationSet del MPD."""
    period = root.find('.//mpd:Period', namespace)
    if not period:
        return []
    return period.findall('.//mpd:AdaptationSet', namespace)

def extract_manifest_info(root, namespace):
    """Extrae información básica del manifest DASH."""
    period = root.find('.//mpd:Period', namespace)
    adaptations = period.findall('.//mpd:AdaptationSet', namespace) if period else []
    info = {
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
        ctype = adaptation.get('contentType', '')
        if ctype == 'video':
            info['video_streams'] += 1
            for rep in adaptation.findall('.//mpd:Representation', namespace):
                if rep.get('bandwidth'):
                    info['bitrates'].append(int(rep.get('bandwidth')))
                if rep.get('width') and rep.get('height'):
                    info['resolutions'].append(f"{rep.get('width')}x{rep.get('height')}")
                if rep.get('codecs'):
                    info['codecs'].append(rep.get('codecs'))
        elif ctype == 'audio':
            info['audio_streams'] += 1
        elif ctype == 'text':
            info['subtitle_streams'] += 1
    return info

def get_segment_urls_from_mpd(root, namespace, manifest_url, max_segments=2):
    """Obtiene URLs de inicialización y segmentos de video del manifest."""
    segment_info_list = []
    adaptations = root.findall('.//mpd:AdaptationSet', namespace)
    for adaptation in adaptations:
        if adaptation.get('contentType') == 'video':
            representations = adaptation.findall('.//mpd:Representation', namespace)
            for rep in representations:
                seg_template = rep.find('.//mpd:SegmentTemplate', namespace)
                if seg_template is not None:
                    init = seg_template.get('initialization', '').replace('$RepresentationID$', rep.get('id', ''))
                    media = seg_template.get('media', '').replace('$RepresentationID$', rep.get('id', ''))
                    start_number = int(seg_template.get('startNumber', 1))
                    init_url = urljoin(manifest_url, init)
                    for i in range(max_segments):
                        seg_url = urljoin(manifest_url, media.replace('$Number$', str(start_number + i)))
                        segment_info_list.append((init_url, seg_url))
                break  # Solo el primer AdaptationSet de video
    return segment_info_list[:max_segments]

def flatten_dict(d, parent_key='', sep='.'):
    """Aplana un diccionario anidado para exportar a CSV."""
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        elif isinstance(v, list):
            items.append((new_key, str(v)))
        else:
            items.append((new_key, v))
    return dict(items)

def save_tabular_log(data, path):
    """Guarda una lista de diccionarios en formato CSV."""
    if not data:
        return
    flat_entries = [flatten_dict(entry) for entry in data]
    all_keys = sorted({k for entry in flat_entries for k in entry})
    with open(path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=all_keys)
        writer.writeheader()
        for entry in flat_entries:
            writer.writerow(entry)

def save_results(data, path):
    import json
    """Guarda los resultados en archivos"""
    # Guardar datos JSON
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)
    
    # Guardar log de texto plano
    save_tabular_log(data, path.replace('.json', '.csv'))
