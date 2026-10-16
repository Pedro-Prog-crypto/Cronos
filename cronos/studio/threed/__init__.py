"""Cronos Studio - Módulo 3D. Modelos e templates enviados pelo usuário."""
from .config import (THREE_CDN_URL, THREE_ORBIT_CONTROLS_CDN, DEFAULT_3D_SETTINGS, DEFAULT_3D_COLORS,
                     PERFORMANCE_SETTINGS, FREE_3D_MODEL_SOURCES, get_threejs_cdn, get_orbit_controls_cdn,
                     get_default_scene_config, get_default_colors)
from .models import Scene3D, MODEL_CATALOG, create_earbuds_model, create_airplane_model, create_hotel_model, get_model, list_models
from .generator import Site3DGenerator, generate_3d_site, generate_3d_template
from .pricing_config import PRICING_TIERS, CATEGORY_PRICING, COMPLEXITY_PRICING, FEATURE_PRICING, get_price_for_site, get_reference_site

__all__ = ['THREE_CDN_URL', 'THREE_ORBIT_CONTROLS_CDN', 'DEFAULT_3D_SETTINGS', 'DEFAULT_3D_COLORS',
           'PERFORMANCE_SETTINGS', 'FREE_3D_MODEL_SOURCES', 'get_threejs_cdn', 'get_orbit_controls_cdn',
           'get_default_scene_config', 'get_default_colors', 'Scene3D', 'MODEL_CATALOG', 'create_earbuds_model',
           'create_airplane_model', 'create_hotel_model', 'get_model', 'list_models', 'Site3DGenerator',
           'generate_3d_site', 'generate_3d_template', 'PRICING_TIERS', 'CATEGORY_PRICING', 'COMPLEXITY_PRICING',
           'FEATURE_PRICING', 'get_price_for_site', 'get_reference_site']
