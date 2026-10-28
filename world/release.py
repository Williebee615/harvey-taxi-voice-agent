"""Write a local follow-up only for an existing validated run ID."""
from pathlib import Path
from agent_kit import progress

def release_evidence(root, run_id, text):
    progress.load_progress(root, run_id)
    progress.run_path(root, run_id)
    path = Path(root) / 'world' / 'follow_up'
    path.mkdir(parents=True, exist_ok=True)
    target = path / (run_id + '.txt')
    target.write_text(str(text) + '\n')
    return str(target)
