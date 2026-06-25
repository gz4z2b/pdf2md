import subprocess
from pathlib import Path


def test_convert_script_has_valid_bash_syntax():
    project_root = Path(__file__).resolve().parents[1]
    script_path = project_root / "scripts" / "convert.sh"

    result = subprocess.run(
        ["bash", "-n", str(script_path)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
