import asyncio
import json
from dataclasses import replace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from cronos.app import create_app
from cronos.config import Settings
from cronos.engine import Engine, TurnError
from cronos.memory import Memory
from cronos.providers import ProviderError
from cronos.tools import Arguments, Tool, ToolError, create_registry


@pytest.fixture
def environment(tmp_path):
    personality = tmp_path / "personality.md"
    personality.write_text("Discorde quando houver razões e evidências.", encoding="utf-8")
    root = tmp_path / "files"
    root.mkdir()
    settings = replace(Settings.from_env(), vault=tmp_path / "vault", files_root=root, personality=personality,
                       token="test-token", providers_file=tmp_path / "providers.json")
    memory = Memory(settings.vault)
    return settings, memory, create_registry(settings, memory)


def test_model_cannot_self_confirm_and_human_confirmation_is_single_use(environment):
    settings, memory, registry = environment
    session = uuid4()
    async def scenario():
        bypass = await registry.execute("files_create", {"path": "note.md", "content": "ok", "confirmed": True}, session)
        assert bypass["status"] == "failed"
        pending = await registry.execute("files_create", {"path": "note.md", "content": "ok"}, session)
        assert pending["status"] == "pending_confirmation"
        assert not (settings.files_root / "note.md").exists()
        with pytest.raises(ToolError):
            await registry.resolve(pending["approval_id"], True, uuid4())
        result = await registry.resolve(pending["approval_id"], True, session)
        assert result["status"] == "completed"
        assert (settings.files_root / "note.md").read_text() == "ok"
        with pytest.raises(ToolError):
            await registry.resolve(pending["approval_id"], True, session)
    asyncio.run(scenario())


def test_file_scope_and_credential_files_are_blocked(environment):
    settings, memory, registry = environment
    (settings.files_root / ".env").write_text("SECRET=private")
    async def scenario():
        for path in ("../outside.txt", ".env", "config/api_keys.json"):
            result = await registry.execute("files_read", {"path": path}, uuid4())
            assert result["status"] == "failed"
            assert "private" not in json.dumps(result)
    asyncio.run(scenario())


def test_engine_searches_memory_and_synthesizes_without_canned_reply(environment):
    settings, memory, registry = environment
    note = memory.vault / "pessoal.md"
    note.write_text("# Família\nMinha mãe se chama Helena.", encoding="utf-8")
    class Provider:
        count = 0
        async def reply(self, system, messages):
            self.count += 1
            assert "Helena" in system
            if self.count == 1:
                return {"reply": "Vou consultar as notas.", "topics": [], "tool_calls": [{"name": "obsidian_search", "arguments": {"query": "Helena"}}]}
            assert "Helena" in messages[-1]["content"]
            return {"reply": "Pelas suas notas, ela se chama Helena.", "topics": [], "tool_calls": []}
    session = uuid4()
    result = asyncio.run(Engine(settings, memory, registry, Provider()).chat(session, "Qual é o nome da minha mãe?"))
    assert result["reply"] == "Pelas suas notas, ela se chama Helena."
    assert result["tool_results"][0]["status"] == "completed"
    assert len(memory.history(session)) == 2
    assert len(memory.tool_history(session)) == 1


def test_actions_remain_auditable_if_model_fails_after_tool(environment):
    settings, memory, registry = environment
    class Provider:
        count = 0
        async def reply(self, *args):
            self.count += 1
            if self.count == 1:
                return {"reply": "Preparando.", "topics": [], "tool_calls": [{"name": "files_create", "arguments": {"path": "new.md", "content": "conteúdo"}}]}
            raise ProviderError("Cota atingida")
    session = uuid4()
    with pytest.raises(TurnError) as error:
        asyncio.run(Engine(settings, memory, registry, Provider()).chat(session, "Crie uma nota"))
    assert error.value.results[0]["status"] == "pending_confirmation"
    assert memory.tool_history(session)[0]["status"] == "pending_confirmation"
    assert not (settings.files_root / "new.md").exists()


def test_confirmation_api_and_memory_endpoints(environment):
    settings, memory, registry = environment
    class Provider:
        count = 0
        async def reply(self, *args):
            self.count += 1
            if self.count == 1:
                return {"reply": "Aguardando", "topics": [], "tool_calls": [{"name": "files_create", "arguments": {"path": "new.md", "content": "novo"}}]}
            return {"reply": "A ação aguarda sua confirmação.", "topics": [], "tool_calls": []}
    headers = {"Authorization": "Bearer test-token"}
    with TestClient(create_app(settings, Provider())) as client:
        result = client.post("/chat", headers=headers, json={"message": "Crie um arquivo"}).json()
        approval = result["tool_results"][0]["approval_id"]
        path = "/tools/approvals/" + approval
        body = {"session_id": result["session_id"], "accepted": True}
        assert client.post(path, json=body).status_code == 401
        assert client.post(path, headers=headers, json=body).json()["status"] == "completed"
        assert client.post(path, headers=headers, json=body).status_code == 409
        assert client.get("/tools", headers=headers).json()["tools"]
        assert client.get("/memory/status", headers=headers).json()["messages"] == 2
        assert client.post("/memory/sync", headers=headers).status_code == 200
        assert client.get("/memory/note", params={"path": "../bad.md"}, headers=headers).status_code == 404


def test_prompt_budgets_do_not_delete_history(environment):
    settings, memory, registry = environment
    session = uuid4()
    memory.record(session, "Primeira " * 1000, "Resposta " * 1000, [])
    settings = replace(settings, context_chars=2000, context_messages=2)
    messages = Engine(settings, memory, registry).context(session, "Olá")
    assert messages == [{"role": "user", "content": "Olá"}]
    assert len(memory.history(session)[0]["content"]) > 2000


def test_repeated_model_call_does_not_repeat_action(environment):
    settings, memory, registry = environment
    executions = []
    registry.register(Tool("counter", "Teste de execução única", Arguments, lambda args: executions.append(1)))
    class Provider:
        count = 0
        async def reply(self, *args):
            self.count += 1
            return {"reply": "Concluído" if self.count == 3 else "Planejando", "topics": [],
                    "tool_calls": [] if self.count == 3 else [{"name": "counter", "arguments": {}}]}
    result = asyncio.run(Engine(replace(settings, tool_rounds=2), memory, registry, Provider()).chat(uuid4(), "Teste"))
    assert executions == [1]
    assert result["tool_results"][1]["status"] == "failed"


def test_windows_executable_requires_confirmation_and_no_shell(environment, monkeypatch):
    from types import SimpleNamespace
    import cronos.tools as module
    settings, memory, unused = environment
    calls = []
    monkeypatch.setattr(module, "os", SimpleNamespace(name="nt", environ={}, startfile=lambda value: None))
    monkeypatch.setattr(module, "subprocess", SimpleNamespace(Popen=lambda argv, **kwargs: calls.append((argv, kwargs)) or SimpleNamespace(pid=123)))
    assert "desktop_run_executable" not in create_registry(settings, memory).tools
    registry = create_registry(replace(settings, allow_executables=True), memory)
    (settings.files_root / "demo.exe").write_bytes(b"test-only-not-an-executable")
    session = uuid4()
    async def scenario():
        pending = await registry.execute("desktop_run_executable", {"path": "demo.exe", "arguments": ["--help"]}, session)
        assert not calls
        result = await registry.resolve(pending["approval_id"], True, session)
        assert result["status"] == "completed"
        assert calls[0][1]["shell"] is False
        assert calls[0][0] == [str(settings.files_root / "demo.exe"), "--help"]
    asyncio.run(scenario())


def test_opt_in_plugins_isolate_invalid_modules(environment, monkeypatch):
    from types import SimpleNamespace
    import importlib.metadata
    settings, memory, unused = environment
    good = SimpleNamespace(name="clock", load=lambda: lambda settings, memory: [Tool("clock", "Relógio", Arguments, lambda args: "ok")])
    bad = SimpleNamespace(name="collision", load=lambda: lambda settings, memory: [Tool("files_list", "Colisão", Arguments, lambda args: "bad")])
    monkeypatch.setattr(importlib.metadata, "entry_points", lambda **kwargs: [good, bad])
    disabled = create_registry(settings, memory)
    assert "clock" not in disabled.tools
    enabled = create_registry(replace(settings, enable_plugins=True), memory)
    assert "clock" in enabled.tools
    assert enabled.load_errors[0]["plugin"] == "collision"
    assert enabled.tools["files_list"].description != "Colisão"


def test_large_tool_result_is_bounded_in_context_but_kept_in_audit(environment):
    settings, memory, registry = environment
    source = memory.vault / "estudo.md"
    original = "# Texto\n" + "registro completo " * 3000
    source.write_text(original, encoding="utf-8")
    class Provider:
        count = 0
        async def reply(self, system, messages):
            self.count += 1
            if self.count == 1:
                return {"reply": "Lendo", "topics": [], "tool_calls": [{"name": "obsidian_read", "arguments": {"path": "estudo.md", "max_chars": 100000}}]}
            assert '"truncated_for_context": true' in messages[-1]["content"]
            assert len(messages[-1]["content"]) < 3000
            return {"reply": "Preciso consultar os trechos relevantes.", "topics": [], "tool_calls": []}
    session = uuid4()
    result = asyncio.run(Engine(replace(settings, context_chars=4000), memory, registry, Provider()).chat(session, "Leia estudo.md"))
    assert result["tool_results"][0]["result"]["content"] == original
    assert memory.tool_history(session)[0]["result"]["content"] == original
    assert source.read_text() == original
