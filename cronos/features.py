"""Doze módulos com verificações explícitas e evidência, sem fingir testes reais."""
import asyncio
import platform
import time
from datetime import datetime, timezone
from uuid import uuid4

from cronos.integrations import provider_catalog, available_models
from cronos.providers import ProviderError, make_provider

MODULES = [
    ("processing", "Processamento", "Recursos e teste leve do processamento local."),
    ("vision", "Visão computacional", "Imagem, câmera ou captura escolhida por você; análise via Gemini."),
    ("voice", "Síntese de voz", "Síntese Fish Audio e transcrição pelo microfone."),
    ("language", "Entendimento de linguagem", "Conversa com personalidade e contexto."),
    ("planning", "Planejamento", "Planos salvos com etapas e progresso declarado por você."),
    ("tools", "Ferramentas", "Ferramentas disponíveis e confirmações de ações."),
    ("integrations", "Integrações", "Provedores oficiais configurados e seleção em tempo de execução."),
    ("database", "Banco de dados", "SQLite, memória Obsidian, busca e sincronização."),
    ("internet", "Internet", "Busca web com fontes e resultado real da operação."),
    ("devices", "Dispositivos", "Dispositivos locais, microfone e iniciador por voz."),
    ("security", "Segurança", "Auditoria Windows e correções restritas com confirmação."),
    ("monitoring", "Monitoramento", "Radar, alertas ativos e estado do diagnóstico."),
]


class Features:
    def __init__(self, app):
        self.app = app
        self.checks = {}

    @property
    def settings(self):
        return self.app.state.engine.settings

    def catalog(self):
        settings = self.settings
        windows = self.app.state.windows.platform == "win32"
        configured = bool(settings.gemini_key) if settings.provider == "gemini" else True
        try:
            configured = next((item["configured"] for item in provider_catalog(settings) if item["id"] == settings.provider), False)
        except ProviderError:
            configured = False
        states = {identifier: "available" for identifier, _, _ in MODULES}
        states["language"] = "available" if configured else "configuration_required"
        states["vision"] = "available" if settings.gemini_key and settings.privacy_mode == "online" else "configuration_required"
        states["voice"] = "available" if settings.fish_key and settings.privacy_mode == "online" else "configuration_required"
        states["internet"] = "disabled" if settings.privacy_mode != "online" else "available"
        for identifier in ("devices", "security"):
            states[identifier] = "available" if windows else "windows_required"
        return [{"id": identifier, "name": name, "description": description, "availability": states[identifier],
                 "last_check": self.checks.get(identifier)} for identifier, name, description in MODULES]

    async def check(self, identifier):
        if identifier not in {item[0] for item in MODULES}:
            raise ValueError("Módulo não encontrado.")
        status, evidence, scope = "passed", {}, "Verificação da operação indicada, não certificação geral."
        try:
            state, settings = self.app.state, self.settings
            if identifier == "processing":
                start = time.perf_counter()
                result = sum(range(10000))
                if result != 49995000:
                    raise ValueError("O cálculo de teste falhou.")
                evidence = {"calculation_ok": True, "elapsed_ms": round((time.perf_counter() - start) * 1000, 3),
                            "python": platform.python_version(), "resources": state.monitor.snapshot()["resources"]}
                scope = "Cálculo e recursos locais; não mede inteligência do modelo."
            elif identifier in {"voice", "vision"}:
                configured = (settings.fish_key if identifier == "voice" else settings.gemini_key) and settings.privacy_mode == "online"
                status = "configuration_only" if configured else "unavailable"
                evidence = {"configured": bool(configured)}
                scope = "Nenhuma chamada paga foi feita. Use Gerar voz ou Analisar imagem para testar o serviço real."
            elif identifier == "language":
                from cronos.usage import request_scope
                provider = state.engine.provider or make_provider(settings)
                with request_scope('module_check'):
                    response = await provider.reply("Teste de comunicação. Responda brevemente, sem ferramentas e sem temas.",
                                                    [{"role": "user", "content": "Diga olá em português."}])
                evidence = {"reply": response["reply"], "provider": settings.provider}
                scope = "Uma geração real; pode consumir cota. Não avalia todas as capacidades de linguagem."
            elif identifier in {"planning", "database"}:
                def database_check():
                    with state.memory.connect() as db:
                        if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                            raise ValueError("A integridade do banco exige revisão.")
                        db.execute("SAVEPOINT diagnostic")
                        marker = "diagnostic-" + str(uuid4())
                        db.execute("INSERT INTO imports(path) VALUES(?)", (marker,))
                        if not db.execute("SELECT 1 FROM imports WHERE path=?", (marker,)).fetchone():
                            raise ValueError("Leitura de teste falhou.")
                        db.execute("ROLLBACK TO diagnostic")
                        db.execute("RELEASE diagnostic")
                    return {"integrity": "ok", "transaction_read_write": True,
                            "missions": len(state.missions.list())} if identifier == "planning" else state.memory.stats()
                evidence = await asyncio.to_thread(database_check)
                scope = "Integridade e escrita/leitura com rollback; não cria temas nem conclui missões."
            elif identifier == "tools":
                evidence = {"tools": state.registry.catalog(), "plugin_errors": state.registry.load_errors}
                scope = "Inventário das ferramentas realmente registradas. Execute uma ferramenta para testar sua ação."
            elif identifier == "integrations":
                evidence = {"provider": settings.provider, "models": await available_models(settings, settings.provider)}
                scope = "Consulta real ao catálogo do provedor; não comprova geração de texto ou saldo futuro."
            elif identifier == "internet":
                result = await state.registry.execute("web_search", {"query": "Python official documentation", "limit": 3}, uuid4())
                if result["status"] != "completed":
                    raise ValueError(result.get("error", "Busca indisponível."))
                evidence = {"results": result["result"]}
                scope = "Busca real com URLs, sem executar conteúdo das páginas."
            elif identifier == "devices":
                evidence = await state.windows.devices()
                scope = "Inventário do Windows local; não testa fisicamente todos os periféricos."
            elif identifier == "security":
                evidence = await state.windows.audit()
                scope = evidence["scope"]
            elif identifier == "monitoring":
                evidence = state.monitor.snapshot()
                scope = evidence["scope"]
        except (ProviderError, ValueError) as exc:
            status, evidence = "failed", {"message": str(exc)}
        except Exception:
            status, evidence = "failed", {"message": "A verificação falhou; confira dependências e acesso. Nenhum sucesso foi confirmado."}
        result = {"id": identifier, "status": status, "checked_at": datetime.now(timezone.utc).isoformat(),
                  "scope": scope, "evidence": evidence}
        self.checks[identifier] = result
        return result

    def record(self, identifier, status, scope):
        self.checks[identifier] = {"id": identifier, "status": status, "checked_at": datetime.now(timezone.utc).isoformat(),
                                  "scope": scope, "evidence": {}}
