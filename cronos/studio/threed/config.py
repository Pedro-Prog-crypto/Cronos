"""Configurações gerais para o módulo de geração de sites 3D."""
from copy import deepcopy
from typing import Dict, Any

THREE_CDN_URL = "https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"
THREE_ORBIT_CONTROLS_CDN = "https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"
THREE_GLB_LOADER_CDN = "https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/loaders/GLTFLoader.js"
THREE_DRACO_LOADER_CDN = "https://www.gstatic.com/draco/v1/decoders/three_draco_decoder.js"
THREE_DRACO_WASM = "https://www.gstatic.com/draco/v1/decoders/three_draco_decoder.wasm"
FREE_3D_MODEL_SOURCES = {
    "sketchfab": {"url": "https://sketchfab.com", "api": "https://api.sketchfab.com/v3/models", "free": True, "note": "Requer API key gratuita para download de modelos"},
    "poly_haven": {"url": "https://polyhaven.com", "api": None, "free": True, "note": "Modelos CC0, download direto"},
    "thingiverse": {"url": "https://www.thingiverse.com", "api": None, "free": True, "note": "Modelos para impressão 3D, pode ser convertido para GLB"},
    "cgtrader": {"url": "https://www.cgtrader.com", "api": None, "free": True, "note": "Filtro por modelos gratuitos"}
}
DEFAULT_3D_SETTINGS = {
    "camera": {"position": [0, 0, 5], "fov": 75, "near": 0.1, "far": 1000, "aspect": 16/9},
    "lighting": {"ambient": {"color": 0x404040, "intensity": 0.5}, "directional": {"color": 0xffffff, "intensity": 1.0, "position": [5, 10, 7]}, "hemisphere": {"color": 0xffffbb, "groundColor": 0x080820, "intensity": 0.6}},
    "renderer": {"antialias": True, "alpha": True, "clearColor": 0x000000, "shadowMap": True},
    "background": {"color": 0x000000, "gradient": ["0x1a1a2e", "0x16213e"], "environment": None},
    "materials": {"standard": {"color": 0xffffff, "roughness": 0.5, "metalness": 0.5}, "metallic": {"color": 0xcccccc, "roughness": 0.1, "metalness": 1.0}, "plastic": {"color": 0xffffff, "roughness": 0.8, "metalness": 0.1}, "glass": {"color": 0xffffff, "roughness": 0.1, "metalness": 0.0, "transparent": True, "opacity": 0.5}}
}
DEFAULT_3D_COLORS = {"primary": 0x3b82f6, "secondary": 0x1e40af, "accent": 0x60a5fa, "background": 0x0f172a, "text": 0xf8fafc, "light": 0xffffff, "dark": 0x111827, "success": 0x10b981, "warning": 0xf59e0b, "error": 0xef4444}
PERFORMANCE_SETTINGS = {"max_textures": 8, "max_geometry": 1000000, "max_bones": 500, "shadow_resolution": 1024, "render_scale": 1.0, "lod": {"enabled": True, "levels": 3, "distance": [5, 15, 30]}}

def get_threejs_cdn() -> str: return THREE_CDN_URL

def get_orbit_controls_cdn() -> str: return THREE_ORBIT_CONTROLS_CDN

def get_default_scene_config() -> Dict[str, Any]: return deepcopy(DEFAULT_3D_SETTINGS)

def get_default_colors() -> Dict[str, int]: return dict(DEFAULT_3D_COLORS)
