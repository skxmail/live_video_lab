#!/usr/bin/env python3
"""
Test script para verificar que todas las herramientas de análisis estén funcionando
"""

import os
import sys
import subprocess
import importlib

def test_imports():
    """Prueba que todos los módulos se puedan importar"""
    print("=== Probando imports de módulos ===")
    
    modules = [
        'requests',
        'numpy', 
        'pandas',
        'matplotlib',
        'seaborn',
        'plotly',
        'flask',
        'xml.etree.ElementTree'
    ]
    
    for module in modules:
        try:
            importlib.import_module(module)
            print(f"✓ {module}")
        except ImportError as e:
            print(f"✗ {module}: {e}")
    
    print()

def test_scripts():
    """Prueba que todos los scripts existan y sean ejecutables"""
    print("=== Probando scripts ===")
    
    scripts = [
        '/app/quality_analyzer.sh',
        '/app/stream_monitor.py',
        '/app/stream_quality_analyzer.py',
        '/app/stream_latency_analyzer.py',
        '/app/stream_adaptation_analyzer.py',
        '/app/stream_analysis_suite.py',
        '/app/dashboard.py',
        '/app/entrypoint.sh'
    ]
    
    for script in scripts:
        if os.path.exists(script):
            if os.access(script, os.X_OK):
                print(f"✓ {script} (ejecutable)")
            else:
                print(f"⚠ {script} (existe pero no es ejecutable)")
        else:
            print(f"✗ {script} (no encontrado)")
    
    print()

def test_directories():
    """Prueba que los directorios necesarios existan"""
    print("=== Probando directorios ===")
    
    directories = [
        '/app/logs',
        '/app/stream_analysis',
        '/tmp'
    ]
    
    for directory in directories:
        if os.path.exists(directory):
            if os.access(directory, os.W_OK):
                print(f"✓ {directory} (existe y escribible)")
            else:
                print(f"⚠ {directory} (existe pero no escribible)")
        else:
            print(f"✗ {directory} (no encontrado)")
    
    print()

def test_ffmpeg():
    """Prueba que FFmpeg esté disponible"""
    print("=== Probando FFmpeg ===")
    
    try:
        result = subprocess.run(['ffmpeg', '-version'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            version = result.stdout.split('\n')[0]
            print(f"✓ FFmpeg: {version}")
        else:
            print("✗ FFmpeg: Error al ejecutar")
    except Exception as e:
        print(f"✗ FFmpeg: {e}")
    
    print()

def test_python_scripts():
    """Prueba que los scripts de Python se puedan ejecutar con --help"""
    print("=== Probando scripts de Python ===")
    
    python_scripts = [
        '/app/stream_quality_analyzer.py',
        '/app/stream_latency_analyzer.py',
        '/app/stream_adaptation_analyzer.py',
        '/app/stream_analysis_suite.py'
    ]
    
    for script in python_scripts:
        if os.path.exists(script):
            try:
                result = subprocess.run([sys.executable, script, '--help'], 
                                      capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    print(f"✓ {os.path.basename(script)}")
                else:
                    print(f"⚠ {os.path.basename(script)}: Error en --help")
            except Exception as e:
                print(f"✗ {os.path.basename(script)}: {e}")
        else:
            print(f"✗ {os.path.basename(script)}: No encontrado")
    
    print()

def test_dashboard():
    """Prueba que el dashboard se pueda importar"""
    print("=== Probando dashboard ===")
    
    try:
        # Cambiar al directorio del script
        original_dir = os.getcwd()
        os.chdir('/app')
        
        # Importar el dashboard
        import dashboard
        print("✓ Dashboard: Se puede importar correctamente")
        
        # Verificar que tenga las funciones necesarias
        if hasattr(dashboard, 'app'):
            print("✓ Dashboard: Tiene aplicación Flask")
        else:
            print("⚠ Dashboard: No tiene aplicación Flask")
            
        os.chdir(original_dir)
        
    except Exception as e:
        print(f"✗ Dashboard: {e}")
    
    print()

def main():
    """Función principal de pruebas"""
    print("🧪 PRUEBAS DE HERRAMIENTAS DE ANÁLISIS DE STREAMS")
    print("=" * 50)
    print()
    
    test_imports()
    test_scripts()
    test_directories()
    test_ffmpeg()
    test_python_scripts()
    test_dashboard()
    
    print("=== RESUMEN ===")
    print("Si todas las pruebas pasaron (✓), las herramientas están listas para usar.")
    print("Si hay errores (✗), revisa la configuración del Dockerfile.")
    print()
    print("Para usar las herramientas:")
    print("  python3 /app/stream_analysis_suite.py <manifest_url> -i 30")
    print("  python3 /app/stream_quality_analyzer.py <manifest_url> -i 30")
    print("  python3 /app/stream_latency_analyzer.py <manifest_url> -i 5")
    print("  python3 /app/stream_adaptation_analyzer.py <manifest_url> -i 10")

if __name__ == "__main__":
    main() 