from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def test_preview_tools_require_explicit_credentials_without_echoing_them() -> None:
    seed = (REPOSITORY_ROOT / "scripts" / "seed_ops_preview.py").read_text()
    host_launcher = (REPOSITORY_ROOT / "scripts" / "run_ops_preview.sh").read_text()
    replit_launcher = (REPOSITORY_ROOT / "scripts" / "run_ops_preview_replit.sh").read_text()
    ui_smoke = (REPOSITORY_ROOT / "scripts" / "ui_smoke_cdp.mjs").read_text()

    assert 'os.environ["OPS_PREVIEW_EMAIL"]' in seed
    assert 'os.environ["OPS_PREVIEW_PASSWORD"]' in seed
    assert 'os.environ.get("OPS_PREVIEW_EMAIL"' not in seed
    assert 'os.environ.get("OPS_PREVIEW_PASSWORD"' not in seed

    for launcher in (host_launcher, replit_launcher):
        assert ': "${OPS_PREVIEW_EMAIL:?' in launcher
        assert ': "${OPS_PREVIEW_PASSWORD:?' in launcher
        assert "Password:" not in launcher
        assert "login founder@" not in launcher

    assert "const EMAIL = process.env.DEMO_EMAIL;" in ui_smoke
    assert "const PASSWORD = process.env.DEMO_PASSWORD;" in ui_smoke
    assert "if (!EMAIL || !PASSWORD)" in ui_smoke
