"""In-memory store for decision_engine's tables (context_snapshot ... outcome).

Same documents as db/schema.sql stores in JSONB; swap in a Postgres store with the
same methods when the DB is switched on.
"""
import copy
import threading
from collections import defaultdict


class Store:
    def __init__(self):
        self._lock = threading.RLock()
        self.reset()

    def reset(self):
        with self._lock:
            self.context_snapshots = defaultdict(list)  # business_id -> [snapshot]
            self.signals = {}            # business_id -> signals document
            self.recommendations = {}    # recommendation_id -> recommendation
            self.plans = {}              # plan_id -> plan (tasks inline)
            self.outcomes = {}           # plan_id -> outcomes document
            self.counters = defaultdict(int)

    def next_id(self, kind: str) -> int:
        with self._lock:
            self.counters[kind] += 1
            return self.counters[kind]

    # snapshots -------------------------------------------------------------
    def add_context_snapshot(self, business_id: str, snapshot: dict):
        with self._lock:
            self.context_snapshots[business_id].append(copy.deepcopy(snapshot))

    # signals ---------------------------------------------------------------
    def put_signals(self, business_id: str, doc: dict):
        with self._lock:
            self.signals[business_id] = copy.deepcopy(doc)

    # recommendations ---------------------------------------------------------
    def put_recommendation(self, rec: dict):
        with self._lock:
            self.recommendations[rec["recommendation_id"]] = copy.deepcopy(rec)

    def get_recommendation(self, rec_id: str):
        with self._lock:
            rec = self.recommendations.get(rec_id)
            return copy.deepcopy(rec) if rec else None

    def recommendations_for(self, business_id: str) -> list:
        with self._lock:
            return [copy.deepcopy(r) for r in self.recommendations.values()
                    if r["business_id"] == business_id]

    def drop_recommendations(self, business_id: str, keep: set):
        with self._lock:
            for rid in [r for r, rec in self.recommendations.items()
                        if rec["business_id"] == business_id and r not in keep]:
                del self.recommendations[rid]

    def recommendation_owner(self, rec_id: str):
        with self._lock:
            rec = self.recommendations.get(rec_id)
            return rec["business_id"] if rec else None

    # plans and tasks ---------------------------------------------------------
    def put_plan(self, plan: dict):
        with self._lock:
            self.plans[plan["plan_id"]] = copy.deepcopy(plan)

    def get_plan(self, plan_id: str):
        with self._lock:
            plan = self.plans.get(plan_id)
            return copy.deepcopy(plan) if plan else None

    def plans_for(self, business_id: str) -> list:
        with self._lock:
            return [copy.deepcopy(p) for p in self.plans.values() if p["business_id"] == business_id]

    def find_task(self, task_id: str):
        """Return (plan_id, task) or (None, None)."""
        with self._lock:
            for plan in self.plans.values():
                for task in plan["tasks"]:
                    if task["task_id"] == task_id:
                        return plan["plan_id"], copy.deepcopy(task)
            return None, None

    def update_task(self, task_id: str, changes: dict):
        with self._lock:
            for plan in self.plans.values():
                for task in plan["tasks"]:
                    if task["task_id"] == task_id:
                        task.update(changes)
                        return copy.deepcopy(task)
            return None

    # outcomes ----------------------------------------------------------------
    def put_outcomes(self, plan_id: str, doc: dict):
        with self._lock:
            self.outcomes[plan_id] = copy.deepcopy(doc)

    def get_outcomes(self, plan_id: str):
        with self._lock:
            doc = self.outcomes.get(plan_id)
            return copy.deepcopy(doc) if doc else None
