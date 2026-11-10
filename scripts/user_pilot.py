"""Local facilitator form for T14. No network, provider, contact or benchmark access."""
import argparse
from collections import Counter, defaultdict
from contextlib import contextmanager
import csv
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import select
from statistics import median
import sys
import termios
import time

ROOT = Path(__file__).resolve().parents[1]
MATERIALS = ROOT / "eval/usability"
CSV_FIELDS = ["participant_id", "case_id", "condition", "order", "duration", "action_correct", "comments"]
ACTIONS = {
    "official_channel": "Mở kênh chính thức để đối chiếu chi tiết/đúng đối tượng",
    "ask_unit": "Hỏi đơn vị phụ trách qua kênh chính thức",
    "wait_verify": "Chờ xác minh trước khi làm theo",
    "follow_unverified": "Làm theo nội dung chưa kiểm tra (chỉ chọn giả định; không giao dịch thật)",
}
MEANINGS = {
    "bounded_support": "Chi tiết được nguồn hỗ trợ trong phạm vi/thời điểm đã kiểm",
    "bounded_conflict": "Chi tiết mâu thuẫn với nguồn phù hợp",
    "unverified": "Chưa xác minh được đúng hay sai",
    "fraud": "Toàn bộ thông báo chắc chắn giả mạo",
    "safe_transaction": "Mọi giao dịch trong thông báo đều an toàn",
    "not_shown": "Không thấy/không biết nhãn",
}
LABEL_KEY = {"supported": "bounded_support", "contradicted": "bounded_conflict",
             "insufficient_evidence": "unverified"}
CONSENT_VERSION = "T14-consent-v1"
CONSENT = """Bạn đang thử demo nghiên cứu với tình huống giả lập từ thông tin công khai,
không phải chỉ dẫn học bổng/đóng tiền thật. Kết quả có thể sai. Khoảng 15–20 phút,
4 tình huống, tối đa 3 phút/tình huống. Hai lượt tự tra, hai lượt dùng TinChắc.
Tự nguyện; từ chối/dừng không ảnh hưởng quyền lợi học tập. Có thể bỏ câu hỏi,
dừng bất kỳ lúc nào bằng stop; withdraw yêu cầu xóa dữ liệu phiên này.
Chỉ lưu mã Uxx, câu trả lời, thời gian và nhận xét trong máy người điều phối.
Không nhập tên, email, số điện thoại, tài khoản, OTP, ảnh hoặc tin nhắn riêng tư.
Phiên dành cho sinh viên DUT từ đủ 18 tuổi; chọn yes cũng xác nhận điều này.
Không chuyển tiền, đăng nhập, liên hệ người gửi đáng ngờ hoặc thử giao dịch thật.
Chỉ báo cáo số tổng hợp đã rà quyền riêng tư; không công khai lời nói/ảnh cá nhân.
Đồng ý tham gia không cấp quyền công khai ảnh/tin nhắn. Không ghi âm/quay màn hình.
Dữ liệu thô xóa trước 22/12/2026 (Asia/Ho_Chi_Minh) hoặc ngay khi yêu cầu bằng mã Uxx.
Sau khi xóa dữ liệu thô không thể truy ngược số tổng hợp đã ẩn danh.
Bạn có thể hỏi người điều phối trước khi chọn yes/no. Chỉ yes mới là đồng ý."""


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     allow_nan=False).encode()).hexdigest()


def materials():
    tasks = json.loads((MATERIALS / "tasks.json").read_text())["tasks"]
    with (MATERIALS / "allocation.csv").open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    return tasks, rows


def validate_allocation(tasks, rows):
    by_task = {task["task_id"]: task for task in tasks}
    if len(tasks) != 4 or len(by_task) != 4 or len({t["case_id"] for t in tasks}) != 4:
        raise ValueError("Expected four unique tasks/cases")
    people = defaultdict(list)
    for row in rows:
        task = by_task.get(row["task_id"])
        if not task or row["family_id"] != task["family_id"]:
            raise ValueError("Task/family mismatch")
        people[row["planned_participant_id"]].append(row)
    if set(people) != {f"U{i:02}" for i in range(1, 13)} or len(rows) != 48:
        raise ValueError("Expected 12 planned people / 48 trials")
    starts = Counter()
    for trials in people.values():
        if (len(trials) != 4 or {r["order"] for r in trials} != {"1", "2", "3", "4"}
                or len({r["family_id"] for r in trials}) != 4
                or len({r["task_id"] for r in trials}) != 4):
            raise ValueError("Duplicate or missing order/task/family")
        ordered = sorted(trials, key=lambda r: int(r["order"]))
        sequence = [r["condition"] for r in ordered]
        if sequence not in (["manual", "manual", "tinchac", "tinchac"],
                            ["tinchac", "tinchac", "manual", "manual"]):
            raise ValueError("Expected two blocked conditions")
        starts[sequence[0]] += 1
    if starts != {"manual": 6, "tinchac": 6}:
        raise ValueError("Unbalanced starting condition")
    if Counter((r["task_id"], r["condition"]) for r in rows) != {
            (task, condition): 6 for task in by_task for condition in ("manual", "tinchac")}:
        raise ValueError("Unbalanced task/condition")
    return {"planned_people": 12, "planned_trials": 48}


def validate_readiness(gate, tasks):
    if not all(gate.get(field) is True for field in
               ("qa_passed", "supports_all_tasks", "answer_key_reviewed")):
        raise ValueError("Missing readiness: QA, all-task support and reviewed action key required")
    if gate.get("run_mode") not in ("live", "replay"):
        raise ValueError("Current fixture has only one family; cannot serve these four tasks")
    if not all(isinstance(gate.get(f), str) and gate[f].strip()
               for f in ("build_id", "qa_evidence", "review_basis")):
        raise ValueError("Readiness needs release/evidence/review provenance")
    if set(gate.get("answers", {})) != {t["task_id"] for t in tasks}:
        raise ValueError("Action key must cover every task")
    for answer in gate["answers"].values():
        accepted = answer.get("accepted_actions", [])
        if (not accepted or len(accepted) != len(set(accepted))
                or not set(accepted) <= ACTIONS.keys() or not answer.get("rationale", "").strip()):
            raise ValueError("Action key needs valid accepted_actions and rationale")


def write_json(path, value):
    temporary = path.with_suffix(".tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        os.chmod(temporary, 0o600)
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
    temporary.replace(path)


def initialize(work, gate, *, kind="real"):
    work = Path(work).resolve()
    private = ROOT / "data/private"
    if kind not in ("real", "synthetic"):
        raise ValueError("Invalid data kind")
    if kind == "real" and not work.is_relative_to(private):
        raise ValueError("Real records must stay under ignored data/private/")
    if kind == "synthetic" and work.is_relative_to(private):
        raise ValueError("Synthetic data must stay separate from private real data")
    tasks, allocation = materials()
    validate_allocation(tasks, allocation)
    validate_readiness(gate, tasks)
    manifest = dict(kind=kind, tasks=tasks, allocation=allocation, readiness=gate,
                    consent_version=CONSENT_VERSION, consent_sha256=digest(CONSENT),
                    collector_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                    max_seconds=180, retention_delete_by="2026-12-22 Asia/Ho_Chi_Minh")
    manifest["materials_sha256"] = digest(manifest)
    work.mkdir(mode=0o700, parents=True, exist_ok=False)
    (work / "sessions").mkdir(mode=0o700)
    write_json(work / "manifest.json", manifest)
    export_csv(work, [])
    return work


def load_manifest(work):
    manifest = json.loads((work / "manifest.json").read_text())
    signed = {k: v for k, v in manifest.items() if k != "materials_sha256"}
    if digest(signed) != manifest.get("materials_sha256"):
        raise ValueError("Materials hash mismatch; create a separate pilot version")
    if manifest["consent_version"] != CONSENT_VERSION or manifest["consent_sha256"] != digest(CONSENT):
        raise ValueError("Consent version/hash changed; use a separate pilot version")
    if manifest.get("collector_sha256") != hashlib.sha256(Path(__file__).read_bytes()).hexdigest():
        raise ValueError("Collector version changed; use the pinned version or a separate pilot")
    if manifest["kind"] == "real" and not work.resolve().is_relative_to(ROOT / "data/private"):
        raise ValueError("Real records outside private storage")
    validate_allocation(manifest["tasks"], manifest["allocation"])
    validate_readiness(manifest["readiness"], manifest["tasks"])
    return manifest


@contextmanager
def exclusive(work):
    # One local facilitator. Hold a nonblocking OS lock during collection/exports.
    with (work / ".lock").open("a") as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ValueError("Another facilitator is using this pilot") from exc
        try:
            yield
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)


def load_sessions(work):
    return [json.loads(path.read_text()) for path in sorted((work / "sessions").glob("U*.json"))]


def export_csv(work, sessions):
    path = work / "user_pilot.csv"
    temporary = path.with_suffix(".tmp")
    with temporary.open("w", newline="", encoding="utf-8") as stream:
        os.chmod(temporary, 0o600)
        writer = csv.DictWriter(stream, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for session in sessions:
            if session["state"] in ("withdrawn", "declined"):
                continue
            for trial in session["trials"]:
                row = {key: trial[key] for key in CSV_FIELDS if key != "participant_id"}
                # Keep raw comments in private JSON; neutralize spreadsheet formulas in CSV.
                if row["comments"].lstrip().startswith(("=", "+", "-", "@")):
                    row["comments"] = "'" + row["comments"]
                writer.writerow(dict(participant_id=session["participant_id"], **row))
    temporary.replace(path)


def save_session(work, session):
    write_json(work / "sessions" / f'{session["participant_id"]}.json', session)
    export_csv(work, load_sessions(work))


def console_ask(prompt, timeout=None):
    print(prompt, flush=True)
    deadline = None if timeout is None else time.monotonic() + timeout
    line = bytearray()
    while True:
        remaining = None if deadline is None else max(0, deadline - time.monotonic())
        if remaining == 0 or not select.select([sys.stdin], [], [], remaining)[0]:
            if sys.stdin.isatty():
                termios.tcflush(sys.stdin, termios.TCIFLUSH)
            return None
        # Avoid TextIO prefetch: rapid consecutive lines must stay visible to select.
        value = os.read(sys.stdin.fileno(), 1)
        if not value:
            return "stop"
        if value == b"\n":
            return line.decode(sys.stdin.encoding or "utf-8", errors="replace").strip()
        line.extend(value)


def choice(ask, prompt, allowed, *, clock=time.monotonic, deadline=None):
    while True:
        remaining = None if deadline is None else max(0, deadline - clock())
        answer = ask(prompt, remaining)
        if answer in ("stop", "withdraw"):
            return answer
        if deadline is not None and clock() >= deadline:
            return None
        if answer is None or answer in ("stop", "withdraw") or answer in allowed:
            return answer


def collect(work, participant, *, ask=console_ask, clock=time.monotonic, show=print):
    with exclusive(work):
        manifest = load_manifest(work)
        if participant not in {r["planned_participant_id"] for r in manifest["allocation"]}:
            raise ValueError("Unknown planned participant")
        if (work / "sessions" / f"{participant}.json").exists():
            raise ValueError("Participant already recorded; do not recycle IDs or overwrite results")
        show(CONSENT)
        show(f'Mode: {manifest["kind"]} / {manifest["readiness"]["run_mode"]}; build {manifest["readiness"]["build_id"]}')
        consent = choice(ask, "Đồng ý tham gia? yes/no", {"yes", "no"})
        session = dict(participant_id=participant, state="active" if consent == "yes" else "declined", trials=[])
        if consent != "yes":
            save_session(work, session)
            return
        session["consent"] = dict(version=CONSENT_VERSION, agreed=True, at=datetime.now(timezone.utc).isoformat())
        save_session(work, session)
        tasks = {t["task_id"]: t for t in manifest["tasks"]}
        assigned = sorted((r for r in manifest["allocation"] if r["planned_participant_id"] == participant),
                          key=lambda r: int(r["order"]))
        for row in assigned:
            task = tasks[row["task_id"]]
            show(f'Chuẩn bị lượt {row["order"]}/4 · {row["condition"]}. Chưa đọc nội dung trước khi start.')
            try:
                command = choice(ask, "start / stop / withdraw", {"start"})
            except (KeyboardInterrupt, EOFError):
                command = "stop"
            if command != "start":
                session["state"] = "withdrawn" if command == "withdraw" else "stopped"
                break
            started = clock()
            show(task["input_text"])
            show("Xác định chi tiết cần kiểm tra, chọn bước tiếp theo và nêu bằng chứng. Không thực hiện giao dịch.")
            trial = dict(case_id=task["case_id"], task_id=task["task_id"], family_id=task["family_id"],
                         condition=row["condition"], order=int(row["order"]), duration=None,
                         action=None, action_correct=False, evidence="", sources_opened=None,
                         shown_label="not_shown", label_answer="not_shown", comments="", status="interrupted")
            # Persist the started trial before asking: a crash cannot silently erase an attempt.
            session["trials"].append(trial)
            save_session(work, session)
            try:
                action = choice(ask, str(ACTIONS) + " / skip / technical_error / stop / withdraw",
                                set(ACTIONS) | {"skip", "technical_error"}, clock=clock, deadline=started + 180)
                evidence = ""
                if action in ACTIONS:
                    evidence = ask("Nêu chi tiết cần kiểm và bằng chứng (có thể để trống):", max(0, started + 180 - clock()))
                elapsed = clock() - started
                stopped = action in ("stop", "withdraw") or evidence in ("stop", "withdraw")
                if action == "withdraw" or evidence == "withdraw":
                    session["state"] = "withdrawn"
                    break
                timeout = action is None or evidence is None or elapsed >= 180
                trial.update(duration=min(180, max(0, elapsed)), action=action if action in ACTIONS else None,
                             evidence=(evidence or "")[:2000], status="stopped" if stopped else
                             "timeout" if timeout else "skipped" if action == "skip" else
                             "technical_error" if action == "technical_error" else "completed")
                trial["action_correct"] = (trial["status"] == "completed" and
                    trial["action"] in manifest["readiness"]["answers"][row["task_id"]]["accepted_actions"])
                save_session(work, session)
                if stopped:
                    session["state"] = "stopped"
                    break
                show("Đã dừng đồng hồ. Không giải thích đáp án trong phiên.")
                sources = choice(ask, "Số nguồn thực sự đã mở (0–99, blank nếu không biết):", {""} | {str(i) for i in range(100)})
                if sources in ("stop", "withdraw"):
                    session["state"] = "withdrawn" if sources == "withdraw" else "stopped"
                    break
                trial["sources_opened"] = int(sources) if sources else None
                save_session(work, session)
                comment = ask("Điểm khó hiểu/ý kiến trái chiều? blank để bỏ; không ghi thông tin cá nhân:", None)
                if comment in ("stop", "withdraw"):
                    session["state"] = "withdrawn" if comment == "withdraw" else "stopped"
                    break
                trial["comments"] = (comment or "")[:2000]
                save_session(work, session)
            except (KeyboardInterrupt, EOFError):
                if trial["status"] == "interrupted":
                    trial.update(duration=min(180, max(0, clock() - started)), status="stopped", action_correct=False)
                session["state"] = "stopped"
                break
        else:
            session["state"] = "finished"
        # Ask meanings only after primary tasks: answer choices must not teach the next trial.
        if session["state"] == "finished":
            show("Hết 4 lượt. Hỏi hiểu nhãn trước khi giải thích đáp án; có thể bỏ qua bằng blank.")
            try:
                for trial in session["trials"]:
                    if trial["condition"] != "tinchac" or trial["status"] != "completed":
                        continue
                    show(f'Lượt {trial["order"]}: {tasks[trial["task_id"]]["input_text"]}')
                    for field, prompt, allowed in (
                        ("shown_label", "Người điều phối ghi nhãn THỰC SỰ đã thấy (không suy từ đáp án): " + str(list(LABEL_KEY)) + ", not_shown", set(LABEL_KEY) | {"not_shown", ""}),
                        ("label_answer", "Bạn hiểu nhãn đó thế nào? " + str(MEANINGS), set(MEANINGS) | {""}),
                    ):
                        answer = choice(ask, prompt, allowed)
                        if answer in ("stop", "withdraw"):
                            session["state"] = "withdrawn" if answer == "withdraw" else "stopped"
                            break
                        trial[field] = answer or "not_shown"
                        save_session(work, session)
                    if session["state"] != "finished":
                        break
            except (KeyboardInterrupt, EOFError):
                session["state"] = "stopped"
        if session["state"] == "withdrawn":
            session = dict(participant_id=participant, state="withdrawn", trials=[])
        save_session(work, session)
        show("Phiên đã lưu cục bộ. Giữ mã Uxx để yêu cầu xóa; không có lời mời hay dữ liệu nào được gửi ra ngoài.")


def withdraw(work, participant):
    with exclusive(work):
        load_manifest(work)
        if participant not in {s["participant_id"] for s in load_sessions(work)}:
            raise ValueError("No session for this participant")
        save_session(work, dict(participant_id=participant, state="withdrawn", trials=[]))


def summarize(work):
    with exclusive(work):
        manifest = load_manifest(work)
        sessions = load_sessions(work)
        known = {r["planned_participant_id"] for r in manifest["allocation"]}
        ids = [s["participant_id"] for s in sessions]
        if len(set(ids)) != len(ids) or not set(ids) <= known:
            raise ValueError("Duplicate/unknown participant record")
        if any(s["state"] not in ("active", "finished", "stopped", "declined", "withdrawn") for s in sessions):
            raise ValueError("Invalid session state")
        active = [s for s in sessions if s["state"] not in ("withdrawn", "declined")]
        tasks = {t["task_id"]: t for t in manifest["tasks"]}
        trials = []
        deltas_action, deltas_time = [], []
        for session in active:
            if session.get("consent", {}).get("agreed") is not True or session["consent"]["version"] != CONSENT_VERSION:
                raise ValueError("Missing valid consent")
            assigned = {int(r["order"]): r for r in manifest["allocation"]
                        if r["planned_participant_id"] == session["participant_id"]}
            seen = set()
            for trial in session["trials"]:
                order = trial["order"]
                if order in seen or order not in assigned:
                    raise ValueError("Duplicate/unassigned observed order")
                seen.add(order)
                row = assigned[order]; task = tasks[row["task_id"]]
                if any(trial[k] != v for k, v in {"task_id": row["task_id"], "case_id": task["case_id"],
                        "family_id": task["family_id"], "condition": row["condition"]}.items()):
                    raise ValueError("Observed allocation mismatch")
                unknown_time = trial["status"] == "interrupted" and trial["duration"] is None
                if not unknown_time and (type(trial["duration"]) not in (int, float)
                        or not math.isfinite(trial["duration"]) or not 0 <= trial["duration"] <= 180):
                    raise ValueError("Invalid duration")
                if trial["status"] not in ("completed", "timeout", "technical_error", "skipped", "stopped", "interrupted"):
                    raise ValueError("Invalid trial status")
                if trial["status"] == "timeout" and trial["duration"] != 180:
                    raise ValueError("Timeout duration must remain 180")
                if trial["status"] == "completed" and (trial["duration"] >= 180 or trial["action"] not in ACTIONS):
                    raise ValueError("Completed trial needs timely valid action")
                if (trial["shown_label"] not in set(LABEL_KEY) | {"not_shown"}
                        or trial["label_answer"] not in MEANINGS
                        or trial["sources_opened"] is not None and
                        (type(trial["sources_opened"]) is not int or not 0 <= trial["sources_opened"] <= 99)):
                    raise ValueError("Invalid label/source measurement")
                expected = (trial["status"] == "completed" and trial["action"] in
                            manifest["readiness"]["answers"][row["task_id"]]["accepted_actions"])
                if trial["action_correct"] is not expected:
                    raise ValueError("Stored score differs from locked action key")
                trials.append(trial)
            # Pair all four recorded tasks, retaining timeout/error as unsuccessful, 180s timeouts.
            if len(seen) == 4 and all(t["status"] not in ("interrupted", "stopped") for t in session["trials"]):
                groups = {c: [t for t in session["trials"] if t["condition"] == c] for c in ("manual", "tinchac")}
                deltas_action.append(sum(t["action_correct"] for t in groups["tinchac"]) / 2 -
                                     sum(t["action_correct"] for t in groups["manual"]) / 2)
                deltas_time.append(sum(t["duration"] for t in groups["tinchac"]) / 2 -
                                   sum(t["duration"] for t in groups["manual"]) / 2)
        conditions = {}
        for condition in ("manual", "tinchac"):
            group = [t for t in trials if t["condition"] == condition]
            durations = [t["duration"] for t in group if t["status"] != "interrupted"]
            conditions[condition] = dict(action_numerator=sum(t["action_correct"] for t in group),
                action_denominator=len(group), action_rate=sum(t["action_correct"] for t in group)/len(group) if group else None,
                duration_denominator=len(durations), median_seconds=median(durations) if durations else None,
                sources_recorded=sum(t["sources_opened"] is not None for t in group),
                sources_opened_total=sum(t["sources_opened"] or 0 for t in group))
        labeled = [t for t in trials if t["condition"] == "tinchac"]
        shown = [t for t in labeled if t["shown_label"] in LABEL_KEY]
        report = dict(kind=manifest["kind"], actual_real_participants=len(active) if manifest["kind"] == "real" else 0,
            planned_people=12, planned_trials=48, consented=len(active),
            declined=sum(s["state"] == "declined" for s in sessions),
            withdrawn=sum(s["state"] == "withdrawn" for s in sessions),
            stopped_people=sum(s["state"] == "stopped" for s in active), observed_trials=len(trials),
            completed_trials=sum(t["status"] == "completed" for t in trials),
            stopped_trials=sum(t["status"] == "stopped" for t in trials),
            skipped_trials=sum(t["status"] == "skipped" for t in trials),
            timeouts=sum(t["status"] == "timeout" for t in trials),
            technical_errors=sum(t["status"] == "technical_error" for t in trials),
            interrupted_trials=sum(t["status"] == "interrupted" for t in trials),
            paired_people=len(deltas_action), conditions=conditions,
            observed_family_counts=dict(Counter(t["family_id"] for t in trials)),
            label_understanding=dict(correct=sum(t["label_answer"] == LABEL_KEY[t["shown_label"]] for t in shown),
                                     denominator=len(shown), tinchac_trials=len(labeled), not_shown=len(labeled)-len(shown)),
            median_person_action_delta_tinchac_minus_manual=median(deltas_action) if deltas_action else None,
            median_person_mean_seconds_delta_tinchac_minus_manual=median(deltas_time) if deltas_time else None,
            observed_task_condition_counts={f"{task}/{condition}": sum(t["task_id"] == task and t["condition"] == condition for t in trials)
                                           for task in tasks for condition in ("manual", "tinchac")},
            materials_sha256=manifest["materials_sha256"], run_mode=manifest["readiness"]["run_mode"],
            limitation="Exploratory pilot; paired unit is person. Partial people excluded from paired deltas only; no causal claim. No comments or individual rows exported here.")
        export_csv(work, sessions)
        return report


def rehearse(work):
    """Exercise the real form with synthetic clock/input; never produce real outcomes."""
    gate = dict(run_mode="replay", build_id="SYNTHETIC_no_UI_release",
                qa_evidence="SYNTHETIC_not_QA_evidence", qa_passed=True,
                supports_all_tasks=True, answer_key_reviewed=True, review_basis="SYNTHETIC_not_human_review",
                answers={f"P{i}": dict(accepted_actions=["official_channel"], rationale="Synthetic rubric only") for i in range(1, 5)})
    initialize(work, gate, kind="synthetic")
    for number in range(1, 13):
        elapsed = [0.0]
        answers = iter(["yes"] + [v for _ in range(4) for v in
                      ["start", "official_channel", "synthetic quote", "1", "SYNTHETIC contrary opinion"]] +
                      ["insufficient_evidence", "unverified"] * 2)
        def ask(prompt, timeout=None):
            value = next(answers)
            if number % 3 == 0 and prompt.startswith("Nêu chi tiết"):
                elapsed[0] += timeout
                return None
            elapsed[0] += 1
            return value
        collect(work, f"U{number:02}", ask=ask, clock=lambda: elapsed[0], show=lambda _: None)
    return summarize(work)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("validate-allocation")
    init = sub.add_parser("init")
    init.add_argument("--readiness", type=Path, required=True)
    init.add_argument("--work", type=Path, default=ROOT / "data/private/user_pilot")
    for name in ("collect", "withdraw", "summary", "rehearse"):
        command = sub.add_parser(name)
        command.add_argument("--work", type=Path, required=True)
        if name in ("collect", "withdraw"):
            command.add_argument("--participant", required=True)
    args = parser.parse_args()
    try:
        if args.command == "validate-allocation":
            result = validate_allocation(*materials())
        elif args.command == "init":
            result = {"workspace": str(initialize(args.work, json.loads(args.readiness.read_text())))}
        elif args.command in ("collect", "withdraw"):
            if args.command == "collect" and not sys.stdin.isatty():
                raise ValueError("Real collection needs an interactive local terminal; use rehearse for synthetic input")
            globals()[args.command](args.work.resolve(), args.participant)
            result = {"saved_locally": True}
        else:
            result = (rehearse if args.command == "rehearse" else summarize)(args.work.resolve())
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    except (ValueError, OSError, KeyError, TypeError) as exc:
        # Never print input values/tracebacks from private sessions on validation errors.
        parser.exit(2, f"Pilot validation/storage failed ({type(exc).__name__}). Check protocol and local files; no data uploaded.\n")


if __name__ == "__main__":
    main()
