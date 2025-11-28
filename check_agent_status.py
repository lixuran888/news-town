import json, sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')

storage = Path(r"e:\generative_agents-main\environment\frontend_server\storage")
sims = sorted([p for p in storage.iterdir() if p.is_dir() and p.name.startswith("auto_run")], 
              key=lambda p: p.stat().st_mtime, reverse=True)

if not sims:
    print("No simulation found")
    exit()

latest = sims[0]
print(f"Simulation: {latest.name}")
print()

movement_dir = latest / "movement"
if not movement_dir.exists() or not list(movement_dir.glob("*.json")):
    print("No movement data yet. Checking personas folder...")
    personas_dir = latest / "personas"
    if personas_dir.exists():
        for p in sorted(personas_dir.iterdir()):
            scratch = p / "bootstrap_memory" / "scratch.json"
            if scratch.exists():
                with open(scratch, encoding="utf-8") as f:
                    s = json.load(f)
                desc = s.get("act_description") or "(no action yet)"
                sleeping = "sleeping" in desc.lower() if desc else False
                marker = "💤 SLEEPING" if sleeping else "✓ Active"
                print(f"{marker:15} {p.name:35} {desc[:45] if desc else ''}")
    exit()

if movement_dir.exists():
    files = sorted(movement_dir.glob("*.json"), key=lambda f: int(f.stem))
    if files:
        latest_move = files[-1]
        with open(latest_move, encoding="utf-8") as f:
            data = json.load(f)
        
        meta = data.get("meta", {})
        print(f"Step: {latest_move.stem}")
        print(f"Time: {meta.get('curr_time', '?')}")
        print()
        print("All agents status:")
        print("=" * 80)
        
        personas = data.get("persona", {})
        sleeping_list = []
        for name, info in sorted(personas.items()):
            desc = info.get("description", "(no description)")
            sleeping = "sleeping" in desc.lower()
            if sleeping:
                sleeping_list.append(name)
                marker = "💤 SLEEPING"
            else:
                marker = "✓ Active"
            print(f"{marker:15} {name:35} {desc[:45]}")
        
        print()
        print("=" * 80)
        if sleeping_list:
            print(f"💤 Sleeping agents: {', '.join(sleeping_list)}")
        else:
            print("✓ No one is sleeping!")
