from pathlib import Path

from tools.restore_existing_data import automatic_source, default_configuration, find_sources, restore, select_source


def sample_data(path: Path, note: str) -> Path:
    (path / 'vault').mkdir(parents=True)
    (path / '.env').write_text('GEMINI_API_KEY=local-only\n', encoding='utf-8')
    (path / 'vault' / 'memory.md').write_text(note, encoding='utf-8')
    return path


def test_restores_shared_data_without_publishing_or_replacing_the_old_folder(tmp_path):
    home = tmp_path / 'home'
    source = sample_data(home / 'Documents' / 'Cronos-Dados', 'Minha memória antiga')
    sample_data(home / 'Cronos-R39', 'Versão vazia')
    target = home / 'Cronos-R40'
    (target / 'config').mkdir(parents=True)
    (target / 'config' / 'providers.example.json').write_text('{}')
    assert source in find_sources(target, home)
    assert select_source(find_sources(target, home), target, home) == source
    assert restore(target, home) == source
    assert (target / 'vault' / 'memory.md').read_text() == 'Minha memória antiga'
    assert 'GEMINI_API_KEY=local-only' in (target / '.env').read_text()
    assert (source / 'vault' / 'memory.md').read_text() == 'Minha memória antiga'
    assert restore(target, home) is None


def test_restores_one_existing_installation_without_prompt(tmp_path):
    home = tmp_path / 'home'
    source = sample_data(home / 'Cronos-R38', 'Histórico')
    target = home / 'Cronos-R40'
    target.mkdir()
    assert find_sources(target, home) == [source]
    assert restore(target, home) == source
    assert (target / 'vault' / 'memory.md').read_text() == 'Histórico'


def test_fresh_empty_release_is_not_auto_selected_as_the_old_data(tmp_path):
    home = tmp_path / 'home'
    fresh = sample_data(home / 'Cronos-R39', 'Sem conversa anterior')
    example = 'GEMINI_API_KEY=local-only\n'
    (fresh / '.env.example').write_text(example, encoding='utf-8')
    assert default_configuration(fresh)
    assert automatic_source([fresh], home) is None
