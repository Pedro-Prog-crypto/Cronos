# Painéis desktop do Cronos

As 12 entradas da árvore abrem painéis próprios. A bancada `/tests` continua disponível para diagnóstico, mas não é mais embutida na interface principal. Só o painel visível atualiza seus gráficos; o núcleo para de desenhar enquanto um painel está aberto. Fontes, fundo e ilustração do escudo são locais, sem downloads no uso diário.

| Painel | Controles e dados conectados |
|---|---|
| Processamento | CPU medida, fases da conversa, tempos reais do último turno, requisições ativas, economia de quadros e atualização, prioridade normal/baixa no Windows, escuta em segundo plano. |
| Visão computacional | Câmera escolhida, captura explícita da tela, análise Gemini, caixas e confiança estimadas, OCR, filtro de confiança e análise periódica a cada 10 segundos quando ativada. |
| Síntese de voz | Voz já configurada, teste de texto, onda do áudio reproduzido, pausa/retomada, velocidade, tom, volume e seleção de saída quando o WebView fornece essa função. |
| Entendimento de linguagem | Última frase da conversa, abertura do card de escrita, idioma/estilo, limite de contexto e resposta por voz somente após ser chamado, se ativado. A confiança fica sem valor quando o transcritor não fornece essa medição. |
| Planejamento | Planos e etapas reais, estados, datas, prioridade, revisão antes de marcar uma etapa em andamento e criação de novas etapas. Marcar progresso não executa o trabalho descrito. |
| Ferramentas | Permissões aplicadas no servidor e também a aprovações pendentes, confirmação de ações, pasta autorizada e última ação registrada. Shell arbitrário não é habilitado por esse painel. |
| Integrações | Caminho real do Obsidian, seleção de um cofre para o próximo início na janela Windows, sincronização, exportação do diário, verificação SQLite e cadastro de adaptadores sem incluir chaves no manifesto. |
| Banco de dados | Notas reais, SQLite, disco, grafo com zoom/seleção/tela cheia, backup consistente, reindexação e backup diário opcional. Backups anteriores ao prazo vão para a subpasta `archive`; não são apagados. |
| Internet | Teste explícito de conexão sem gerar texto, latência dessa amostra, buscas reais, pesquisa e histórico. Os dois modos de busca usam o adaptador DuckDuckGo existente. |
| Dispositivos | Inventário Windows, níveis do microfone e da voz, escolha de entrada/saída, escuta automática ao iniciar e abertura das configurações nativas de áudio/Bluetooth. |
| Segurança | Auditoria Windows explícita, estado consultado do BitLocker, chaves ocultas, permissões, eventos e bloqueio da sessão do Windows ao minimizar, se ativado. As notas Markdown não são criptografadas pelo Cronos. |
| Monitoramento | CPU/RAM medidas, tempo da última conversa, disponibilidade dos módulos, histórico desta sessão, eventos e frequência de atualização. Disponibilidade não afirma que todo serviço externo foi testado. |

Preferências ficam na tabela `panel_preferences` do SQLite do cofre. Trocar o cofre pelo seletor grava somente `CRONOS_VAULT` no `.env` e requer reinício; as notas do cofre anterior são preservadas. O modelo e as credenciais atuais de Gemini/Fish permanecem intactos. O tom é um ajuste de reprodução local e afeta também a duração do áudio.

O pareamento Bluetooth abre o próprio Windows. Não existe um serviço de sincronização/controle remoto entre notebooks e celulares; o painel indica essa ausência, sem inventar um telefone conectado. Os seletores de voz e de memória mostram a configuração atual; não anunciam perfis inexistentes. A segurança de ações críticas continua exigindo confirmação humana.

## Verificação

`npm --prefix frontend run lint` e `npm --prefix frontend run build` verificam tipos e montam a interface. `python -m pytest -q` inclui persistência, validação, revogação de permissões, backup, retenção, cofre e planos.

`python frontend/scripts/check-panels.py` usa Playwright/Chromium com uma memória temporária, APIs de teste e um executor Windows simulado. Abre os 12 painéis, verifica controles, câmera, reprodução e ondas de áudio, e gera capturas em `.cronos-local/panel-previews`. As notas dessas capturas são demonstrações e nunca entram no cofre do usuário. Nenhuma chave real é usada.

`python frontend/scripts/check-voice-flow.py` verifica microfone contínuo, fala, ESC e Olho de Deus, com provedores simulados. O desempenho físico do Samsung Flash F30, os periféricos reais e a integração Windows precisam ser conferidos no notebook.
