"""Synthetic pilot records only; no human observations or benchmark gold."""
from copy import deepcopy
import csv
import json
import os
import pty
import subprocess
import sys

import pytest

from scripts import user_pilot as pilot


def ready():
    return {
        "run_mode": "live", "build_id": "synthetic-test-build",
        "qa_evidence": "synthetic-test-evidence", "qa_passed": True,
        "supports_all_tasks": True, "answer_key_reviewed": True,
        "review_basis": "SYNTHETIC TEST, not a human review",
        "answers": {f"P{i}": {"accepted_actions": ["official_channel"],
                                "rationale": "Synthetic test rubric"} for i in range(1, 5)},
    }


def workspace(tmp_path):
    return pilot.initialize(tmp_path / "synthetic", ready(), kind="synthetic")


class Form:
    def __init__(self, answers, timeout_at=None):
        self.answers = iter(answers)
        self.now = 0.0
        self.calls = 0
        self.timeout_at = timeout_at

    def clock(self):
        return self.now

    def ask(self, prompt, timeout=None):
        self.calls += 1
        if self.calls == self.timeout_at:
            self.now += timeout
            return None
        self.now += 1
        return next(self.answers)


def responses(count=4):
    # consent; timed task/neutral notes; label debrief only after all primary tasks.
    return ["yes"] + [value for _ in range(count) for value in
                       ["start", "official_channel", "snapshot quote", "1", "disagree"]] + ["supported", "bounded_support"] * 2


def test_allocation_and_negative_controls():
    tasks, rows = pilot.materials()
    assert pilot.validate_allocation(tasks, rows) == {"planned_people": 12, "planned_trials": 48}
    for change in ("duplicate", "family", "condition", "order"):
        bad = deepcopy(rows)
        if change == "duplicate":
            bad.append(bad[0])
        else:
            bad[0][{"family": "family_id", "condition": "condition", "order": "order"}[change]] = "wrong"
        with pytest.raises(ValueError):
            pilot.validate_allocation(tasks, bad)


def test_readiness_and_storage_fail_closed(tmp_path):
    for field in ("qa_passed", "supports_all_tasks", "answer_key_reviewed"):
        gate = ready(); gate[field] = False
        with pytest.raises(ValueError, match="readiness"):
            pilot.initialize(tmp_path / field, gate, kind="synthetic")
    gate = ready(); gate["run_mode"] = "fixture"
    with pytest.raises(ValueError, match="fixture"):
        pilot.initialize(tmp_path / "fixture", gate, kind="synthetic")
    gate = ready(); gate["answers"]["P1"]["accepted_actions"] = ["invented"]
    with pytest.raises(ValueError):
        pilot.initialize(tmp_path / "bad-key", gate, kind="synthetic")
    with pytest.raises(ValueError, match="private"):
        pilot.initialize(tmp_path / "real", ready(), kind="real")
    work = workspace(tmp_path)
    with pytest.raises(FileExistsError):
        pilot.initialize(work, ready(), kind="synthetic")
    manifest = json.loads((work / "manifest.json").read_text())
    manifest["tasks"][0]["input_text"] = "changed"
    (work / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="hash"):
        pilot.summarize(work)


def test_same_form_collects_private_csv_and_paired_summary(tmp_path):
    work = workspace(tmp_path)
    form = Form(responses())
    pilot.collect(work, "U01", ask=form.ask, clock=form.clock, show=lambda _: None)
    result = pilot.summarize(work)
    assert result["actual_real_participants"] == 0
    assert result["consented"] == result["paired_people"] == 1
    assert result["observed_trials"] == result["completed_trials"] == 4
    assert result["median_person_action_delta_tinchac_minus_manual"] == 0
    assert result["label_understanding"]["correct"] == 2
    assert "disagree" not in json.dumps(result)
    with (work / "user_pilot.csv").open() as f:
        rows = list(csv.DictReader(f))
    assert list(rows[0]) == pilot.CSV_FIELDS
    assert rows[0]["case_id"].startswith("T09_dev_")
    assert rows[0]["comments"] == "disagree"
    with pytest.raises(ValueError, match="already"):
        pilot.collect(work, "U01", ask=form.ask, clock=form.clock)


def test_timeout_is_retained_and_partial_person_not_paired(tmp_path):
    work = workspace(tmp_path)
    # Deadline on action in first trial, then stop before the next trial.
    form = Form(["yes", "start", "0", "timeout opinion", "stop"], timeout_at=3)
    pilot.collect(work, "U01", ask=form.ask, clock=form.clock, show=lambda _: None)
    summary = pilot.summarize(work)
    assert summary["observed_trials"] == summary["timeouts"] == 1
    assert summary["completed_trials"] == summary["paired_people"] == 0
    assert summary["conditions"]["manual"]["duration_denominator"] == 1
    assert summary["conditions"]["manual"]["action_rate"] == 0
    records = pilot.load_sessions(work)
    assert records[0]["trials"][0]["duration"] == 180
    assert records[0]["trials"][0]["status"] == "timeout"


def test_refusal_stop_and_withdrawal(tmp_path):
    work = workspace(tmp_path)
    pilot.collect(work, "U01", ask=lambda *_: "no", show=lambda _: None)
    assert pilot.summarize(work)["consented"] == 0
    form = Form(["yes", "start", "stop"])
    pilot.collect(work, "U02", ask=form.ask, clock=form.clock, show=lambda _: None)
    assert pilot.summarize(work)["stopped_people"] == 1
    assert pilot.summarize(work)["observed_trials"] == 1
    pilot.withdraw(work, "U02")
    assert pilot.summarize(work)["withdrawn"] == 1
    assert pilot.summarize(work)["observed_trials"] == 0
    assert list(csv.DictReader((work / "user_pilot.csv").open())) == []
    tombstone = json.loads((work / "sessions/U02.json").read_text())
    assert tombstone == {"participant_id": "U02", "state": "withdrawn", "trials": []}


def test_full_rehearsal_is_not_real_data(tmp_path):
    work = tmp_path / "synthetic"
    summary = pilot.rehearse(work)
    assert summary["kind"] == "synthetic"
    assert summary["actual_real_participants"] == 0
    assert summary["consented"] == summary["paired_people"] == 12
    assert summary["observed_trials"] == 48
    assert summary["timeouts"] > 0


def test_nonfinite_duration_or_edited_score_is_rejected(tmp_path):
    work = workspace(tmp_path)
    form = Form(responses())
    pilot.collect(work, "U01", ask=form.ask, clock=form.clock, show=lambda _: None)
    path = work / "sessions/U01.json"
    original = json.loads(path.read_text())
    for duration in (float("nan"), float("inf"), -1, 181):
        changed = deepcopy(original); changed["trials"][0]["duration"] = duration
        path.write_text(json.dumps(changed))
        with pytest.raises(ValueError):
            pilot.summarize(work)
    changed = deepcopy(original); changed["trials"][0]["action_correct"] = False
    path.write_text(json.dumps(changed))
    with pytest.raises(ValueError, match="score"):
        pilot.summarize(work)


def test_deadline_not_reset_by_invalid_answer_or_late_answer():
    now = [0]
    def invalid(prompt, timeout):
        now[0] += 60
        return "invalid"
    assert pilot.choice(invalid, "action", set(pilot.ACTIONS), clock=lambda: now[0], deadline=180) is None
    assert now[0] == 180
    def late(prompt, timeout):
        now[0] += 181
        return "official_channel"
    now[0] = 0
    assert pilot.choice(late, "action", set(pilot.ACTIONS), clock=lambda: now[0], deadline=180) is None


def test_metadata_stop_is_immediate_and_does_not_change_primary_time(tmp_path):
    work = workspace(tmp_path)
    form = Form(["yes", "start", "official_channel", "evidence", "stop"])
    pilot.collect(work, "U01", ask=form.ask, clock=form.clock, show=lambda _: None)
    assert form.calls == 5
    first = pilot.load_sessions(work)[0]["trials"][0]
    assert first["status"] == "completed" and first["duration"] == 2
    form = Form(["yes", "start", "official_channel", "evidence"])
    def interrupt_sources(prompt, timeout=None):
        if prompt.startswith("Số nguồn"):
            form.now += 50
            raise KeyboardInterrupt
        return form.ask(prompt, timeout)
    pilot.collect(work, "U02", ask=interrupt_sources, clock=form.clock, show=lambda _: None)
    second = pilot.load_sessions(work)[1]["trials"][0]
    assert second["status"] == "completed" and second["duration"] == 2


def test_debrief_does_not_prime_primary_tasks_and_preserves_negative_opinion(tmp_path):
    work = workspace(tmp_path)
    form = Form(responses())
    prompts = []
    def ask(prompt, timeout=None):
        prompts.append(prompt)
        return form.ask(prompt, timeout)
    pilot.collect(work, "U01", ask=ask, clock=form.clock, show=lambda _: None)
    first_label = next(i for i, p in enumerate(prompts) if p.startswith("Người điều phối ghi nhãn"))
    assert sum(p.startswith("Nêu chi tiết") for p in prompts[:first_label]) == 4
    assert all(t["comments"] == "disagree" for t in pilot.load_sessions(work)[0]["trials"])


def test_missing_consent_and_allocated_case_tamper_rejected(tmp_path):
    work = workspace(tmp_path)
    form = Form(responses())
    pilot.collect(work, "U01", ask=form.ask, clock=form.clock, show=lambda _: None)
    path = work / "sessions/U01.json"
    original = json.loads(path.read_text())
    changed = deepcopy(original); changed.pop("consent")
    path.write_text(json.dumps(changed))
    with pytest.raises(ValueError, match="consent"):
        pilot.summarize(work)
    changed = deepcopy(original); changed["trials"][0]["case_id"] = "wrong"
    path.write_text(json.dumps(changed))
    with pytest.raises(ValueError, match="allocation"):
        pilot.summarize(work)


def test_participant_pairing_not_pooled_trials_and_formula_safe_csv(tmp_path):
    work = workspace(tmp_path)
    for participant in ("U01", "U02"):
        form = Form(responses())
        pilot.collect(work, participant, ask=form.ask, clock=form.clock, show=lambda _: None)
        path = work / f"sessions/{participant}.json"
        session = json.loads(path.read_text())
        for trial in session["trials"]:
            correct = (trial["condition"] == "tinchac") == (participant == "U01")
            trial.update(action="official_channel" if correct else "follow_unverified", action_correct=correct,
                         duration=10 if trial["condition"] == "tinchac" else 30, comments=" =private_formula()")
        path.write_text(json.dumps(session))
    partial = Form(["yes", "start", "official_channel", "evidence", "0", "negative opinion", "stop"])
    pilot.collect(work, "U03", ask=partial.ask, clock=partial.clock, show=lambda _: None)
    report = pilot.summarize(work)
    assert report["paired_people"] == 2 and report["observed_trials"] == 9
    assert report["median_person_action_delta_tinchac_minus_manual"] == 0
    assert report["median_person_mean_seconds_delta_tinchac_minus_manual"] == -20
    assert report["conditions"]["manual"]["action_denominator"] == 5
    assert "private_formula" not in json.dumps(report)
    with (work / "user_pilot.csv").open() as stream:
        assert next(csv.DictReader(stream))["comments"].startswith("'")


def test_technical_error_is_not_a_label_and_is_in_denominator(tmp_path):
    work = workspace(tmp_path)
    form = Form(["yes", "start", "technical_error", "0", "provider failed", "stop"])
    pilot.collect(work, "U07", ask=form.ask, clock=form.clock, show=lambda _: None)
    report = pilot.summarize(work)
    assert report["technical_errors"] == report["observed_trials"] == 1
    assert report["conditions"]["tinchac"]["action_denominator"] == 1
    assert report["label_understanding"]["denominator"] == 0


def test_crashed_started_trial_stays_visible_with_unknown_duration(tmp_path):
    work = workspace(tmp_path)
    form = Form(["yes", "start"])
    def crash(prompt, timeout=None):
        if "technical_error" in prompt:
            raise RuntimeError("synthetic process crash")
        return form.ask(prompt, timeout)
    with pytest.raises(RuntimeError):
        pilot.collect(work, "U01", ask=crash, clock=form.clock, show=lambda _: None)
    report = pilot.summarize(work)
    assert report["interrupted_trials"] == report["observed_trials"] == 1
    assert report["conditions"]["manual"]["duration_denominator"] == 0
    assert report["paired_people"] == 0
    assert pilot.load_sessions(work)[0]["trials"][0]["duration"] is None
    with (work / "user_pilot.csv").open() as stream:
        assert next(csv.DictReader(stream))["duration"] == ""


def test_withdrawal_after_deadline_and_skip_are_honored(tmp_path):
    now = [0]
    def late_withdraw(prompt, timeout):
        now[0] += 181
        return "withdraw"
    assert pilot.choice(late_withdraw, "action", set(pilot.ACTIONS), clock=lambda: now[0], deadline=180) == "withdraw"
    work = workspace(tmp_path)
    form = Form(["yes", "start", "skip", "", "", "stop"])
    pilot.collect(work, "U01", ask=form.ask, clock=form.clock, show=lambda _: None)
    report = pilot.summarize(work)
    assert report["skipped_trials"] == report["observed_trials"] == 1
    assert report["conditions"]["manual"]["action_rate"] == 0


def test_two_facilitators_and_changed_collector_are_rejected(tmp_path, monkeypatch):
    work = workspace(tmp_path)
    with pilot.exclusive(work):
        with pytest.raises(ValueError, match="Another facilitator"):
            pilot.summarize(work)
    other_code = tmp_path / "changed_collector.py"
    other_code.write_text("# changed collection/scoring rules")
    monkeypatch.setattr(pilot, "__file__", str(other_code))
    with pytest.raises(ValueError, match="Collector version"):
        pilot.summarize(work)


def test_draft_action_rubric_uses_public_snapshots_not_predicted_labels():
    key = json.loads((pilot.MATERIALS / "action_key.draft.json").read_text())
    sources = {s["version_id"]: s for s in json.loads((pilot.ROOT / "data/corpus/sources.json").read_text())}
    tasks, _ = pilot.materials()
    assert key["independent_human_review"] is False
    assert set(key["answers"]) == {t["task_id"] for t in tasks}
    for task in tasks:
        answer = key["answers"][task["task_id"]]
        source = sources[answer["source_version"]]
        assert source["review_status"] == "approved" and not source["is_fixture"]
        assert source["family_id"] == task["family_id"]
        assert source["content_sha256"] == answer["source_sha256"]
        assert answer["source_quote"] in source["text"]
        assert not (set(answer) & {"expected_label", "gold_label", "predicted_label"})
        assert "follow_unverified" not in answer["accepted_actions"]


def test_local_tty_form_handles_rapid_lines_without_losing_stop(tmp_path):
    work = workspace(tmp_path)
    master, slave = pty.openpty()
    process = subprocess.Popen([sys.executable, "-m", "scripts.user_pilot", "collect", "--work", str(work),
                                "--participant", "U01"], stdin=slave, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               cwd=pilot.ROOT)
    os.close(slave)
    try:
        os.write(master, b"yes\nstart\nstop\n")
        stdout, stderr = process.communicate(timeout=5)
        assert process.returncode == 0, stderr.decode()
        assert b"saved_locally" in stdout
        assert pilot.summarize(work)["stopped_trials"] == 1
    finally:
        if process.poll() is None:
            process.kill(); process.communicate()
        os.close(master)


def test_local_tty_timer_expires_without_input():
    master, slave = pty.openpty()
    process = subprocess.Popen([sys.executable, "-c",
        "from scripts.user_pilot import console_ask; print('EXPIRED', console_ask('synthetic timeout', 0.05) is None)"],
        stdin=slave, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=pilot.ROOT)
    os.close(slave)
    try:
        stdout, stderr = process.communicate(timeout=5)
        assert process.returncode == 0, stderr.decode()
        assert b"EXPIRED True" in stdout
    finally:
        if process.poll() is None:
            process.kill(); process.communicate()
        os.close(master)


def test_empty_pilot_has_zero_counts_and_no_fabricated_rates(tmp_path):
    report = pilot.summarize(workspace(tmp_path))
    assert report["actual_real_participants"] == report["consented"] == report["paired_people"] == 0
    assert report["observed_trials"] == report["label_understanding"]["denominator"] == 0
    assert report["median_person_action_delta_tinchac_minus_manual"] is None
    for group in report["conditions"].values():
        assert group["action_denominator"] == group["duration_denominator"] == 0
        assert group["action_rate"] is group["median_seconds"] is None
