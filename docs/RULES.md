# Restricted functions

The basic PDF path needs none of this tooling.

Install the Python integration:

```text
python -m pip install -e ".[rules]"
```

Install the official [Extism JS compiler](https://github.com/extism/js-pdk) and [Binaryen](https://github.com/WebAssembly/binaryen) so `extism-js`, `wasm-merge`, and `wasm-opt` are discoverable. Set `SHARP_RULE_COMPILER` if the compiler has a different location. The implementation was exercised with the Extism v1.7.0 Windows release asset (its binary reports 1.6.1), Binaryen version_133, Extism Python 1.1.1, and extism-sys 1.41.0. Prefer released binaries and verify their published checksums. Sharp does not download or execute installers automatically.

One function declaration is accepted:

```javascript
function rule(input) {
  return {colors: {name: "#2463a6"}};
}
```

This example's output belongs to after_layout. It is not a shipped active default. Source must contain exactly `function rule(input) { ... }`, with no top-level side effects, imports, or default parameter expressions. Comments are allowed. A parser enforces the declaration boundary before compilation. This protects the compile step from executing arbitrary top-level user code.

Functions are user-owned implementation, not a new MCP tool per function. The MCP contract-management operation compiles with fixed arguments and shell disabled. For an enabled function it also runs a supplied representative input and validates the output schema before changing effective settings. Runtime always validates returned IDs, ranges, properties and constraints again; a smoke test cannot prove every branch correct.

The Wasm runtime receives JSON data only. No allowed hosts or preopened directories are configured; no privileged application host callbacks are supplied. Each invocation gets fresh state, a memory ceiling, a deadline, and input/output limits. Functions should be pure. Time/randomness are not a reproducibility guarantee merely because Wasm is sandboxed.

Source, wrapper, contract, compiler, and runtime identity determine the artifact cache. Installed metadata allows execution without starting or locating the compiler. Changing runtime/contract requires reinstalling functions. Generated source wrappers and Wasm are derived cache artifacts, never a second editable source of truth.

The source declaration boundary and runtime isolation are distinct from schema validity. Both are tested. No sandbox is claimed for the host AI agent or the trusted local MCP file-management tools themselves.
