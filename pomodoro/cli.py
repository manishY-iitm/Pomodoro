"""Command-line interface for Kali Pomodoro Clock."""
import sys
import argparse
from typing import Optional
from pomodoro.ipc import IPCClient


def get_client() -> IPCClient:
    client = IPCClient()
    if not client.is_server_running():
        print("Error: Pomodoro daemon is not running.", file=sys.stderr)
        print("Run 'pomodoro-app' or 'pomodoro-daemon &' to start it.", file=sys.stderr)
        sys.exit(1)
    return client


def cmd_status(args):
    client = get_client()
    resp = client.send_command("status")
    if not resp.get("ok"):
        print(f"Error: {resp.get('error')}", file=sys.stderr)
        sys.exit(1)

    data = resp["data"]
    state = data["state"]
    formatted_time = data["formatted_time"]
    cycle = data["cycle_count"]
    target_cycles = data["sessions_before_long_break"]
    task = data.get("active_task")

    # Fetch today's stats too
    stats_resp = client.send_command("get_stats")
    stats = stats_resp.get("stats", {}) if stats_resp.get("ok") else {}

    print("═══════════════════════════════════════════════")
    print(" 🍅 KALI POMODORO PRODUCTIVITY CLOCK")
    print("═══════════════════════════════════════════════")
    print(f" Status:       {state} ({data['panel_icon']} {data['panel_label']})")
    print(f" Time Left:    {formatted_time} ({int(data['progress']*100)}% elapsed)")
    print(f" Cycle:        {cycle} / {target_cycles} before long break")
    if task:
        subj = f" [{task.get('subject_name')}]" if task.get("subject_name") else ""
        print(f" Active Task:  {task['name']}{subj}")
        if task.get("target"):
            print(f" Target:       {task['target']}")
    else:
        print(" Active Task:  (None selected)")
    print("───────────────────────────────────────────────")
    print(f" Today Focus:  {stats.get('formatted_focus_time', '0m')}")
    print(f" Completed:    {stats.get('completed_sessions', 0)} sessions | {stats.get('completed_tasks', 0)} tasks")
    print(f" Top Subject:  {stats.get('top_subject', 'None')}")
    print("═══════════════════════════════════════════════")


def cmd_simple(action: str):
    client = get_client()
    resp = client.send_command(action)
    if resp.get("ok"):
        data = resp.get("data", {})
        print(f"Pomodoro {action} successful. Status: {data.get('state')} ({data.get('formatted_time')})")
    else:
        print(f"Error: {resp.get('error')}", file=sys.stderr)
        sys.exit(1)


def cmd_task(args):
    client = get_client()
    if args.task_action == "list":
        resp = client.send_command("list_tasks", include_completed=args.all)
        tasks = resp.get("tasks", [])
        if not tasks:
            print("No tasks found.")
            return
        print(f"{'ID':<4} {'STATUS':<10} {'SUBJECT':<20} {'NAME':<30} {'TARGET':<15}")
        print("─" * 80)
        for t in tasks:
            st = "✓ Done" if t["completed"] else "○ Active"
            subj = t.get("subject_name") or "-"
            target = t.get("target") or "-"
            print(f"{t['id']:<4} {st:<10} {subj:<20} {t['name']:<30} {target:<15}")

    elif args.task_action == "add":
        # Resolve subject if passed
        sub_id = None
        if args.subject:
            s_resp = client.send_command("list_subjects")
            for s in s_resp.get("subjects", []):
                if s["name"].lower() == args.subject.lower():
                    sub_id = s["id"]
                    break
        resp = client.send_command(
            "add_task",
            name=args.name,
            subject_id=sub_id,
            target=args.target,
            notes=args.notes,
        )
        if resp.get("ok"):
            print(f"Task created successfully (ID {resp['task_id']})")
        else:
            print(f"Error: {resp.get('error')}", file=sys.stderr)

    elif args.task_action == "select":
        resp = client.send_command("set_task", task_id=args.task_id)
        if resp.get("ok"):
            print(f"Active task set to ID {args.task_id}")
        else:
            print(f"Error: {resp.get('error')}", file=sys.stderr)

    elif args.task_action == "clear":
        client.send_command("set_task", task_id=None)
        print("Active task cleared.")

    elif args.task_action == "complete":
        resp = client.send_command("complete_task", task_id=args.task_id, completed=True)
        if resp.get("ok"):
            print(f"Task {args.task_id} marked as completed.")
        else:
            print(f"Error: {resp.get('error')}", file=sys.stderr)


def cmd_stats(args):
    client = get_client()
    resp = client.send_command("get_stats", date=args.date)
    if not resp.get("ok"):
        print(f"Error: {resp.get('error')}", file=sys.stderr)
        return

    st = resp["stats"]
    print(f"═══════════════════════════════════════════════")
    print(f" 📊 STATISTICS FOR {st['date']}")
    print(f"═══════════════════════════════════════════════")
    print(f" Total Focused Time:    {st['formatted_focus_time']}")
    print(f" Completed Sessions:    {st['completed_sessions']}")
    print(f" Completed Tasks:       {st['completed_tasks']}")
    print(f" Top Subject:           {st['top_subject']}")
    print(f"───────────────────────────────────────────────")
    if st["by_subject"]:
        print(" Focus Time by Subject:")
        for sub in st["by_subject"]:
            bar_len = int(sub["percentage"] / 5)
            bar = "█" * bar_len + "░" * (20 - bar_len)
            print(f"   • {sub['name']:<24} {sub['formatted']:<8} [{bar}] {sub['percentage']}%")
    else:
        print(" No study sessions recorded for this day yet.")
    print(f"═══════════════════════════════════════════════")


def main():
    parser = argparse.ArgumentParser(description="Kali Pomodoro Clock CLI Controller")
    subparsers = parser.add_subparsers(dest="command")

    # status
    subparsers.add_parser("status", help="Show current timer status")

    # controls
    subparsers.add_parser("start", help="Start timer")
    subparsers.add_parser("pause", help="Pause timer")
    subparsers.add_parser("resume", help="Resume timer")
    subparsers.add_parser("toggle", help="Toggle start/pause")
    subparsers.add_parser("reset", help="Reset current interval")
    subparsers.add_parser("skip", help="Skip to next session")

    # tasks
    task_p = subparsers.add_parser("task", help="Manage study tasks")
    task_sub = task_p.add_subparsers(dest="task_action")

    # task list
    t_list = task_sub.add_parser("list", help="List tasks")
    t_list.add_argument("--all", action="store_true", help="Include completed tasks")

    # task add
    t_add = task_sub.add_parser("add", help="Add new study task")
    t_add.add_argument("name", help="Task name")
    t_add.add_argument("--subject", help="Subject category")
    t_add.add_argument("--target", help="Task goal or target")
    t_add.add_argument("--notes", help="Optional notes")

    # task select
    t_sel = task_sub.add_parser("select", help="Select active task for timer")
    t_sel.add_argument("task_id", type=int, help="Task ID to select")

    # task clear
    task_sub.add_parser("clear", help="Clear active task")

    # task complete
    t_comp = task_sub.add_parser("complete", help="Mark task as complete")
    t_comp.add_argument("task_id", type=int, help="Task ID to complete")

    # stats
    stats_p = subparsers.add_parser("stats", help="View daily study statistics")
    stats_p.add_argument("--date", help="Target date in YYYY-MM-DD format (defaults to today)")

    args = parser.parse_args()

    if not args.command or args.command == "status":
        cmd_status(args)
    elif args.command in ("start", "pause", "resume", "toggle", "reset", "skip"):
        cmd_simple(args.command)
    elif args.command == "task":
        if not args.task_action:
            args.task_action = "list"
            args.all = False
        cmd_task(args)
    elif args.command == "stats":
        cmd_stats(args)


if __name__ == "__main__":
    main()
