import pytest
from cronos.live_output import parse_live_output
from cronos.providers import ProviderError


def test_live_recovers_literal_newlines_and_bad_memory_without_regenerating():
    result,recovered=parse_live_output('{"tool_calls":[],"reply":"Uma explicação.\nOutra linha.","topics":[{"title":"incompleto"}]}')
    assert recovered and result=={'reply':'Uma explicação.\nOutra linha.','tool_calls':[],'topics':[]}


def test_live_preserves_good_topics_and_real_tools():
    result,recovered=parse_live_output('{"tool_calls":[{"name":"obsidian_search","arguments":{"query":"Platão"}}],"reply":"Buscando.\nAguarde.","topics":[{"title":"Platão","summary":"Filósofo"},{}]}')
    assert recovered and result['topics'][0]['title']=='Platão'
    assert result['tool_calls'][0]['arguments']=={'query':'Platão'}


def test_live_accepts_valid_tool_only_response_without_inventing_narration():
    result,recovered=parse_live_output('{"tool_calls":[{"name":"music_search","arguments":{"query":"Nada pra Fazer"}}]}')
    assert recovered and result['reply']=='' and result['topics']==[]
    assert result['tool_calls'][0]['name']=='music_search'
    with pytest.raises(ProviderError):parse_live_output('{"tool_calls":[{"name":"delete","arguments":"guess"}]}')


def test_live_truncated_metadata_only_recovers_at_end_after_empty_tools():
    raw='{"tool_calls":[],"reply":"Resposta completa.","topics":[{"title":'
    with pytest.raises(ProviderError):parse_live_output(raw)
    assert parse_live_output(raw,complete=True)[0]['reply']=='Resposta completa.'
    with pytest.raises(ProviderError):parse_live_output(raw.replace('"tool_calls":[]','"tool_calls":[{"name":"delete"}]'),complete=True)


@pytest.mark.parametrize('raw', ['{"tool_calls":"execute","reply":"ok"}', '{"reply":"incompleto', 'texto sem estrutura'])
def test_live_does_not_guess_actions_or_incomplete_responses(raw):
    with pytest.raises(ProviderError):parse_live_output(raw,complete=True)


def test_plain_live_speech_requires_confirmed_turn_and_does_not_create_tools():
    text='Sócrates foi um filósofo ateniense. Vamos pensar em um exemplo?'
    with pytest.raises(ProviderError):parse_live_output(text,complete=True)
    with pytest.raises(ProviderError):parse_live_output(text,allow_plain=True)
    result,recovered=parse_live_output(text,complete=True,allow_plain=True)
    assert recovered and result=={'reply':text,'tool_calls':[],'topics':[]}
    for raw in ('{"reply":"quebrou', '[{"name":"delete"}]', '"tool_calls": [{"name":"delete"}]'):
        with pytest.raises(ProviderError):parse_live_output(raw,complete=True,allow_plain=True)


def test_completed_rest_reply_recovers_optional_memory_but_never_invalid_tools():
    from cronos.providers import parse_completed_reply
    result=parse_completed_reply('```json\n{"reply":"Olá!","topics":[{"title":"inválido"}]}\n```')
    assert result=={'reply':'Olá!','topics':[],'tool_calls':[]}
    result=parse_completed_reply('{"tool_calls":[{"name":"music_search","arguments":{"query":"Nada pra Fazer"}}]}')
    assert result['reply']=='' and result['tool_calls'][0]['name']=='music_search'
    with pytest.raises(ProviderError):parse_completed_reply('{"reply":"ok","tool_calls":[{"name":"delete","arguments":"guess"}]}')
