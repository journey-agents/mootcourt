"""Model registry: champion and challenger per source, promotion by gate, and the fit command.

``models/registry.json`` holds, per source::

    {"<source>": {"champion": id, "challenger": id or null,
                  "summaries": {id: {"brier_skill", "n", ...}}, "history": [events]}}

The first model registered for a source becomes the champion; every later one becomes the challenger. A
backtest summary is the model's Brier skill against the base rate on the rows scored in its backtest and
the number of those rows. Writes are atomic (a temporary file in the same directory, then ``os.replace``), so
a concurrent reader sees the old file or the new one, never a partial file. There is no cross-process lock:
the registry is written by one operator at a time (builder call 34).

Champion refresh (round 00, docs/method.md call 165; review L tightened it). A bundle fit with the champion's METHOD (the same ``method_id``, a
hash of the method version and the fixed hyperparameters, never of the data) on strictly newer data (``data_through``, the latest result the fit
saw; the fit time only breaks a tie) is the same method on newer data. ``register_model`` makes it the champion without the challenger margin,
after a no-regression check on its backtest: refused (it becomes the challenger and the history says why) when its Brier skill interval lies
entirely below the champion's. A same-method fit with no backtest summary yet is a pending refresh, held as the challenger, and the check runs
when the summary is attached. A bundle with a different ``method_id`` is a different method and needs the margin below.

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

    def pending_refresh(self, source: str) -> str | None:
        """The model id held as a pending refresh of the champion (a same-method fit waiting for its backtest), or None."""
        e = self._read().get(source)
        return e.get("pending_refresh") if e else None

    def register_model(self, source: str, model_id: str, backtest_summary: dict | None = None, now: dt.datetime | None = None,
                       method_id: str | None = None, fitted_at: str | None = None, data_through: str | None = None) -> str:
        """Register a fitted model. Returns ``"champion"`` or ``"challenger"``, the role it holds afterwards.

        The first model of a source becomes the champion. A later model is a refresh of the champion, and becomes the champion, only when
        it has the champion's ``method_id``, was fit on strictly newer data (``data_through``, the latest result it saw; ``fitted_at`` is only
        the tie breaker when that is equal) and its backtest is not clearly worse (``decide_refresh``). A same-method fit that has no backtest
        summary yet is held as a pending refresh (a challenger) until the summary is attached, where the check runs. Any other later model
        becomes the challenger (replacing any earlier challenger), and the history says why. A model that already is the champion or the
        challenger only has its summary refreshed.
        """
        doc = self._read()
        e = self._entry(doc, source)
        if backtest_summary is not None:
            e["summaries"][model_id] = backtest_summary
        for key, value in (("methods", method_id), ("fitted_at", fitted_at), ("data_through", data_through)):
            if value is not None:
                e.setdefault(key, {})[model_id] = value
        if e["champion"] is None:
            e["champion"] = model_id
            role = "champion"
            self._log(e, "champion_set", now, model_id=model_id)
        elif e["champion"] == model_id:
            role = "champion"
        else:
            self._derive_through(e, e["champion"], now)
            verdict, reason = self.decide_refresh(e, model_id)
            if verdict == "refresh":
                self._refresh(e, model_id, now, reason)
                role = "champion"
            else:
                if e["challenger"] != model_id:
                    self._log(e, "challenger_set", now, model_id=model_id, method_id=method_id, reason=reason)
                e["challenger"] = model_id
                if verdict == "pending":
                    e["pending_refresh"] = model_id
                role = "challenger"
        self._write(doc)
        return role

    def _refresh(self, e: dict, model_id: str, now, reason: str) -> None:
        old = e["champion"]
        e["champion"] = model_id
        if e.get("challenger") == model_id:
            e["challenger"] = None
        if e.get("pending_refresh") == model_id:
            e["pending_refresh"] = None
        self._log(e, "champion_refreshed", now, model_id=model_id, replaced=old, method_id=e.get("methods", {}).get(model_id), reason=reason)

    def _derive_through(self, e: dict, model_id: str, now) -> None:
        """Fill a missing ``data_through`` of a registered model from its bundle (the fit cutoff), and log that the value was derived.

        A registry written before the field existed has none for its champion, and without it no refresh could ever be decided (REV-N-003).
        A bundle that cannot be read leaves the field missing, and the decision then says the recency is unknown."""
        if e.get("data_through", {}).get(model_id):
            return
        from mootcourt.bundle import load_bundle

        try:
            cutoff = load_bundle(model_id, self.models_dir).fit_cutoff
        except Exception:
            return
        if cutoff is None:
            return
        e.setdefault("data_through", {})[model_id] = cutoff.isoformat()
        self._log(e, "data_through_derived", now, model_id=model_id, data_through=cutoff.isoformat(),
                  reason="read from the bundle's fit cutoff; the registry predates the field")

    @staticmethod
    def decide_refresh(e: dict, model_id: str) -> tuple[str, str]:
        """``(verdict, reason)`` for a model against the champion: ``refresh``, ``pending`` (no backtest summary yet) or ``no``.

        A refresh needs the champion's method, strictly newer data and a backtest whose Brier skill interval does not lie entirely below the
        champion's. Unknown data recency counts as not newer: a refit of an older snapshot has a new fit time and must not take the champion back.
        """
        champ = e["champion"]
        methods, fitted, through = e.get("methods", {}), e.get("fitted_at", {}), e.get("data_through", {})
        mid = methods.get(model_id)
        if not mid or methods.get(champ) != mid:
            return "no", "a different method (or an unknown one): it needs the promotion margin"
        new_d, old_d = through.get(model_id), through.get(champ)
        if not new_d or not old_d:
            return "no", "the recency of its data or the champion's is unknown, so it is not shown to be newer"
        d_new, d_old = dt.datetime.fromisoformat(new_d), dt.datetime.fromisoformat(old_d)
        if d_new < d_old:
            return "no", "fit on older data than the champion"
        if d_new == d_old:
            f_new, f_old = fitted.get(model_id), fitted.get(champ)
            if not f_new or not f_old or dt.datetime.fromisoformat(f_new) <= dt.datetime.fromisoformat(f_old):
                return "no", "fit on the same data as the champion and not later"
        s_new, s_old = e["summaries"].get(model_id) or {}, e["summaries"].get(champ) or {}
        if s_new.get("brier_skill_hi") is None:
            return "pending", "a refresh is pending: the backtest summary of this fit is not attached yet, and the no-regression check needs it"
        if s_old.get("brier_skill_lo") is not None and s_new["brier_skill_hi"] < s_old["brier_skill_lo"]:
            return "no", "refresh refused: its backtest Brier skill interval lies entirely below the champion's"
        return "refresh", "same method on strictly newer data, backtest not clearly worse"

    def set_challenger(self, source: str, model_id: str, now: dt.datetime | None = None) -> None:
        """Name the challenger of a source."""
        doc = self._read()
        e = self._entry(doc, source)
        e["challenger"] = model_id
        self._log(e, "challenger_set", now, model_id=model_id)
        self._write(doc)

    def attach_summary(self, source: str, model_id: str, summary: dict, now: dt.datetime | None = None) -> None:
        """Store or replace a model's backtest summary. A pending refresh of this model is decided now (the no-regression check)."""
        doc = self._read()
        e = self._entry(doc, source)
        e["summaries"][model_id] = summary
        if e.get("pending_refresh") == model_id and e.get("champion") not in (None, model_id):
            self._derive_through(e, e["champion"], now)
            verdict, reason = self.decide_refresh(e, model_id)
            if verdict == "refresh":
                self._refresh(e, model_id, now, reason + " (decided when the backtest summary was attached)")
            elif verdict == "no":
                e["pending_refresh"] = None
                self._log(e, "refresh_refused", now, model_id=model_id, reason=reason)
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
        source, bundle.model_id, summary, method_id=bundle.method_id or None, fitted_at=bundle.fit_time or None,
        data_through=bundle.fit_cutoff.isoformat() if bundle.fit_cutoff is not None else None,
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
