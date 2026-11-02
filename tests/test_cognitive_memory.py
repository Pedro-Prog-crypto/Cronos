from datetime import datetime
from uuid import uuid4

from cronos.cognition import plan_for
from cronos.memory import Memory
from cronos.temporal_memory import SAO_PAULO, explicit_event
from fastapi.testclient import TestClient
from cronos.app import create_app
from test_backend import AUTH, settings


def test_explicit_dates_are_recorded_without_turning_questions_into_commitments(tmp_path):
    memory = Memory(tmp_path / 'vault')
    session = uuid4()
    memory.record(session, 'Quando é minha prova de matemática?', 'Ainda não tenho a data.', [])
    assert memory.upcoming_events(60) == []
    memory.record(session, 'Minha prova de matemática será daqui a três semanas.', 'Vou acompanhar.', [])
    restored = Memory(memory.vault)
    events = restored.upcoming_events(30)
    assert len(events) == 1
    assert events[0]['kind'] == 'prova'
    assert events[0]['days_left'] == 21
    assert restored.due_suggestion() is None
    assert restored.layers()['temporal'] == 1
    assert any(node['title'].startswith('prova') for node in restored.graph()['nodes'])


def test_due_commitment_can_prompt_once_and_be_completed(tmp_path):
    memory = Memory(tmp_path / 'vault')
    session = uuid4()
    memory.record(session, 'Minha prova de biologia é daqui a dois dias.', 'Vamos revisar.', [])
    event = memory.due_suggestion()
    assert event and event['days_left'] == 2
    memory.mark_nudged(event['id'])
    assert memory.due_suggestion() is None
    memory.record(session, 'Já fiz a prova.', 'Boa.', [])
    assert Memory(memory.vault).upcoming_events() == []


def test_personal_preferences_survive_restart_and_newer_correction_wins(tmp_path):
    memory = Memory(tmp_path / 'vault')
    session = uuid4()
    memory.record(session, 'Prefiro que você explique com exemplos.', 'Certo.', [])
    memory.record(session, 'Não quero que você faça respostas curtas.', 'Entendi.', [])
    stored = Memory(memory.vault).procedural_context()
    assert len(stored) == 1
    assert stored[0]['content'] == 'Não quero que você faça respostas curtas.'


def test_temporal_parser_rejects_imaginary_and_invalid_dates():
    today = datetime(2026, 11, 2, 10, tzinfo=SAO_PAULO)
    assert explicit_event('Minha prova acontecerá daqui a três semanas.', today)['due_date'] == '2026-11-23'
    assert explicit_event('Tenho uma prova dia 31/02/2027.', today) is None
    assert explicit_event('Imagine que eu tenho uma prova amanhã.', today) is None
    assert explicit_event('Tenho uma prova amanhã?', today) is None


def test_cognition_chooses_work_for_the_actual_question():
    simple = plan_for('Bom dia')
    complex_task = plan_for('Compare as fontes e faça um plano para minha prova de física', {'web_search'})
    assert simple.roles == ('contexto', 'raciocínio')
    assert {'educador', 'planejamento', 'tempo', 'verificação'} <= set(complex_task.roles)
    assert 'composição visual' not in complex_task.roles


def test_long_term_goal_survives_restarts_without_duplicates(tmp_path):
    memory = Memory(tmp_path / 'vault')
    session = uuid4()
    memory.record(session, 'Quero aprender Engenharia de Software.', 'Vamos organizar um plano.', [])
    memory.record(session, 'Quero aprender Engenharia de Software.', 'Vamos seguir.', [])
    restored = Memory(memory.vault)
    goals = restored.active_goals()
    assert len(goals) == 1
    assert goals[0]['title'] == 'Engenharia de Software'
    assert any(node['title'] == 'Engenharia de Software' for node in restored.graph()['nodes'])
    assert restored.set_goal_status(goals[0]['id'], 'completed')
    assert Memory(memory.vault).active_goals() == []


def test_commitment_reaches_conversation_and_authenticated_controls(settings):
    observed = []
    class Provider:
        async def reply(self, system, messages):
            observed.append(system)
            return {'reply': 'Senhor, sua prova está próxima. Posso ajudar na revisão.',
                    'topics': [], 'tool_calls': []}
    with TestClient(create_app(settings, Provider())) as client:
        assert client.get('/memory/commitments').status_code == 401
        first = client.post('/chat', headers=AUTH,
                            json={'message': 'Minha prova de matemática é daqui a dois dias.'})
        assert first.status_code == 200
        events = client.get('/memory/commitments', headers=AUTH).json()['events']
        assert len(events) == 1 and events[0]['days_left'] == 2
        assert client.get('/memory/layers', headers=AUTH).json()['temporal'] == 1
        assert client.get('/memory/goals').status_code == 401
        second = client.post('/chat', headers=AUTH, json={'message': 'Bom dia'})
        assert second.status_code == 200
        assert 'compromisso real próximo' in observed[-1]
        result = client.post(f"/memory/commitments/{events[0]['id']}/status", headers=AUTH,
                             json={'status': 'completed'})
        assert result.json() == {'updated': True}
        assert client.get('/memory/commitments', headers=AUTH).json()['events'] == []
