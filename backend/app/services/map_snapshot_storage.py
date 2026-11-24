from pathlib import Path

from ..core.config import BASE_DIR

MAP_SNAPSHOT_DIR = BASE_DIR / "backend" / "storage" / "map_snapshots"


def resolve_map_snapshot_path(stored_path: str | None) -> Path | None:
    if not stored_path:
        return None

    stored = Path(stored_path)
    storage_dir = MAP_SNAPSHOT_DIR.resolve()
    if stored.is_absolute():
        snapshot_path = stored.resolve()
    else:
        expected_relative_dir = Path("backend") / "storage" / "map_snapshots"
        if stored.parent != expected_relative_dir:
            return None
        snapshot_path = (BASE_DIR / stored).resolve()
    if snapshot_path.parent != storage_dir or not snapshot_path.is_file():
        return None
    return snapshot_path
