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
