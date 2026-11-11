"""Independent changed-inventory/compiler/notice refusal cases; actual native packaging observes the real wheel. Jason Stys."""
# Index: declarations module.fixture_observations@L17, module.test_inventory_projection_ignores_only_unclaimed_metadata@L34, module.test_complete_component_identity_refuses_unreviewed_scope@L63, module.test_missing_different_or_mixed_compilers_fail_closed@L94, module.test_captured_original_texts_are_not_silently_replaced@L110, module.test_actual_provider_observation_and_bounded_source_reader@L123; variables LICENSES@L14, inventory@L19, components@L20, row@L26, monkeypatch@L34, module@L36, sbom@L36, blocks@L43, receipt@L43, fault@L63, monkeypatch@L63, module@L65, sbom@L65, rows@L66, module@L94, monkeypatch@L94, _@L96, sbom@L96, monkeypatch@L110, name@L110, tmp_path@L110, source@L112, path@L115, module@L117, sbom@L117, tmp_path@L123, module@L125, sbom@L125, source@L127. Purposes/parameters: docs/code-map.json.

import copy
import hashlib
import json
import shutil
from pathlib import Path

import pytest

from scripts import runtime_terms as terms

LICENSES = Path(__file__).resolve().parents[1] / "licenses"


def fixture_observations():
    """Use the captured provider's exact public39-component declaration and an explicit inert compiler-marker fixture."""
    inventory = json.loads((LICENSES / "cryptography-50.0.2-rust-inventory.json").read_bytes())
    components = inventory["internalComponents"] + [
        {
            "name": row["name"],
            "version": row["version"],
            "licenses": row["declaredLicenses"],
        }
        for row in inventory["externalComponents"]
    ]
    return {
        "components": components,
        "metadata": {"provider_local_path": "omitted"},
    }, b"fixture/rustc/" + terms.COMPILER.encode() + b"/library/std"


def test_inventory_projection_ignores_only_unclaimed_metadata(monkeypatch):
    """Row order and provider-local paths cannot change known name/version/license terms or leak into public receipts."""
    sbom, module = fixture_observations()
    sbom["components"].reverse()
    sbom["metadata"] = {
        "provider_local_path": "PRIVATE-PROVIDER-PATH",
        "timestamp": "different-OS-build",
    }
    monkeypatch.setattr(terms, "observations", lambda: (json.dumps(sbom).encode(), module))
    blocks, receipt = terms.collect(LICENSES)
    assert receipt["externalCrates"] == 32 and receipt["originalNoticeFiles"] == 62
    assert receipt["actualModuleSha256"] == hashlib.sha256(module).hexdigest()
    assert b"unicode-ident-1.0.24" in blocks and b"target-lexicon-0.13.5" in blocks
    assert b"Copyright notices for The Rust Standard Library" in blocks
    assert "PRIVATE-PROVIDER-PATH" not in json.dumps(receipt)


@pytest.mark.parametrize(
    "fault",
    [
        "missing",
        "extra",
        "duplicate",
        "version",
        "license",
        "license-shape",
        "identity",
    ],
)
def test_complete_component_identity_refuses_unreviewed_scope(monkeypatch, fault):
    """No missing/duplicated/changed component or alternate license may borrow a previously reviewed term set."""
    sbom, module = fixture_observations()
    rows = sbom["components"]
    if fault == "missing":
        rows.pop()
    elif fault == "extra":
        rows.append(copy.deepcopy(rows[0]))
    elif fault == "duplicate":
        rows[1] = copy.deepcopy(rows[0])
    elif fault == "version":
        rows[0]["version"] = "99.0.0"
    elif fault == "license":
        rows[0]["licenses"] = [{"expression": "LicenseRef-UNREVIEWED"}]
    elif fault == "license-shape":
        rows[0]["licenses"] = [{"name": "not-the-provider-expression"}]
    else:
        rows[0]["name"] = "../../foreign"
    monkeypatch.setattr(terms, "observations", lambda: (json.dumps(sbom).encode(), module))
    with pytest.raises(ValueError):
        terms.collect(LICENSES)


@pytest.mark.parametrize(
    "module",
    [
        b"no compiler observation",
        b"/rustc/" + b"b" * 40 + b"/library",
        b"/rustc/" + terms.COMPILER.encode() + b"/library /rustc/" + b"b" * 40 + b"/library",
    ],
)
def test_missing_different_or_mixed_compilers_fail_closed(monkeypatch, module):
    """Other operating systems must be observed, never admitted under the Windows binary hash by assumption."""
    sbom, _ = fixture_observations()
    monkeypatch.setattr(terms, "observations", lambda: (json.dumps(sbom).encode(), module))
    with pytest.raises(ValueError, match="compiler identity"):
        terms.collect(LICENSES)


@pytest.mark.parametrize(
    "name",
    [
        "cryptography-50.0.2-rust-inventory.json",
        "cryptography-50.0.2-rust-notices.txt",
        "RUST-COPYRIGHT-library.html",
    ],
)
def test_captured_original_texts_are_not_silently_replaced(tmp_path, monkeypatch, name):
    """Actual source text corruption is refused before a package can claim the reviewed original notice identities."""
    for source in LICENSES.glob("*"):
        if source.is_file():
            shutil.copyfile(source, tmp_path / source.name)
    path = tmp_path / name
    path.write_bytes(path.read_bytes() + b"changed")
    sbom, module = fixture_observations()
    monkeypatch.setattr(terms, "observations", lambda: (json.dumps(sbom).encode(), module))
    with pytest.raises(ValueError, match="identity changed"):
        terms.collect(tmp_path)


def test_actual_provider_observation_and_bounded_source_reader(tmp_path):
    """Read the installed wheel's actual declared inventory; this is source metadata, not a native runtime/compiler claim."""
    sbom, module = terms.observations()
    assert len(terms.normalized(json.loads(sbom)["components"])) == 39 and len(module) > 100000
    source = tmp_path / "bounded.txt"
    source.write_bytes(b"abc")
    assert terms.bounded(source, 3) == b"abc"
    with pytest.raises(ValueError):
        terms.bounded(source, 2)
    with pytest.raises((ValueError, OSError)):
        terms.bounded(tmp_path, 100)
    with pytest.raises(ValueError):
        json.loads('{"same":1,"same":2}', object_pairs_hook=terms.unique)
