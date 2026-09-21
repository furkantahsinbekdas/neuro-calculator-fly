"""
brain_state.py — the cybernetic fly's homeostatic vitals + a thread-safe event bus.

Phase 1 of the Autonomous Cybernetic Fly. Two responsibilities, deliberately kept free
of any LLM / connectome / web dependency so every other module can import them safely:

  * FlyState — Enerji / Açlık / Can sıkıntısı. A background GameLoop degrades these
    every tick; the HTTP threads, the game loop and the LLM executor all read/write it,
    so every access goes through a re-entrant lock.
  * EventBus — an append-only, sequence-numbered JSON event log. The web UI polls it
    with ``?since=<seq>``; nothing ever blocks on a consumer.

Phase 9 note: the fly has no physical body. A recognized message changes the vitals
through :meth:`FlyState.apply_delta` and may raise a short-lived *flag* (``startled``),
which is what the mood and the HUD read.

Event kinds published here and by the rest of the app (all plain JSON):
  state        vitals snapshot            {"energy":..,"hunger":..,"boredom":..,"mood":..}
  say          the fly speaks (Turkish)   {"text": "..."}
  thought      internal monologue         {"text": "..."}
  token        streamed LLM token chunk   {"text": "..."}
  tool_call    a tool was invoked         {"tool": "show3d", "args": {...}}
  tool_result  and its summary            {"tool": "show3d", "result": {...}}
  viz          a new 3D scene             {"data": {...}}
  classifier   mushroom-body decision     {"category": "besin", "word": "şeker",
                                           "confidence": 0.81}   (KC -> readout, Phase 9)
  teach        a word was taught live     {"word": "karpuz", "category": "besin", "steps": 2,
                                           "before": {...}, "after": {...}, "warning": null}
                                           (single delta step + measured regression, Phase 11)
  reflex       effect the chip applied    {"action": "eat", "category": "besin", ...}
  user         echo of a user message     {"text": "..."}
  queued       a job entered the executor {"origin": "autonomous"}
  think_start  the executor picked it up  {"origin": "autonomous"}
  event        an autonomous trigger      {"need": "hunger", "text": "..."}
  mode         autonomy toggled           {"autonomy": true}
  error        something went wrong       {"message": "..."}
"""
from __future__ import annotations

import sys
import threading
import time
from collections import deque
from dataclasses import dataclass

# --------------------------------------------------------------------------- #
# tunables — vitals are 0..100 and move in "minutes", not seconds, by design
# --------------------------------------------------------------------------- #
ENERGY_CRITICAL = 25.0     # below this -> "dinlen" (rest) impulse
HUNGER_CRITICAL = 70.0     # above this -> "beslen" (feed) impulse
BOREDOM_CRITICAL = 70.0    # above this -> "etkileşim kur" (social) impulse

MIN_IDLE_S = 45.0          # boredom only starts climbing after this much silence

ENERGY_DECAY = 0.30        # per second
HUNGER_RISE = 0.45         # per second
BOREDOM_RISE = 0.60        # per second, once idle

# A flag is a short-lived emotional marker that a vital cannot express: a threat makes
# the fly startled for a while without permanently changing its homeostasis.
FLAG_TTL = 20.0            # seconds an unrefreshed flag stays active
FLAG_MOOD = {"startled": "ürkmüş"}      # active flag -> mood override

_LO, _HI = 0.0, 100.0


def _clamp(x, lo=_LO, hi=_HI):
    return max(lo, min(hi, float(x)))


def enable_utf8_console():
    """Make stdout/stderr UTF-8 so Turkish text survives a redirected shell.

    Windows consoles are cp1252 by default whenever output is piped or captured —
    printing 'ı' or 'ğ' then raises UnicodeEncodeError and kills the fly mid-sentence.
    Every entry point (server.py, the self-tests) calls this first.
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:                                   # noqa: BLE001
            pass


@dataclass
class Vitals:
    """The three homeostatic variables the game loop degrades every tick."""
    energy: float = 100.0     # 0..100 — drops with activity, restored by resting/eating
    hunger: float = 0.0       # 0..100 — climbs with time (100 = starving)
    boredom: float = 0.0      # 0..100 — climbs while nobody talks to the fly
    alive: bool = True

    def as_dict(self):
        return {"energy": round(self.energy, 1), "hunger": round(self.hunger, 1),
                "boredom": round(self.boredom, 1), "alive": bool(self.alive)}


class FlyState:
    """Thread-safe homeostatic state.

    One writer (the GameLoop tick) and many readers (HTTP threads, the LLM executor);
    every accessor takes the lock, so nothing is ever read half-updated.
    """

    # what a "life action" chosen by the LLM does to the vitals
    LIFE = {
        "eat":   {"hunger": -35.0, "energy": +8.0, "boredom": -5.0},
        "rest":  {"energy": +25.0, "hunger": +4.0, "boredom": -3.0},
        "play":  {"boredom": -30.0, "energy": -8.0, "hunger": +5.0},
        "groom": {"boredom": -15.0, "energy": -2.0},
    }

    def __init__(self, energy=100.0, hunger=0.0, boredom=0.0, autonomy=True, *,
                 energy_critical=ENERGY_CRITICAL, hunger_critical=HUNGER_CRITICAL,
                 boredom_critical=BOREDOM_CRITICAL, min_idle_s=MIN_IDLE_S,
                 energy_decay=ENERGY_DECAY, hunger_rise=HUNGER_RISE,
                 boredom_rise=BOREDOM_RISE):
        self._v = Vitals(energy=energy, hunger=hunger, boredom=boredom)
        self.lock = threading.RLock()
        self.autonomy = bool(autonomy)
        self.energy_critical = float(energy_critical)
        self.hunger_critical = float(hunger_critical)
        self.boredom_critical = float(boredom_critical)
        self.min_idle_s = float(min_idle_s)
        self.energy_decay = float(energy_decay)
        self.hunger_rise = float(hunger_rise)
        self.boredom_rise = float(boredom_rise)
        self._born = time.time()
        self._last_touch = time.time()
        self._ticks = 0
        self._flags = {}            # name -> expiry timestamp (see FLAG_TTL)

    # ------------------------------------------------------------------ write #
    def tick(self, dt=1.0):
        """Degrade the vitals by ``dt`` seconds. Called by the GameLoop."""
        dt = max(0.0, float(dt))
        with self.lock:
            v = self._v
            v.energy = _clamp(v.energy - self.energy_decay * dt)
            v.hunger = _clamp(v.hunger + self.hunger_rise * dt)
            if (time.time() - self._last_touch) >= self.min_idle_s:
                v.boredom = _clamp(v.boredom + self.boredom_rise * dt)
            self._ticks += 1
            return v

    def touch(self, calm=25.0):
        """Human contact: resets the idle clock and calms boredom a little."""
        with self.lock:
            self._last_touch = time.time()
            self._v.boredom = _clamp(self._v.boredom - float(calm))
            return self.snapshot_locked()

    def apply(self, action, amount=1.0):
        """Run a life action the LLM picked (eat / rest / play / groom)."""
        with self.lock:
            name = str(action).lower().strip()
            delta = self.LIFE.get(name)
            if delta is None:
                return {"ok": False, "action": action, "error": "bilinmeyen eylem",
                        "known": sorted(self.LIFE)}
            amp = _clamp(amount if amount is not None else 1.0, 0.25, 3.0)
            for key, dv in delta.items():
                setattr(self._v, key, _clamp(getattr(self._v, key) + dv * amp))
            return {"ok": True, "action": name, "amount": round(amp, 2),
                    "state": self.snapshot_locked()}

    def apply_delta(self, delta=None, *, flag=None, flag_ttl=FLAG_TTL, action=None):
        """Apply an *explicit* vitals delta — the classifier's decision, not the LLM's.

        ``apply()`` covers the four life actions the model may pick; this is the general
        form the mushroom-body readout needs: ``{"hunger": -35.0}`` for food, or a boredom
        reset plus a ``startled`` flag for an approaching threat. Only energy / hunger /
        boredom are writable and unknown keys are ignored (never raised), so a bad table
        entry can't kill a turn.

        ``delta`` is what actually moved (0..100 clamping included) and ``want`` what the
        table asked for; ``saturated`` lists the keys where the vital was already at its
        limit, so the UI can say "the fly was already full" instead of showing a bogus -35.
        """
        with self.lock:
            applied, want, saturated = {}, {}, []
            for key, dv in (delta or {}).items():
                if key not in self.LIFE["eat"] and key not in ("energy", "hunger",
                                                               "boredom"):
                    continue
                try:
                    dv = float(dv)
                except (TypeError, ValueError):
                    continue
                before = getattr(self._v, key)
                setattr(self._v, key, _clamp(before + dv))
                after = getattr(self._v, key)
                applied[key] = round(after - before, 2)
                want[key] = round(dv, 2)
                if abs(after - before) < abs(dv) - 1e-9:
                    saturated.append(key)
            if flag:
                self._set_flag_locked(flag, flag_ttl)
            return {"ok": True, "action": action or "delta", "delta": applied,
                    "want": want, "saturated": sorted(saturated),
                    "flag": (str(flag) if flag else None),
                    "state": self.snapshot_locked()}

    def set_flag(self, name, ttl=FLAG_TTL):
        """Raise a temporary emotional marker (``startled``) and refresh its timer."""
        with self.lock:
            self._set_flag_locked(name, ttl)
            return self.snapshot_locked()

    def clear_flag(self, name):
        with self.lock:
            self._flags.pop(str(name), None)
            return self.snapshot_locked()

    def set_autonomy(self, on):
        with self.lock:
            self.autonomy = bool(on)
            return self.autonomy

    def reset(self, energy=100.0, hunger=0.0, boredom=0.0):
        with self.lock:
            self._v.energy = _clamp(energy)
            self._v.hunger = _clamp(hunger)
            self._v.boredom = _clamp(boredom)
            self._v.alive = True
            self._last_touch = time.time()
            return self.snapshot_locked()

    # ------------------------------------------------------------------- read #
    def idle_seconds(self):
        with self.lock:
            return time.time() - self._last_touch

    def _set_flag_locked(self, name, ttl=FLAG_TTL):
        try:
            ttl = max(0.0, float(ttl))
        except (TypeError, ValueError):
            ttl = FLAG_TTL
        if ttl <= 0.0:
            self._flags.pop(str(name), None)
        else:
            self._flags[str(name)] = time.time() + ttl
        return sorted(self._flags)

    def flags_locked(self):
        """Active flag names, expired ones pruned (call with the lock held)."""
        now = time.time()
        for name in [n for n, exp in self._flags.items() if exp <= now]:
            self._flags.pop(name, None)
        return sorted(self._flags)

    def flags(self):
        with self.lock:
            return self.flags_locked()

    def mood_locked(self):
        v = self._v
        if not v.alive:
            return "bitkin"
        for name in self.flags_locked():
            override = FLAG_MOOD.get(name)
            if override:
                return override
        if v.hunger >= self.hunger_critical:
            return "aç"
        if v.energy <= self.energy_critical:
            return "yorgun"
        if v.boredom >= self.boredom_critical:
            return "sıkılmış"
        if v.energy >= 80.0 and v.hunger <= 25.0:
            return "keyifli"
        return "sakin"

    def snapshot_locked(self):
        d = self._v.as_dict()
        d.update({"mood": self.mood_locked(), "autonomy": self.autonomy,
                  "flags": self.flags_locked(),
                  "idle_s": round(time.time() - self._last_touch, 1),
                  "uptime_s": round(time.time() - self._born, 1), "ticks": self._ticks})
        return d

    def snapshot(self):
        with self.lock:
            return self.snapshot_locked()

    def needs(self):
        """Currently-firing needs, most urgent first (priority 1 = most urgent)."""
        with self.lock:
            v = self._v
            out = []
            if v.hunger >= self.hunger_critical:
                out.append({"need": "hunger", "label": "açlık", "priority": 1,
                            "level": v.hunger})
            if v.energy <= self.energy_critical:
                out.append({"need": "energy", "label": "enerji", "priority": 2,
                            "level": v.energy})
            if v.boredom >= self.boredom_critical:
                out.append({"need": "boredom", "label": "can sıkıntısı", "priority": 3,
                            "level": v.boredom})
            out.sort(key=lambda n: n["priority"])
            return out

    def top_need(self):
        n = self.needs()
        return n[0] if n else None

    def status_line(self):
        """The line injected into every LLM prompt so the fly knows its own body."""
        with self.lock:
            v = self._v
            idle = time.time() - self._last_touch
            who = ("kullanıcı az önce konuştu" if idle < 30.0
                   else "kullanıcı %.0f saniyedir sessiz" % idle)
            return ("DURUMUM: enerji=%.0f/100, açlık=%.0f/100, can sıkıntısı=%.0f/100, "
                    "ruh halim=%s, %s." % (v.energy, v.hunger, v.boredom,
                                           self.mood_locked(), who))


class EventBus:
    """Append-only, sequence-numbered JSON event log with a bounded history.

    Producers (game loop, LLM executor, HTTP handlers) call :meth:`publish` and never
    block. Consumers (the browser) call :meth:`since` with the last
    sequence number they saw — the classic poll pattern, so a slow or absent consumer
    can never stall the fly. :meth:`wait_for` is there if we ever want long-polling.
    """

    def __init__(self, maxlen=2000):
        self._lock = threading.Lock()
        self._cond = threading.Condition(self._lock)
        self._events = deque(maxlen=int(maxlen))
        self._seq = 0
        self.dropped = 0

    def publish(self, kind, payload=None, **fields):
        body = dict(payload) if payload else {}
        body.update(fields)
        body.pop("seq", None)
        body.pop("kind", None)
        with self._cond:
            self._seq += 1
            ev = {"seq": self._seq, "t": round(time.time(), 3), "kind": str(kind)}
            ev.update(body)
            if len(self._events) == self._events.maxlen:
                self.dropped += 1
            self._events.append(ev)
            self._cond.notify_all()
            return self._seq

    def since(self, seq=0, limit=300, kinds=None):
        """Every event newer than ``seq`` (oldest first), optionally filtered by kind."""
        try:
            seq = int(seq)
        except (TypeError, ValueError):
            seq = 0
        with self._lock:
            out = [e for e in self._events if e["seq"] > seq]
            last = self._seq
        if kinds:
            wanted = {str(k) for k in kinds}
            out = [e for e in out if e["kind"] in wanted]
        limit = max(1, int(limit or 300))
        return {"events": out[:limit], "seq": last, "truncated": len(out) > limit}

    def wait_for(self, seq, timeout=25.0):
        """Block until something newer than ``seq`` exists (or the timeout expires)."""
        deadline = time.monotonic() + max(0.0, float(timeout))
        with self._cond:
            while self._seq <= int(seq):
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                self._cond.wait(remaining)
            return self._seq

    def last_seq(self):
        with self._lock:
            return self._seq

    def size(self):
        """Buffered event count.

        Deliberately NOT ``__len__``: a container-like truthiness would make an empty
        bus falsy, so ``if bus: bus.publish(...)`` would silently drop every event
        until something else filled it. Use ``size()`` / ``status()`` instead.
        """
        with self._lock:
            return len(self._events)

    def status(self):
        with self._lock:
            return {"seq": self._seq, "buffered": len(self._events),
                    "maxlen": self._events.maxlen, "dropped": self.dropped}


# --------------------------------------------------------------------------- #
# smoke test — no connectome, no LLM, no server required
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    st = FlyState()
    st.energy_decay = 20.0      # crank the rates so the demo finishes in a second
    st.hunger_rise = 30.0
    st.boredom_rise = 30.0
    st.min_idle_s = 0.0
    print("ilk durum:", st.status_line())
    for _ in range(6):
        st.tick(1.0)
    print("6 tick sonra:", st.status_line())
    print("ihtiyaçlar:", st.needs())
    print("beslen:", st.apply("eat", 2.0)["state"])
    print("dokunma:", st.touch())

    # Phase 9: the classifier path — an explicit vitals delta + the startled flag
    st.reset(hunger=60.0, boredom=90.0)
    fed = st.apply_delta({"hunger": -35.0, "energy": +8.0}, action="besin")
    print("sınıflandırıcı (besin):", fed["delta"], "-> açlık", fed["state"]["hunger"])
    assert fed["state"]["hunger"] == 25.0, fed
    scared = st.apply_delta({"boredom": -90.0}, flag="startled", flag_ttl=5.0,
                            action="tehlike")
    print("sınıflandırıcı (tehlike):", scared["state"]["flags"],
          scared["state"]["mood"], scared["delta"])
    assert scared["state"]["flags"] == ["startled"], scared
    assert scared["state"]["mood"] == "ürkmüş", scared
    assert scared["state"]["boredom"] == 0.0, scared
    st.clear_flag("startled")
    assert st.flags() == [], st.flags()
    print("(bilinmeyen anahtar sessizce yok sayılır):",
          st.apply_delta({"kilo": 3.0})["delta"])

    bus = EventBus(maxlen=10)
    for i in range(3):
        bus.publish("state", payload={"state": {"tick": i}})
    page = bus.since(1)
    print("bus:", bus.status(), "->", [(e["seq"], e["kind"]) for e in page["events"]])
    assert [e["seq"] for e in page["events"]] == [2, 3], "since() filtrelemesi bozuk"
    assert bus.since(3)["events"] == []
    print("OK — brain_state self-test geçti")

