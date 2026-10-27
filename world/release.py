from pathlib import Path
def release_evidence(root, run_id, text):
    p = Path(root) / 'world' / 'follow_up'
    p.mkdir(parents=True, exist_ok=True)
    f = p / f'{run_id}.txt'
    f.write_text(str(text) + '\n')
    return str(f)
