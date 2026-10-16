# Estúdio de Sites do Cronos

Abra pelo botão **ESTÚDIO DE SITES** ou diga **“Cronos, abrir estúdio de sites”**. **“Cronos, faça um site para…”** abre o briefing com o pedido preenchido. O Cronos passa a tratar o usuário como **senhor** por uma instrução adicional; o arquivo de personalidade existente não é sobrescrito.

## Criar e revisar

A galeria reúne 13 direções de demonstração, com ilustrações vetoriais originais. Não representa clientes captados, trabalho já entregue nem fotografia de um negócio real. As duas referências enviadas orientaram a organização em categorias, galeria/prévia e painel de direção.

“Explorar demonstração funcional” salva um rascunho sem consultar a IA. “Personalizar com IA” pede nome, briefing e a escolha entre planejamento autônomo e referência. A integração é escolhida entre as já cadastradas; nenhum modelo proprietário ou API nova é inventado. Não é preciso recadastrar credenciais.

O gerador usa a integração escolhida para entregar HTML, CSS e JavaScript. Após uma entrega inválida, pode pedir **uma correção** ao mesmo modelo. Não há repetição de falhas de cota/conexão por parte do estúdio; os adaptadores existentes mantêm seu próprio comportamento de transporte. Gemini usa REST para código, sem mudar o transporte da conversa cotidiana. Cada etapa informa o que está ocorrendo, com horários e tempo decorrido; a barra em movimento indica atividade, sem porcentagem fictícia. Fechar a tela não apaga nem cancela uma criação aceita pelo servidor.

Envie referências em **Imagens e 3D**. A descrição visual usa o analisador já configurado (Gemini); pode consumir uma chamada adicional. Uma descrição textual também serve como referência. Imagens próprias são normalizadas e perdem metadados EXIF; até 2 MiB por envio. A opção de pesquisa de imagem na criação permite ao Cronos buscar uma imagem pública quando faltam recursos próprios. Se a fonte não responder, registra a falha e segue com ilustração original. A pesquisa no Wikimedia Commons apresenta fonte, autor e licença para conferência, e baixa uma cópia limitada. A disponibilidade da fonte externa varia.

No projeto aberto, use **Pedir ao Cronos** para revisar. Pedidos reconhecidos por voz como “mude a cor”, “ajuste o layout”, “corrija…” também são encaminhados ao projeto aberto. “Planeje sozinho” escolhe a direção autônoma; “nome do projeto…” preenche o nome no briefing; “inicie a criação” inicia quando os campos necessários estiverem preenchidos. “Cancele a criação”, “mostre o código” e “exporte o projeto” têm ações locais. A interface continua disponível para completar informações que a fala não trouxe.

**Briefing e dados confirmados** permite atualizar nome, categoria e informações comerciais. Depois peça uma revisão para aplicá-los ao código. O editor também permite salvar HTML/CSS/JS manualmente. Edições usam a revisão de origem para impedir que uma aba antiga sobrescreva uma versão nova. Cada alteração aceita cria uma versão; a restauração preserva todo o histórico. “Duplicar” cria outro projeto a partir da versão atual, com cópia dos recursos e sem os envios de teste. Há até 80 projetos ativos e 40 versões por projeto: arquive sem apagar e reative pela lista de arquivados, ou duplique para continuar outro histórico.

## Funções e verificações

Contato e solicitação de horário usam um runtime próprio, com SQLite, validação no servidor, consentimento, limite de envio e restrição de horário duplicado. Dentro do Cronos os envios pertencem exclusivamente à base de **testes da prévia**. Não enviam e-mail/SMS nem confirmam atendimento com terceiros. O calendário tem um horário por site; capacidade, equipe, feriados e fuso precisam ser adaptados à operação real.

O código gerado não é executado como Python, terminal, npm ou comando local. A prévia tem origem opaca, ticket temporário, CSP específica e sandbox; não recebe o token do Cronos. A comunicação com o pai verifica janela, canal e tipo de operação e permite apenas os formulários daquele projeto e resultados de teste. A permissão de formulários permite validação e eventos; `form-action 'none'` bloqueia envio externo. Não há acesso a arquivos, chaves ou APIs internas a partir da prévia.

As verificações têm três origens identificadas:

- **Código:** arquivos permitidos, recursos locais, estrutura, destinos, campos e sintaxe quando Node está disponível. No Windows, o parser é iniciado sem janela de console. Não instala Node automaticamente.
- **Backend:** contatos, entrada inválida, falta de consentimento, texto excessivo, honeypot, campos inesperados, conflito de horário e texto adverso em banco temporário separado.
- **Navegador:** DOM em 390 e 1280 px, largura, imagens, destinos, labels, conexão dos formulários, validação nativa e erros JavaScript observados. Novas versões geradas são verificadas quando sua prévia está aberta; também há botão para repetir. Sem navegador aberto, esses testes ficam pendentes, sem simular aprovação.

Isso não equivale a auditoria de segurança, certificação de acessibilidade ou garantia de todos os fluxos de negócio. Pagamento real, autenticação de clientes, estoque, e-mail e serviços comerciais exigem implementação específica e credenciais antes da entrega. Falhas detectadas podem compor um pedido de correção no painel, sem geração adicional oculta.

## 3D e desempenho

O visualizador é carregado só em projetos com um **GLB 2.0 autocontido**, até 8 MiB, sem extensões obrigatórias, URIs externas ou geometria acima do limite leve. Há rotação, zoom, teclado, restauração da câmera e separação dos objetos existentes. Ele não cria um modelo fiel de um Buds nem inventa componentes internos: um modelo adequado e seus direitos de uso precisam ser fornecidos. Há um modelo ativo por projeto para preservar versões anteriores.

Three.js fica no recurso do visualizador, fora do carregamento inicial da aplicação. A renderização ocorre por interação/redimensionamento, sem loop contínuo; a densidade de pixels é limitada. A prévia usa tamanho real disponível para manter cliques e leitura. Os testes ajustam a largura do documento para observar celular e desktop. A cena principal pausa durante o estúdio.

## Oportunidades e proposta

A pesquisa aceita cidades brasileiras e categorias como restaurantes, hotéis/pousadas/motéis, lava-jatos, lojas, clínicas, salões, academias, imóveis, educação, eventos e serviços profissionais. Não varre todo o Brasil de uma vez. Mostra registros reais das fontes, respeitando limites e cobertura. “Cruzar fontes” pesquisa evidências adicionais sobre o site. Contatos, avaliações e porte ausentes permanecem desconhecidos.

A avaliação pública lê HTML com conexão presa a IP público validado, TLS verificado, limites de tamanho/tempo e nova validação a cada redirecionamento. Relata status HTTP, HTTPS, título, viewport, headings, formulários e imagens sem alt. Não executa scripts do site alheio nem comprova ausência de falhas. Aparência do negócio não permite deduzir capacidade financeira ou interesse em contratar.

As faixas de R$400 a R$15.000 representam sugestões por complexidade do escopo. Conteúdo, hospedagem, licenças, manutenção, requisitos e orçamento devem ser combinados com o responsável. A IA pode recomendar reduzir ou ampliar o escopo com justificativa, sem inventar demanda ou dinheiro disponível.

## Arquivos e entrega

Projetos e versões ficam em **`<cofre atual>/.cronos/studio/projects.sqlite3`**. Imagens/modelos e dados da prévia ficam nas subpastas do projeto nesse diretório. A pasta é excluída da indexação de notas. A ferramenta somente de leitura `studio_status` permite ao Cronos consultar projetos, etapas e verificações reais.

Exportar gera um ZIP com `site/`, código editável, imagens/modelo utilizados, atribuições, runtime de formulários, servidor local em Python padrão e relatório. Não inclui `.env`, credenciais, notas, conversas, referências privadas, briefing interno ou base de contatos da prévia. Abra `ABRIR-SITE.bat` ou execute `python server.py`; a prévia exportada usa `127.0.0.1:8080`. Não é publicação automática: hospedagem de produção exige HTTPS, domínio, acesso administrativo, políticas, backups e manutenção, conforme o documento incluído no ZIP.

A atualização do Cronos continua no **pacote único**: extraia tudo e abra **ABRIR-CRONOS.bat**, mantendo a pasta antiga. O aplicador altera somente os arquivos de código do manifesto e mantém `.env`, `config`, personalidades, cofre e integrações.

## Verificação de desenvolvimento

No ambiente existente, sem worktree adicional:

```sh
cd /workspace/Cronos
npm --prefix frontend ci --cache /tmp/cronos-npm-cache
npm --prefix frontend run lint
npm --prefix frontend run build
.venv/bin/python -m pytest
```

O comando de build também gera `cronos/studio/product-3d.js` e inclui a licença MIT da Three.js. O navegador de teste requer Playwright e Chromium; não são dependências do aplicativo do usuário. Para exercitar a integração sem chaves ou cobrança, em um terminal execute:

```sh
.venv/bin/python frontend/scripts/studio-fixture-server.py
```

Em outro, execute `.venv/bin/python frontend/scripts/check-studio.py`. Depois do fluxo principal, `.venv/bin/python frontend/scripts/check-studio-export.py` verifica o ZIP exportado em um servidor HTTP independente, incluindo sessão/CSRF, gravação de contato pelo navegador e GLB local. A fixture usa cofre temporário e provedor de teste identificado. A suíte cobre a API real local, sandbox/CSP, formulários, conflitos, desktop/celular, GLB, geração de teste, edição, histórico, restauração, exportação e roteamento local. Não constitui validação da qualidade das respostas dos provedores externos nem teste no Windows/notebook do usuário.
