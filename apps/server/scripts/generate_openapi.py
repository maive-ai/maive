import argparse
import json
import sys
from pathlib import Path
from typing import Optional


def generate_openapi(output_path: Optional[Path] = None) -> Path:
    try:
        # Add project root to path so we can import the app
        project_root = Path(__file__).parent.parent
        sys.path.insert(0, str(project_root))

        from src.main import app

        openapi_spec = app.openapi()

        # Default output path
        if output_path is None:
            output_path = Path(__file__).parent.parent / "openapi.json"

        # Ensure directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as f:
            json.dump(openapi_spec, f, indent=2)

        print(f"✅ OpenAPI spec generated at: {output_path}")
        return output_path

    except ImportError as e:
        print(f"❌ Failed to import FastAPI app: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Failed to generate OpenAPI spec: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Generate OpenAPI spec from FastAPI app"
    )
    parser.add_argument(
        "--output", "-o", type=Path, help="Output path for OpenAPI spec"
    )
    args = parser.parse_args()

    generate_openapi(args.output)


if __name__ == "__main__":
    main()
