import gzip
import json
from pathlib import Path

from editorial import _write_spellchecker_dictionary_file


def test_write_spellchecker_dictionary_file(tmp_path: Path) -> None:
    payload = gzip.compress(json.dumps({"hello": 1}).encode("utf-8"))
    target = tmp_path / "dictionary.json"

    written_path = _write_spellchecker_dictionary_file(payload, str(target))

    assert written_path == str(target)
    assert json.loads(target.read_text(encoding="utf-8")) == {"hello": 1}
