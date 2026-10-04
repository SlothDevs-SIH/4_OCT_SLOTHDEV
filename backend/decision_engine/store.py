"""In-memory store for decision_engine's tables (diagnosis, action, follow-up, draft log).

Same documents a Postgres store would keep as JSONB (db/schema.sql); swap in one with the same
methods when the database is switched on. A restart clears this store.
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
            self.diagnoses = {}                         # (business_id, week) -> diagnosis
            self.actions = {}                           # action_id -> action
            self.followups = {}                         # (business_id, week) -> follow-up
            self.partner_results = defaultdict(dict)    # business_id -> {partner_id: [stranger leads, ...]}
            self.warm_contacts = defaultdict(set)       # business_id -> {(lead_id, reason)}

    def put_diagnosis(self, doc):
        with self._lock:
            self.diagnoses[(doc["business_id"], doc["week"])] = copy.deepcopy(doc)

    def get_diagnosis(self, business_id, week):
        with self._lock:
            d = self.diagnoses.get((business_id, week))
            return copy.deepcopy(d) if d else None

    def put_action(self, action):
        with self._lock:
            self.actions[action["action_id"]] = copy.deepcopy(action)

    def get_action(self, action_id):
        with self._lock:
            a = self.actions.get(action_id)
            return copy.deepcopy(a) if a else None

    def actions_for(self, business_id, week=None):
        with self._lock:
            return [copy.deepcopy(a) for a in self.actions.values()
                    if a["business_id"] == business_id and (week is None or a["week"] == week)]

    def drop_actions(self, business_id, week, keep):
        with self._lock:
            for aid in [i for i, a in self.actions.items()
                        if a["business_id"] == business_id and a["week"] == week and i not in keep]:
                del self.actions[aid]

    def put_followup(self, doc):
        with self._lock:
            self.followups[(doc["business_id"], doc["week"])] = copy.deepcopy(doc)

    def followups_for(self, business_id):
        with self._lock:
            return [copy.deepcopy(d) for (b, _), d in sorted(self.followups.items()) if b == business_id]

    def add_partner_result(self, business_id, partner_id, stranger_leads):
        with self._lock:
            self.partner_results[business_id].setdefault(partner_id, []).append(stranger_leads)

    def partner_results_for(self, business_id):
        with self._lock:
            return copy.deepcopy(self.partner_results[business_id])

    def mark_warm_contacted(self, business_id, lead_id, reason):
        with self._lock:
            self.warm_contacts[business_id].add((lead_id, reason))

    def warm_contacted(self, business_id):
        with self._lock:
            return set(self.warm_contacts[business_id])
