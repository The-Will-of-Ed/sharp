"""Optional restricted JS execution. Extism details never enter core contracts."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

from sharp.contracts import Customization


class RestrictedRules:
    def __init__(self, cache, *, compiler="extism-js", timeout_ms=1000, max_output=1_000_000):
        self.cache, self.compiler = Path(cache), str(compiler)
        self.timeout_ms, self.max_output = timeout_ms, max_output
        self.cache.mkdir(parents=True, exist_ok=True)
        self._compiler_version = None

    def _version(self):
        if self._compiler_version is None:
            try:
                result = subprocess.run(
                    [self.compiler, "--version"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    check=True,
                    shell=False,
                )
            except (OSError, subprocess.SubprocessError) as exc:
                raise ValueError(
                    "Rule compiler unavailable. Install extism-js; see Sharp rules setup."
                ) from exc
            self._compiler_version = result.stdout.strip()
        return self._compiler_version

    def artifact(self, rule: Customization):
        from importlib.metadata import version

        index = self.cache / (
            "installed-" + hashlib.sha256(rule.source.encode()).hexdigest() + ".json"
        )
        if index.exists():
            recorded = json.loads(index.read_text(encoding="utf-8"))
            if (
                recorded.get("contract") == 1
                and recorded.get("wrapper") == 1
                and recorded.get("runtime") == version("extism-sys")
            ):
                return self.cache / recorded["artifact"]
        key = json.dumps(
            [
                rule.source,
                "sharp-wrapper-1",
                1,
                self._version(),
                version("extism"),
                version("extism-sys"),
            ]
        )
        return self.cache / (hashlib.sha256(key.encode()).hexdigest() + ".wasm")

    def _validate_source(self, source):
        # Only a declaration is accepted: no top-level code executes while compiling.
        import tree_sitter_javascript
        from tree_sitter import Language, Parser

        parser = Parser(Language(tree_sitter_javascript.language()))
        tree = parser.parse(source.encode())
        nodes = [n for n in tree.root_node.named_children if n.type != "comment"]
        if tree.root_node.has_error or len(nodes) != 1 or nodes[0].type != "function_declaration":
            raise ValueError(
                "Rule source must be one function declaration: function rule(input) { ... }"
            )
        node = nodes[0]
        name, parameters = (
            node.child_by_field_name("name"),
            node.child_by_field_name("parameters"),
        )
        if name.text != b"rule" or parameters.text.replace(b" ", b"") != b"(input)":
            raise ValueError("Expected exactly function rule(input), with no default arguments")

    def install(self, rule: Customization):
        self._validate_source(rule.source)
        target = self.artifact(rule)
        if target.exists():
            return target
        source = target.with_suffix(".js")
        interface = target.with_suffix(".d.ts")
        source.write_text(
            rule.source
            + "\nfunction sharp_run() { const input=JSON.parse(Host.inputString()); Host.outputString(JSON.stringify(rule(input))); }\nmodule.exports={sharp_run};",
            encoding="utf-8",
        )
        interface.write_text(
            'declare module "main" { export function sharp_run(): I32; }',
            encoding="utf-8",
        )
        temporary = target.with_suffix(".pending.wasm")
        try:
            process = subprocess.run(
                [
                    self.compiler,
                    str(source.resolve()),
                    "-i",
                    str(interface.resolve()),
                    "-o",
                    str(temporary.resolve()),
                    "--skip-opt",
                ],
                cwd=self.cache,
                capture_output=True,
                text=True,
                timeout=30,
                shell=False,
            )
            if process.returncode:
                raise ValueError("Rule compilation failed: " + process.stderr[-2000:])
            temporary.replace(target)
            from importlib.metadata import version

            index = self.cache / (
                "installed-" + hashlib.sha256(rule.source.encode()).hexdigest() + ".json"
            )
            index.write_text(
                json.dumps(
                    {
                        "artifact": target.name,
                        "contract": 1,
                        "wrapper": 1,
                        "compiler": self._version(),
                        "runtime": version("extism-sys"),
                    }
                ),
                encoding="utf-8",
            )
        except subprocess.TimeoutExpired as exc:
            raise ValueError("Rule compilation exceeded 30 seconds") from exc
        finally:
            source.unlink(missing_ok=True)
            interface.unlink(missing_ok=True)
            temporary.unlink(missing_ok=True)
        return target

    def run(self, customization: Customization, payload: dict):
        import extism

        encoded = json.dumps(payload, ensure_ascii=False).encode()
        if len(encoded) > 8_000_000:
            raise ValueError("Rule input exceeds 8 MB")
        index = self.cache / (
            "installed-" + hashlib.sha256(customization.source.encode()).hexdigest() + ".json"
        )
        if not index.is_file():
            raise ValueError("Rule has not been installed; compile it before rendering")
        from importlib.metadata import version

        installed = json.loads(index.read_text(encoding="utf-8"))
        if (
            installed.get("runtime") != version("extism-sys")
            or installed.get("contract") != 1
            or installed.get("wrapper") != 1
        ):
            raise ValueError("Rule runtime/contract changed; reinstall this customization")
        target = self.artifact(customization)
        if not target.is_file():
            raise ValueError("Rule has not been installed; compile it before rendering")
        manifest = {
            "wasm": [{"path": str(target.resolve())}],
            "allowed_hosts": [],
            "allowed_paths": {},
            "timeout_ms": self.timeout_ms,
            "memory": {
                "max_pages": 1024,
                "max_http_response_bytes": 0,
                "max_var_bytes": 65536,
            },
        }
        try:
            # Fresh instance: no cross-run Var state. WASI has no preopened directories.
            with extism.Plugin(manifest, wasi=True, functions=[]) as plugin:
                result = plugin.call("sharp_run", encoded)
                if len(result) > self.max_output:
                    raise ValueError("Rule output exceeds size limit")
                value = json.loads(bytes(result))
                if not isinstance(value, dict):
                    raise ValueError("Rule output must be a JSON object")
                return value
        except Exception as exc:
            raise ValueError(f"Restricted rule failed: {exc}") from exc
