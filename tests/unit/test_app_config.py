import importlib.util
import sys
from pathlib import Path


def test_database_url_conversion(monkeypatch, tmp_path):
    module_name = "app_config_under_test"
    app_path = Path(__file__).resolve().parents[2] / "app.py"

    monkeypatch.setenv("DATABASE_URL", "postgres://example.com/db")
    monkeypatch.chdir(tmp_path)

    spec = importlib.util.spec_from_file_location(module_name, app_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        assert spec.loader is not None
        spec.loader.exec_module(module)

        configured_uri = module.app.config["SQLALCHEMY_DATABASE_URI"]
        assert configured_uri == "postgresql://example.com/db"
        assert module.os.environ["DATABASE_URL"] == configured_uri
    finally:
        sys.modules.pop(module_name, None)
        if hasattr(module, "db"):
            with module.app.app_context():
                module.db.session.remove()
