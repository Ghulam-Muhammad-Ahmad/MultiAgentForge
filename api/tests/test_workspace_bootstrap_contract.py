import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _function_source(path: Path, function_name: str) -> str:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function_name:
            return ast.get_source_segment(source, node) or ""
    raise AssertionError(f"{function_name} not found in {path}")


class WorkspaceBootstrapContractTest(unittest.TestCase):
    def test_project_creation_queues_workspace_initialization(self) -> None:
        source = _function_source(ROOT / "routers" / "projects.py", "create_project")

        self.assertIn("init_workspace.delay(project.id)", source)
        self.assertIn("workspace.initialization_queued", source)

    def test_pm_agent_initializes_workspace_before_analyzing_requirements(self) -> None:
        source = _function_source(ROOT / "workers" / "orchestrator.py", "_run_pm_agent")

        workspace_index = source.index("await _init_workspace(project_id)")
        analyze_index = source.index("analysis = await analyze_requirements(doc.raw_content, project.name, project_id)")

        self.assertLess(workspace_index, analyze_index)

    def test_pm_analysis_receives_existing_workspace_context(self) -> None:
        source = _function_source(ROOT / "agents" / "pm_agent.py", "_workspace_context")

        self.assertIn("Astro + TailwindCSS boilerplate has already been created", source)
        self.assertIn("Do not create project setup tickets", source)
        self.assertIn("src/layouts/MainLayout.astro", source)

    def test_docker_compose_mounts_shared_workspace_volume(self) -> None:
        compose = (ROOT.parent / "docker-compose.yml").read_text(encoding="utf-8")

        self.assertIn("workspaces:/workspaces", compose)

    def test_agent_cannot_mark_done_after_failed_command(self) -> None:
        source = _function_source(ROOT / "agents" / "base_agent.py", "execute")

        self.assertIn("command_failed = False", source)
        self.assertIn("command_failed = True", source)
        self.assertIn("command_failed = False  # successful build clears earlier failed attempt", source)
        self.assertIn("if command_failed and args.get(\"outcome\") == \"done\":", source)

    def test_npm_scripts_install_dependencies_before_running(self) -> None:
        source = _function_source(ROOT / "agents" / "base_agent.py", "_handle_run_command")
        full_source = (ROOT / "agents" / "base_agent.py").read_text(encoding="utf-8")

        self.assertIn("if command.startswith(\"npm run \"):", source)
        self.assertIn("npm install", full_source)
        self.assertIn("node_modules", full_source)
