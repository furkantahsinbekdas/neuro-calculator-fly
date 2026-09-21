"""
game_loop.py — the autonomous heartbeat of the cybernetic fly.

Two pieces, both pure Phase-1 backend, no web and no connectome dependency:

  * LLMExecutor — ONE worker thread in front of Ollama. Every LLM call in the app (a
    user message, a speech transcript, an autonomous impulse) is submitted as a Task
    into a PriorityQueue and runs off the HTTP request path. This is what makes
    server.py non-blocking: the handler returns instantly and the reply streams back to
    the UI through the EventBus as think_start / token / tool_call / tool_result / viz /
    say events.

  * GameLoop — a background tick loop (~1 Hz) that degrades the fly's vitals and, when
    a threshold is crossed *and* the cooldowns allow it, injects an autonomous trigger
    task into the executor. The trigger is a plain Turkish "system event" string, so the
    LLM's ReAct JSON contract ({"tool": ...} / {"final": ...}) is completely unchanged.

Priorities (lower number runs first): user/sensory 0/5, autonomous 20 — you never wait
behind a bored fly.
"""
from __future__ import annotations

import inspect
import itertools
import json
import queue
import random
import threading
import time

PRIORITY_USER = 0
PRIORITY_SENSORY = 5
PRIORITY_AUTONOMOUS = 20

# --------------------------------------------------------------------------- #
# autonomous triggers — Turkish, first person, exactly one JSON action expected back
# --------------------------------------------------------------------------- #
NEED_PROMPTS = {
    "hunger": ("AÇLIK KRİTİK (açlık {level:.0f}/100). Şeker sinyali yok; beslenme devresi "
               "devreye girmeli."),
    "energy": ("ENERJİ TÜKENDİ (enerji {level:.0f}/100). Hareket için güç kalmadı; "
               "dinlenme devresi devreye girmeli."),
    "boredom": ("CAN SIKINTISI YÜKSEK (can sıkıntısı {level:.0f}/100). Yeni uyarım gerekiyor; "
                "keşif devresi devreye girmeli."),
}

AUTONOMOUS_FOOTER = (
    "Kimse sana bir şey sormadı; içsel dürtünle hareket ediyorsun. Şu an bir şey yapmak "
    "istemiyorsan {\"noop\": true} yazabilirsin."
)

# What the fly should DO about each need: the first tool that both addresses it and
# lights the 3D view up. The trigger quote is machine-readable, so if the model refuses
# to act the harness runs this call itself (server.run_agent) — the 3D always lights up.
NEED_TOOL = {
    "hunger": {
        "tool": "show3d", "args": {"query": "sugar", "seeds": 40, "dur_ms": 200},
        "why": "şeker (gustatory) devrelerini uyar, 3D'de parlat — beslenme refleksini "
               "çip kendisi uygular, sen sadece Patron'a anlat"},
    "energy": {
        "tool": "show3d", "args": {"query": "clock", "seeds": 30, "dur_ms": 200},
        "why": "kanatların ağırken beyinndeki saat (clock) nöronlarını göster",
    },
    "boredom": {
        "tool": "show_compass", "args": {"regime": "raw"},
        "why": "sıkıldın — merkez kompleks pusulanı oynat, kendine meşgale bul",
    },
}
DEFAULT_TOOL = ("find_neurons", {"query": "sugar"})

# --------------------------------------------------------------------------- #
# effects — what a recognized category DOES to the fly (deterministic, not the LLM's call)
# --------------------------------------------------------------------------- #
# Seeing food is not eating it. A 4B model reliably lights up the sugar circuit and then
# just SAYS it is hungry, so the appetite impulse would fire forever (the vitals never
# actually move). The link between "found food" and "fed" therefore lives in deterministic
# code, not in the model's judgement; the fly only narrates it in Turkish.
#
# Phase 9: with no body, a decision has exactly two possible consequences — a vitals delta
# and/or a short-lived flag. `cognitive_matrix.py` produces the category, this table says
# what that category MEANS, and the model is handed the result as a fact it may only
# narrate (`classifier_note`). One table, so an autonomous need and a typed word ("şeker")
# cannot drift apart.
CATEGORY_EFFECTS = {
    "besin": {                       # yiyecek var → beslenme refleksi
        "action": "eat",
        "delta": {"hunger": -35.0, "energy": +8.0, "boredom": -5.0},   # == LIFE["eat"] ×1
        "after": ("show3d", "find_neurons", "stimulate"),   # tools that mean "food"
        "match": ("sugar", "gustatory", "taste", "food"),
        "why": "yiyecek var → beslenme refleksi (çip uyguladı)",
        "tool": {"tool": "show3d",
                 "args": {"query": "sugar", "seeds": 40, "dur_ms": 200}},
    },
    "tehlike": {                     # tehdit → looming/kaçış devresi, beden irkilir
        "delta": {"boredom": -40.0, "energy": -6.0},
        "flag": "startled", "flag_ttl": 25.0,
        "why": "tehdit → kaçış devresi irkildi (LPLC2/LC4 → Dev Fiber)",
        "tool": {"tool": "dodge_swatter", "args": {}},
    },
    "selam": {                       # sosyal temas: vital değişmez, sıkıntı düşer
        "delta": {"boredom": -25.0},
        "why": "selam → sosyal temas (vital değişmez, can sıkıntısı düşer)",
    },
    "açlık": {                       # SORU: ölçüm anlatılır, hiçbir şey değişmez
        "delta": {},
        "why": "açlık sorusu → sinek kendi ölçümünü anlatır, vital değişmez",
    },
    "onay": {"delta": {"boredom": -10.0},
             "why": "onay → sosyal, can sıkıntısı biraz düşer"},
    "red": {"delta": {}, "why": "ret → vital değişmez"},
}

# An autonomous *need* is a category we already know how to answer. `hunger` means "food is
# here" as far as the fly is concerned — that is what closes the hunger loop. Phase 14 adds the
# energy equivalent: resting is a *reflex*, not something the model may decide (or forget).
NEED_CATEGORY = {"hunger": "besin", "energy": "dinlenme"}

# --------------------------------------------------------------------------- #
# Phase 14/15 — autonomic + stimulus effects: the fly's own body, its environment,
# and the direct-knob stimuli (/interact buttons, the "eş" keyword route)
# --------------------------------------------------------------------------- #
# Same shape, same apply_effect(), same `reflex` event as CATEGORY_EFFECTS — but a separate table,
# because `CATEGORY_EFFECTS` is 1:1 with cognitive_matrix.CATEGORIES and both self-tests assert
# that (the classifier's six decisions must not grow by accident, even when Phase 15 adds a
# seventh *stimulus*). Nothing here is reachable from a vocabulary word: these rows belong to the
# autonomous reflex path, to the environment generator and to /interact, so a *taught* category
# can never silently borrow one of them.
AUTONOMIC_EFFECTS = {
    # Task 1 — the missing energy reflex. Phase 5 gave hunger a deterministic `eat`; energy only
    # ever got a 3D "clock" query, so a tired fly asked for the clock forever while energy kept
    # falling. The opening instalment lands when the reflex fires (server.fire_reflex) and the
    # GameLoop tops it up tick by tick — `recover` is that schedule, data not code.
    "dinlenme": {
        "action": "rest",
        "delta": {"energy": +8.0, "hunger": +2.0},       # opening instalment (≈0.3 × LIFE.rest)
        "recover": {"energy": 3.0, "ticks": 10},          # …then +3/tick × 10 (GameLoop clock)
        "after": ("rest", "show3d", "find_neurons"),      # tools that mean "I am resting"
        "match": ("clock", "rest", "dinlen"),
        "why": "enerji bitti → dinlenme refleksi (çip enerjiyi kademeli toplar)",
        "tool": {"tool": "show3d", "args": {"query": "clock", "seeds": 30, "dur_ms": 200}},
        "label": "dinlenme",
    },
    # Task 2 — the environment. It pokes the fly through exactly the same pipeline a typed word
    # uses (category → effect_for-style row → apply_effect → vitals/flag + event), so there is no
    # second effect system to keep in sync.
    "darbe": {
        "action": "hit",
        "delta": {"energy": -15.0, "boredom": -10.0},
        "flag": "startled", "flag_ttl": 25.0,
        "why": "darbe → gövdeye çarpma; kaçış devresi irkildi (çevre olayı)",
        "label": "darbe",
    },
    "rastgele-besin": {
        "action": "eat",
        "delta": {"hunger": -20.0},
        "why": "beklenmedik besin → çip yedi (çevre olayı)",
        "label": "beklenmedik besin",
    },
    # Task 3 — the courtship / mate response. A seventh *stimulus* (not a connectome decision):
    # seeing a female fly wakes the fly up. Wing vibration is real courtship behaviour in
    # Drosophila (the male extends and vibrates one wing), so the phrase bank says so.
    "eş": {
        "action": "court",
        "delta": {"boredom": -20.0},
        "flag": "heyecanlı", "flag_ttl": 25.0,
        "why": "dişi sinek → kur devresi uyandı (kanat titremesi), can sıkıntısı düştü",
        "label": "eş adayı",
    },
}

# what the environment may do to an idle fly, and how often (see GameLoop env_* knobs)
ENV_WEIGHTS = {"darbe": 1.0, "rastgele-besin": 1.0}


def autonomic_effect(category):
    """The autonomic effect for ``category`` (rest reflex / environmental event), or None."""
    eff = AUTONOMIC_EFFECTS.get(str(category or "").strip().lower())
    return dict(eff) if eff else None


def effect_for(category):
    """The deterministic effect of a *classifier* category, or None if we don't know it."""
    eff = CATEGORY_EFFECTS.get(str(category or "").strip().lower())
    return dict(eff) if eff else None


def reflex_for(need):
    """The effect of an autonomous need (hunger → feeding, energy → resting), or None.

    Kept as its own door because the laziness guard and the `reflex` event speak in needs. It is
    the only lookup that sees both tables: a need may be answered by a classifier category
    (hunger → besin) or by an autonomic one (energy → dinlenme).
    """
    cat = NEED_CATEGORY.get((need or {}).get("need"))
    if not cat:
        return None
    return effect_for(cat) or autonomic_effect(cat)


def reflex_matches(reflex, tool, args):
    """Does this tool call mean the fly actually found food?"""
    if not reflex:
        return False
    if str(tool) not in reflex.get("after", ()):
        return False
    blob = json.dumps(args or {}, ensure_ascii=False).lower()
    return any(word in blob for word in reflex.get("match", ()))


def apply_effect(state, effect, reason=None):
    """Apply an effect to a ``FlyState`` and describe what happened.

    Pure — it publishes nothing, so both callers (the autonomous reflex path and the
    classifier path in server.py) share one implementation and one set of numbers.
    Returns ``None`` when there is no effect at all, and ``{"noop": True}`` when the
    category deliberately changes nothing (a question, a refusal).
    """
    if state is None or not effect:
        return None
    delta = dict(effect.get("delta") or {})
    flag = effect.get("flag")
    if not delta and not flag:
        return {"ok": True, "action": "none", "delta": {}, "flag": None, "noop": True,
                "reason": reason, "state": state.snapshot()}
    res = state.apply_delta(delta, flag=flag, flag_ttl=effect.get("flag_ttl", 20.0),
                            action=effect.get("action") or "delta")
    res["reason"] = reason
    return res


def classifier_note(hit, effect, applied, state=None):
    """Hand the classifier's decision to the LLM as a FACT it may only narrate.

    This is the firewall of Phase 9 rule D: the connectome model already decided, so the
    prompt forbids re-labelling, second-guessing the confidence or inventing a reason.
    The model's only freedom is *how* it says it happened — and it is told its own vitals
    after the effect, so it cannot narrate a hunger it no longer has.

    ``hit`` is one entry from ``cognitive_matrix.scan()`` (optional ``label`` for the
    Turkish category name), ``effect`` the CATEGORY_EFFECTS row and ``applied`` what
    ``apply_effect`` actually did.
    """
    cat = str(hit.get("category") or "?")
    label = hit.get("label") or cat
    lines = [
        "SINIFLANDIRICI KARARI (mantar cismi / Kenyon hücreleri verdi — bu kararı SEN "
        "vermedin):",
        "- Algılanan sözcük: \"%s\" → kategori: %s (%s), güven: %.2f"
        % (hit.get("word"), label, cat, float(hit.get("confidence") or 0.0)),
    ]
    if applied and applied.get("noop"):
        lines.append("- Beden etkisi: YOK — bu kategori bilinçli olarak hiçbir şeyi "
                     "değiştirmez (%s)." % effect.get("why", ""))
    else:
        delta = ", ".join("%s %+g" % (k, v)
                          for k, v in (applied or {}).get("delta", {}).items())
        lines.append("- Beden etkisi (çip kendi uyguladı, sen karar vermedin): %s"
                     % (delta or "yok"))
        if (applied or {}).get("flag"):
            lines.append("- Bayrak: %s — %.0f sn boyunca ruh halini belirler."
                         % (applied["flag"], float(effect.get("flag_ttl", 20.0))))
    if state is not None:
        lines.append("- " + state.status_line())
    lines.append("KURALLAR: kategori DEĞİŞTİRİLEMEZ. Başka kategori önerme, güveni "
                 "tartışma, gerekçe uydurma. SEN ANLATMIYORSUN, ÇÖZÜYORSUN: bu kararı "
                 "2-4 kelimelik bir durum parçasına çevir (\"durum · eylem\"). "
                 "Cümle, birinci şahıs, metafor ve ünlem YOK.")
    tool = effect.get("tool")
    if tool:
        lines.append("İSTEĞE BAĞLI: ilgili devreyi 3D'de göstermek istersen "
                     "{\"tool\": \"%s\", \"args\": %s} çağırabilirsin (zorunlu değil)."
                     % (tool["tool"], json.dumps(tool["args"], ensure_ascii=False)))
    else:
        lines.append("ARAÇ GEREKMİYOR: bu turda araç çağırmak zorunda değilsin.")
    return "\n".join(lines)


def suggested_call(need):
    """(tool, args) for a need — what the harness executes if the model refuses."""
    sug = NEED_TOOL.get((need or {}).get("need"))
    return (sug["tool"], dict(sug["args"])) if sug else (DEFAULT_TOOL[0],
                                                        dict(DEFAULT_TOOL[1]))


def build_trigger(need, status_line):
    """Turn a fired need into the Turkish 'system event' handed to the LLM as a user turn.

    The tool requirement is stated explicitly and repeated (the enforcement in
    server.run_agent backs it up), because a model that just says "I am hungry" without
    touching the connectome makes the whole simulation pointless.
    """
    body = NEED_PROMPTS.get(need["need"], "İçimde bir dürtü hissediyorum.").format(
        level=float(need.get("level", 0.0)))
    tool, args = suggested_call(need)
    exact = "{\"tool\": \"%s\", \"args\": %s}" % (tool, json.dumps(args, ensure_ascii=False))
    forced = (
        "ZORUNLU KURAL: bu turda İLK eylemin bir ARAÇ ÇAĞIRMAK olacak. Bir araç "
        "çalışana kadar {\"final\": ...} YASAK — 3D beynin ışıldaması gerekiyor.\n"
        "Hemen şuna benzer bir çağrı yaz: %s\n(%s)\n"
        "ARAÇ ÇALIŞTIKTAN SONRA 2-4 KELİMELİK Türkçe bir durum parçası yaz "
        "(\"durum · eylem\", örn. \"aç · yaklaşıyor\")."
        % (exact, NEED_TOOL.get(need["need"], {}).get("why", "araç çağır")))
    return "%s\nOTONOM UYARI: %s\n%s\n%s" % (status_line, body, forced, AUTONOMOUS_FOOTER)


def build_status(message, state, origin="user"):
    """Prefix every task with the vitals snapshot, so the fly is aware of its own body."""
    tag = {"user": "KULLANICI", "sensory": "DUYU", "autonomous": "OTONOM"}.get(origin, origin)
    return f"[{tag}] {state.status_line()}\n{message}"


class LLMExecutor:
    """A single worker thread in front of Ollama, fed by a PriorityQueue.

    Why one thread: a local 4b model on CPU is slow, and two concurrent
    ``ollama.chat`` calls thrash the same weights. Serialising every call here keeps
    the model warm, keeps the HTTP handlers instant, and gives the UI a clean,
    ordered event stream to poll.

    ``runner`` is injected by server.py and has the signature
        runner(text, emit=emit, origin=origin) -> (answer_text, viz_data_or_None)
    where ``emit(kind, **fields)`` publishes an EventBus event mid-flight (tokens,
    tool calls, viz updates). Older two-argument runners are tolerated (decided by
    signature, so a TypeError raised inside a runner is never mistaken for one).
    """

    def __init__(self, runner, bus=None, name="llm-executor", on_result=None):
        self.runner = runner
        self.bus = bus
        self.name = name
        self.on_result = on_result
        self._q = queue.PriorityQueue()
        self._counter = itertools.count()
        self._stop = threading.Event()
        self._busy = threading.Event()
        self._current = None
        self._lock = threading.Lock()
        self._thread = None
        self.completed = 0
        self.failed = 0
        self._results = {}          # job id -> (answer, viz, task)
        self._done = {}             # job id -> threading.Event
        self._results_lock = threading.Lock()
        self._accepts = None        # cached: which kwargs the injected runner takes

    # --------------------------------------------------------------- lifecycle #
    def start(self):
        if self._thread and self._thread.is_alive():
            return self
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name=self.name, daemon=True)
        self._thread.start()
        return self

    def stop(self, timeout=5.0):
        self._stop.set()
        t = self._thread
        if t and t.is_alive():
            t.join(timeout=timeout)
        self._thread = None

    # ------------------------------------------------------------------ submit #
    def submit(self, text, origin="user", priority=PRIORITY_USER, meta=None):
        """Queue one LLM job. Returns the job id; never blocks."""
        job = next(self._counter)
        self._q.put((int(priority), job,
                     {"text": str(text), "origin": origin, "meta": dict(meta or {})}))
        if self.bus:
            self.bus.publish("queued", payload={"origin": origin,
                                                "priority": int(priority), "job": job})
        return job

    @property
    def busy(self):
        return self._busy.is_set()

    @property
    def queued(self):
        return self._q.qsize()

    def status(self):
        with self._lock:
            cur = self._current
        return {"busy": self.busy, "queued": self.queued, "completed": self.completed,
                "failed": self.failed,
                "current": ({"origin": cur["origin"], "text": cur["text"][:200]}
                            if cur else None)}

    def _mark_done(self, job_id, answer, viz, task):
        with self._results_lock:
            self._results[job_id] = (answer, viz, task)
            event = self._done.get(job_id)
            if len(self._results) > 64:             # keep the map small
                for old in sorted(self._results)[:-64]:
                    self._results.pop(old, None)
                    self._done.pop(old, None)
        if event is not None:
            event.set()

    def wait_result(self, job_id, timeout=180.0):
        """Block until ``job_id`` finishes; returns ``(answer, viz, task)`` or None.

        This is the escape hatch for a client that would rather wait than poll
        (e.g. a legacy POST /chat {wait: true}); the worker thread still does the
        work, so nothing else on the server is held up.
        """
        with self._results_lock:
            if job_id in self._results:
                return self._results[job_id]
            event = self._done.setdefault(job_id, threading.Event())
        if not event.wait(max(0.0, float(timeout))):
            return None
        with self._results_lock:
            return self._results.get(job_id)

    def result_for(self, job_id):
        with self._results_lock:
            return self._results.get(job_id)

    # -------------------------------------------------------------- worker loop #
    def _emit_for(self, origin):
        bus = self.bus

        def emit(kind, **fields):
            if not bus:
                return -1
            body = {"origin": origin}
            body.update(fields)
            return bus.publish(kind, payload=body)

        return emit

    def _runner_kwargs(self):
        """Which of emit / origin / meta the injected runner actually accepts.

        Checked by signature ONCE, not by catching TypeError: a TypeError raised *inside*
        a runner (a real bug in a turn) must not silently re-run the whole turn — that
        duplicated tool calls and 3D scenes. Older two-argument runners still work.
        """
        if self._accepts is None:
            try:
                params = inspect.signature(self.runner).parameters
            except (TypeError, ValueError):                 # builtins, no signature
                params = {}
            names = set(params)
            if any(p.kind == p.VAR_KEYWORD for p in params.values()):   # **kwargs
                names.update(("emit", "origin", "meta"))
            self._accepts = {n for n in ("emit", "origin", "meta") if n in names}
        return self._accepts

    def _run(self):
        while not self._stop.is_set():
            try:
                _prio, job_id, task = self._q.get(timeout=0.4)
            except queue.Empty:
                continue
            self._busy.set()
            with self._lock:
                self._current = task
            if self.bus:
                self.bus.publish("think_start", payload={
                    "origin": task["origin"], "job": job_id,
                    "text": task["text"][:400], "meta": task["meta"]})
            emit = self._emit_for(task["origin"])
            t0 = time.time()
            answer, viz = None, None
            accepts = self._runner_kwargs()
            kwargs = {"emit": emit} if "emit" in accepts else {}
            if "origin" in accepts:
                kwargs["origin"] = task["origin"]
            if "meta" in accepts:
                kwargs["meta"] = task["meta"]
            try:
                answer, viz = self.runner(task["text"], **kwargs)
            except Exception as e:                          # noqa: BLE001
                self.failed += 1
                emit("error", message="%s: %s" % (type(e).__name__, e))
            took = round(time.time() - t0, 2)
            self._mark_done(job_id, answer, viz, task)
            if answer:
                if self.bus:
                    # Phase 13: `mode` rides along so the client never has to guess what it is
                    # looking at — caption (decoded signal), chat (free-form LLM) or system (ours).
                    self.bus.publish("say", payload={
                        "text": str(answer),
                        "origin": task["origin"],
                        "mode": (task.get("meta") or {}).get("mode") or "chat",
                        "took_s": took})
            self.completed += 1
            if self.on_result:
                try:
                    self.on_result(answer, viz, task)
                except Exception:                           # noqa: BLE001
                    pass
            with self._lock:
                self._current = None
            self._busy.clear()
            self._q.task_done()


# --------------------------------------------------------------------------- #
# Phase 14 — the GameLoop's own knobs
# --------------------------------------------------------------------------- #
# Task 1: below this the fly starts resting by itself. It sits above brain_state.ENERGY_CRITICAL
# (25), which is when the *need* fires, so the body recovers before the impulse would spin on it.
REST_THRESHOLD = 30.0
REST_COOLDOWN = 60.0        # seconds between two rest episodes

# Task 2: random environmental events. One tick is ~1 s, so 0.004 ≈ one event every ~4 minutes of
# TRUE idling — deliberately rare: this is seasoning, not a source of noise.
ENV_CHANCE_PER_TICK = 0.004
ENV_COOLDOWN = 90.0         # never two environmental events closer than this
ENV_MIN_IDLE_S = 45.0       # no human contact and no impulse for this long


class GameLoop:
    """The fly's autonomic nervous system: a low-rate tick that drives the vitals and
    decides *when* to think.

    Every tick it degrades the state and looks for a fired need (hungry / exhausted /
    bored). A need only becomes an LLM call when four gates all pass, which is what
    keeps a slow local model usable:

      * autonomy is enabled,
      * that need's own cooldown has elapsed,
      * the global "don't think again yet" gap has elapsed,
      * the executor is idle and its queue is empty (the human always goes first).

    Phase 14 adds two deterministic layers around that (no LLM involved in either):

      * the **rest reflex** — below ``REST_THRESHOLD`` the fly recovers energy tick by tick,
        taken from the ``dinlenme`` row's ``recover`` schedule;
      * the **environment** — a rare, randomness-driven poke (``darbe`` / ``rastgele-besin``)
        that only ever fires while nothing else is happening.

    ``tick_once`` is public and side-effect-visible, so it can be unit-tested without
    starting a thread.
    """

    def __init__(self, state, bus=None, executor=None, *, tick=1.0, max_think_gap=30.0,
                 need_cooldowns=None, publish_state_every=3.0,
                 priority=PRIORITY_AUTONOMOUS, rest_threshold=REST_THRESHOLD,
                 rest_cooldown=REST_COOLDOWN, env_chance=ENV_CHANCE_PER_TICK,
                 env_cooldown=ENV_COOLDOWN, env_min_idle=ENV_MIN_IDLE_S, env_rng=None,
                 env_weights=None, impulse=None):
        self.state = state
        self.bus = bus
        self.executor = executor
        # Phase 15: when an `impulse` callable is injected, an autonomous need is answered by it
        # **deterministically** (scene + reflex + fixed phrase) instead of an LLM turn. The
        # executor path below stays for back-compat/tests, but nothing in the live server uses it.
        self.impulse = impulse
        self.tick_interval = float(tick)
        self.max_think_gap = float(max_think_gap)
        self.publish_state_every = float(publish_state_every)
        self.priority = int(priority)
        self._need_cooldowns = dict(need_cooldowns or
                                    {"hunger": 40.0, "energy": 50.0, "boredom": 60.0})
        self._last_need_at = {}
        self._last_think = 0.0
        self._last_state_pub = 0.0
        self._stop = threading.Event()
        self._thread = None
        self.ticks = 0
        self.triggers = 0
        # Phase 14 Task 1 — the rest reflex
        self.rest_threshold = float(rest_threshold)
        self.rest_cooldown = float(rest_cooldown)
        self._rest_left = 0
        self._rest_at = 0.0
        self.rest_episodes = 0
        # Phase 14 Task 2 — the environment
        self.env_chance = float(env_chance)
        self.env_cooldown = float(env_cooldown)
        self.env_min_idle = float(env_min_idle)
        self.env_weights = dict(env_weights or ENV_WEIGHTS)
        self.env_rng = env_rng or random.random
        self.env_events = 0
        self._last_env = 0.0

    # --------------------------------------------------------------- lifecycle #
    def start(self):
        if self._thread and self._thread.is_alive():
            return self
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="game-loop", daemon=True)
        self._thread.start()
        if self.bus:
            self.bus.publish("system", payload={"event": "game-loop-started",
                                                "tick_s": self.tick_interval})
        return self

    def stop(self, timeout=3.0):
        self._stop.set()
        t = self._thread
        if t and t.is_alive():
            t.join(timeout=timeout)
        self._thread = None
        if self.bus:
            self.bus.publish("system", payload={"event": "game-loop-stopped"})

    # ------------------------------------------------------------------- tick #
    def tick_once(self, dt=None):
        """One metabolic step. Returns a small report (also handy for tests)."""
        dt = self.tick_interval if dt is None else float(dt)
        self.state.tick(dt)
        self.ticks += 1
        now = time.time()
        snap = self.state.snapshot()
        if self.bus and (now - self._last_state_pub) >= self.publish_state_every:
            self.bus.publish("state", payload={"state": snap})
            self._last_state_pub = now

        report = {"dt": round(dt, 2), "state": snap, "need": None,
                  "triggered": False, "reason": "no-need"}

        # Phase 14 Task 1: the body's own recovery, checked before any thinking. Deliberately NOT
        # gated on autonomy — decay is not either, and a fly whose user is chatting must not
        # quietly run itself flat.
        self._tick_rest(now, report)

        if not self.state.autonomy:
            report["reason"] = "autonomy-off"
            return report
        if self._maybe_impulse(now, report):
            return report
        # Nothing to think about → the environment may poke the fly (rarely, see _maybe_environment)
        self._maybe_environment(now, report)
        return report

    def _tick_rest(self, now, report):
        """Phase 14 Task 1 — the missing energy reflex, tick by tick.

        Below ``rest_threshold`` the fly starts a rest *episode*: one deterministic recovery step
        per tick, for as long as the ``dinlenme`` row's ``recover`` schedule says, with a cooldown
        between episodes so energy settles instead of oscillating. The opening instalment belongs
        to the reflex itself (server.fire_reflex), so an LLM turn and the body agree on one
        episode. Returns the applied result, or None when the fly is not resting.
        """
        schedule = (autonomic_effect("dinlenme") or {}).get("recover") or {}
        per, ticks = float(schedule.get("energy") or 0.0), int(schedule.get("ticks") or 0)
        if per <= 0 or ticks <= 0:
            return None
        if self._rest_left <= 0:
            energy = float(self.state.snapshot().get("energy") or 0.0)
            if energy > self.rest_threshold or (now - self._rest_at) < self.rest_cooldown:
                return None
            self._rest_left = ticks
            self._rest_at = now
            self.rest_episodes += 1
            report["rest"] = "start"
            if self.bus:
                self.bus.publish("reflex", payload={
                    "origin": "environment", "need": "energy", "category": "dinlenme",
                    "action": "rest", "delta": {}, "flag": None,
                    "why": "enerji %.0f/100 (eşik %.0f) → dinlenme refleksi: kademeli toparlanma"
                           % (energy, self.rest_threshold),
                    "triggered_by": "reflex", "recovery": {"energy": per, "ticks": ticks},
                    "state": self.state.snapshot()})
            return None
        self._rest_left -= 1
        res = apply_effect(self.state, {"delta": {"energy": per}, "action": "rest"},
                           reason="reflex:dinlenme-tick")
        report["rest"] = self._rest_left
        return res

    def _maybe_impulse(self, now, report):
        """The need → answer path. True when the need was answered this tick.

        Two modes, same gates otherwise: with ``impulse`` injected (the live server, Phase 15) the
        answer is deterministic and needs no worker at all; without it the legacy LLM job path runs
        unchanged (harness phases and anything that still injects an executor).
        """
        need = self.state.top_need()
        if need is None:
            return False
        report["need"] = need

        cooldown = self._need_cooldowns.get(need["need"], 30.0)
        if now - self._last_need_at.get(need["need"], 0.0) < cooldown:
            report["reason"] = "need-cooldown"
            return False
        if now - self._last_think < self.max_think_gap:
            report["reason"] = "global-cooldown"
            return False

        tool, args = suggested_call(need)
        if self.impulse is not None:
            self._last_need_at[need["need"]] = now
            self._last_think = now
            self.triggers += 1
            if self.bus:
                self.bus.publish("event", payload={"need": need["need"],
                                                   "label": need["label"],
                                                   "level": round(float(need["level"]), 1),
                                                   "tool": tool, "tool_args": args,
                                                   "mode": "deterministic"})
            self.impulse(need, tool, args)
            report["triggered"] = True
            report["reason"] = "triggered"
            return True

        if self.executor is None:
            report["reason"] = "no-executor"
            return False
        if self.executor.busy or self.executor.queued > 0:
            report["reason"] = "executor-busy"
            return False

        trigger = build_trigger(need, self.state.status_line())
        job = self.executor.submit(trigger, origin="autonomous",
                                   priority=self.priority,
                                   meta={"need": need["need"], "require_tool": True,
                                         "tool": tool, "args": args,
                                         "mode": "caption"})
        self._last_need_at[need["need"]] = now
        self._last_think = now
        self.triggers += 1
        if self.bus:
            self.bus.publish("event", payload={"need": need["need"],
                                               "label": need["label"],
                                               "level": round(float(need["level"]), 1),
                                               "job": job, "text": trigger})
        report["triggered"] = True
        report["reason"] = "triggered"
        return True

    def _pick_environment(self):
        """One weighted draw from ``env_weights`` (split out so a test can seed it)."""
        items = list(self.env_weights.items())
        if not items:
            return None
        total = sum(max(0.0, float(w)) for _c, w in items)
        if total <= 0:
            return items[0][0]
        r = self.env_rng() * total
        acc = 0.0
        for cat, weight in items:
            acc += max(0.0, float(weight))
            if r <= acc:
                return cat
        return items[-1][0]

    def _maybe_environment(self, now, report):
        """Phase 14 Task 2 — a rare, random environmental event, applied like any other effect.

        Every gate must pass, so this can never interrupt real interaction:

          * the per-tick chance (``env_chance``) and the ``env_cooldown`` spacing,
          * no human contact for ``env_min_idle`` seconds (``FlyState.touch()`` runs on every user
            message, every reflex and every life action, so a conversation resets this),
          * no autonomous impulse that recently either,
          * nothing in the executor (no turn running or queued),
          * no rest episode in progress.

        The event goes through ``apply_effect`` exactly like a classifier decision — same delta /
        flag semantics, same ``reflex`` event shape — so there is one effect pipeline, not two.
        Returns the category that fired, or None.
        """
        if self.env_chance <= 0 or not self.env_weights:
            return None
        if (now - self._last_env) < self.env_cooldown:
            return None
        if self._rest_left > 0:
            return None
        if self.state.idle_seconds() < self.env_min_idle:
            return None
        if (now - self._last_think) < self.env_min_idle:
            return None
        if self.executor is not None and (self.executor.busy or self.executor.queued > 0):
            return None
        if self.env_rng() >= self.env_chance:
            return None

        category = self._pick_environment()
        effect = autonomic_effect(category)
        if not effect:
            return None
        res = apply_effect(self.state, effect, reason="environment:" + str(category))
        self._last_env = now
        self.env_events += 1
        report["environment"] = category
        if self.bus and res is not None:
            self.bus.publish("state", payload={"state": self.state.snapshot()})
            self.bus.publish("reflex", payload={
                "origin": "environment", "need": None, "category": category,
                "action": res.get("action"), "delta": res.get("delta"), "flag": res.get("flag"),
                # `want` vs `delta` exactly like a classifier event: a fly already at 0 boredom
                # shows the intention, not a bogus -10
                "want": res.get("want"), "saturated": res.get("saturated"),
                "why": effect.get("why", ""), "triggered_by": "çevre",
                "state": res.get("state")})
        return category

    def _run(self):
        last = time.monotonic()
        while not self._stop.is_set():
            now = time.monotonic()
            dt = min(5.0, max(0.05, now - last))
            last = now
            try:
                self.tick_once(dt)
            except Exception as e:                          # noqa: BLE001
                if self.bus:
                    self.bus.publish("error", payload={
                        "message": "game loop: %s: %s" % (type(e).__name__, e)})
            self._stop.wait(self.tick_interval)

    def status(self):
        with self.state.lock:
            return {"running": bool(self._thread and self._thread.is_alive()),
                    "tick_s": self.tick_interval, "ticks": self.ticks,
                    "triggers": self.triggers, "autonomy": self.state.autonomy,
                    "max_think_gap_s": self.max_think_gap,
                    "need_cooldowns": dict(self._need_cooldowns),
                    # Phase 14: the two deterministic layers are visible from /state too
                    "rest_episodes": self.rest_episodes,
                    "rest_threshold": self.rest_threshold,
                    "rest_left": self._rest_left,
                    "env_events": self.env_events,
                    "env_chance": self.env_chance}


# --------------------------------------------------------------------------- #
# smoke test — no connectome, no LLM, no server required
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    import brain_state

    bus = brain_state.EventBus()
    state = brain_state.FlyState(hunger=90.0, energy=80.0)   # force a hunger impulse

    seen = []

    def fake_runner(text, emit=None, origin="user", meta=None):
        if emit:
            emit("tool_call", tool="find_neurons", args={"query": "sugar"})
            emit("token", text="şeker...")
        seen.append((origin, text.splitlines()[-1][:60]))
        return "Ben bir sineğim; şeker arıyorum.", {"query": "sugar"}

    ex = LLMExecutor(fake_runner, bus=bus).start()
    loop = GameLoop(state, bus=bus, executor=ex, tick=0.05, max_think_gap=60.0,
                    need_cooldowns={"hunger": 60.0})
    rep = loop.tick_once(1.0)
    print("tick raporu:", {k: rep[k] for k in ("triggered", "reason", "need")})
    assert rep["triggered"], "açlık dürtüsü tetiklenmedi"

    for _ in range(40):
        time.sleep(0.05)
        if seen:
            break
    ex.stop()
    print("çağrıldı:", seen)
    assert seen and seen[0][0] == "autonomous", "otonom görev çalıştırılmadı"
    res = ex.wait_result(0, timeout=2.0)
    print("wait_result:", (res[0] if res else None))
    assert res and res[0], "wait_result işin sonucunu döndürmedi"
    kinds = [e["kind"] for e in bus.since(0)["events"]]
    print("olay türleri:", kinds)
    for need in ("queued", "think_start", "tool_call", "say", "event", "state"):
        assert need in kinds, "eksik olay: " + need

    # cooldown / executor-busy kapıları
    rep2 = loop.tick_once(1.0)
    print("ikinci tick:", rep2["reason"])
    assert not rep2["triggered"], "cooldown kapısı çalışmadı"

    # ---- Phase 9: category -> vitals delta table + the classifier note --------
    import cognitive_matrix
    import brain_state as bs

    assert set(CATEGORY_EFFECTS) == set(cognitive_matrix.CATEGORIES), \
        "her kategori için bir etki satırı olmalı: %s" % sorted(CATEGORY_EFFECTS)
    assert CATEGORY_EFFECTS["besin"]["delta"] == bs.FlyState.LIFE["eat"], \
        "besin deltası LIFE['eat']'ten kaymış"
    assert reflex_for({"need": "hunger"})["action"] == "eat", "açlık refleksi kayboldu"
    assert reflex_for({"need": "boredom"}) is None, "olmayan bir ihtiyaç etki üretti"

    # ---- Phase 14 Task 1/2: the rest reflex, the environment, and the 1:1 table guard --------
    assert set(CATEGORY_EFFECTS) == set(cognitive_matrix.CATEGORIES), \
        "otonom etkiler fabrika tablosuna sızmış: %s" % sorted(set(CATEGORY_EFFECTS) -
                                                              set(cognitive_matrix.CATEGORIES))
    rest_reflex = reflex_for({"need": "energy"})
    print("enerji refleksi:", rest_reflex["action"], rest_reflex["delta"], rest_reflex["recover"])
    assert rest_reflex and rest_reflex["action"] == "rest", "enerji refleksi yok"
    assert rest_reflex["recover"]["ticks"] > 0 and rest_reflex["recover"]["energy"] > 0, rest_reflex
    assert reflex_for({"need": "boredom"}) is None, "can sıkıntısı refleks uydurdu"
    for cat in ("darbe", "rastgele-besin"):
        eff = autonomic_effect(cat)
        assert eff and eff.get("delta"), "çevre olayı eksik: %s" % cat
    assert effect_for("darbe") is None, "çevre olayı sınıflandırıcı yolundan görünüyor"
    assert autonomic_effect("besin") is None, "fabrika kategorisi otonom tabloya sızmış"
    print("çevre olayları:", {c: autonomic_effect(c)["delta"] for c in ("darbe", "rastgele-besin")})

    tired = bs.FlyState(energy=0.0, hunger=10.0, autonomy=True)
    loop2 = GameLoop(tired, bus=bus, executor=None, tick=1.0, max_think_gap=0.0,
                     rest_cooldown=0.0, env_chance=0.0)
    for _ in range(20):
        loop2.tick_once(1.0)
    recovered = tired.snapshot()["energy"]
    print("enerji 0 → %.1f (%d dinlenme turu, %d tick)" % (recovered, loop2.rest_episodes,
                                                           loop2.ticks))
    assert recovered >= REST_THRESHOLD, "dinlenme refleksi enerjiyi toparlamadı: %s" % recovered
    assert loop2.rest_episodes >= 1, "dinlenme turları sayılmadı"
    assert tired.top_need() is None, "enerji toparlandı ama ihtiyaç hâlâ ateşliyor: %s" \
        % (tired.top_need(),)
    kinds14 = [e["kind"] for e in bus.since(0)["events"]]
    assert "reflex" in kinds14, "dinlenme refleksi olay yayınlamadı: %s" % kinds14
    # the environment obeys its gates: never while the human is around…
    seen_env = GameLoop(tired, bus=bus, executor=None, tick=1.0, env_chance=1.0,
                        env_cooldown=0.0, env_min_idle=45.0, env_rng=lambda: 0.0)
    quiet = seen_env.tick_once(1.0)
    assert not quiet.get("environment"), "insan konuşurken çevre olayı ateşledi: %s" % quiet
    # …but it does fire once the fly is really alone (rng forced to "hit")
    tired.touch(calm=0.0)
    tired._last_touch -= 60.0                    # pretend the human left a minute ago
    lonely = GameLoop(tired, bus=bus, executor=None, tick=1.0, env_chance=1.0,
                      env_cooldown=0.0, env_min_idle=45.0, env_rng=lambda: 0.0)
    hit = lonely.tick_once(1.0)
    print("yalnız tick:", hit.get("environment"), lonely.env_events)
    assert hit.get("environment") in ("darbe", "rastgele-besin"), \
        "yalnız kalan sineğe çevre olayı gelmedi: %s" % hit
    assert any(e.get("origin") == "environment" and e.get("category") in
               ("darbe", "rastgele-besin", "dinlenme")
               for e in bus.since(0)["events"] if e["kind"] == "reflex"), "çevre olayı yayınlanmadı"

    probe = bs.FlyState(hunger=80.0, boredom=90.0)
    fed = apply_effect(probe, effect_for("besin"), reason="test")
    print("besin etkisi:", fed["action"], fed["delta"], "-> açlık", fed["state"]["hunger"])
    assert fed["state"]["hunger"] == 45.0, fed
    scared = apply_effect(probe, effect_for("tehlike"), reason="test")
    print("tehlike etkisi:", scared["delta"], scared["state"]["flags"],
          scared["state"]["mood"])
    assert scared["state"]["flags"] == ["startled"], scared
    assert scared["state"]["mood"] == "ürkmüş", scared
    quiet = apply_effect(probe, effect_for("açlık"), reason="test")
    print("açlık etkisi (soru):", quiet["delta"], "noop=%s" % quiet["noop"])
    assert quiet["noop"] and quiet["delta"] == {}, quiet
    assert apply_effect(probe, effect_for("yok-böyle-kategori")) is None

    note = classifier_note({"word": "şeker", "category": "besin", "confidence": 0.96,
                            "label": cognitive_matrix.CATEGORY_TR["besin"]},
                           effect_for("besin"), fed, probe)
    print("--- sınıflandırıcı notu ---\n" + note)
    for must in ("SINIFLANDIRICI", "şeker", "besin", "DEĞİŞTİRİLEMEZ", "DURUMUM"):
        assert must in note, "notta eksik: " + must
    print("OK — kategori → vital eşlemesi ve sınıflandırıcı notu doğrulandı")
    print("OK — game_loop self-test geçti")

