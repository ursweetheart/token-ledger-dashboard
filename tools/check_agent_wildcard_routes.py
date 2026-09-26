from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "docker" / "gateway" / "config.gateway.yaml"


def require_route(routes: list[str], model_name: str, provider_key: str, tag: str) -> None:
    selected = [
        route.split("\ngeneral_settings:", 1)[0]
        for route in routes
        if route.splitlines()[0].strip() == f'"{model_name}"'
        and re.search(rf'^      tags: \["{re.escape(tag)}"\]$', route, re.MULTILINE)
    ]
    assert len(selected) == 1, f"{tag} needs exactly one {model_name} route"
    assert re.search(r'^      model: "gemini/\*"$', selected[0], re.MULTILINE)
    assert re.search(
        rf"^      api_key: os\.environ/{re.escape(provider_key)}$",
        selected[0],
        re.MULTILINE,
    )


def main() -> None:
    config = CONFIG.read_text(encoding="utf-8")
    routes = re.split(r"^  - model_name:", config, flags=re.MULTILINE)[1:]
    require_route(routes, "gemini/*", "KEY_GOOGLE_AI_STU", "dms-feedback")
    require_route(routes, "gemini/*", "KEY_CRM_FEEDBACK", "crm-feedback")
    require_route(routes, "gemini/*", "KEY_TLA_HD", "tla-hd")
    require_route(routes, "*", "KEY_RALLI", "ralli")
    assert re.search(r"^  enable_tag_filtering: true$", config, re.MULTILINE)

    expected = {
        ROOT / "docker-compose.yml": "KEY_TLA_HD: ${KEY_TLA_HD:-}",
        ROOT / "docker-compose.bench.yml": (
            'KEY_TLA_HD: "KHONG-PHAI-KHOA-THAT-bench-khong-duoc-goi-ra-ngoai"'
        ),
        ROOT / "docker" / "gateway" / "entrypoint.sh": "KEY_RALLI KEY_TLA_HD DATABASE_URL",
        ROOT / ".env.example": "KEY_TLA_HD=",
    }
    for path, marker in expected.items():
        assert marker in path.read_text(encoding="utf-8"), path

    print("PASS: DMS, CRM, Law Insight and Ralli Gemini wildcard routes are isolated by tag")


if __name__ == "__main__":
    main()
