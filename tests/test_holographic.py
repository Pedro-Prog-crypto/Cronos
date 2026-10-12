import re
from pathlib import Path
from fastapi.testclient import TestClient
from cronos.app import create_app


def test_holographic_assets_and_workbench_frame_policy():
    with TestClient(create_app()) as client:
        root=client.get('/')
        assert 'id="root"' in root.text
        for path in re.findall(r'(?:src|href)="(/ui/[^\"]+)"',root.text):
            assert client.get(path).status_code==200
        assert root.headers['x-frame-options']=='DENY'
        workbench=client.get('/tests')
        assert workbench.headers['x-frame-options']=='SAMEORIGIN'
        assert "frame-ancestors 'self'" in workbench.headers['content-security-policy']
        assert "script-src 'self'" in root.headers['content-security-policy']
        assert 'unsafe-inline' not in root.headers['content-security-policy']


def test_production_interface_keeps_animation_and_no_browser_ai_keys():
    package=Path(__file__).resolve().parents[1]
    for component in ('CronosOrb','StellarCore'):
        content=(package/'frontend/src/components'/f'{component}.tsx').read_text()
        assert 'requestAnimationFrame(render)' in content
        assert 'cancelAnimationFrame(animId)' in content
    script=(package/'frontend/src/hooks/useCronosVoice.ts').read_text()
    assert "'/voice/speech'" in script and "'/voice/transcribe'" in script
    assert 'SpeechSynthesisUtterance' not in script and 'startSimulationLevel' not in script
    for file in (package/'cronos/ui').rglob('*.js'):
        content=file.read_text()
        assert 'GEMINI_API_KEY' not in content and 'FISH_API_KEY' not in content
        assert 'localStorage' not in content
