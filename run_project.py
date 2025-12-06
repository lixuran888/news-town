import argparse
import datetime
import os
import signal
import subprocess
import sys
import threading
import time
import json
from pathlib import Path

# 尝试导入 requests，如果失败则使用 urllib
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    try:
        import urllib.request
        import urllib.parse
    except ImportError:
        pass


def find_latest_sim(storage_dir: Path) -> str:
    candidates = [p for p in storage_dir.iterdir() if p.is_dir()]
    # 只选择包含完整数据的有效仿真
    valid = []
    for p in candidates:
        meta_exists = (p / "reverie" / "meta.json").exists()
        env_exists = (p / "environment").exists()
        personas_dir = p / "personas"
        # personas 目录必须存在，且至少一个 persona 有 scratch.json
        personas_valid = False
        if personas_dir.exists():
            for persona in personas_dir.iterdir():
                if persona.is_dir() and (persona / "bootstrap_memory" / "scratch.json").exists():
                    personas_valid = True
                    break
        if meta_exists and env_exists and personas_valid:
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


def wait_for_django(port: int, timeout: int = 30) -> bool:
    """等待 Django 服务器启动"""
    url = f"http://127.0.0.1:{port}/check_start_time_configured/"
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            if HAS_REQUESTS:
                response = requests.get(url, timeout=2)
                if response.status_code == 200:
                    return True
            else:
                # 使用 urllib
                req = urllib.request.Request(url)
                with urllib.request.urlopen(req, timeout=2) as response:
                    if response.status == 200:
                        return True
        except:
            pass
        time.sleep(0.5)
    return False


def check_start_time_configured(port: int) -> bool:
    """检查开始时间是否已配置"""
    url = f"http://127.0.0.1:{port}/check_start_time_configured/"
    try:
        if HAS_REQUESTS:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                return data.get("configured", False)
        else:
            # 使用 urllib
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode('utf-8'))
                    return data.get("configured", False)
    except Exception as e:
        print(f"检查开始时间配置失败: {e}")
    return False


def start_reverie(reverie_py: Path, reverie_dir: Path, origin: str, target: str, autorun_steps: int = 0) -> subprocess.Popen:
    """
    启动 reverie.py 进程，使用 PIPE 模式由程序控制输入。
    """
    p = subprocess.Popen([sys.executable, str(reverie_py)], cwd=str(reverie_dir), stdin=subprocess.PIPE)
    try:
        # reverie.py expects two input lines: origin and target
        init_input = f"{origin}\n{target}\n".encode("utf-8")
        p.stdin.write(init_input)
        p.stdin.flush()
        # Optionally kick off steps automatically
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
        time.sleep(2.0)  # 增加初始延迟，确保 reverie 完全启动
        tick_count = 0
        while True:
            if proc.poll() is not None:
                print(f"[AutoTick] Reverie process ended, stopping auto-tick")
                break
            try:
                cmd = f"run {tick}\n".encode("utf-8")
                if proc.stdin:
                    proc.stdin.write(cmd)
                    proc.stdin.flush()
                    tick_count += 1
                    if tick_count % 100 == 0:
                        print(f"[AutoTick] Sent {tick_count} ticks")
                else:
                    print("[AutoTick] stdin is None!")
                    break
            except Exception as e:
                print(f"[AutoTick] Error: {e}")
                break
            time.sleep(max(0.05, interval))
        print(f"[AutoTick] Thread ended after {tick_count} ticks")
    th = threading.Thread(target=_writer, daemon=True)
    th.start()
    print("[AutoTick] Thread started")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--origin", type=str, default="")
    parser.add_argument("--target", type=str, default="")
    parser.add_argument("--autorun", type=int, default=0, help="Number of steps to auto-run once after starting Reverie. Set 0 to disable.")
    parser.add_argument("--tick", type=int, default=100, help="Auto-ticking: steps per tick. 0 to disable continuous ticking.")
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

    print("[1/4] 运行数据库迁移...")
    rc = run_migrate(frontend_dir)
    if rc != 0:
        print("迁移失败，已退出。")
        sys.exit(rc)

    print(f"[2/4] 启动 Django 前端 (port={args.port}) ...")
    django_proc = start_django(frontend_dir, args.port)
    
    # 等待 Django 启动
    print("等待 Django 服务器启动...")
    if not wait_for_django(args.port, timeout=30):
        print("Django 服务器启动超时，已退出。")
        django_proc.terminate()
        sys.exit(1)
    print("Django 服务器已启动。")
    
    # 无论如何都先打开时间设置页面
    print("[3/4] 打开时间设置页面...")
    # 等待一下确保 Django 完全启动
    time.sleep(2)
    setup_url = f"http://127.0.0.1:{args.port}/start_time_setup/"
    try:
        import webbrowser
        webbrowser.open(setup_url)
    except:
        print(f"无法自动打开浏览器，请手动访问: {setup_url}")
    
    # 记录配置文件的初始修改时间
    config_file = frontend_dir / "temp_storage" / "start_time_config.json"
    initial_mtime = None
    if config_file.exists():
        initial_mtime = config_file.stat().st_mtime
    
    print("\n" + "="*60)
    print("请在设置页面确认或修改开始时间，然后点击保存...")
    print("保存完成后会自动启动后端")
    print("="*60)
    
    # 等待配置文件被更新（说明用户保存了）
    max_wait = 300  # 5分钟
    check_interval = 1  # 每1秒检查一次
    waited = 0
    while waited < max_wait:
        if config_file.exists():
            current_mtime = config_file.stat().st_mtime
            # 如果文件被更新了（修改时间变化），说明用户保存了
            if initial_mtime is None or current_mtime > initial_mtime:
                print("检测到时间配置已保存！正在启动后端...")
                break
        time.sleep(check_interval)
        waited += check_interval
        if waited % 10 == 0:
            print(f"等待保存中... ({waited}/{max_wait}秒)")
    else:
        print("等待超时，未检测到保存操作，退出。")
        django_proc.terminate()
        sys.exit(1)
    
    # 时间配置完成后，如果页面未自动跳转，提示用户
    home_url = f"http://127.0.0.1:{args.port}/simulator_home"
    print(f"如果页面未自动跳转到仿真界面，请手动访问: {home_url}")

    print(f"[4/4] 启动 Reverie 后端，origin='{origin}', target='{target}' ...")
    
    reverie_proc = start_reverie(reverie_py, reverie_dir, origin, target, args.autorun)
    if args.tick > 0 and args.interval > 0:
        print(f"[AutoTick] 每 {args.interval}s 推进 {args.tick} 步")
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
