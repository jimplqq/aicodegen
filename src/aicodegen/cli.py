from __future__ import annotations

import argparse
import json
from pathlib import Path

from .generator import CrudGenerator
from .mcp_server import run_stdio_server
from .runtime import RuntimeService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="aicodegen")
    parser.add_argument(
        "--workspace",
        default=".",
        help="Workspace path. Defaults to the current directory.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)
    init = subparsers.add_parser("init", help="Initialize .agent state for the workspace.")
    init.add_argument("--language", help="Override the detected project language.")
    init.add_argument("--framework", help="Override the detected project framework.")
    init.add_argument("--template-root", help="Template root path relative to the workspace or absolute.")
    init.add_argument("--build-command", help="Optional build command stored in workspace configuration.")
    init.add_argument("--test-command", help="Optional test command stored in workspace configuration.")
    init.add_argument("--force", action="store_true", help="Replace existing workspace configuration with fresh defaults before applying overrides.")
    subparsers.add_parser("detect", help="Detect the workspace language and stack.")
    subparsers.add_parser("status", help="Show workspace runtime status.")
    subparsers.add_parser("mcp", help="Run the MCP stdio entry point.")
    ensure_template = subparsers.add_parser("ensure-template", help="Ensure a learned template exists for a tool.")
    ensure_template.add_argument("--tool", default="crud_generator", help="Tool name to prepare. Defaults to crud_generator.")
    generate = subparsers.add_parser("generate", help="Generate code artifacts from workspace presets.")
    generate_subparsers = generate.add_subparsers(dest="generate_command", required=True)
    crud = generate_subparsers.add_parser("crud", help="Generate CRUD scaffold code.")
    crud.add_argument("--entity", required=True, help="Entity name, for example DemoFeature.")
    crud.add_argument("--comment", help="Human-readable comment used in generated files.")
    entity = generate_subparsers.add_parser("entity", help="Generate only the entity/domain scaffold.")
    entity.add_argument("--entity", required=True, help="Entity name, for example DeviceLedger.")
    entity.add_argument("--comment", help="Human-readable comment used in generated files.")
    feature = generate_subparsers.add_parser("feature", help="Generate a feature scaffold with automatic entity inference.")
    feature.add_argument("--name", required=True, help="Feature name, for example 设备台账.")
    feature.add_argument("--entity", help="Optional explicit entity name, for example DeviceLedger.")
    feature.add_argument("--spec-file", help="Optional JSON file with structured generation parameters.")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    workspace = Path(args.workspace).resolve()
    service = RuntimeService(workspace)

    if args.command == "init":
        print(
            json.dumps(
                service.init_workspace(
                    language=getattr(args, "language", None),
                    framework=getattr(args, "framework", None),
                    template_root=getattr(args, "template_root", None),
                    build_command=getattr(args, "build_command", None),
                    test_command=getattr(args, "test_command", None),
                    force=bool(getattr(args, "force", False)),
                ),
                indent=2,
                ensure_ascii=False,
            )
        )
        return
    if args.command == "detect":
        print(json.dumps(service.detect_workspace(), indent=2, ensure_ascii=False))
        return
    if args.command == "status":
        print(json.dumps(service.status(), indent=2, ensure_ascii=False))
        return
    if args.command == "mcp":
        raise SystemExit(run_stdio_server(workspace))
    if args.command == "ensure-template":
        print(json.dumps(service.ensure_template(args.tool), indent=2, ensure_ascii=False))
        return
    if args.command == "generate":
        if args.generate_command == "feature":
            spec_data = None
            if getattr(args, "spec_file", None):
                spec_path = Path(args.spec_file).resolve()
                spec_data = json.loads(spec_path.read_text(encoding="utf-8"))
            print(
                json.dumps(
                    service.generate_feature(
                        args.name,
                        entity_name=getattr(args, "entity", None),
                        spec_data=spec_data,
                    ),
                    indent=2,
                    ensure_ascii=False,
                )
            )
            return
        tools_config = service.storage.load_tools_config()
        if args.generate_command == "entity":
            generated = CrudGenerator(workspace, tools_config).generate_entity(
                args.entity,
                comment=getattr(args, "comment", None),
            )
            print(
                json.dumps(
                    {
                        "workspace": str(workspace),
                        "entity": args.entity,
                        "generated_file": {"kind": generated.kind, "path": str(generated.path)},
                    },
                    indent=2,
                    ensure_ascii=False,
                )
            )
            return
        if args.generate_command == "crud":
            generated = CrudGenerator(workspace, tools_config).generate(
                args.entity,
                comment=getattr(args, "comment", None),
            )
            print(
                json.dumps(
                    {
                        "workspace": str(workspace),
                        "entity": args.entity,
                        "generated_files": [
                            {"kind": item.kind, "path": str(item.path)}
                            for item in generated
                        ],
                    },
                    indent=2,
                    ensure_ascii=False,
                )
            )
            return

    parser.error(f"Unknown command: {args.command}")


if __name__ == "__main__":
    main()
