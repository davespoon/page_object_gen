from pathlib import Path
import tempfile
from pog.tools.sln_finder import find_nearest_sln


def test_find_nearest_sln_walks_upward():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "Repo.sln").write_text("Fake solution", encoding="utf-8")

        nested = root / "a" / "b" / "c"
        nested.mkdir(parents=True)

        found = find_nearest_sln(nested)
        assert found is not None
        assert found.name == "Repo.sln"
