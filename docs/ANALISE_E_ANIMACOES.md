# Análise de arquivos e nova animação

Esta atualização altera código e recursos visuais. Não muda `.env`, `config/providers.json`, personalidade, preferências, banco de memória, cofre ou configurações de voz. O arquivo atual enviado excedeu o limite de transferência de 32 MiB; a implementação usa a revisão do repositório b736566 como base. Não houve leitura nem cópia das chaves da instalação do usuário.

## Interface

- O holograma central é um anel de filamentos azuis que se deformam continuamente, com variação por escuta e áudio da resposta. A referência de movimento é o vídeo Download87.mp4; não se usa o vídeo como fundo nem se adiciona o monge da prévia anterior.
- Geometria limitada, base angular em cache e brilho em meia resolução. Continua usando um único worker para o holograma, com alternativa Canvas no navegador sem suporte. Pausa quando a cena não está visível.
- O fundo contém uma camada estática de centenas de estrelas, 38 realces que cintilam e duas estrelas cadentes espaçadas. Movimento reduzido do sistema pausa os efeitos CSS.
- O espiral só aparece quando existem notas reais. Partículas decorativas pequenas e brancas acompanham as notas, com até 3 mil pontos em três caminhos SVG. Rastros crescem com as notas; eles não indicam novas memórias nem relações semânticas. Os vínculos semânticos vêm do grafo real.
- Nenhum globo fica carregado na tela inicial. “Cronos, abrir Olho de Deus” e a ação no painel continuam abrindo o aplicativo em tela cheia sob demanda.

## Análise

Os ícones de imagem e arquivo ficam ao lado do microfone. “Cronos, quero que você analise uma imagem” ou “Cronos, analisar um ZIP” abre o seletor correspondente, sem uma geração de conversa desnecessária. A escolha de arquivo exige clique no navegador.

A prévia é local ao servidor Cronos. A imagem/trechos só seguem para a IA ao clicar em **Analisar**, com indicação do destino. A barra mostra “ANALISANDO” e o scanner passa pela imagem apenas enquanto a chamada está pendente. Conclusão e erro param o scanner. Fechar/ESC aborta a espera no navegador e não reproduz resposta atrasada; o provedor pode já ter recebido a chamada.

- Imagens PNG/JPEG de até 2 MiB; normalizadas a até 1600 px e sem EXIF pelo caminho de visão existente. Usa Gemini configurado, sem mudar modelo ou voz.
- ZIP, texto UTF-8 e código de até 2 MiB. ZIP é lido em memória, sem extração no disco, com até 120 entradas, 6 MiB descompactado e 2 MiB por arquivo.
- Não executa comandos/scripts nem aceita instruções internas como autorização de ferramentas. PDF, vídeo e binários não são suportados por esta função.
- Ignora arquivos ocultos, credenciais conhecidas e binários; reduz padrões reconhecidos de chaves em texto. Isso não identifica todo segredo possível: a prévia informa os arquivos selecionados e o envio depende do usuário.
- Contexto limitado a 24 mil caracteres com aviso de truncamento; usa a IA de conversa selecionada para documentos. Nenhum arquivo ou imagem é salvo automaticamente no cofre.

## Instalação e evidência

Prefira o atualizador supervisionado do Cronos, que faz backup local e aplica apenas arquivos de código, preservando configuração e memória. Ao usar o ZIP manualmente, feche o Cronos, faça cópia da instalação e substitua somente a pasta `cronos` dentro da instalação já usada. Não comece por uma pasta nova vazia e não substitua `.env`, `config`, cofre ou `.cronos-local`.

Testes de backend cobrem autenticação, consentimento, limites, arquivos privados, ZIP inválido, truncamento e recusa de ferramentas. Testes de navegador usam provedores e notas simulados para verificar seleção, scanner, resultados, erros, comandos locais e ausência de globo ocioso. Capturas da interface usam 300 notas de teste; não são as memórias do usuário. Não houve teste com as chaves reais nem medição no Samsung Flash F30.
