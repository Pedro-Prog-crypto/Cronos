# Um pacote para abrir e atualizar

`releases/CRONOS-Completo-Um-Arquivo.zip` reúne todo o código de execução, interface compilada, Olho de Deus, recursos visuais, modelos de configuração e um único botão de entrada: **ABRIR-CRONOS.bat**. O usuário extrai o ZIP e abre esse arquivo. Não é preciso baixar/aplicar o pacote separado anterior.

O botão inicia uma pequena janela local. Ela procura instalações configuradas nos diretórios próximos e em Downloads, Área de Trabalho e Documentos, incluindo localizações padrão do OneDrive. A busca é limitada a 500 diretórios e dois níveis, sem ler os valores das chaves. Diretórios privados de dependências/cofre não são percorridos. Se houver exatamente uma instalação, ela é usada; se houver várias, a janela apresenta as opções. Se não houver uma nesses locais, abre o seletor de pasta. Não escolhe uma instalação pelo nome mais recente nem mistura memórias de pastas diferentes.

O código da interface é atualizado na pasta existente com o aplicador verificado. Depois abre o supervisor usando o ambiente Python dessa mesma pasta, inclusive o supervisor em cache, quando existente. `.env`, `config`, cofre, preferências e memórias continuam no mesmo lugar; não se copia nem reescreve seu conteúdo. A pasta antiga deve ser mantida, pois continua sendo a instalação em uso. O usuário não precisa recadastrar as APIs.

A entrada funciona por Windows Script Host e pelo Python já instalado. Ela usa `pyw`/`py` quando disponíveis e, na ausência deles, solicita a pasta anterior para usar seu Python. Não baixa dependências, não instala um runtime novo nem modifica políticas do Windows. O pacote é completo em código, mas requer a instalação anterior funcional com ambiente virtual e credenciais. Não contém as chaves do usuário e não pode recuperar credenciais de uma pasta apagada.

A busca, seleção sem adivinhação, preservação, recuperação da aplicação e comando de abertura foram testados em diretórios isolados. A janela Tk e o iniciador Windows não foram executados nesta máquina Linux. Os testes funcionais anteriores da aplicação continuam descritos em ANALISE_E_ANIMACOES.md.

O construtor tools/build_complete_bundle.py usa uma lista explícita de código rastreado e arquivos de inicialização. Exclui `.env`, `.venv`, cofre, banco e dados locais, e verifica CRC e os hashes dos arquivos de atualização. O ZIP completo não contém outro ZIP de atualização aninhado.

O pacote também inclui o [Estúdio de Sites](STUDIO_DE_SITES.md), sem dependência adicional de Python: projetos, código gerado, prévia isolada, versões, formulários locais, 3D fornecido, testes e exportação. Os dados ficam no cofre existente, em `.cronos/studio`, fora do manifesto de atualização.
