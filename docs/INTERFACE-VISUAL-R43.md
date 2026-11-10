# Interface visual R43

A tela inicial do CRONOS continua sendo React/Vite em `frontend/src/App.tsx`, servida pelo FastAPI em `/ui/`. O fundo do planeta usa apenas o asset decorativo enviado pelo usuário. Menu, indicadores, dock, painéis e controles são elementos DOM reais. O holograma é desenhado a cada quadro pelo renderer de canvas existente; a animação recebe os estados de captura do microfone e reprodução de voz do hook existente.

Os cinco itens do menu abrem um painel curto sobre a tela inicial. Eles mostram métricas obtidas de `/system/metrics`, total de notas da memória local, catálogo real de `/providers`, entrada para os analisadores existentes e preferências persistidas em `/panels/preferences`. Cada seção também permite abrir o módulo completo anterior. Todos os módulos, Studio, Área de Estudos, Obsidian, ferramentas e provedores anteriores foram preservados.

`frontend/src/capabilities.ts` registra as entradas da interface e roteia comandos exatos de voz ou texto, como “Cronos, abrir memória”. O registro local não concede acesso a ferramentas do sistema: o registro de ferramentas do servidor em `cronos/tools.py` continua responsável por permissões e confirmação. Perguntas abertas seguem para a conversa normal.

Em telas estreitas, os dois painéis laterais começam recolhidos e podem ser abertos separadamente. Esta é uma adaptação responsiva da interface, testada em Chromium a 390 × 844. O assistente completo ainda depende do backend autenticado no computador; não há URL pública ou pareamento remoto nesta revisão. O instalador completo preserva e importa dados antigos localmente, sem incluí-los no GitHub.

Verificações realizadas: lint TypeScript, build Vite, testes de roteamento, testes de telemetria e de instalação, e navegação visual em Chromium a 1280 × 720 e 390 × 844. A aparência no Windows precisa ser conferida na instalação final.
