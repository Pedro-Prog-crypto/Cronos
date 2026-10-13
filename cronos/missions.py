"""Planos persistentes; concluir uma etapa é uma declaração humana, não execução."""
import json
from datetime import datetime, timezone, date
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class Step(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=500)
    done: bool = False
    status: Literal["pending", "in_progress", "completed"] = "pending"
    due_date: date | None = None


class Plan(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=120)
    steps: list[Step] = Field(min_length=1, max_length=30)
    due_date: date | None = None
    priority: Literal["low", "medium", "high"] = "medium"
    review: bool = True


class Missions:
    def __init__(self, memory):
        self.memory = memory
        with memory.connect() as db:
            db.execute('''CREATE TABLE IF NOT EXISTS missions (
                id TEXT PRIMARY KEY, objective TEXT NOT NULL, plan TEXT NOT NULL,
                created TEXT NOT NULL, updated TEXT NOT NULL)''')

    def create(self, objective, plan):
        # Modelo pode propor passos, mas não concluir ações por conta própria.
        plan = plan.model_copy(update={"steps": [step.model_copy(update={"done": False, "status":"pending"}) for step in plan.steps]})
        identifier, now = str(uuid4()), datetime.now(timezone.utc).isoformat()
        with self.memory.connect() as db:
            db.execute("INSERT INTO missions VALUES(?,?,?,?,?)", (identifier, objective, plan.model_dump_json(), now, now))
        return self.get(identifier)

    def get(self, identifier):
        with self.memory.connect() as db:
            row = db.execute("SELECT * FROM missions WHERE id=?", (str(identifier),)).fetchone()
        if row is None:
            raise ValueError("Plano não encontrado.")
        plan = Plan.model_validate_json(row['plan'])
        for step in plan.steps:
            if step.done:step.status = 'completed'
        return {"id": row["id"], "objective": row["objective"], "plan": plan.model_dump(mode='json'),
                "created": row["created"], "updated": row["updated"]}

    def list(self):
        with self.memory.connect() as db:
            rows = db.execute("SELECT id FROM missions ORDER BY updated DESC LIMIT 100").fetchall()
        return [self.get(row["id"]) for row in rows]

    def mark(self, identifier, index, done):
        with self.memory.connect() as db:
            row = db.execute("SELECT plan FROM missions WHERE id=?", (str(identifier),)).fetchone()
            if row is None:
                raise ValueError("Plano não encontrado.")
            plan = Plan.model_validate_json(row["plan"])
            if index < 0 or index >= len(plan.steps):
                raise ValueError("Etapa não encontrada.")
            plan.steps[index].done = done
            plan.steps[index].status = "completed" if done else "pending"
            db.execute("UPDATE missions SET plan=?,updated=? WHERE id=?", (
                plan.model_dump_json(), datetime.now(timezone.utc).isoformat(), str(identifier)))
        return self.get(identifier)

    def update(self, identifier, plan):
        with self.memory.connect() as db:
            if not db.execute('SELECT 1 FROM missions WHERE id=?', (str(identifier),)).fetchone():
                raise ValueError('Plano não encontrado.')
            for step in plan.steps:
                step.done = step.status == 'completed'
            db.execute('UPDATE missions SET plan=?,updated=? WHERE id=?', (plan.model_dump_json(), datetime.now(timezone.utc).isoformat(), str(identifier)))
        return self.get(identifier)
