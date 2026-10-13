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

## Demora da resposta e captação

O transporte Gemini Live continua usando o mesmo modelo e modo AUDIO. Quando a transcrição já contém o JSON completo e validado (incluindo temas e chamadas de ferramentas), a sessão é encerrada sem esperar pelo áudio Gemini descartado. Nenhuma resposta parcial é enviada à memória ou executada como ferramenta.

O painel Processamento informa os tempos de reconhecimento, conversa, primeira síntese Fish e reprodução. São medições sem texto nem chaves, salvas em `.cronos-local/last-client-latency.json`; os tempos de conexão/primeira transcrição Live ficam em `.cronos-local/last-live-timing.json`. O tempo “da pergunta enviada até a voz” não inclui a gravação: a detecção de fim da fala ainda usa aproximadamente 750 ms de silêncio. Comparar as etapas permite verificar se a espera vem do reconhecimento, da IA ou do áudio, sem atribuir tudo ao Google.

Dispositivos oferece sensibilidade e ganho do microfone. O padrão agora detecta sinais mais baixos e aplica ganho 2x ao áudio de entrada do transcritor; ruído constante e cliques curtos continuam filtrados. Ganho não cria palavras ausentes nem separa uma voz distante de ruído alto. As configurações do provedor e a voz personalizada continuam intactas.

O fundo dos painéis e os desenhos de Processamento, Internet e Segurança reutilizam regiões das imagens originais. Essas ilustrações são estáticas; os dados e controles permanecem elementos funcionais separados.

### Notícias do dia

Pedidos explícitos de notícias atuais fazem a busca antes da primeira geração: o Gemini já recebe as fontes e pode responder com uma única chamada, em vez de decidir a busca em uma chamada anterior. Notas e resultados de buscas antigas não são usados como fontes atuais nesse caminho. A ferramenta `web_news` usa o filtro das últimas 24 horas, preserva datas/URLs e mantém um cache por até 90 segundos. Permissões, modo local e confirmação de ferramentas continuam sendo respeitados. Se a busca falha, a falha é fornecida ao modelo; nenhuma manchete é preenchida com exemplos.

Processamento passa a exibir o tempo de busca e a quantidade de chamadas à IA. A primeira parte enviada ao Fish tem até 120 caracteres para iniciar a reprodução antes; as partes restantes continuam sendo reproduzidas integralmente. Modelos, chaves e ID da voz permanecem os mesmos.

A busca de notícias limita a espera de rede a 3 segundos por operação do buscador. Nesse caminho, novas buscas no mesmo turno são bloqueadas, inclusive com argumentos diferentes, para evitar uma sequência de esperas após falha. Isso não garante um prazo total fixo: Gemini, rede e síntese de voz ainda têm latências próprias.

## Início antecipado da resposta em todas as conversas

A interface usa `POST /chat/stream` (NDJSON autenticado), mantendo `/chat` compatível com clientes existentes. No transporte Gemini Live, o JSON começa com `tool_calls`: pedidos de ferramenta não são anunciados como ações realizadas. Quando esse campo é vazio, uma frase inicial completa (ou um trecho curto em limite de palavra) pode ser enviada à voz enquanto o restante da resposta e os metadados de memória ainda chegam. A resposta integral continua sendo validada e salva; não é cortada para reduzir a espera. Resumos de memória evitam duplicar o texto inteiro.

A interface reproduz o início e o restante na ordem, sem repetir o prefixo. ESC cancela leitura, síntese e reprodução; fechar o fluxo cancela a geração no servidor. Falhas mantêm o código do provedor e não disparam repetição automática. Caso o modelo não respeite a ordem dos campos, o sistema aguarda o resultado validado, sem tentar extrair texto de um pedido de ferramenta. A chave, o ID da voz, o modelo Fish e seu pedido JSON continuam os mesmos.

`chat_ms` no diagnóstico do cliente mede agora a espera até o primeiro trecho enviado à voz quando há transmissão antecipada; a duração total do backend permanece disponível separadamente. Tempos de Gemini e Fish medidos na nuvem não garantem a mesma duração de ponta a ponta no Windows: captura, reconhecimento, rede e reprodução também participam.
