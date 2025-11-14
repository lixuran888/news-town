import argparse
import datetime
import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path


def find_latest_sim(storage_dir: Path) -> str:
    candidates = [p for p in storage_dir.iterdir() if p.is_dir()]
    # 只选择包含 reverie/meta.json 且存在 environment 目录的有效仿真
    valid = []
    for p in candidates:
        if (p / "reverie" / "meta.json").exists() and (p / "environment").exists():
            valid.append(p)
    if not valid:
        return ""
    valid.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return valid[0].name


def run_migrate(frontend_dir: Path) -> int:
    cmd = [sys.executable, "manage.py", "migrate"]
    res = subprocess.run(cmd, cwd=str(frontend_dir))
    return res.returncode


def start_django(frontend_dir: Path, port: int) -> subprocess.Popen:
    addr = f"127.0.0.1:{port}" if port else None
    cmd = [sys.executable, "manage.py", "runserver"]
    if addr:
        cmd.append(addr)
    return subprocess.Popen(cmd, cwd=str(frontend_dir))


def start_reverie(reverie_py: Path, reverie_dir: Path, origin: str, target: str, autorun_steps: int = 0) -> subprocess.Popen:
    p = subprocess.Popen([sys.executable, str(reverie_py)], cwd=str(reverie_dir), stdin=subprocess.PIPE)
    try:
        # reverie.py expects two input lines: origin and target
        init_input = f"{origin}\n{target}\n".encode("utf-8")
        p.stdin.write(init_input)
        p.stdin.flush()
        # Optionally kick off steps automatically so no interactive typing is needed
        if autorun_steps and autorun_steps > 0:
            cmd = f"run {autorun_steps}\n".encode("utf-8")
            p.stdin.write(cmd)
            p.stdin.flush()
    except Exception:
        pass
    return p


def start_reverie_auto_tick(proc: subprocess.Popen, tick: int, interval: float):
    def _writer():
        # Small initial delay to allow OpenServer to initialize fully
        time.sleep(0.5)
        while True:
            if proc.poll() is not None:
                break
            try:
                cmd = f"run {tick}\n".encode("utf-8")
                if proc.stdin:
                    proc.stdin.write(cmd)
                    proc.stdin.flush()
            except Exception:
                break
            time.sleep(max(0.05, interval))
    th = threading.Thread(target=_writer, daemon=True)
    th.start()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--origin", type=str, default="")
    parser.add_argument("--target", type=str, default="")
    parser.add_argument("--autorun", type=int, default=0, help="Number of steps to auto-run once after starting Reverie. Set 0 to disable.")
    parser.add_argument("--tick", type=int, default=1, help="Auto-ticking: steps per tick. 0 to disable continuous ticking.")
    parser.add_argument("--interval", type=float, default=0.5, help="Auto-ticking interval seconds between ticks.")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent
    frontend_dir = root / "environment" / "frontend_server"
    reverie_dir = root / "generative_agents-main" / "reverie" / "backend_server"
    reverie_py = reverie_dir / "reverie.py"
    storage_dir = frontend_dir / "storage"

    if not frontend_dir.exists() or not (frontend_dir / "manage.py").exists():
        print("未找到前端目录或 manage.py。请确认项目结构。")
        sys.exit(1)
    if not reverie_py.exists():
        print("未找到 reverie.py。请确认路径: ", reverie_py)
        sys.exit(1)
    if not storage_dir.exists():
        print("未找到存储目录: ", storage_dir)
        sys.exit(1)

    origin = args.origin.strip() or find_latest_sim(storage_dir)
    if not origin:
        print("未找到可用的仿真源，请先在 storage 下放置一个仿真文件夹。")
        sys.exit(1)

    target = args.target.strip() or ("auto_run_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S"))

    print("[1/3] 运行数据库迁移...")
    rc = run_migrate(frontend_dir)
    if rc != 0:
        print("迁移失败，已退出。")
        sys.exit(rc)

    print(f"[2/3] 启动 Django 前端 (port={args.port}) ...")
    django_proc = start_django(frontend_dir, args.port)

    print(f"[3/3] 启动 Reverie 后端，origin='{origin}', target='{target}' ...")
    reverie_proc = start_reverie(reverie_py, reverie_dir, origin, target, args.autorun)
    if args.tick > 0 and args.interval > 0:
        print(f"[AutoTick] 每 {args.interval}s 推进 {args.tick} 步（可用 stop_project.bat 停止）")
        start_reverie_auto_tick(reverie_proc, args.tick, args.interval)

    print("已启动。按 Ctrl+C 结束所有进程。")

    try:
        # Wait until one of the processes exits
        while True:
            rc_d = django_proc.poll()
            rc_r = reverie_proc.poll()
            if rc_d is not None:
                print(f"Django 进程退出，代码 {rc_d}。正在终止 Reverie...")
                if rc_r is None:
                    reverie_proc.terminate()
                break
            if rc_r is not None:
                print(f"Reverie 进程退出，代码 {rc_r}。正在终止 Django...")
                if rc_d is None:
                    django_proc.terminate()
                break
            # sleep a bit
            try:
                import time
                time.sleep(0.5)
            except Exception:
                pass
    except KeyboardInterrupt:
        print("收到中断信号，正在关闭子进程...")
        for p in [django_proc, reverie_proc]:
            try:
                if p.poll() is None:
                    if os.name == "nt":
                        p.send_signal(signal.CTRL_BREAK_EVENT)
                    p.terminate()
            except Exception:
                pass

    # Ensure processes are closed
    for p in [django_proc, reverie_proc]:
        try:
            if p.poll() is None:
                p.kill()
        except Exception:
            pass

    print("已退出。")


if __name__ == "__main__":
    main()
