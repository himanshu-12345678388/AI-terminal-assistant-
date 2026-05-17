import datetime
import os
import shlex
import shutil
import subprocess
from pathlib import Path

from model import predict_intent

# These commands are intentionally read-only or very limited.  Dangerous actions
# such as rm, mv, chmod, chown, sudo, shutdown, reboot, kill, mkfs, and dd are
# blocked by design because a beginner-friendly assistant should not be able to
# delete data, change permissions, or damage the system by accident.
BLOCKED_NAME_PARTS = ("/", "..", "~", "*", "?", "&", "|", ";", "$", "`", ">", "<")
PROJECT_DIR = Path.cwd().resolve()


def run_command(args):
    """Run a known-safe command without invoking a shell."""
    try:
        subprocess.run(args, check=False)
    except FileNotFoundError:
        print(f"⚠️ Command not available: {args[0]}")


def launch_background(args):
    """Start a known GUI program without using a shell."""
    try:
        subprocess.Popen(args)
    except FileNotFoundError:
        print(f"⚠️ Command not available: {args[0]}")


def print_help():
    print(
        """
Available examples:
  disk usage              cpu info                os info
  gpu info                battery info            network info
  ip address              logged in users         running processes
  environment info        shell info              python version
  package manager info    fastfetch info
  touch notes.txt         mkdir examples          cp notes.txt backup.txt
  create file notes.txt   create folder examples  copy notes.txt to backup.txt

File safety rules:
  - Only simple names in the current project directory are allowed.
  - Paths and shell symbols such as /, .., ~, *, ?, &, |, ;, $, `, >, < are blocked.
  - Destructive commands are intentionally not supported.
""".strip()
    )


def safe_name(name, label):
    """Accept only one simple filename/folder name inside this project folder."""
    if not name:
        print(f"Please provide a {label} name.")
        return None

    if any(part in name for part in BLOCKED_NAME_PARTS):
        print(
            "Blocked unsafe name. Use a simple name without /, .., ~, *, ?, &, |, ;, $, `, >, or <."
        )
        return None

    candidate = (PROJECT_DIR / name).resolve()
    if candidate.parent != PROJECT_DIR:
        print("Blocked path outside the current project directory.")
        return None

    return candidate


def parse_words(text):
    try:
        return shlex.split(text)
    except ValueError:
        print("I could not read that input. Please check the quotes and try again.")
        return []


def handle_touch(words):
    if len(words) < 2:
        print("Please provide a file name, for example: touch notes.txt")
        return
    if len(words) > 2:
        print("Please provide only one file name, for example: touch notes.txt")
        return

    path = safe_name(words[1], "file")
    if path:
        path.touch(exist_ok=True)
        print(f"Created file: {path.name}")


def handle_mkdir(words):
    if len(words) < 2:
        print("Please provide a folder name, for example: mkdir examples")
        return
    if len(words) > 2:
        print("Please provide only one folder name, for example: mkdir examples")
        return

    path = safe_name(words[1], "folder")
    if not path:
        return

    try:
        path.mkdir(exist_ok=False)
        print(f"Created folder: {path.name}")
    except FileExistsError:
        print(f"Folder already exists: {path.name}")


def handle_copy(words):
    if len(words) < 3:
        print("Please provide a source and destination, for example: cp notes.txt backup.txt")
        return
    if len(words) > 3:
        print("Please provide only a source and destination, for example: cp notes.txt backup.txt")
        return

    source = safe_name(words[1], "source file")
    destination = safe_name(words[2], "destination file")
    if not source or not destination:
        return
    if not source.is_file():
        print(f"Source file does not exist: {source.name}")
        return

    # copy2 preserves useful metadata while still avoiding shell=True entirely.
    shutil.copy2(source, destination)
    print(f"Copied {source.name} to {destination.name}")


def show_gpu_info():
    if not shutil.which("lspci"):
        print("⚠️ lspci is not installed, so GPU information is unavailable.")
        return

    result = subprocess.run(["lspci"], capture_output=True, text=True, check=False)
    gpu_lines = [
        line
        for line in result.stdout.splitlines()
        if any(word in line.lower() for word in ("vga", "3d", "display"))
    ]
    print("\n".join(gpu_lines) if gpu_lines else "No GPU entry found.")


def show_battery_info():
    batteries = sorted(Path("/sys/class/power_supply").glob("BAT*"))
    if not batteries:
        print("No battery information found.")
        return

    for battery in batteries:
        capacity = battery / "capacity"
        status = battery / "status"
        capacity_text = capacity.read_text().strip() if capacity.exists() else "unknown"
        status_text = status.read_text().strip() if status.exists() else "unknown"
        print(f"{battery.name}: {capacity_text}% ({status_text})")


def show_environment_info():
    for key in ("USER", "HOME", "SHELL", "LANG", "TERM", "PATH"):
        print(f"{key}={os.environ.get(key, '')}")


def show_running_processes():
    result = subprocess.run(["ps", "aux", "--sort=-%mem"], capture_output=True, text=True, check=False)
    lines = result.stdout.splitlines()[:11]  # header plus the 10 largest processes
    print("\n".join(lines))


def show_package_manager_info():
    managers = ("apt", "dnf", "pacman", "zypper", "apk")
    found = [manager for manager in managers if shutil.which(manager)]
    print("Detected package manager(s): " + ", ".join(found) if found else "No common package manager detected.")


def show_fastfetch_info():
    if shutil.which("fastfetch"):
        run_command(["fastfetch"])
        return

    print("fastfetch is not installed. Showing safe fallback system information instead.\n")
    for command in (["uname", "-a"], ["lscpu"], ["free", "-h"], ["df", "-h"]):
        print(f"$ {' '.join(command)}")
        run_command(command)
        print()


def handle_command(text):
    words = parse_words(text)
    if not words:
        return

    first_word = words[0].lower()
    if first_word == "help":
        print_help()
        return
    if first_word == "touch":
        handle_touch(words)
        return
    if first_word == "mkdir":
        handle_mkdir(words)
        return
    if first_word == "cp":
        handle_copy(words)
        return

    # Friendly aliases keep file operations easier to discover while still
    # reusing the same strict validation as the terminal-style forms above.
    if words[:2] == ["create", "file"]:
        handle_touch(["touch", *words[2:]])
        return
    if words[:2] == ["create", "folder"]:
        handle_mkdir(["mkdir", *words[2:]])
        return
    if len(words) >= 1 and words[0] == "copy":
        if len(words) == 4 and words[2] == "to":
            handle_copy(["cp", words[1], words[3]])
        else:
            print("Please use: copy source to destination")
        return

    intent = predict_intent(text)
    print(f"[DEBUG] Predicted intent: {intent}")

    handlers = {
        "list_files": lambda: run_command(["ls"]),
        "current_dir": lambda: run_command(["pwd"]),
        "disk_usage": lambda: run_command(["df", "-h"]),
        "memory_usage": lambda: run_command(["free", "-h"]),
        "date_time": lambda: print(datetime.datetime.now()),
        "system_uptime": lambda: run_command(["uptime"]),
        "kernel_info": lambda: run_command(["uname", "-a"]),
        "cpu_info": lambda: run_command(["lscpu"]),
        "current_user": lambda: run_command(["whoami"]),
        "hostname": lambda: run_command(["hostname"]),
        "open_firefox": lambda: launch_background(["firefox"]),
        "calculator": lambda: launch_background(["gnome-calculator"]),
        "os_info": lambda: run_command(["lsb_release", "-a"]) if shutil.which("lsb_release") else run_command(["cat", "/etc/os-release"]),
        "gpu_info": show_gpu_info,
        "battery_info": show_battery_info,
        "network_info": lambda: run_command(["ip", "addr", "show"]),
        "ip_address": lambda: run_command(["ip", "addr", "show"]),
        "logged_in_users": lambda: run_command(["who"]),
        "running_processes": show_running_processes,
        "environment_info": show_environment_info,
        "shell_info": lambda: print(os.environ.get("SHELL", "Unknown shell")),
        "python_version": lambda: run_command(["python3", "--version"]),
        "package_manager_info": show_package_manager_info,
        "fastfetch_info": show_fastfetch_info,
    }

    handler = handlers.get(intent)
    if handler:
        handler()
    else:
        print("❓ Command not recognized")
