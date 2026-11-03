"""Model registry: champion and challenger per source, promotion by gate, and the fit command.

``models/registry.json`` holds, per source::

    {"<source>": {"champion": id, "challenger": id or null,
                  "summaries": {id: {"brier_skill", "n", ...}}, "history": [events]}}

The first model registered for a source becomes the champion; every later one becomes the challenger. A
backtest summary is the model's Brier skill against the base rate on the rows scored in its backtest and
the number of those rows. Writes are atomic (a temporary file in the same directory, then ``os.replace``), so
a concurrent reader sees the old file or the new one, never a partial file. There is no cross-process lock:
the registry is written by one operator at a time (builder call 34).

Champion refresh (round 00, docs/method.md call 165). A bundle fit with the champion's METHOD (the same ``method_id``, a hash of the method
version and the fixed hyperparameters, never of the data) on a newer fit time is the same method on newer data. ``register_model`` makes
it the champion directly, without the challenger margin, after a no-regression check: it is refused (and the bundle becomes the
challenger, with the reason in the history) only when its backtest Brier skill interval lies entirely below the champion's. A bundle with
a different ``method_id`` is a different method and is a challenger that needs the margin below. Without this split a method with skill
near zero could never replace a champion that is merely older.

Promotion rule (``promote``, for a different method): the challenger replaces the champion only when its Brier skill beats the
champion's by at least the margin (default ``config.PROMOTION_MARGIN``, 0.02 in Brier skill) and its
backtest row count reaches the gate for its own skill: ``n_200`` when the challenger's skill is at least
0.20, otherwise ``n_400``, both read from gates.json. Otherwise the reason says which condition failed and by
how much; the champion changes only on promotion.

Units: Brier skill is unitless; ``n`` is a count of scored rows.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from mootcourt.config import PROMOTION_MARGIN
from mootcourt.storage import visible_glob

SKILL_FOR_N_200 = 0.20
_EPS = 1e-9


@dataclass(frozen=True)
class PromotionResult:
    """Outcome of ``Registry.promote``: whether the champion changed and why or why not."""

    promoted: bool
    reason: str
    champion: str | None = None
    challenger: str | None = None


class Registry:
    """The registry file of a models directory."""

    def __init__(self, models_dir):
        self.models_dir = Path(models_dir)
        self.path = self.models_dir / "registry.json"

    # ---------------------------------------------------------------- io
    def _read(self) -> dict:
        if not self.path.exists():
            return {}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _write(self, doc: dict) -> None:
        self.models_dir.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=self.models_dir, prefix=".registry-", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(doc, fh, indent=1, sort_keys=True)
                fh.write("\n")
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp, self.path)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)

    @staticmethod
    def _entry(doc: dict, source: str) -> dict:
        return doc.setdefault(source, {"champion": None, "challenger": None, "summaries": {}, "history": []})

    @staticmethod
    def _log(entry: dict, event: str, now: dt.datetime | None, **fields) -> None:
        entry["history"].append({"at": (now or dt.datetime.now(dt.timezone.utc)).isoformat(), "event": event, **fields})

    # ------------------------------------------------------------ queries
    def sources(self) -> list[str]:
        """Sources that have a registry entry."""
        return sorted(self._read())

    def get_champion(self, source: str) -> str:
        """Model id of the champion; KeyError when the source has none."""
        champ = self._read().get(source, {}).get("champion")
        if not champ:
            raise KeyError(f"no champion registered for source {source}")
        return champ

    def get_challenger(self, source: str) -> str | None:
        """Model id of the challenger, or None."""
        return self._read().get(source, {}).get("challenger")

    def summary(self, source: str, model_id: str) -> dict | None:
        """Backtest summary stored for a model, or None."""
        return self._read().get(source, {}).get("summaries", {}).get(model_id)

    def get_second_opinion(self, source: str, provider_id: str, version: str | None = None) -> dict | None:
        """The stored weight record of a provider that is in force, or None.

        A record is in force only for the version it was earned for (``version`` None skips that check, for listings)
        and only while the champion it was stacked on is still the champion: a refit or a promotion changes
        ``p_sig``, so the weight has to be earned again.
        """
        entry = self._read().get(source, {})
        rec = entry.get("second_opinion", {}).get(provider_id)
        if not rec:
            return None
        if version is not None and str(rec.get("version")) != str(version):
            return None
        stacked_on = rec.get("champion")
        if stacked_on is not None and stacked_on != entry.get("champion"):
            return None
        return rec

    def get_second_opinion_weight(self, source: str, provider_id: str, version: str | None = None) -> float:
        """The stacking weight in force for a provider version on a source; 0.0 until that version earns one."""
        rec = self.get_second_opinion(source, provider_id, version)
        return float(rec["weight"]) if rec else 0.0

    def second_opinion_history(self, source: str) -> list[dict]:
        """Records of earlier provider versions that a newer version displaced, oldest first."""
        return list(self._read().get(source, {}).get("second_opinion_history", []))

    def second_opinion(self, source: str) -> dict:
        """Stored second-opinion records of a source, keyed by provider id."""
        return dict(self._read().get(source, {}).get("second_opinion", {}))

    # ------------------------------------------------------------- writes
    def set_second_opinion_weight(self, source: str, provider_id: str, version: str, weight: float, evidence: dict,
                                  now: dt.datetime | None = None, contaminated: bool = False) -> None:
        """Store the earned weight of a provider version. Only ``moot earn-weight`` calls this, after the gate and margin are met.

        The record keeps the champion the weight was stacked on and ``contaminated``, true when origins before the
        provider's knowledge cutoff (or any origin, when no cutoff is declared) were used to earn it.

        Raises KeyError when the source has no registered model and ValueError when the weight is outside [0, 1].
        """
        if not 0.0 <= float(weight) <= 1.0:
            raise ValueError("weight must be in [0, 1]")
        doc = self._read()
        if source not in doc:
            raise KeyError(f"no model is registered for source {source}")
        e = doc[source]
        old = e.setdefault("second_opinion", {}).get(provider_id)
        if old and str(old.get("version")) != str(version):          # a new version displaces the record, which stays in the audit trail (REV-046)
            e.setdefault("second_opinion_history", []).append({"provider_id": provider_id, **old})
        e.setdefault("second_opinion", {})[provider_id] = {"version": version, "weight": float(weight), "evidence": evidence,
                                                          "champion": e.get("champion"), "contaminated": bool(contaminated),
                                                          "at": (now or dt.datetime.now(dt.timezone.utc)).isoformat()}
        self._log(e, "second_opinion_weight", now, provider_id=provider_id, version=version, weight=float(weight), contaminated=bool(contaminated))
        self._write(doc)

    def register_model(self, source: str, model_id: str, backtest_summary: dict | None = None, now: dt.datetime | None = None,
                       method_id: str | None = None, fitted_at: str | None = None) -> str:
        """Register a fitted model. Returns ``"champion"`` or ``"challenger"``, the role it holds afterwards.

        The first model of a source becomes the champion. A later model with the champion's ``method_id`` and a newer ``fitted_at`` is
        a refresh and becomes the champion (see the module docstring); any other later model becomes the challenger (replacing any
        earlier challenger) unless it already is the champion or the challenger, in which case only its summary is refreshed.
        """
        doc = self._read()
        e = self._entry(doc, source)
        if backtest_summary is not None:
            e["summaries"][model_id] = backtest_summary
        if method_id is not None:
            e.setdefault("methods", {})[model_id] = method_id
        if fitted_at is not None:
            e.setdefault("fitted_at", {})[model_id] = fitted_at
        if e["champion"] is None:
            e["champion"] = model_id
            role = "champion"
            self._log(e, "champion_set", now, model_id=model_id)
        elif e["champion"] == model_id:
            role = "champion"
        elif self._is_refresh(e, model_id):
            old = e["champion"]
            e["champion"] = model_id
            if e.get("challenger") == model_id:
                e["challenger"] = None
            role = "champion"
            self._log(e, "champion_refreshed", now, model_id=model_id, replaced=old, method_id=method_id)
        else:
            if e["challenger"] != model_id:
                self._log(e, "challenger_set", now, model_id=model_id)
            e["challenger"] = model_id
            role = "challenger"
        self._write(doc)
        return role

    @staticmethod
    def _is_refresh(e: dict, model_id: str) -> bool:
        """True when ``model_id`` is the champion's method on a newer fit and its backtest is not clearly worse than the champion's."""
        champ = e["champion"]
        methods, fitted = e.get("methods", {}), e.get("fitted_at", {})
        mid = methods.get(model_id)
        if not mid or methods.get(champ) != mid:
            return False
        new_t, old_t = fitted.get(model_id), fitted.get(champ)
        if not new_t or not old_t or dt.datetime.fromisoformat(new_t) <= dt.datetime.fromisoformat(old_t):
            return False
        s_new, s_old = e["summaries"].get(model_id) or {}, e["summaries"].get(champ) or {}
        if s_new.get("brier_skill_hi") is not None and s_old.get("brier_skill_lo") is not None and s_new["brier_skill_hi"] < s_old["brier_skill_lo"]:
            return False            # clearly worse on the backtest: not a refresh, a challenger
        return True

    def set_challenger(self, source: str, model_id: str, now: dt.datetime | None = None) -> None:
        """Name the challenger of a source."""
        doc = self._read()
        e = self._entry(doc, source)
        e["challenger"] = model_id
        self._log(e, "challenger_set", now, model_id=model_id)
        self._write(doc)

    def attach_summary(self, source: str, model_id: str, summary: dict) -> None:
        """Store or replace a model's backtest summary."""
        doc = self._read()
        self._entry(doc, source)["summaries"][model_id] = summary
        self._write(doc)

    def promote(self, source: str, gates: dict, margin: float = PROMOTION_MARGIN, now: dt.datetime | None = None) -> PromotionResult:
        """Promote the challenger when it clears the margin and the gate; see the module docstring."""
        doc = self._read()
        e = doc.get(source)
        champ = e.get("champion") if e else None
        chall = e.get("challenger") if e else None
        if not champ:
            return PromotionResult(False, f"no champion is registered for source {source}")
        if not chall:
            return PromotionResult(False, "no challenger is registered, nothing to promote", champ, None)
        s_ch, s_cp = e["summaries"].get(chall), e["summaries"].get(champ)
        if not s_ch or s_ch.get("brier_skill") is None:
            return PromotionResult(False, f"no backtest summary for the challenger {chall}; run `moot backtest` then `moot fit`", champ, chall)
        if not s_cp or s_cp.get("brier_skill") is None:
            return PromotionResult(False, f"no backtest summary for the champion {champ}; run `moot backtest` then `moot fit`", champ, chall)
        gain = float(s_ch["brier_skill"]) - float(s_cp["brier_skill"])
        n_need = gates["n_200"] if float(s_ch["brier_skill"]) >= SKILL_FOR_N_200 else gates["n_400"]
        # The gate counts tests, not rows (REV-007, call 83): rows of one test share an arm and are not independent. A summary
        # written before the test count was stored falls back to its row count.
        n_have = int(s_ch["n_tests"] if s_ch.get("n_tests") is not None else s_ch.get("n", 0))
        unit = "tests" if s_ch.get("n_tests") is not None else "rows"
        problems = []
        if gain + _EPS < margin:
            problems.append(f"Brier skill gain {gain:.4f} is short by {margin - gain:.4f} of the margin {margin:.4f}")
        if n_have < n_need:
            problems.append(f"the challenger's backtest has {n_have} {unit}, below gate n = {n_need} tests for its skill")
        if problems:
            return PromotionResult(False, "; ".join(problems), champ, chall)
        e["champion"], e["challenger"] = chall, None
        self._log(e, "promoted", now, model_id=chall, replaced=champ, brier_skill_gain=gain, n=n_have, gate_n=n_need, margin=margin)
        self._write(doc)
        return PromotionResult(True, f"promoted {chall} over {champ}: Brier skill gain {gain:.4f} at n = {n_have} (gate n = {n_need})", chall, None)


def backtest_summary(report: dict, report_name: str) -> dict:
    """Headline backtest summary of the card rung from a backtest report document (the ``ALL`` cell of P2).

    Falls back to the last rung when there is no P2. Holds the Brier skill with its interval, the scored row
    count, the log score and the report file name.
    """
    rows = report["tables"]["aggregate"]
    rungs = sorted({r["rung"] for r in rows})
    rung = "P2" if "P2" in rungs else rungs[-1]
    r = next(x for x in rows if x["cell"] == "ALL" and x["rung"] == rung)
    return {"snapshot_id": report["header"]["snapshot_id"], "rung": rung, "brier_skill": r["brier_skill"],
            "brier_skill_lo": r["brier_skill_lo"], "brier_skill_hi": r["brier_skill_hi"], "n": r["n"],
            "n_tests": r.get("n_tests"), "logscore": r["logscore"],
            "report": report_name}


def find_backtest(reports_dir, source: str, snapshot_id: str) -> tuple[dict, str] | None:
    """The backtest report document for a source and snapshot, with its file name, or None."""
    path = Path(reports_dir) / f"backtest-{source}-{snapshot_id}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8")), path.name


def find_scores(reports_dir, source: str, snapshot_id: str) -> Path | None:
    """The per-row score table of the main backtest at a snapshot (``scores-<source>-<snapshot>.parquet``), or None.

    Looked up by the snapshot id, never by modification time: a stale table that happens to be newer must not be used.
    """
    path = Path(reports_dir) / f"scores-{source}-{snapshot_id}.parquet"
    return path if path.is_file() else None


def fit_command(source: str, df, ledger_dir, models_dir, reports_dir) -> tuple[str, str, str, dict | None]:
    """Fit the bundle at the current snapshot, save it and register it.

    Returns ``(model_id, snapshot_id, role, summary)``; ``summary`` is None when no backtest exists for the
    snapshot (the manifest slot stays empty and the message says so).
    """
    from mootcourt.bundle import fit_bundle, save_bundle
    from mootcourt.ledger import ensure_snapshot

    sid = ensure_snapshot(df, ledger_dir)
    bundle = fit_bundle(df, source, sid)
    found = find_backtest(reports_dir, source, sid)
    summary = backtest_summary(*found) if found else None
    bundle.backtest_summary = summary
    save_bundle(bundle, models_dir)
    role = Registry(models_dir).register_model(
        source, bundle.model_id, summary, method_id=bundle.method_id or None, fitted_at=bundle.fit_time or None
    )
    return bundle.model_id, sid, role, summary


def attach_backtest(models_dir, source: str, snapshot_id: str, report: dict, report_name: str) -> list[str]:
    """After a backtest, fill the summary slot of every registered bundle fitted at that snapshot.

    Updates the registry and each bundle's manifest (the manifest checksums cover the artifacts, not the
    manifest, so the slot can be filled later). Returns the model ids updated.
    """
    from mootcourt.bundle import bundle_dir

    reg = Registry(models_dir)
    summary = backtest_summary(report, report_name)
    updated = []
    for manifest in visible_glob(models_dir, "*/manifest.json"):
        m = json.loads(manifest.read_text(encoding="utf-8"))
        if m.get("source") != source or m.get("snapshot_id") != snapshot_id:
            continue
        m["backtest_summary"] = summary
        tmp = manifest.with_name(".manifest.json.tmp")         # dot-prefixed: a crash leaves a file the bundle loader ignores
        tmp.write_text(json.dumps(m, indent=1, sort_keys=True), encoding="utf-8")
        os.replace(tmp, bundle_dir(m["model_id"], models_dir) / "manifest.json")
        if source in reg.sources():
            reg.attach_summary(source, m["model_id"], summary)
        updated.append(m["model_id"])
    return updated
