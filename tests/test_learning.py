import json

from fastapi.testclient import TestClient

from cronos.app import create_app
from cronos.learning import GeneratedExercise, LearningStore, exercise_topic, learning_mode
from pydantic import ValidationError
import pytest
from cronos.study_intent import is_study_request
from test_backend import AUTH, settings


class Tutor:
    def __init__(self):
        self.calls = []

    async def reply(self, system, messages):
        self.calls.append((system, messages))
        if "Crie UMA questão original" in system:
            return {"reply": json.dumps({"question": "Explique por que o discriminante permite analisar as raízes de uma função quadrática.",
                                         "expected_answer": "O sinal de delta determina o número de raízes reais.",
                                         "explanation": "Delta é b² - 4ac. Positivo: duas raízes reais; zero: uma; negativo: nenhuma real.",
                                         "skill": "Discriminante"}), "topics": [], "tool_calls": []}
        if "corrigindo uma questão SIMULADA" in system:
            return {"reply": json.dumps({"correct": False,
                                         "feedback": "Você confundiu o sinal de delta com o sinal de a. Calcule b² - 4ac primeiro.",
                                         "error_point": "interpretação do discriminante",
                                         "next_step": "Resolva outro exemplo com delta negativo."}), "topics": [], "tool_calls": []}
        return {"reply": "A segunda lei de Newton relaciona força resultante e aceleração. Por exemplo, um carrinho acelera mais com uma força maior.",
                "topics": [], "tool_calls": []}


def test_modes_are_shared_and_difficulty_is_recognized():
    assert learning_mode("Não entendi a segunda lei de Newton") == "tutor"
    assert is_study_request("Não entendi a segunda lei de Newton")
    assert learning_mode("Explique tudo sobre termodinâmica") == "deep"
    assert learning_mode("O que é termodinâmica?", "simple") == "simple"
    assert learning_mode("Pesquise profundamente o impacto da energia") == "research"
    assert exercise_topic("Cronos, me dê um exercício sobre função quadrática") == "função quadrática"


def test_generated_question_cannot_claim_to_be_official():
    with pytest.raises(ValidationError):
        GeneratedExercise(question="Questão oficial do PAS: explique a função quadrática.",
                          expected_answer="A função tem grau dois.",
                          explanation="A função quadrática tem variável elevada ao quadrado.",
                          skill="Funções")


def test_study_exercise_correction_progress_and_plan_persist(settings):
    tutor = Tutor()
    with TestClient(create_app(settings, tutor)) as client:
        subject = client.post("/studies/subjects", headers=AUTH, json={"name": "Matemática"}).json()
        sid = subject["id"]
        created = client.post(f"/studies/subjects/{sid}/exercise", headers=AUTH,
                              json={"topic": "Função quadrática"})
        assert created.status_code == 200, created.text
        exercise = created.json()
        assert exercise["origin"] == "simulated" and "discriminante" in exercise["question"]
        assert "expected_answer" not in exercise and "explanation" not in exercise
        pending = client.get(f"/studies/subjects/{sid}/exercise/pending", headers=AUTH).json()
        assert pending["id"] == exercise["id"]
        graded = client.post(f"/studies/exercises/{exercise['id']}/answer", headers=AUTH,
                             json={"answer": "Depende apenas do valor de a."})
        assert graded.status_code == 200, graded.text
        assert graded.json()["correct"] is False
        assert "discriminante" in graded.json()["error_point"]
        assert client.get(f"/studies/subjects/{sid}/exercise/pending", headers=AUTH).json() == {}
        progress = client.get("/learning/progress", headers=AUTH).json()
        assert progress["topics"][0]["attempts"] == 1 and progress["topics"][0]["correct"] == 0
        plan = client.post("/learning/plan", headers=AUTH,
                           json={"daily_minutes": 70, "focus_subjects": ["Matemática", "Redação"]}).json()
        assert plan["daily_minutes"] == 70 and plan["weak_topics"] == ["Função quadrática"]
        assert plan["date_status"].startswith("informada pelo usuário")
        assert sum(int(block.split(" min")[0]) for block in plan["suggested_blocks"]) == 70
        assert client.get("/learning/plan", headers=AUTH).json()["focus_subjects"] == ["Matemática", "Redação"]
    reopened = LearningStore(settings.vault)
    assert reopened.profile()["topics"][0]["attempts"] == 1
    assert reopened.plan()["daily_minutes"] == 70


def test_normal_chat_creates_and_corrects_exercise_in_same_learning_store(settings):
    tutor = Tutor()
    with TestClient(create_app(settings, tutor)) as client:
        first = client.post("/chat/stream", headers=AUTH,
                            json={"message": "Cronos, crie um exercício sobre função quadrática."})
        assert first.status_code == 200, first.text
        result = json.loads(first.text.splitlines()[-1])["result"]
        assert "Exercício simulado" in result["reply"]
        second = client.post("/chat/stream", headers=AUTH,
                             json={"session_id": result["session_id"], "message": "Minha resposta é que depende só de a."})
        assert second.status_code == 200, second.text
        grade = json.loads(second.text.splitlines()[-1])["result"]
        assert "Você confundiu" in grade["reply"]
        assert client.get("/learning/progress", headers=AUTH).json()["topics"][0]["correct"] == 0
        assert not any("expected_answer" in call[1][-1]["content"] for call in tutor.calls)


def test_study_lesson_uses_shared_mode_and_keeps_existing_layout(settings):
    tutor = Tutor()
    with TestClient(create_app(settings, tutor)) as client:
        subject = client.post("/studies/subjects", headers=AUTH, json={"name": "Física"}).json()
        response = client.post(f"/studies/subjects/{subject['id']}/lessons", headers=AUTH,
                               json={"question": "Não entendi a segunda lei de Newton.", "mode": "tutor"})
        assert response.status_code == 200, response.text
        assert response.json()["teaching_mode"] == "tutor"
        assert response.json()["layout"]
        assert "Modo selecionado: tutor" in tutor.calls[-1][0]
        history = client.get(f"/studies/subjects/{subject['id']}/sources", headers=AUTH).json()["lessons"]
        assert history[0]["teaching_mode"] == "tutor"


def test_invalid_model_json_never_creates_fake_exercise(settings):
    class Broken:
        async def reply(self, *_args):
            return {"reply": "Questão oficial do PAS: confie em mim", "topics": [], "tool_calls": []}
    with TestClient(create_app(settings, Broken())) as client:
        subject = client.post("/studies/subjects", headers=AUTH, json={"name": "História"}).json()
        response = client.post(f"/studies/subjects/{subject['id']}/exercise", headers=AUTH,
                               json={"topic": "Revolução Industrial"})
        assert response.status_code == 502
        assert client.get("/learning/progress", headers=AUTH).json()["topics"] == []
