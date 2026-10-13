from uuid import uuid4
import pytest
from cronos.memory import Memory
from cronos.memory_policy import knowledge_topics

@pytest.mark.parametrize('message',['Cronos, na escuta?','Kronos, você tá me ouvindo?','Oi, bom dia!','Obrigado','Abrir painel','teste de áudio'])
def test_social_turn_never_creates_knowledge_even_if_model_proposes_it(tmp_path,message):
    memory=Memory(tmp_path/'vault')
    assert memory.record(uuid4(),message,'Estou aqui.',[{'title':'Disponibilidade do assistente','summary':'Saudação'}])==[]
    assert not list((memory.vault/'Memorias').glob('*.md'))
    assert not list((memory.vault/'Temas').glob('*.md'))
    assert memory.graph()['nodes']==[]
    assert memory.stats()['messages']==2

@pytest.mark.parametrize('subject',['Sócrates','Platão','Programação Python','Equações quadráticas','Geografia','Pecuária','Notícias mundiais','Astronomia','Cronos'])
def test_subjects_are_open_ended_and_not_restricted_to_a_fixed_list(subject):
    topic={'title':subject,'summary':'Conhecimento discutido.'}
    assert knowledge_topics('Explique '+subject,[topic])==[topic]

def test_greeting_with_real_question_keeps_knowledge(tmp_path):
    memory=Memory(tmp_path/'vault')
    paths=memory.record(uuid4(),'Bom dia, quem foi Sócrates?','Resposta',[{'title':'Sócrates','summary':'Filósofo grego.'}])
    assert len(paths)==1 and len(list((memory.vault/'Memorias').glob('*.md')))==1
    assert all(not n['path'].startswith('Conversas/') for n in memory.graph()['nodes'])

def test_old_social_notes_are_hidden_not_deleted_and_pagination_is_correct(tmp_path):
    memory=Memory(tmp_path/'vault')
    old=memory.vault/'Memorias/old.md';old.write_text('# Cronos, na escuta?\nEstou aqui.')
    note=memory.vault/'Temas/socrates.md';note.write_text('# Sócrates\nFilósofo.')
    memory.sync_notes()
    graph=memory.graph(0,1)
    assert graph['total']==1 and graph['next_offset'] is None and graph['nodes'][0]['title']=='Sócrates'
    assert old.read_text()=='# Cronos, na escuta?\nEstou aqui.'

def test_followup_can_save_real_content_and_cronos_myth_is_not_an_assistant_call(tmp_path):
    memory=Memory(tmp_path/'vault')
    paths=memory.record(uuid4(),'Explique Cronos na mitologia','Um titã grego.',[{'title':'Cronos','summary':'Mitologia grega.'}])
    assert paths[0] in {node['path'] for node in memory.graph()['nodes']}
    assert memory.record(uuid4(),'Sim','Mais ideias de Sócrates.',[{'title':'Sócrates','summary':'Continuação filosófica.'}])
