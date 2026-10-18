# /// script
# requires-python = ">=3.12"
# dependencies = ["PyGithub>=2.1.0", "jinja2>=3.0.0", "rich>=13.0.0", "typer>=0.12.0", "pyyaml>=6.0"]
# ///
"""Regresiones de selección y publicación; no acceden a GitHub."""

from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

from github import GithubException
from typer.testing import CliRunner
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts import common, gen_repo_readme, sync_readme, sync_repos


def subject_repo(name="isi-2008-fisica-i"):
    repo = Mock()
    repo.name = name
    repo.archived = False
    repo.private = False
    repo.description = "Física I"
    repo.default_branch = "main"
    repo.html_url = f"https://github.com/apuntes-frre/{name}"
    return repo


class SyncTests(unittest.TestCase):
    def setUp(self):
        self.repo = subject_repo()
        self.org = Mock()
        self.org.get_repos.return_value = [self.repo]
        self.created_repos = []

        def create_repo(name, **kwargs):
            repo = subject_repo(name)
            repo.get_contents.side_effect = GithubException(404, {}, {})
            self.created_repos.append(repo)
            return repo

        self.org.create_repo.side_effect = create_repo
        client = Mock()
        client.get_organization.return_value = self.org
        self.client_patch = patch.object(sync_repos, "_client", return_value=client)
        self.client_patch.start()
        self.addCleanup(self.client_patch.stop)
        self.env_patch = patch.dict(os.environ, {"GITHUB_ACTIONS": "false"})
        self.env_patch.start()
        self.addCleanup(self.env_patch.stop)
        self.runner = CliRunner()

    def test_sync_2023_never_archives_2008(self):
        result = self.runner.invoke(
            sync_repos.app,
            ["manifest", "sync", "isi", "--plan", "2023", "--archive", "--apply"],
        )
        self.assertEqual(result.exit_code, 0, result.output)
        self.repo.edit.assert_not_called()
        self.assertEqual(self.org.create_repo.call_count, 36)
        self.assertTrue(
            all(
                c.args[0].startswith("isi-2023-")
                for c in self.org.create_repo.call_args_list
            )
        )

    def test_sync_only_archives_selected_plan_extras(self):
        extra = subject_repo("isi-2008-extra")
        other_plan = subject_repo("isi-2023-fisica-i")
        other_career = subject_repo("lic-2008-fisica-i")
        self.org.get_repos.return_value += [extra, other_plan, other_career]
        result = self.runner.invoke(
            sync_repos.app, ["manifest", "sync", "isi", "--archive", "--apply"]
        )
        self.assertEqual(result.exit_code, 0, result.output)
        extra.edit.assert_called_once_with(archived=True)
        other_plan.edit.assert_not_called()
        other_career.edit.assert_not_called()

    def test_sync_dry_run_never_creates_edits_or_archives(self):
        self.repo.description = "Nombre viejo"
        extra = subject_repo("isi-2008-extra")
        self.org.get_repos.return_value.append(extra)
        result = self.runner.invoke(
            sync_repos.app, ["manifest", "sync", "isi", "--archive"]
        )
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("DRY-RUN", result.output)
        self.org.create_repo.assert_not_called()
        self.repo.edit.assert_not_called()
        extra.edit.assert_not_called()

    def test_new_subjects_receive_complete_bootstrap_on_creation(self):
        result = self.runner.invoke(
            sync_repos.app, ["manifest", "sync", "isi", "--apply"]
        )
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertEqual(len(self.created_repos), 34)
        for repo in self.created_repos:
            with self.subTest(repo=repo.name):
                files = {call.args[0]: call.args[2] for call in repo.create_file.call_args_list}
                self.assertEqual(len(files), 7)
                self.assertEqual(files["AGENTS.md"], (common.ROOT / "templates/subject_agents.md").read_text())
                self.assertEqual(files["CONTRIBUTING.md"], (common.ROOT / "CONTRIBUTING.md").read_text())
                self.assertIn(".github/workflows/transcription.yml", files)
                self.assertIn(".github/transcription/check.py", files)
                self.assertIn(".github/transcription/preflight.py", files)
        self.repo.create_file.assert_not_called()
        self.repo.update_file.assert_not_called()

    def test_shared_instructions_skip_archived_unknown_and_control_repos(self):
        archived = subject_repo("isi-2008-quimica")
        archived.archived = True
        ignored = [
            archived,
            subject_repo("isi-2008-extra"),
            subject_repo("isi-1900-fisica-i"),
            subject_repo("lic-2008-fisica-i"),
            subject_repo(".github"),
        ]
        self.org.get_repos.return_value += ignored
        self.repo.get_contents.side_effect = GithubException(404, {}, {})
        result = self.runner.invoke(sync_repos.app, ["agents", "--apply"])
        self.assertEqual(result.exit_code, 0, result.output)
        self.repo.create_file.assert_called_once()
        for repo in ignored:
            repo.get_contents.assert_not_called()
            repo.create_file.assert_not_called()
            repo.update_file.assert_not_called()

    def test_bootstrap_recovers_partial_setup_and_is_idempotent(self):
        contents = {"AGENTS.md": b"old instructions"}
        def get_contents(path):
            if path not in contents:
                raise GithubException(404, {}, {})
            return SimpleNamespace(decoded_content=contents[path], sha="sha")
        def write(path, message, content, *args):
            contents[path] = content.encode()
        self.repo.get_contents.side_effect = get_contents
        self.repo.create_file.side_effect = write
        self.repo.update_file.side_effect = write
        dry = self.runner.invoke(sync_repos.app, ["bootstrap"])
        self.assertEqual(dry.exit_code, 0, dry.output)
        self.repo.create_file.assert_not_called()
        self.repo.update_file.assert_not_called()
        applied = self.runner.invoke(sync_repos.app, ["bootstrap", "--apply"])
        self.assertEqual(applied.exit_code, 0, applied.output)
        self.assertEqual(len(contents), 7)
        self.repo.reset_mock()
        repeated = self.runner.invoke(sync_repos.app, ["bootstrap", "--apply"])
        self.assertEqual(repeated.exit_code, 0, repeated.output)
        self.repo.create_file.assert_not_called()
        self.repo.update_file.assert_not_called()

    def test_invalid_auth_reports_gh_login_without_remote_writes(self):
        client = Mock()
        client.get_user.side_effect = GithubException(401, {"message": "Bad credentials"}, {})
        with patch.object(sync_repos, "_client", return_value=client):
            result = self.runner.invoke(sync_repos.app, ["auth"])
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("gh auth login", str(result.exception))
        self.org.create_repo.assert_not_called()
        self.repo.create_file.assert_not_called()

    def test_default_sync_publishes_existing_subjects_and_is_idempotent(self):
        other_plan = subject_repo("isi-2023-fisica-i")
        archived = subject_repo("isi-2008-quimica")
        archived.archived = True
        ignored = [
            archived,
            subject_repo("isi-2008-extra"),
            subject_repo("lic-2008-fisica-i"),
            subject_repo(".github"),
        ]
        self.org.get_repos.return_value += [other_plan, *ignored]
        for repo in (self.repo, other_plan):
            contents = {".gitignore": b"custom ignore rules"}
            def get_contents(path, contents=contents):
                if path not in contents:
                    raise GithubException(404, {}, {})
                return SimpleNamespace(decoded_content=contents[path], sha="sha")
            def write(path, message, content, *args, contents=contents):
                contents[path] = content.encode()
            repo.get_contents.side_effect = get_contents
            repo.create_file.side_effect = write
            repo.update_file.side_effect = write
        first = self.runner.invoke(sync_repos.app, [])
        self.assertEqual(first.exit_code, 0, first.output)
        self.assertIn("2 materia(s)", first.output)
        for repo in (self.repo, other_plan):
            self.assertEqual(repo.create_file.call_count, 8)
            self.assertNotIn(
                ".gitignore", [c.args[0] for c in repo.get_contents.call_args_list]
            )
            repo.reset_mock()
        second = self.runner.invoke(sync_repos.app, [])
        self.assertEqual(second.exit_code, 0, second.output)
        self.assertIn("sin escrituras", second.output)
        self.org.create_repo.assert_not_called()
        for repo in (self.repo, other_plan, *ignored):
            repo.create_file.assert_not_called()
            repo.update_file.assert_not_called()
            repo.edit.assert_not_called()
        for repo in ignored:
            repo.get_contents.assert_not_called()

    def test_default_sync_auth_failure_stops_before_publication(self):
        client = Mock()
        client.get_user.side_effect = GithubException(401, {}, {})
        with patch.object(sync_repos, "_client", return_value=client):
            result = self.runner.invoke(sync_repos.app, [])
        self.assertNotEqual(result.exit_code, 0)
        self.repo.get_contents.assert_not_called()
        self.org.create_repo.assert_not_called()

    def test_default_sync_rejects_invalid_manifest_before_github_access(self):
        with (
            patch.object(sync_repos, "load_manifests", side_effect=ValueError("invalid manifest")),
            patch.object(sync_repos, "_client") as client,
        ):
            result = self.runner.invoke(sync_repos.app, [])
        self.assertNotEqual(result.exit_code, 0)
        client.assert_not_called()

    def test_default_sync_is_local_only_but_readonly_audit_still_works_in_ci(self):
        with patch.dict(os.environ, {"GITHUB_ACTIONS": "true"}):
            result = self.runner.invoke(sync_repos.app, [])
            self.assertNotEqual(result.exit_code, 0)
            self.assertIn("solo local", str(result.exception))
            readonly = self.runner.invoke(sync_repos.app, ["manifest", "validate", "isi"])
            self.assertEqual(readonly.exit_code, 0, readonly.output)
        self.repo.get_contents.assert_not_called()

    def test_diff_2023_does_not_report_2008_as_extra(self):
        result = self.runner.invoke(
            sync_repos.app, ["manifest", "diff", "isi", "--plan", "2023"]
        )
        self.assertEqual(result.exit_code, 1, result.output)
        self.assertNotIn("isi-2008-fisica-i", result.output)

    def test_readme_permission_error_never_creates_file(self):
        self.repo.get_contents.side_effect = GithubException(
            403, {"message": "Forbidden"}, {}
        )
        result = self.runner.invoke(sync_repos.app, ["readmes", "isi", "--apply"])
        self.assertNotEqual(result.exit_code, 0)
        self.repo.create_file.assert_not_called()
        self.repo.update_file.assert_not_called()

    def test_publication_handles_missing_changed_and_unchanged_files(self):
        for command, path in [
            ("readmes", "README.md"),
            ("contributing", "CONTRIBUTING.md"),
            ("gitignore", ".gitignore"),
            ("agents", "AGENTS.md"),
        ]:
            with self.subTest(command=command):
                self.repo.reset_mock()
                self.repo.get_contents.side_effect = GithubException(404, {}, {})
                result = self.runner.invoke(sync_repos.app, [command])
                self.assertEqual(result.exit_code, 0, result.output)
                self.repo.create_file.assert_not_called()
                self.repo.update_file.assert_not_called()
                result = self.runner.invoke(sync_repos.app, [command, "--apply"])
                self.assertEqual(result.exit_code, 0, result.output)
                self.repo.create_file.assert_called_once()
                content = self.repo.create_file.call_args.args[2]
                self.assertEqual(self.repo.create_file.call_args.args[0], path)
                self.repo.reset_mock()
                self.repo.get_contents.side_effect = None
                self.repo.get_contents.return_value = SimpleNamespace(
                    decoded_content=content.encode(), sha="current-sha"
                )
                result = self.runner.invoke(sync_repos.app, [command, "--apply"])
                self.assertEqual(result.exit_code, 0, result.output)
                self.repo.create_file.assert_not_called()
                self.repo.update_file.assert_not_called()
                self.repo.get_contents.return_value = SimpleNamespace(
                    decoded_content=b"outdated", sha="current-sha"
                )
                result = self.runner.invoke(sync_repos.app, [command, "--apply"])
                self.assertEqual(result.exit_code, 0, result.output)
                self.repo.update_file.assert_called_once_with(
                    path,
                    self.repo.update_file.call_args.args[1],
                    content,
                    "current-sha",
                )

    def test_publication_propagates_permission_server_and_network_errors(self):
        for command in ["readmes", "contributing", "gitignore", "agents", "bootstrap"]:
            for error in [
                GithubException(403, {}, {}),
                GithubException(500, {}, {}),
                ConnectionError("offline"),
            ]:
                with self.subTest(command=command, error=error):
                    self.repo.reset_mock()
                    self.repo.get_contents.side_effect = error
                    result = self.runner.invoke(sync_repos.app, [command, "--apply"])
                    self.assertNotEqual(result.exit_code, 0)
                    self.repo.create_file.assert_not_called()
                    self.repo.update_file.assert_not_called()

    def test_unknown_plan_rejected_before_github_access(self):
        with patch.object(sync_repos, "_client") as client:
            for args in [
                ["manifest", "list"],
                ["manifest", "diff"],
                ["manifest", "sync"],
                ["readmes"],
            ]:
                result = self.runner.invoke(
                    sync_repos.app, args + ["isi", "--plan", "1900"]
                )
                self.assertNotEqual(result.exit_code, 0)
                self.assertIn("no existe", result.output)
            client.assert_not_called()

    def test_invalid_manifest_rejected_before_remote_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "data").mkdir()
            source = (common.ROOT / "data" / "isi.toml").read_text()
            (root / "data" / "isi.toml").write_text(
                source.replace("orden = 1\n", "orden = 0\n", 1)
            )
            with (
                patch.object(common, "ROOT", root),
                patch.object(sync_repos, "_client") as client,
            ):
                result = self.runner.invoke(
                    sync_repos.app, ["manifest", "sync", "isi", "--apply"]
                )
                self.assertNotEqual(result.exit_code, 0)
                self.assertIn("positivo", result.output)
                client.assert_not_called()

    def test_diff_reports_description_drift_and_excludes_archived_repos(self):
        self.repo.description = "Nombre viejo"
        archived = subject_repo("isi-2008-materia-retirada")
        archived.archived = True
        self.org.get_repos.return_value.append(archived)
        result = self.runner.invoke(sync_repos.app, ["manifest", "diff", "isi"])
        self.assertEqual(result.exit_code, 1)
        self.assertIn("Descripciones diferentes", result.output)
        self.assertNotIn(archived.name, result.output)


class CredentialTests(unittest.TestCase):
    def test_local_login_obtains_credential_from_gh(self):
        env = {"GITHUB_ACTIONS": "false", "ORG_ADMIN_TOKEN": "old-token", "GITHUB_TOKEN": "old-token"}
        with (
            patch.dict(os.environ, env),
            patch.object(sync_repos.subprocess, "run", return_value=SimpleNamespace(stdout="gh-credential\n")) as command,
            patch.object(sync_repos.Auth, "Token") as auth,
            patch.object(sync_repos, "Github") as github,
        ):
            sync_repos._client()
        command.assert_called_once_with(
            ["gh", "auth", "token", "--hostname", "github.com"],
            capture_output=True, text=True, check=True,
        )
        auth.assert_called_once_with("gh-credential")
        github.assert_called_once_with(auth=auth.return_value)

    def test_missing_or_failed_gh_login_has_actionable_error_without_credentials(self):
        for error in (
            FileNotFoundError(),
            subprocess.CalledProcessError(1, ["gh"], output="private-token", stderr="private-token"),
        ):
            with (
                self.subTest(error=type(error).__name__),
                patch.dict(os.environ, {"GITHUB_ACTIONS": "false"}),
                patch.object(sync_repos.subprocess, "run", side_effect=error),
                patch.object(sync_repos, "Github") as github,
            ):
                with self.assertRaises(SystemExit) as result:
                    sync_repos._client()
                self.assertIn("gh auth login", str(result.exception))
                self.assertNotIn("private-token", str(result.exception))
                github.assert_not_called()

    def test_readonly_ci_auth_uses_builtin_token_without_gh(self):
        with (
            patch.dict(os.environ, {"GITHUB_ACTIONS": "true", "GITHUB_TOKEN": "builtin-token"}),
            patch.object(sync_repos.subprocess, "run") as command,
            patch.object(sync_repos.Auth, "Token") as auth,
            patch.object(sync_repos, "Github"),
        ):
            sync_repos._client()
        command.assert_not_called()
        auth.assert_called_once_with("builtin-token")


class ManifestTests(unittest.TestCase):
    def setUp(self):
        self.manifest = common.load_manifest("isi")

    def test_invalid_fields_references_and_duplicate_order_are_rejected(self):
        for field, value in [
            ("nivel", True),
            ("hs-semanales", "five"),
            ("orden", 2),
            ("nombre", ""),
            ("correlativas-cursar-cursadas", ["missing"]),
            ("correlativas-rendir-todas", "yes"),
        ]:
            with self.subTest(field=field):
                manifest = deepcopy(self.manifest)
                manifest["planes"]["2008"]["materias"]["analisis-matematico-i"][
                    field
                ] = value
                with self.assertRaises(ValueError):
                    common.validate_manifest(manifest)

    def test_prerequisite_cycle_is_rejected(self):
        subjects = self.manifest["planes"]["2008"]["materias"]
        subjects["analisis-matematico-i"]["correlativas-cursar-cursadas"] = [
            "algebra-y-geometria-analitica"
        ]
        subjects["algebra-y-geometria-analitica"]["correlativas-rendir-aprobadas"] = [
            "analisis-matematico-i"
        ]
        with self.assertRaisesRegex(ValueError, "ciclo"):
            common.validate_manifest(self.manifest)

    def test_all_71_subject_readmes_render_deterministically(self):
        template = common.template_environment().get_template("subject_readme.md.j2")
        count = 0
        for plan, data in self.manifest["planes"].items():
            for slug, subject in data["materias"].items():
                rendered = sync_repos._render_subject_readme(
                    self.manifest, plan, slug, template
                )
                self.assertIn(subject["nombre"], rendered)
                self.assertEqual(
                    rendered,
                    sync_repos._render_subject_readme(
                        self.manifest, plan, slug, template
                    ),
                )
                if plan == "2023":
                    self.assertNotIn("Pendientes", rendered)
                    self.assertIn("## 🔗 Correlativas", rendered)
                count += 1
        self.assertEqual(count, 71)

    def test_exam_completed_requirements_validate_types_references_and_cycles(self):
        field = "correlativas-rendir-cursadas"
        for value in ("fisica-i", [1], ["missing"], ["analisis-matematico-i"]):
            with self.subTest(value=value):
                manifest = deepcopy(self.manifest)
                manifest["planes"]["2023"]["materias"]["analisis-matematico-i"][field] = value
                with self.assertRaises(ValueError):
                    common.validate_manifest(manifest)
        subjects = self.manifest["planes"]["2023"]["materias"]
        subjects["analisis-matematico-i"][field] = ["analisis-matematico-ii"]
        with self.assertRaisesRegex(ValueError, "ciclo"):
            common.validate_manifest(self.manifest)

    def test_exam_completed_requirements_render_without_other_requirements(self):
        subjects = self.manifest["planes"]["2023"]["materias"]
        subjects["fisica-i"]["correlativas-rendir-cursadas"] = ["ingles-i"]
        common.validate_manifest(self.manifest)
        template = common.template_environment().get_template("subject_readme.md.j2")
        rendered = sync_repos._render_subject_readme(self.manifest, "2023", "fisica-i", template)
        self.assertIn("## 🔗 Correlativas", rendered)
        self.assertIn("**Para rendir — cursadas:** Inglés I", rendered)
        self.assertNotIn("**Para cursar", rendered)
        self.assertNotIn("**Para rendir — aprobadas", rendered)
        self.assertNotIn("Sin correlativas", rendered)

    def test_unknown_prerequisite_keys_are_rejected(self):
        self.manifest["planes"]["2023"]["materias"]["fisica-i"]["correlativas-rendir-cursada"] = []
        with self.assertRaisesRegex(ValueError, "correlativas-rendir-cursada"):
            common.validate_manifest(self.manifest)

    def test_all_2023_rows_match_reviewed_annex_and_render_each_requirement(self):
        expected = json.loads((common.ROOT / "tests/fixtures/isi-2023-prerequisites.json").read_text())
        plan = self.manifest["planes"]["2023"]
        subjects = plan["materias"]
        self.assertEqual(plan["correlativas-estado"], "completas")
        self.assertEqual(len(expected), 36)
        self.assertEqual({row["order"] for row in expected}, set(range(1, 37)))
        self.assertEqual({row["slug"] for row in expected}, set(subjects))
        slugs = {row["order"]: row["slug"] for row in expected}
        names = {row["order"]: row["name"] for row in expected}
        template = common.template_environment().get_template("subject_readme.md.j2")
        empty = []
        for row in expected:
            with self.subTest(order=row["order"]):
                subject = subjects[row["slug"]]
                self.assertEqual(subject["orden"], row["order"])
                self.assertEqual(subject["nombre"], row["name"])
                rendered = sync_repos._render_subject_readme(self.manifest, "2023", row["slug"], template)
                for action, label in (("cursar", "Para cursar"), ("rendir", "Para rendir")):
                    for kind, column in (("cursadas", "completed"), ("aprobadas", "approved")):
                        numbers = [] if action == "rendir" and row["order"] == 36 else row[column]
                        self.assertEqual(subject[f"correlativas-{action}-{kind}"], [slugs[n] for n in numbers])
                        prefix = f"**{label} — {kind}:**"
                        if numbers:
                            self.assertIn(prefix + " " + ", ".join(names[n] for n in numbers), rendered)
                        else:
                            self.assertNotIn(prefix, rendered)
                self.assertEqual(subject.get("correlativas-rendir-todas", False), row["order"] == 36)
                if row["order"] == 36:
                    self.assertIn("**Para rendir:** tener aprobadas todas las asignaturas previas del plan de estudios.", rendered)
                if not row["completed"] and not row["approved"]:
                    empty.append(row["order"])
                    self.assertIn("Sin correlativas para cursar ni rendir.", rendered)
                else:
                    self.assertNotIn("Sin correlativas", rendered)
        self.assertEqual(empty, [1, 2, 3, 4, 5, 6, 7, 8, 11])

    def test_2023_source_provenance_and_pps_are_plan_metadata(self):
        plan = self.manifest["planes"]["2023"]
        self.assertEqual(plan["correlativas-fuente"], "data/sources/corre.pdf")
        digest = hashlib.sha256((common.ROOT / plan["correlativas-fuente"]).read_bytes()).hexdigest()
        self.assertEqual(digest, "982f1b148e3ae7e64081ee1d01fa75a7c8cef6bd272aebc45f0138d8f7df998f")
        provenance = (common.ROOT / "data/sources/corre.md").read_text()
        for value in (digest, "https://www.frre.utn.edu.ar/media/ISI/documentos/corre.pdf", "2026-10-17", "3–5"):
            self.assertIn(value, provenance)
        self.assertEqual(plan["practica-supervisada-requisitos"], "Para iniciar y acreditar la PPS se requieren las condiciones académicas de inscripción a Proyecto Final.")
        self.assertEqual(plan["practica-supervisada-hs"], 200)
        self.assertFalse(any("pps" in slug or "practica" in slug for slug in plan["materias"]))

    def test_all_35_plan_2008_renders_are_byte_identical(self):
        expected = json.loads((common.ROOT / "tests/fixtures/isi-2008-readme-sha256.json").read_text())
        self.assertEqual(set(expected), set(self.manifest["planes"]["2008"]["materias"]))
        self.assertEqual(len(expected), 35)
        template = common.template_environment().get_template("subject_readme.md.j2")
        for slug, digest in expected.items():
            with self.subTest(slug=slug):
                rendered = sync_repos._render_subject_readme(self.manifest, "2008", slug, template)
                self.assertEqual(hashlib.sha256(rendered.encode()).hexdigest(), digest)

    def test_pending_plan_remains_explicit_without_claiming_undefined_rules(self):
        self.manifest["planes"]["2023"]["correlativas-estado"] = "pendientes"
        template = common.template_environment().get_template("subject_readme.md.j2")
        rendered = sync_repos._render_subject_readme(self.manifest, "2023", "fisica-i", template)
        self.assertIn("Pendientes de carga y verificación documental", rendered)
        self.assertNotIn("Sin correlativas", rendered)
        self.assertNotIn("Pendientes de definición", rendered)


class RenderingTests(unittest.TestCase):
    def test_inventory_includes_non_jinja_templates_and_matches_generated_file(self):
        state = gen_repo_readme.collect_state()
        self.assertIn("subject.gitignore", state["templates"])
        self.assertIn("transcription/workflow.yml", state["templates"])
        self.assertEqual(
            gen_repo_readme.render(state),
            (common.ROOT / "docs" / "README.md").read_text(),
        )

    def test_profile_uses_manifest_names_real_notes_and_stable_activity(self):
        repo = subject_repo()
        repo.description = "Nombre viejo"
        repo.get_git_tree.return_value = SimpleNamespace(
            truncated=False,
            tree=[
                SimpleNamespace(type="blob", path="notes/2026/practica/README.md"),
                SimpleNamespace(type="blob", path="notes/2026/teoria/README.md"),
                SimpleNamespace(type="blob", path="notes/2025/teoria/tema-anterior.md"),
                SimpleNamespace(type="tree", path="notes/2026/teoria"),
                SimpleNamespace(type="blob", path="notes/2026/teoria/ondas.md"),
                SimpleNamespace(
                    type="blob", path="notes/2026/practica/oscilaciones.md"
                ),
            ],
        )

        def commit(message):
            return SimpleNamespace(
                commit=SimpleNamespace(
                    message=message,
                    author=SimpleNamespace(
                        date=datetime(2026, 5, 1, tzinfo=timezone.utc)
                    ),
                )
            )

        repo.get_commits.return_value = [
            commit("docs: README autogenerado desde manifest"),
            commit("docs: sincronizar CONTRIBUTING"),
            commit("docs: agregar ondas"),
        ]
        other = subject_repo("isi-2008-ingles-i")
        other.get_git_tree.return_value = SimpleNamespace(truncated=False, tree=[])
        other.get_commits.return_value = []
        org = Mock()
        org.get_repos.return_value = [repo, other]
        first = sync_readme.collect_org_state(org)
        org.get_repos.return_value = [other, repo]
        second = sync_readme.collect_org_state(org)
        rendered = sync_readme.render(first)
        self.assertEqual(rendered, sync_readme.render(second))
        self.assertIn("**Física I** — Oscilaciones, Ondas", rendered)
        self.assertNotIn("Nombre viejo", rendered)
        self.assertNotIn("Readme", rendered)
        self.assertNotIn("README autogenerado", rendered)
        self.assertEqual(
            [r["description"] for r in first["recent_updates"]], ["docs: agregar ondas"]
        )

    def test_profile_api_failure_is_not_rendered_as_empty_content(self):
        repo = subject_repo()
        repo.get_git_tree.side_effect = GithubException(403, {}, {})
        org = Mock()
        org.get_repos.return_value = [repo]
        with self.assertRaises(GithubException):
            sync_readme.collect_org_state(org)

    def test_profile_does_not_rewrite_identical_content(self):
        state = {
            "subjects_by_carrera": {},
            "recent_updates": [],
            "active_subjects": 0,
            "carreras": [],
            "carrera_nombres": {},
            "planes": [],
            "last_updated": "—",
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "profile").mkdir()
            with (
                patch.object(sync_readme, "ROOT", root),
                patch.object(sync_readme, "load_token", return_value="fake"),
                patch.object(sync_readme, "Github"),
                patch.object(sync_readme, "collect_org_state", return_value=state),
            ):
                self.assertEqual(sync_readme.main(), 0)
                target = root / "profile" / "README.md"
                modified = target.stat().st_mtime_ns
                self.assertEqual(sync_readme.main(), 0)
                self.assertEqual(target.stat().st_mtime_ns, modified)


class WorkflowTests(unittest.TestCase):
    def test_embedded_shell_syntax(self):
        for path in (common.ROOT / ".github" / "workflows").glob("*.yml"):
            workflow = yaml.safe_load(path.read_text())
            for job in workflow["jobs"].values():
                for step in job["steps"]:
                    if "run" in step:
                        with self.subTest(workflow=path.name, step=step.get("name")):
                            result = subprocess.run(
                                ["bash", "-n"],
                                input=step["run"],
                                text=True,
                                capture_output=True,
                            )
                            self.assertEqual(result.returncode, 0, result.stderr)

    def test_repeated_link_reports_update_one_issue(self):
        workflow = yaml.safe_load(
            (common.ROOT / ".github" / "workflows" / "link-check.yml").read_text()
        )
        step = next(
            s
            for s in workflow["jobs"]["lychee"]["steps"]
            if s.get("name") == "Update recurring issue on scheduled failure"
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "lychee").mkdir()
            (root / "lychee" / "out.md").write_text("Broken link report")
            gh = root / "gh"
            gh.write_text("""#!/bin/bash
case "$2" in
  list) if [ -f issue ]; then echo 42; fi ;;
  create) touch issue; echo create >> calls ;;
  edit) echo edit >> calls ;;
  *) exit 2 ;;
esac
""")
            gh.chmod(0o755)
            env = dict(os.environ, PATH=f"{root}{os.pathsep}{os.environ['PATH']}")
            for _ in range(2):
                result = subprocess.run(
                    ["bash", "-e", "-o", "pipefail", "-c", step["run"]],
                    cwd=root,
                    env=env,
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                (root / "calls").read_text().splitlines(), ["create", "edit"]
            )


if __name__ == "__main__":
    unittest.main()
