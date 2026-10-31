import sys
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from cronos.app import create_app
from cronos import desktop,resident,wake
from test_backend import settings


def test_desktop_uses_persistent_profile_and_closing_ui_keeps_backend(settings,tmp_path,monkeypatch):
    from cronos import persistent_data
    monkeypatch.setattr(persistent_data,'activate',lambda root:None)
    monkeypatch.setattr(desktop,'load_dotenv',lambda *a,**kw:None)
    monkeypatch.setattr(desktop,'sys',SimpleNamespace(platform='win32'))
    monkeypatch.setattr(resident,'folder',lambda root=None:tmp_path/'runtime')
    monkeypatch.setattr(wake,'root',lambda:tmp_path/'wake')
    monkeypatch.setattr(wake,'status',lambda:{'model_installed':False,'dependencies_installed':False})
    monkeypatch.setattr(wake,'set_ui_listening',lambda active:state.update(listening=active))
    state={};closed=[]
    class Event:
        def __init__(self):self.callbacks=[]
        def __iadd__(self,value):self.callbacks.append(value);return self
    class Window:
        def __init__(self):self.events=SimpleNamespace(loaded=Event())
        def get_current_url(self):return state['url']
        def evaluate_js(self,script):state['script']=script
        def create_file_dialog(self,kind):return [str(tmp_path)]
        def restore(self):state['restored']=True
        def show(self):state['shown']=True
        def destroy(self):state['closed']=True
    def create_window(title,url,**kwargs):
        assert title=='Cronos';state.update(url=url,bridge=kwargs['js_api'],window=Window())
        return state['window']
    def start(**kwargs):
        assert kwargs=={'gui':'edgechromium','debug':False,'private_mode':False,'storage_path':str(tmp_path/'webview-profile')}
        for callback in state['window'].events.loaded.callbacks:callback()
        assert 'requestSubmit' in state['script']
        assert state['bridge'].connection()=={'token':settings.token}
        assert state['bridge'].choose_vault()==str(tmp_path)
        assert state['bridge'].show_main()=={'requested':True}
        assert state['restored'] and state['shown']
        original=state['url'];state['url']='https://example.org'
        assert state['bridge'].connection() is None and state['bridge'].choose_vault() is None
        assert state['bridge'].show_main() is None and state['bridge'].close_main() is None
        state['url']=original
    with TestClient(create_app(settings),headers={'Authorization':'Bearer '+settings.token}) as client:
        connection=SimpleNamespace(data={'url':'http://127.0.0.1:54001','token':settings.token},close=lambda:closed.append(True))
        monkeypatch.setattr(resident,'ensure',lambda project:connection)
        monkeypatch.setitem(sys.modules,'webview',SimpleNamespace(create_window=create_window,start=start,FileDialog=SimpleNamespace(FOLDER='folder')))
        desktop._run()
        assert client.get('/status').status_code==200,'Closing a view must not stop the independent assistant backend'
    assert closed==[True] and state['listening'] is False


def test_desktop_explains_missing_dependency(monkeypatch):
    monkeypatch.setattr(desktop,'sys',SimpleNamespace(platform='win32'))
    monkeypatch.setitem(sys.modules,'webview',None)
    with pytest.raises(SystemExit,match='Instale o modo desktop'):desktop.main()
