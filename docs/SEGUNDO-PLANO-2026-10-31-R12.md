# Cronos em segundo plano — R12

## O que mudou

O ouvinte anterior reconhecia o nome, abria a janela e reproduzia uma saudação. Ele não encaminhava uma pergunta completa para a IA sem depender da interface. Agora o ouvinte tem uma conversa própria: gravação, reconhecimento, pergunta real no mesmo motor de conversa e memória, síntese da resposta e reprodução nativa do Windows. A saudação de ativação não é contabilizada como uma resposta da IA.

- **“Cronos”** chama a conversa e conserva a janela atual. Aguarde a confirmação e faça a pergunta. Também é possível começar a pergunta na mesma fala, sem usar o nome como um comando para abrir a janela.
- **“Abrir Cronos”** abre/restaura a interface principal. A frase de chamada e a de abertura são configurações separadas. “Fechar Cronos” fecha a interface; o serviço já iniciado continua disponível.
- O servidor continua ativo após fechar a janela. Não precisa manter o holograma, uma aba do navegador ou uma janela de CMD aberta para conversar em segundo plano.
- Quando a interface usa o microfone, a captura nativa libera o dispositivo. Ao fechar a interface, ele volta ao ouvinte. Há uma reserva curta para a inicialização e uma expiração automática se a janela parar de informar seu estado.
- O aplicativo usa um **perfil persistente do WebView2**, sem modo privado, e conserva a porta local do servidor entre reinicializações quando ela está disponível. Não instala uma regra de concessão automática de permissões nem apaga uma negativa do usuário.
- A visão em segundo plano utiliza a captura local do Windows. Mantém somente a captura mais recente na RAM e renova sua sessão enquanto o serviço autorizado estiver ativo. Desligar a visão limpa a sessão. Não usa o seletor de aba/janela do navegador nesse modo local.
- Perguntas comuns de conhecimento não recebem uma captura pelo ouvinte nativo. Quando a pergunta se refere à tela, o motor recebe o contexto disponível. Há uma tentativa de ler o endereço e o texto **público** da página em primeiro plano usando a acessibilidade do Windows, sem atalhos de teclado nem alteração da área de transferência. Se o navegador não expuser o endereço, a página exigir login ou a leitura não concluir, o conteúdo fica limitado à captura disponível. Textos longos podem ser recortados; o assistente não deve afirmar que leu o artigo completo nesse caso.
- Resumos pedidos na tela aparecem em um **card nativo separado**, com texto, rolagem, arrastar, minimizar e X. Ele não abre a interface principal. A apresentação de imagens e as demais funções existentes continuam na interface principal.
- A voz configurada segue como primeira opção. Se sua síntese falhar antes de começar, a mesma resposta pode ser lida por uma voz em português instalada no Windows. Esse timbre de reserva pode ser diferente. A reprodução nativa utiliza a saída padrão de áudio do Windows. Se nenhuma voz funcionar, a resposta recebida aparece no card e a gravação fica disponível para tentar novamente.
- Interromper cancela os pedidos de reconhecimento/síntese em andamento no servidor. A gravação é mantida para uma tentativa explícita; o aplicativo não repete ações automaticamente. Uma falha posterior nos metadados não descarta uma resposta completa já recebida; o relatório distingue a confirmação da memória.

## Instalar e usar

1. Encerre a versão antiga. Se ela tiver um indicador no canto da tela, clique com o botão direito e escolha **Encerrar assistente**. Nas versões anteriores sem esse recurso, feche o Cronos e pare o ouvinte antigo, se estiver ativo.
2. Extraia **todo o ZIP** em uma pasta permanente. O pacote contém o aplicativo completo, não somente um iniciador.
3. Para conservar suas chaves, integrações e memórias, execute **MIGRAR-DADOS-DA-VERSAO-ANTIGA.bat** e selecione a pasta antiga que realmente contém esses dados. O arquivo público não inclui `.env` ou vault privado.
4. Execute **ABRIR-CRONOS.bat**. A instalação completa prepara as dependências e o modelo de reconhecimento local. Se o modelo estiver pendente, use a preparação oferecida no painel.
5. Abra **Entendimento de linguagem → Comando de voz em segundo plano**. Confira as quatro frases e as opções **Responder em segundo plano** e **Acompanhar a tela no Windows**. Clique em **Salvar frases** se alterar algo e em **Iniciar ouvinte** se ainda estiver desativado. Um ouvinte antigo ativo é substituído pela versão nova.
6. Se quiser o serviço disponível após ligar o notebook, ative **Iniciar com Windows** uma vez. A escolha permanece salva; um atalho de inicialização já habilitado é atualizado para a instalação atual.
7. Feche a janela principal e mantenha o serviço ativo. O indicador pequeno fica no canto inferior direito: amarelo durante a preparação, azul na escuta e cinza quando pausado. Clique com o botão direito para abrir o menu.

Exemplo: diga **“Cronos”**, aguarde a confirmação e diga **“Faça um resumo da matéria da Wikipedia que está na minha tela”**. O resumo deve vir por voz e em um card separado, sem abrir o holograma. Para abrir o holograma, peça **“Abrir Cronos”**.

## Controles sem abrir a interface

No indicador, o botão direito oferece **Abrir Cronos**, **Enviar fala agora**, **Interromper resposta**, **Tentar novamente**, **Pausar/retomar escuta**, **Ligar/desligar visão**, **Restaurar último card** e **Encerrar assistente**. Enviar fala agora encerra a gravação atual sem esperar silêncio. O detector automático continua disponível. Gravações são limitadas a três minutos por solicitação; não há promessa de transcrição ilimitada.

Para encerrar todos os componentes manualmente, também existe **ENCERRAR-CRONOS.bat**. Fechar somente o card não encerra o serviço. Desativar o início com Windows impede o próximo início automático; não substitui o comando de encerramento da sessão atual.

## Permissões e limites reais

É necessário permitir o microfone nas configurações de privacidade do Windows para aplicativos da área de trabalho. A câmera só é acessada quando uma função de câmera é ativada. Na interface, a primeira autorização ainda pode aparecer; o perfil persistente permite conservar a escolha enquanto o Windows/WebView a mantiverem válida. Revogação pelo usuário, políticas do sistema e telas protegidas continuam sendo respeitadas. Não há captura por cima dessas restrições.

O ouvinte e a captura precisam de algum processamento e memória locais. A IA e a síntese configuradas continuam usando suas integrações; não foi instalado um modelo de linguagem local pesado. Não se promete consumo zero, prazo fixo para qualquer serviço externo ou acesso a conteúdo privado que não foi compartilhado.

## Referência e verificação

O ZIP enviado excedeu o limite de transferência de 32 MiB e não pôde ser aberto neste ambiente. A referência consultada foi o código do commit **b736566089df7676678a76f1789fe064937059e2**, correspondente ao nome do arquivo, disponível no histórico do projeto. Isso não confirma conteúdo privado ou modificações adicionais que possam existir dentro do anexo.

As verificações automatizadas cobrem a entrega ASR → IA → WAV, voz de reserva com a resposta real, cancelamento durante reconhecimento e síntese, preservação da gravação, ausência de abertura para o nome isolado, separação dos controles, troca da entrada de áudio entre ouvinte e interface e proteção do acesso local à tela. O card foi exercitado com widgets Tk reais sob Xvfb. O ciclo do servidor foi exercitado em um subprocesso real com HTTP, fechamento/reabertura de interfaces controladas, perfil compartilhado e conservação da porta.

Esses testes não certificam o microfone, o alto-falante, o WebView2 ou a acessibilidade do navegador físico no notebook Windows. As integrações externas foram controladas nos testes. Os resultados estão em **VERIFICACAO-2026-10-31-R12.json**.

Resultado final local: **713 testes passaram em 98,11 segundos, sem falhas**, com nove avisos de depreciação das bibliotecas de testes. Passaram **21 cenários de conversa em Chromium**, **12 cenários da apresentação de imagens**, **seis verificações do ciclo do servidor residente** e **cinco verificações dos widgets Tk reais**. TypeScript e compilação passaram. Nenhum desses números representa validação física de microfone, alto-falante, permissões ou navegador Windows.
