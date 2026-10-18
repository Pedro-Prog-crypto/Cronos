"""A valid HTML package can still be a visibly unfinished website."""
from cronos.studio.catalog import starter
from cronos.studio.directions import visual_review
from cronos.studio.designs import site


def failures(files):
    return {item['name'] for item in visual_review(files, {}, []) if item['status'] == 'failed'}


def test_review_rejects_the_pending_text_only_wireframe_from_the_reported_preview():
    files = {
        'index.html': '''<!doctype html><html lang="pt-BR"><head><title>Nau</title>
        <meta name="viewport" content="width=device-width"><link rel="stylesheet" href="styles.css">
        <script src="app.js" defer></script></head><body><main>
        <section><h2>Conheça a Nau</h2><p>Conteúdo pendente: descrição do restaurante.</p></section>
        <section><h2>Cardápio Selecionado</h2><p>Conteúdo pendente: itens do cardápio.</p></section>
        <section><h2>Como Chegar</h2><p>Conteúdo pendente: mapa interativo.</p></section>
        </main></body></html>''',
        'styles.css': 'body{background:#f0e7dc;color:#86411c}section{min-height:190px;text-align:center}',
        'app.js': '',
    }
    assert {'Sem texto de rascunho ou conteúdo pendente', 'Abertura tem elemento visual',
            'CSS apresenta layout próprio'} <= failures(files)


def test_finished_studio_directions_pass_the_new_quality_bar():
    for category in ('restaurante', 'barbearia', 'hotel'):
        files = site(category, 'Estudo local')
        baseline = starter(category, 'Direcao antiga')
        assert not {item['name'] for item in visual_review(files, baseline, []) if item['status'] == 'failed'}


def test_rich_restaurant_starter_is_not_confused_with_pending_ai_output():
    files = starter('restaurante', 'Restaurante Nau')
    assert 'Conteúdo pendente: descrição do restaurante.' not in files['index.html']
    assert 'Conteúdo pendente: itens do cardápio.' not in files['index.html']
    baseline = starter('restaurante', 'Direcao anterior')
    failed = {item['name'] for item in visual_review(files, baseline, []) if item['status'] == 'failed'}
    assert 'CSS apresenta layout próprio' not in failed
    assert not failed
