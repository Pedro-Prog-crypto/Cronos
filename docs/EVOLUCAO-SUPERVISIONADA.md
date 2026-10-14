# Evolução supervisionada do Cronos

A central fica no painel existente **Integrações**; não adiciona controles à tela principal, modelos em RAM nem serviços em segundo plano.

## Uso

- “Cronos, consulte seus dados internos e diga o que pode melhorar.” A ferramenta `cronos_internal_data` lê estatísticas reais da memória, catálogo de ferramentas, configuração sem credenciais e últimas medições. Não consulta conversas de outras sessões. Notas específicas usam `obsidian_search` e `obsidian_read`.
- “Cronos, faça seu check-up.” `cronos_checkup` mostra configuração e propostas baseadas nos tempos do último turno. Um tempo alto é evidência da etapa, não diagnóstico da causa.
- “Cronos, pesquise novas IAs em fontes oficiais e compare compatibilidade e custo.” Usa a busca existente. Não existe uma listagem universal garantida. Não basta um anúncio para provar que uma API existe ou é gratuita.
- “Cronos, consulte os modelos da integração X.” Consulta autenticada `/models`, sem geração, sem concluir que há cota gratuita.
- Integrações OpenAI compatíveis, Anthropic, Gemini REST e Ollama usam o contrato já existente. Outros protocolos precisam de implementação; nomes de modelos não criam novos conectores.
- O assistente pode propor `integrations_register`. A confirmação mostra a URL, modelo e nome da variável de credencial; nunca recebe o valor da chave. Antes de registrar, confere o modelo na API. Se a chave ainda não está configurada, registre primeiro no formulário existente do painel, depois cadastre a chave no campo protegido da central e consulte os modelos. Essa primeira inscrição manual não equivale a um teste da API.
- Chaves são salvas no `.env` local existente, fora da conversa/manifesto. Não são criptografadas. O cadastro novo não altera as variáveis protegidas Gemini/Fish. Proteja sua conta e pasta do Windows. Não envie chaves pela conversa.
- Conselho: `consult_models` continua consultando os IDs escolhidos, incluindo uma IA específica; não substitui silenciosamente o provedor solicitado.

## Alternativas autorizadas

`integrations_routing` salva uma lista ordenada de IDs já configurados, sem quantidade fixa. Por padrão fica desligado. A confirmação autoriza enviar o contexto aos provedores listados, que podem cobrar. Não há inferência de preço ou liberação automática de faturamento.

As alternativas atendem somente **conversas de texto** diante de falhas transitórias/cota informadas pelo provedor. Cada alternativa é tentada uma vez. Não se troca depois de já transmitir parte da resposta, nem diante de erro local de formato/configuração. Consultas específicas/conselho, imagens e áudio direto Gemini Live ficam fora da troca. Uma cadeia extensa pode aumentar a demora; escolha poucas alternativas relevantes apesar de não haver limite fixo de integrações.

O resultado informa `provider_used` e `fallback_used`. Isso não transforma uma assinatura de ChatGPT em crédito de API. O endpoint não gera texto para testar créditos.

`integrations_rollback` restaura a política anterior. As configurações persistem em `config/evolution.json`, ignorado pelo Git. A voz e o provedor principal existente são preservados.

## Limites desta entrega

Esta central consulta dados, propõe melhorias e administra conectores compatíveis após confirmação. O [atualizador independente](ATUALIZADOR.md) agora também prepara pacotes do repositório, propostas limitadas de código explicitamente solicitadas e instalação com backup/recuperação. Não há reescrita irrestrita, testes funcionais universais, publicação automática ou autoaprovação por IA. As limitações e o fluxo de revisão estão no documento do atualizador.

Não há garantia de resposta instantânea, ausência de cota, precisão de pesquisa ou compatibilidade de toda API OpenAI. Novas chaves e acessos continuam dependendo das contas do usuário.
