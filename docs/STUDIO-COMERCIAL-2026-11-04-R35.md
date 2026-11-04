# CRONOS Studio comercial — revisão R35

Esta versão amplia o Studio existente. O código do site, a interface principal,
o histórico e os dados pessoais continuam nas pastas já usadas pelo Cronos.

## Caminho de uso

1. Abra **Estúdio de Sites → Oportunidades no Brasil** para pesquisar negócios
   em fonte pública (OpenStreetMap ou Google Places, se configurado). Confira a
   fonte, cruze dados e clique em **Guardar ficha no CRM**. Também pode cadastrar
   um negócio informado diretamente por você em **Gestão comercial → Negócios**.
2. Em **Gestão comercial**, complete o briefing com a origem de cada campo,
   analise o HTML do site público quando disponível e registre as etapas reais.
3. Crie o site no Studio, anexe fotografias autorizadas, edite por conversa,
   confira a prévia e exporte os arquivos do projeto.
4. Calcule uma faixa de preço a partir de horas, valor da sua hora, custos e
   margem informados por você. Prepare e revise uma proposta em HTML. O navegador
   pode imprimir esse HTML como PDF.
5. Prepare uma mensagem local, envie-a você mesmo se decidir fazê-lo, registre
   a resposta do cliente e só marque contratação após registrar o acordo real.
6. Registre cobranças e recebimentos reais manualmente. Use os lembretes dos
   próximos sete dias, a lista de entrega e o portfólio local. Nenhum desses
   lançamentos aciona banco, hospedagem ou mensageria.

O assistente de voz pode consultar o CRM e preparar rascunhos de proposta e
contato. Alterações de etapa solicitadas à IA pedem confirmação na conversa.
O teste automatizado desse caminho usa áudio/provedores simulados e não comprova
o funcionamento do microfone ou da conta de IA do notebook do usuário.

## Dados e limites

- As fichas e o histórico comercial persistem em
  `vault/.cronos/studio/commercial.sqlite3` e acompanham o backup dos dados.
- **Baixar dados comerciais** exporta todas as tabelas comerciais em JSON;
  projetos e recursos do site usam a exportação própria de cada projeto.
- Pesquisa geográfica automática continua priorizando o Brasil. Fichas manuais
  aceitam outros países e preços podem usar BRL, USD ou EUR, sem câmbio inventado.
- A auditoria lê HTML público, sem testar desempenho real no celular, segurança,
  existência de demanda ou interesse do cliente. Fotos exigem confirmação de
  direitos de uso.
- Mensagens, publicação, pagamentos, conversão monetária, traduções automáticas,
  geração de PDF no servidor e busca internacional automática não são executados
  por esta versão. O Studio nunca afirma que essas ações ocorreram.
- O documento de expansão e a especificação principal têm recursos adicionais
  para fases futuras. Esta revisão entrega o ciclo comercial local, preservando
  o projeto funcional entre fases.

## Instalação em um arquivo

Use `ABRIR-CRONOS-COM-MEUS-DADOS.bat` baixado do GitHub. Escolha a pasta da
instalação existente com `cronos` e `.env` quando solicitado. O iniciador faz
backup antes de aplicar uma revisão mais nova e não reaplica a mesma revisão
quando aberto novamente. Uma versão antiga não substitui uma versão nova.
Não apague a pasta `Documentos\Cronos-Dados`: ela guarda as APIs, memórias e
dados do Studio usados pelo iniciador. O pacote completo ZIP é uma alternativa
para inspecionar ou montar uma instalação nova, sem dados privados embutidos.
