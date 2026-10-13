"""PF-1A-E1 static guards: keep the require_roles() -> require_permission() migration
from silently regressing.

Three independent guards, deliberately narrow in scope (see
`docs/agent/TESTING_STRATEGY.md` section 13 on static guards versus deterministic
tests). This file is the PF-1A-E1 C3 correction pass over the guard: a second
independent re-review (C3) found the post-C2 version of all three guards still had
narrow, exploitable bypasses, and this rewrite closes them. See
`docs/continuity/PF_1A_E1_C3_CORRECTION_HANDOFF.md` for the full review finding and
what changed; `docs/continuity/PF_1A_E1_C2_CORRECTION_HANDOFF.md` records the prior
(C2) pass this one builds on.

1. No `backend/app/modules/*/routes.py` file may reference `require_roles` at all,
   under any name, in any executable position - not only as a direct or qualified
   CALL. Guard 1 is AST-based and fails closed at the REFERENCE level (PF-1A-E1 C3
   finding 1.C): it rejects the import statement itself (regardless of alias), any
   bare `Name` load of `require_roles` or a tracked alias of it (which also catches
   `rr = require_roles` and `rr = deps.require_roles` at the point of assignment,
   before any later call), and any `Attribute` access whose final attribute name is
   `require_roles` regardless of the module/alias used to reach it. `require_roles(...)`
   no longer exists: TB-1 TB1-905 removed it from `app.modules.identity.dependencies` on
   8 October 2026, as nothing used it, so importing it fails. The guard stays, because a
   route reaching a `require_roles` defined again would silently bypass the ORA-owned
   `authz_role_permission` compatibility mapping this package made authoritative.
2. Every FastAPI route under `/api/` that is not on the small, EXACT (not prefix-wide)
   baseline-derived "authenticated-only, no role/permission distinction" allowlist must
   resolve its authorization through `require_permission(...)`, and a baseline-protected
   route must carry EXACTLY ONE such dependency across its COMPLETE dependency graph,
   requesting EXACTLY the permission code the independently baseline-derived route
   inventory expects for that route. "Complete" means the full recursive FastAPI
   dependency tree, not only the route's top-level `dependant.dependencies` list
   (PF-1A-E1 C3 finding 1.A): a permission dependency nested inside another
   dependency's own dependencies was invisible to the pre-C3 helper, which inspected
   only the top level. Collecting every matching dependency anywhere in the graph is
   what makes "exactly one" provable at all: a route carrying the expected permission
   plus a second permission dependency (top-level or nested) must be rejected as
   `multiple`. This directly catches: a route omitted from migration; a route migrated
   to the wrong permission; a route that lost its permission guard entirely; a route
   silently gaining a second, undocumented permission dependency anywhere in its
   dependency graph; and a genuinely new route silently swallowed by an overly broad
   exemption.
3. No `backend/app/modules/*/routes.py` file may reintroduce direct application-role
   authorization logic. This guard is a FAIL-CLOSED rule: EVERY `.role_codes` attribute
   access anywhere in a route module is treated as an offense unless it matches one of
   exactly two documented, EXACT, structurally-constrained shapes (see
   `_is_allowed_role_codes_usage`) - not merely a file-scoped pattern match
   (PF-1A-E1 C3 finding 1.B). Each exception is pinned to the literal real production
   call shape: the exact enclosing function, the exact call target (a bare `Name`, not
   an arbitrary qualified attribute call), the exact argument position `.role_codes`
   appears in, and the exact permission constant/dict key used. A wrong permission
   code, a qualified `policy.has_permission(...)` call, or the identical-looking shape
   inside a different function are all rejected, because none of them is the literal
   real production statement the exception exists to describe. The route-local
   `*_ROLES` tuple-constant check is retained separately, because it does not involve
   `.role_codes` at all and the fail-closed rule above cannot see it.

Guard 2 and guard 3 both compare against
`tests.fixtures.pf_1a_e1_baseline_authorization`, the independently baseline-derived
snapshot (see that module's docstring for provenance and re-verification commands).
Neither guard derives its expected value from `app.modules.authorization.contract` or
from route-module source at collection time; the baseline route/permission inventory is
data the test compares the live route table against, not code generated from it.

This file also carries the PF-1A-E1 C4 correction. A further independent re-review found
two narrower bypasses that survived the C3 rewrite above, both closed here:

4. Guard 1 (require_roles reference-level detection) did not recognize a deterministic
   dynamic lookup of the literal string "require_roles" via `getattr(x, "require_roles")`,
   `vars(x)["require_roles"]` or `x.__dict__["require_roles"]` (PF-1A-E1 C4 finding 1).
   These are not general dataflow analysis; they are AST-obvious literal-string lookups of
   the exact banned member name via a structurally recognizable idiom, and are now
   rejected the same way a direct reference already was.
5. Guard 3's two `.role_codes` allow-shapes matched on call/keyword shape alone, without
   proving the helper name used (`has_permission`, `record_business_event`) was still the
   genuine, unshadowed import, and without pinning the `.role_codes` base object to the
   real production variable (`user`, `response.user`) or the login-success event identity
   (`event_name="UserLoginSucceeded"`) (PF-1A-E1 C4 finding 2). A locally rebound helper
   name (`has_permission = policy.has_permission`), a wrong base object
   (`other.role_codes`), a fabricated event identity carrying the same payload shape, and a
   dynamic `getattr(...)`/`vars(...)`/`__dict__` equivalent of `.role_codes` are all now
   rejected.

See `docs/continuity/PF_1A_E1_C3_CORRECTION_HANDOFF.md` for the C4 addendum recording this
pass and the fresh independent review it responds to.

This file also carries the PF-1A-E1 C5 correction. A further independent re-review (fresh
re-run of the C4-corrected guard) reconfirmed the runtime authorization candidate is sound and
found exactly two remaining classes of bypass in the STATIC GUARD ITSELF (not runtime
behavior), both closed here:

6. Guard 1's C4 dynamic-literal-attribute detector recognized only a literal string constant
   equal to the banned attribute name as the `getattr(...)` name argument or subscript/`.get(...)`
   key. It did not evaluate a bounded compile-time string expression such as
   `"require_" + "roles"`, and it did not recognize the `.get(...)` method-call form of the
   `vars(x)`/`x.__dict__` idiom at all (only the subscript form `vars(x)["require_roles"]` /
   `x.__dict__["require_roles"]`). This let `vars(deps).get("require_roles")`,
   `deps.__dict__.get("require_roles")` and `getattr(deps, "require_" + "roles")` all evade
   detection (independently demonstrated). A small, bounded compile-time string evaluator
   (`_eval_compile_time_string`) now understands a plain string constant and an `Add` `BinOp`
   whose both sides recursively evaluate to compile-time strings, and the dynamic-access scan now
   also recognizes `.get(...)` calls against `vars(x)`/`x.__dict__`. This is still not general
   dataflow analysis: a string built through anything other than literal concatenation (a
   variable, a function call, string formatting/methods) is deliberately not resolved, and is
   correctly NOT flagged.
7. Guard 3's two `.role_codes` allow-shapes proved the callee spelling and the base-object
   spelling, but did not prove: (a) that the tracked helper name (`has_permission`,
   `record_business_event`) actually resolves to a genuine, EXISTING expected import - a module
   relying on `from fake_policy import *` (or `from fake_events import *`) to supply the name
   passed every prior check, because the guard only rejected an EXPLICIT conflicting binding, not
   the absence of any genuine explicit binding at all; (b) that pattern-match capture bindings
   (`case has_permission:`) count as shadowing - `_iter_binding_names` did not enumerate
   `ast.MatchAs`/`ast.MatchStar`/`ast.MatchMapping` binding sites at all, so a match-statement
   capture of the tracked name was invisible to the shadow check; (c) that the `.role_codes` base
   object (`user` in accounts, `response` in identity) and, for accounts, the permission constant
   (`ACCOUNT_TAX_VERIFY`) resolve to their genuine production provenance rather than an
   in-function rebinding (`user = other`, `ACCOUNT_TAX_VERIFY = ACCOUNT_READ`,
   `response = fake_response`); and (d) that the enclosing target function is unique - a second,
   decoy `def _assert_tax_verification_permission(...)` or `def login(...)` elsewhere in the
   module was never checked for. All were independently demonstrated as live bypasses. The C5
   correction replaces the enclosing-function-name/shadow checks with an explicit provenance
   model: the call/dict SHAPE match is now a separate, reusable predicate
   (`_accounts_role_codes_shape_matches` / `_identity_role_codes_shape_matches`); the target
   function must be the unique `FunctionDef`/`AsyncFunctionDef` with the expected name AND the
   expected sync/async-ness (`_unique_target_function`); the shape-matching statement must occur
   EXACTLY ONCE inside that unique function; the `.role_codes` base object's provenance is proved
   trustworthy (`_user_provenance_is_trustworthy` / `_response_provenance_is_trustworthy` - the
   real parameter position for `user`, or the real single `response = login_user(...)` assignment
   for `response`, with no other binding of that name anywhere in the function); and every tracked
   helper/constant name (`has_permission`, `ACCOUNT_TAX_VERIFY`, `record_business_event`) must
   resolve to EXACTLY ONE genuine expected `ImportFrom` binding, with the whole module failing
   closed if it contains ANY star import at all (`_helper_provenance_is_trustworthy`), since a
   star import can supply an arbitrary same-named symbol that static analysis cannot rule out.
   `_iter_binding_names` is also extended to enumerate `ast.MatchAs`/`ast.MatchStar`/
   `ast.MatchMapping` binding sites, so a pattern-match capture of a tracked name is treated as
   shadowing the same as an ordinary assignment. This remains bounded AST analysis: it is not a
   general Python interpreter, symbolic executor, control-flow engine or whole-program analyzer,
   and the binding-site enumeration covers the bounded set of Python binding forms this guard
   explicitly enumerates, not a claim of exhaustive coverage of every possible way a name can be
   bound in Python.

See `docs/continuity/PF_1A_E1_C3_CORRECTION_HANDOFF.md` section 12 for the C5 addendum recording
this pass and the fresh independent review it responds to.

This file also carries the PF-1A-E1 C6 correction. A further independent re-review (fresh
re-run of the C5-corrected guard) AGAIN independently reconfirmed the runtime authorization
candidate is sound, and found exactly two further classes of bypass in the STATIC GUARD ITSELF
(not runtime behavior), both closed here:

8. The C5 import-provenance check (`_is_expected_import_binding` /
   `_count_expected_import_bindings`) proved provenance PER `ImportFrom` STATEMENT, not per
   individual `ast.alias` within it. A single ImportFrom statement can bind the same local
   name more than once - `from mod import ACCOUNT_TAX_VERIFY, ACCOUNT_READ as
   ACCOUNT_TAX_VERIFY` contains one genuine alias for `ACCOUNT_TAX_VERIFY` AND one conflicting
   alias (`ACCOUNT_READ as ACCOUNT_TAX_VERIFY`) that OVERWRITES the same local name with a
   different symbol - and the pre-C6 check asked only "does this STATEMENT contain a genuine
   alias for this name somewhere", which is true even though the statement also contains the
   conflicting one. This was independently demonstrated as a live bypass for every tracked
   name in both modules (`ACCOUNT_TAX_VERIFY`, `has_permission`, `record_business_event`,
   `login_user`), regardless of which alias appeared first. The C6 correction changes the
   binding marker `_iter_binding_names` yields for an `ImportFrom` binding from the bare
   `ImportFrom` node to a `(import_node, alias)` tuple identifying the SPECIFIC alias that
   produced that occurrence (`_is_expected_import_binding` now checks that alias directly,
   never "any alias in the same statement"), and `_count_expected_import_bindings` now counts
   per-alias rather than per-statement for the same reason. `_name_is_shadowed` needed no
   logic change - once the marker distinguishes the two aliases, its existing "every binding
   occurrence must resolve to the expected import" loop already rejects the conflicting one
   correctly, because that occurrence's own marker no longer satisfies
   `_is_expected_import_binding`.
9. The C5 occurrence-uniqueness check counted a shape-matching statement as belonging to the
   unique target function whenever `ast.walk(target_function)` reached it - and `ast.walk`
   descends into EVERY nested lexical scope (a nested `def`, `async def`, `lambda`, or `class`
   body), because those are themselves ordinary child nodes in the AST. This was independently
   demonstrated as a live bypass by moving the accounts `has_permission(...)` statement, and
   both the identity `response = login_user(...)` assignment and its audit call, inside a
   nested function under the real target function - and separately, by using a `lambda user:
   ...` / `lambda response: ...` whose OWN parameter shadows the real outer `user`/`response`
   while the base-object NAME check still matched textually. `_iter_binding_names` also did
   not enumerate lambda parameters as binding sites at all. The C6 correction adds bounded
   lexical-scope analysis (`_iter_immediate_scope_nodes`): a traversal rooted at the target
   function that yields every node in its own body EXCEPT the contents of a nested
   `def`/`async def`/`lambda`/`class` (the scope-introducing node itself is yielded, so its
   presence is still visible, but recursion never descends into it). Both
   `_is_allowed_accounts_role_codes_usage` and `_is_allowed_identity_role_codes_usage` now
   collect candidate occurrences through this traversal instead of `ast.walk`, so a
   statement moved into any nested scope no longer counts as an occurrence of the target
   function's own immediate body - and because the fail-closed `.role_codes` visitor still
   visits every `.role_codes` access anywhere in the module (not only ones inside the target
   function), a nested-scope occurrence is not silently dropped from consideration; it is
   still visited, still fails the immediate-scope occurrence check, and is still reported as
   an offense. `_find_legitimate_response_assignment` is changed the same way, so a
   `response = login_user(...)` assignment moved into a nested scope is no longer accepted as
   the real production binding either. `_iter_binding_names` is also extended to enumerate
   `ast.Lambda` parameters as binding sites (defense in depth alongside the scope
   restriction, not the primary defense against it). This remains bounded AST/lexical-scope
   analysis: it is not a general Python interpreter, closure-semantics engine, symbolic
   executor, control-flow engine or whole-program analyzer, and it answers only "is this node
   written directly in this function's own body, without crossing into a nested lexical
   scope" - nothing about actual runtime closures, cell variables, or `nonlocal`/`global`
   declarations is modeled.

See `docs/continuity/PF_1A_E1_C3_CORRECTION_HANDOFF.md` section 14 for the C6 addendum recording
this pass and the fresh independent review it responds to.

This file also carries the PF-1A-E1 C7 correction. A further independent re-review (fresh
re-run of the C6-corrected guard) AGAIN independently reconfirmed the runtime authorization
candidate is sound, and found exactly one further class of bypass in the STATIC GUARD ITSELF
(not runtime behavior), closed here:

10. The C6 bounded lexical-scope model (`_SCOPE_INTRODUCING_NODE_TYPES`,
    `_iter_immediate_scope_nodes`) recognized nested `def`/`async def`/`lambda`/`class` as scope
    boundaries but did not recognize Python comprehensions or generator expressions
    (`ast.ListComp`, `ast.SetComp`, `ast.DictComp`, `ast.GeneratorExp`), even though each of
    these executes its element/key/value expression in its own implicit nested scope exactly
    like a nested `def`/`lambda` does. This was independently demonstrated as a live bypass by
    wrapping the real accounts `has_permission(db, user.role_codes, ACCOUNT_TAX_VERIFY)`
    statement, and separately the real identity `record_business_event(...)` audit call, inside
    a bare generator expression assigned to a local and never consumed - e.g.
    `check = (has_permission(db, user.role_codes, ACCOUNT_TAX_VERIFY) for item in (1,))`. This
    is especially dangerous at the RUNTIME level, independent of this guard: the generator
    object itself is truthy, so `if not check:` never raises and the wrapped permission call is
    never even executed, silently turning what looks like an enforced check into a no-op. The C7
    correction adds all four comprehension/generator node types to
    `_SCOPE_INTRODUCING_NODE_TYPES`, so `_iter_immediate_scope_nodes` yields the
    comprehension/generator node itself (its presence stays visible) but never descends into its
    body - the same treatment already given to a nested `def`/`async def`/`lambda`/`class`. The
    fail-closed global `.role_codes` scan (`_RoleCodesFailClosedVisitor`) needed no change: it
    already uses plain `ast.NodeVisitor.generic_visit`, which visits every node regardless of
    lexical scope, so a `.role_codes` access moved inside a comprehension/generator was already
    being visited - it simply is no longer counted as belonging to the target function's own
    immediate-scope occurrence set after this correction, so it now falls through to being
    reported as an offense, the same provenance-rejection path already used for a nested
    `def`/`lambda`. Comprehension/generator TARGET names (`for item in ...`) were already
    enumerated as binding sites by `_iter_binding_names` via `ast.comprehension` before this
    correction and needed no change.

See `docs/continuity/PF_1A_E1_C3_CORRECTION_HANDOFF.md` section 15 for the C7 addendum recording
this pass and the fresh independent review it responds to.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from types import SimpleNamespace

from fastapi.routing import APIRoute

from app.main import app
from tests.fixtures.pf_1a_e1_baseline_authorization import (
    BASELINE_ROUTE_PERMISSION_INVENTORY,
    BASELINE_UNGATED_ROUTES,
)
from tests.fixtures.post_baseline_tightened_routes import (
    POST_BASELINE_NEW_ROUTES,
    POST_BASELINE_TIGHTENED_ROUTES,
)

BACKEND_ROOT = Path(__file__).resolve().parents[1]
ROUTE_MODULES_DIR = BACKEND_ROOT / "app" / "modules"


# =========================================================================================
# Guard 1: require_roles must not be referenced in any route module, under any name, in
# any executable position - not only as a call.
# =========================================================================================
#
# AST-based, fail-closed at the REFERENCE level (PF-1A-E1 C3 finding 1.C). The pre-C3
# version only flagged an actual `Call` whose func was a tracked name or ended in
# `.require_roles`, which meant a local rebinding such as `rr = require_roles` or
# `rr = deps.require_roles` passed the guard entirely as long as `rr(...)` was never
# called - and even a later `rr(...)` call would have evaded the guard too, since `rr`
# itself is not a name the guard tracked. This version rejects the reference itself:
#
#   - the `ImportFrom` statement importing `require_roles` under any alias, whether or
#     not it is ever subsequently used;
#   - any bare `Name` load of `require_roles` or of any local alias introduced by such
#     an import - this alone makes `rr = require_roles` and `x = require_roles` fail at
#     the assignment, before any call;
#   - any `Attribute` access whose final `.attr` is literally `require_roles`,
#     regardless of the object/module it hangs off (`deps.require_roles`,
#     `identity_dependencies.require_roles`, etc.) - this makes `rr = deps.require_roles`
#     fail at the assignment too, and also fails a bare non-called reference such as
#     `handlers.append(require_roles)` or `handlers.append(deps.require_roles)`.
#
# This does not attempt full dataflow/alias tracking of `rr` after the fact (e.g. a
# second hop `x = rr; x(...)`); it does not need to, because the reference to the
# ORIGINAL `require_roles` name/attribute is itself already an offense at the point it
# first appears, per the requirement that ANY executable/reference use must fail
# closed - not only a use that is eventually called.


class _RequireRolesGuardVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.offenses: list[str] = []
        self._banned_names: set[str] = {"require_roles"}

    def collect_import_aliases(self, tree: ast.AST) -> None:
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    if alias.name == "require_roles":
                        self._banned_names.add(alias.asname or alias.name)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        for alias in node.names:
            if alias.name == "require_roles":
                bound_as = alias.asname or alias.name
                self.offenses.append(
                    f"line {node.lineno}: import of require_roles (bound as {bound_as!r})"
                )
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        if node.id in self._banned_names:
            self.offenses.append(
                f"line {node.lineno}: reference to require_roles via name {node.id!r}"
            )
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if node.attr == "require_roles":
            self.offenses.append(
                f"line {node.lineno}: reference to a qualified require_roles attribute"
            )
        self.generic_visit(node)


def _eval_compile_time_string(node: ast.expr | None) -> str | None:
    """Evaluate a small, bounded subset of compile-time-constant string expressions and
    return the resulting string, or `None` if `node` is not one of the forms this
    evaluator understands (PF-1A-E1 C5 finding 6). Understood forms:

    - a plain string `ast.Constant` (`"require_roles"`);
    - an `Add` `ast.BinOp` whose both sides recursively evaluate to compile-time strings
      (`"require_" + "roles"`) - Python's own parser already folds adjacent literal
      string constants (`"require_" "roles"`) into a single `Constant`, so that case is
      naturally covered without needing its own branch;
    - an `ast.JoinedStr` (f-string) all of whose components are themselves compile-time
      strings, i.e. no `ast.FormattedValue` (an interpolated `{expression}`) anywhere in
      it - an f-string with an actual interpolation is not compile-time and correctly
      yields `None`.

    This is deliberately NOT a general expression evaluator: it never resolves a
    variable reference, function call, string method, or any other Python expression
    form. A string built through anything other than these bounded literal forms is
    intentionally left unresolved (returns `None`) rather than guessed at.
    """
    if node is None:
        return None
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left = _eval_compile_time_string(node.left)
        right = _eval_compile_time_string(node.right)
        if left is not None and right is not None:
            return left + right
        return None
    if isinstance(node, ast.JoinedStr):
        parts: list[str] = []
        for value in node.values:
            if isinstance(value, ast.FormattedValue):
                return None
            part = _eval_compile_time_string(value)
            if part is None:
                return None
            parts.append(part)
        return "".join(parts)
    return None


def _find_dynamic_literal_attribute_accesses(tree: ast.AST, banned_attr: str) -> list[str]:
    """Return offense descriptions for any AST-obvious dynamic access to `banned_attr` via
    `getattr(x, "<banned_attr>")`, `vars(x)["<banned_attr>"]`, `x.__dict__["<banned_attr>"]`,
    `vars(x).get("<banned_attr>")` or `x.__dict__.get("<banned_attr>")` (PF-1A-E1 C4
    finding 1 / finding 2; PF-1A-E1 C5 finding 6 adds the two `.get(...)` forms and the
    bounded compile-time string evaluator above, so a deterministic literal-string
    composition such as `"require_" + "roles"` is recognized in every one of these
    positions, not only a single unbroken string constant). This deliberately does not
    attempt general dataflow or whole-program string analysis: it only recognizes a
    compile-time-constant string equal to `banned_attr`, in one of the five structurally
    obvious idioms above - not every conceivable dynamic-access idiom, and never a string
    produced by a variable, function call or string method.
    """
    offenses: list[str] = []

    def _is_literal_banned(node: ast.expr | None) -> bool:
        return _eval_compile_time_string(node) == banned_attr

    def _unwrap_slice(slice_node: ast.expr) -> ast.expr:
        # Python < 3.9 wraps a constant subscript key in ast.Index; 3.9+ uses the
        # expression directly. Unwrapped defensively for cross-version compatibility.
        if isinstance(slice_node, getattr(ast, "Index", ())):  # pragma: no cover - py<3.9
            return slice_node.value  # type: ignore[attr-defined]
        return slice_node

    def _is_vars_call(node: ast.expr) -> bool:
        return isinstance(node, ast.Call) and (
            (isinstance(node.func, ast.Name) and node.func.id == "vars")
            or (isinstance(node.func, ast.Attribute) and node.func.attr == "vars")
        )

    def _is_dunder_dict_attr(node: ast.expr) -> bool:
        return isinstance(node, ast.Attribute) and node.attr == "__dict__"

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            is_getattr = (isinstance(func, ast.Name) and func.id == "getattr") or (
                isinstance(func, ast.Attribute) and func.attr == "getattr"
            )
            if is_getattr:
                name_arg: ast.expr | None = node.args[1] if len(node.args) >= 2 else None
                if name_arg is None:
                    for kw in node.keywords:
                        if kw.arg == "name":
                            name_arg = kw.value
                            break
                if _is_literal_banned(name_arg):
                    offenses.append(
                        f"line {node.lineno}: dynamic getattr(..., {banned_attr!r}) reference"
                    )
                continue
            # PF-1A-E1 C5 finding 6: `vars(x).get("<banned_attr>")` / `x.__dict__.get(...)`
            # is a `.get(...)` method-call variant of the subscript idiom below, and was
            # independently demonstrated to evade the pre-C5 guard entirely (it produces
            # neither a `getattr(...)` call nor a `Subscript` node).
            if isinstance(func, ast.Attribute) and func.attr == "get":
                base = func.value
                if _is_vars_call(base) or _is_dunder_dict_attr(base):
                    key_arg: ast.expr | None = node.args[0] if node.args else None
                    if _is_literal_banned(key_arg):
                        offenses.append(
                            f"line {node.lineno}: dynamic vars()/__dict__ .get(..., "
                            f"{banned_attr!r}) reference"
                        )
        elif isinstance(node, ast.Subscript):
            key = _unwrap_slice(node.slice)
            if _is_literal_banned(key):
                base = node.value
                if _is_vars_call(base) or _is_dunder_dict_attr(base):
                    offenses.append(
                        f"line {node.lineno}: dynamic subscript access to {banned_attr!r} via "
                        "vars()/__dict__"
                    )
    return offenses


def _scan_for_require_roles(tree: ast.AST) -> list[str]:
    visitor = _RequireRolesGuardVisitor()
    visitor.collect_import_aliases(tree)
    visitor.visit(tree)
    offenses = list(visitor.offenses)
    offenses.extend(_find_dynamic_literal_attribute_accesses(tree, "require_roles"))
    return offenses


def test_no_route_module_reintroduces_require_roles_guard() -> None:
    offenders: list[str] = []
    for path in sorted(ROUTE_MODULES_DIR.glob("*/routes.py")):
        # utf-8-sig transparently strips a leading UTF-8 BOM if present (several existing
        # route modules carry one); ast.parse rejects a literal U+FEFF at the start of
        # source, so a plain "utf-8" read would raise SyntaxError on those files.
        source = path.read_text(encoding="utf-8-sig")
        tree = ast.parse(source, filename=str(path))
        offenses = _scan_for_require_roles(tree)
        if offenses:
            relative = str(path.relative_to(BACKEND_ROOT))
            offenders.extend(f"{relative}: {offense}" for offense in offenses)

    assert offenders == [], "require_roles(...) reintroduced in route module(s): " + "; ".join(offenders)


def test_require_roles_guard_detects_an_aliased_import_and_call() -> None:
    """PF-1A-E1 C2 finding 1.D: aliased import/call of require_roles must be caught."""
    snippet = (
        "from app.modules.identity.dependencies import require_roles as rr\n"
        "\n"
        "def endpoint():\n"
        "    return rr(('ADMIN',))\n"
    )
    tree = ast.parse(snippet)
    offenses = _scan_for_require_roles(tree)
    assert offenses, "guard failed to detect an aliased import/call of require_roles"


def test_require_roles_guard_detects_a_qualified_module_attribute_call() -> None:
    snippet = (
        "import app.modules.identity.dependencies as identity_dependencies\n"
        "\n"
        "def endpoint():\n"
        "    return identity_dependencies.require_roles(('ADMIN',))\n"
    )
    tree = ast.parse(snippet)
    offenses = _scan_for_require_roles(tree)
    assert offenses, "guard failed to detect a qualified module-attribute call of require_roles"


def test_require_roles_guard_detects_the_direct_unaliased_call() -> None:
    snippet = (
        "from app.modules.identity.dependencies import require_roles\n"
        "\n"
        "def endpoint():\n"
        "    return require_roles('ADMIN')\n"
    )
    tree = ast.parse(snippet)
    offenses = _scan_for_require_roles(tree)
    assert offenses, "guard failed to detect a direct, unaliased require_roles(...) call"


def test_require_roles_guard_permits_unrelated_calls() -> None:
    snippet = (
        "from app.modules.authorization.dependencies import require_permission\n"
        "\n"
        "def endpoint():\n"
        "    return require_permission('ACCOUNT_READ')\n"
    )
    tree = ast.parse(snippet)
    offenses = _scan_for_require_roles(tree)
    assert offenses == [], f"guard incorrectly flagged an unrelated require_permission(...) call: {offenses}"


def test_require_roles_guard_detects_local_rebinding_from_the_direct_import_before_any_call() -> None:
    """PF-1A-E1 C3 finding 1.C: `rr = require_roles` must fail at the assignment itself,
    even if `rr` is never subsequently called in a way a call-only guard could see.
    """
    snippet = (
        "from app.modules.identity.dependencies import require_roles\n"
        "\n"
        "def endpoint():\n"
        "    rr = require_roles\n"
        "    return rr(('ADMIN',))\n"
    )
    tree = ast.parse(snippet)
    offenses = _scan_for_require_roles(tree)
    assert offenses, "guard failed to detect local rebinding `rr = require_roles`"


def test_require_roles_guard_detects_local_rebinding_from_a_qualified_module_attribute() -> None:
    """PF-1A-E1 C3 finding 1.C: `rr = deps.require_roles` must fail at the assignment
    itself, the same as the direct-name rebinding case above.
    """
    snippet = (
        "import app.modules.identity.dependencies as deps\n"
        "\n"
        "def endpoint():\n"
        "    rr = deps.require_roles\n"
        "    return rr(('ADMIN',))\n"
    )
    tree = ast.parse(snippet)
    offenses = _scan_for_require_roles(tree)
    assert offenses, "guard failed to detect local rebinding `rr = deps.require_roles`"


def test_require_roles_guard_detects_a_bare_reference_passed_without_being_called() -> None:
    """PF-1A-E1 C3 finding 1.C: passing the bare `require_roles` reference into another
    structure (never itself called at that point) must still fail closed.
    """
    snippet = (
        "from app.modules.identity.dependencies import require_roles\n"
        "\n"
        "handlers = []\n"
        "handlers.append(require_roles)\n"
    )
    tree = ast.parse(snippet)
    offenses = _scan_for_require_roles(tree)
    assert offenses, "guard failed to detect a bare, uncalled reference to require_roles"


def test_require_roles_guard_detects_an_aliased_import_even_if_never_used() -> None:
    """PF-1A-E1 C3 finding 1.C: the import statement itself is an offense, independent
    of whether the imported name is ever referenced again in the module.
    """
    snippet = "from app.modules.identity.dependencies import require_roles as rr\n"
    tree = ast.parse(snippet)
    offenses = _scan_for_require_roles(tree)
    assert offenses, "guard failed to detect an aliased import of require_roles that is never called"


def test_require_roles_guard_detects_getattr_dynamic_lookup() -> None:
    """PF-1A-E1 C4 finding 1: `getattr(x, "require_roles")` obtains the banned dependency
    dynamically, evading every name/attribute-reference check above (there is no `Name`
    load of `require_roles` and no `Attribute` node whose `.attr` is `require_roles` - the
    string only ever appears as a literal call argument).
    """
    snippet = (
        "import app.modules.identity.dependencies as identity_dependencies\n"
        "\n"
        "def endpoint():\n"
        "    rr = getattr(identity_dependencies, 'require_roles')\n"
        "    return rr(('ADMIN',))\n"
    )
    tree = ast.parse(snippet)
    offenses = _scan_for_require_roles(tree)
    assert offenses, "guard failed to detect a dynamic getattr(..., 'require_roles') lookup"


def test_require_roles_guard_detects_vars_subscript_dynamic_lookup() -> None:
    """PF-1A-E1 C4 finding 1: `vars(x)["require_roles"]` is a second obvious dynamic-lookup
    idiom for the same bypass.
    """
    snippet = (
        "import app.modules.identity.dependencies as identity_dependencies\n"
        "\n"
        "def endpoint():\n"
        "    rr = vars(identity_dependencies)['require_roles']\n"
        "    return rr(('ADMIN',))\n"
    )
    tree = ast.parse(snippet)
    offenses = _scan_for_require_roles(tree)
    assert offenses, "guard failed to detect a dynamic vars(...)['require_roles'] lookup"


def test_require_roles_guard_detects_dunder_dict_subscript_dynamic_lookup() -> None:
    """PF-1A-E1 C4 finding 1: `x.__dict__["require_roles"]` is the third obvious
    dynamic-lookup idiom for the same bypass.
    """
    snippet = (
        "import app.modules.identity.dependencies as identity_dependencies\n"
        "\n"
        "def endpoint():\n"
        "    rr = identity_dependencies.__dict__['require_roles']\n"
        "    return rr(('ADMIN',))\n"
    )
    tree = ast.parse(snippet)
    offenses = _scan_for_require_roles(tree)
    assert offenses, "guard failed to detect a dynamic x.__dict__['require_roles'] lookup"


def test_require_roles_guard_permits_unrelated_dynamic_lookups() -> None:
    """PF-1A-E1 C4 finding 1 regression guard: the new dynamic-lookup detection must stay
    pinned to the literal string "require_roles" and must not flag ordinary, unrelated
    getattr/vars/__dict__ usage such as the real `_user_public_id` helper pattern already
    used across several route modules.
    """
    snippet = (
        "def _user_public_id(user):\n"
        "    value = getattr(user, 'user_public_id', None) or getattr(user, 'public_id', None)\n"
        "    return value\n"
        "\n"
        "def other(obj):\n"
        "    return vars(obj)['some_other_key']\n"
        "\n"
        "def other2(obj):\n"
        "    return obj.__dict__['some_other_key']\n"
    )
    tree = ast.parse(snippet)
    offenses = _scan_for_require_roles(tree)
    assert offenses == [], f"guard incorrectly flagged unrelated dynamic getattr/vars/__dict__ usage: {offenses}"


# -----------------------------------------------------------------------------------------
# PF-1A-E1 C5 finding 6: `.get(...)` method-call forms and compile-time string composition
# (e.g. `"require_" + "roles"`) were independently demonstrated as live bypasses of the C4
# dynamic-literal detector above. All five are closed by the bounded compile-time string
# evaluator (`_eval_compile_time_string`) and the new `.get(...)` recognition added to
# `_find_dynamic_literal_attribute_accesses`.
# -----------------------------------------------------------------------------------------


def test_require_roles_guard_detects_vars_get_dynamic_lookup() -> None:
    """PF-1A-E1 C5 finding 6, independently demonstrated bypass 1:
    `vars(deps).get("require_roles")` is a `.get(...)` method-call variant of the
    existing `vars(x)["require_roles"]` subscript detection, which the pre-C5 guard did
    not recognize at all (it produces neither a `getattr(...)` call nor a `Subscript`).
    """
    snippet = (
        "import app.modules.identity.dependencies as deps\n"
        "\n"
        "def endpoint():\n"
        "    rr = vars(deps).get('require_roles')\n"
        "    return rr(('ADMIN',))\n"
    )
    tree = ast.parse(snippet)
    offenses = _scan_for_require_roles(tree)
    assert offenses, "guard failed to detect vars(deps).get('require_roles')"


def test_require_roles_guard_detects_dunder_dict_get_dynamic_lookup() -> None:
    """PF-1A-E1 C5 finding 6, independently demonstrated bypass 2:
    `deps.__dict__.get("require_roles")` is the `x.__dict__` equivalent of the bypass
    above.
    """
    snippet = (
        "import app.modules.identity.dependencies as deps\n"
        "\n"
        "def endpoint():\n"
        "    rr = deps.__dict__.get('require_roles')\n"
        "    return rr(('ADMIN',))\n"
    )
    tree = ast.parse(snippet)
    offenses = _scan_for_require_roles(tree)
    assert offenses, "guard failed to detect deps.__dict__.get('require_roles')"


def test_require_roles_guard_detects_getattr_with_compile_time_string_concatenation() -> None:
    """PF-1A-E1 C5 finding 6, independently demonstrated bypass 3:
    `getattr(deps, "require_" + "roles")` composes the banned literal string at the
    call site through ordinary `+` concatenation of two string constants, which the
    pre-C5 guard's exact-`Constant`-equality check did not evaluate.
    """
    snippet = (
        "import app.modules.identity.dependencies as deps\n"
        "\n"
        "def endpoint():\n"
        "    rr = getattr(deps, 'require_' + 'roles')\n"
        "    return rr(('ADMIN',))\n"
    )
    tree = ast.parse(snippet)
    offenses = _scan_for_require_roles(tree)
    assert offenses, "guard failed to detect getattr(deps, 'require_' + 'roles')"


def test_require_roles_guard_detects_vars_subscript_with_compile_time_string_concatenation() -> None:
    """PF-1A-E1 C5 finding 6: the same compile-time string composition, used as a
    subscript key against `vars(...)` instead of a `getattr(...)` name argument.
    """
    snippet = (
        "import app.modules.identity.dependencies as deps\n"
        "\n"
        "def endpoint():\n"
        "    rr = vars(deps)['require_' + 'roles']\n"
        "    return rr(('ADMIN',))\n"
    )
    tree = ast.parse(snippet)
    offenses = _scan_for_require_roles(tree)
    assert offenses, "guard failed to detect vars(deps)['require_' + 'roles']"


def test_require_roles_guard_permits_unrelated_get_calls() -> None:
    """PF-1A-E1 C5 finding 6 regression guard: the new `.get(...)` detection must stay
    pinned to the literal/compile-time string "require_roles" against exactly
    `vars(...)`/`.__dict__` bases, and must not flag an ordinary dict `.get(...)` call or
    an unrelated key against `vars(...)`/`.__dict__`.
    """
    snippet = (
        "def endpoint(some_dict, obj):\n"
        "    a = some_dict.get('something_else')\n"
        "    b = vars(obj).get('other_key')\n"
        "    c = obj.__dict__.get('role_codes_other')\n"
        "    return a, b, c\n"
    )
    tree = ast.parse(snippet)
    offenses = _scan_for_require_roles(tree)
    assert offenses == [], f"guard incorrectly flagged unrelated .get(...) calls: {offenses}"


def test_require_roles_guard_permits_unrelated_compile_time_string_composition() -> None:
    """PF-1A-E1 C5 finding 6 regression guard: the bounded compile-time string evaluator
    must still correctly evaluate an unrelated concatenation to a non-matching string
    (here "foobar") and must not flag it, proving the evaluator is not merely "any BinOp
    concatenation is suspicious".
    """
    snippet = "def endpoint(obj):\n    return getattr(obj, 'foo_' + 'bar', None)\n"
    tree = ast.parse(snippet)
    offenses = _scan_for_require_roles(tree)
    assert offenses == [], f"guard incorrectly flagged unrelated compile-time string composition: {offenses}"


# =========================================================================================
# Guard 2: every protected route requests exactly the expected permission code, checked
# across the COMPLETE recursive FastAPI dependency graph.
# =========================================================================================


def _iter_all_dependencies(dependant: object, _ancestors: frozenset[int] | None = None):
    """Recursively yield every `Dependant` object in the FULL dependency graph rooted at
    `dependant` - not only the route's immediate/top-level `dependant.dependencies` list
    (PF-1A-E1 C3 finding 1.A). A permission dependency declared inside the signature of
    another dependency (a "sub-dependency") is otherwise invisible to a helper that only
    inspects the top level.

    `_ancestors` tracks the object-identity chain of the CURRENT recursion path (root down
    to `dependant`), not every object visited anywhere in the graph. This distinction is
    deliberate (PF-1A-E1 C3 correction 3):

    - A true cycle - a dependency reachable again from within its own descendant chain -
      is detected because the repeated object's id is already an ancestor of the path that
      reached it, so it is skipped (not yielded, not re-descended into), which terminates
      recursion safely and yields the cycle member exactly once (via its first, outer
      occurrence).
    - The SAME dependency object reached through two independent sibling branches (a
      "diamond", not a cycle - see
      `test_iter_all_dependencies_does_not_revisit_the_same_object_reached_twice`) is still
      yielded once per branch, because it is not an ancestor of the *other* branch's
      traversal path. A single global visited set shared across the whole graph would
      incorrectly collapse this case to one yield, which would silently hide a route that
      genuinely carries the same permission dependency twice.

    The ancestor check happens before a child is ever yielded, so a back-edge cannot cause
    the same object to be emitted more than once by way of the edge that closes the cycle.
    """
    if _ancestors is None:
        _ancestors = frozenset()
    current_ancestors = _ancestors | {id(dependant)}
    for child in getattr(dependant, "dependencies", None) or []:
        if id(child) in current_ancestors:
            continue
        yield child
        yield from _iter_all_dependencies(child, current_ancestors)


def _route_required_permission_codes(route: APIRoute) -> list[str]:
    """Return EVERY permission code any dependency ANYWHERE in a route's complete
    dependency graph carries via the `required_permission_code` metadata
    `app.modules.authorization.dependencies.require_permission` attaches to its returned
    closure (PF-1A-E1 C1-01). PF-1A-E1 C2 finding 1.A collected every TOP-LEVEL match;
    PF-1A-E1 C3 finding 1.A extends this to every match anywhere in the recursive
    dependency graph, so the caller can assert there is exactly one in the whole graph,
    not just at the top level.
    """
    codes: list[str] = []
    for dependency in _iter_all_dependencies(route.dependant):
        code = getattr(dependency.call, "required_permission_code", None)
        if code is not None:
            codes.append(str(code))
    return codes


def _classify_permission_codes(codes: list[str], expected_permission: str) -> str:
    """Pure classification helper, independently testable against synthetic dependency
    lists without needing a live FastAPI app (PF-1A-E1 C2 finding 1.D). Returns one of
    "ok", "missing", "multiple", "wrong".
    """
    if len(codes) == 0:
        return "missing"
    if len(codes) > 1:
        return "multiple"
    if codes[0] != expected_permission:
        return "wrong"
    return "ok"


def test_permission_classification_rejects_zero_wrong_and_multiple_dependency_counts() -> None:
    assert _classify_permission_codes([], "ACCOUNT_READ") == "missing"
    assert _classify_permission_codes(["ACCOUNT_READ"], "ACCOUNT_READ") == "ok"
    assert _classify_permission_codes(["ACCOUNT_CREATE"], "ACCOUNT_READ") == "wrong"
    assert _classify_permission_codes(["ACCOUNT_READ", "ACCOUNT_TAX_VERIFY"], "ACCOUNT_READ") == "multiple"


def _fake_permission_dependency(permission_code: str | None, dependencies: list | None = None) -> SimpleNamespace:
    def call() -> None:
        return None

    if permission_code is not None:
        call.required_permission_code = permission_code  # type: ignore[attr-defined]
    return SimpleNamespace(call=call, dependencies=dependencies or [])


def test_route_required_permission_codes_collects_every_matching_dependency_not_only_the_first() -> None:
    """PF-1A-E1 C2 finding 1.A / 1.D: direct regression proof that the helper collects
    ALL matching top-level dependencies, not only the first - the exact bug the reviewer
    found in the pre-correction guard. A route carrying the expected permission plus a
    second, narrower permission dependency must surface as two collected codes, not one.
    """
    fake_route = SimpleNamespace(
        dependant=SimpleNamespace(
            dependencies=[
                _fake_permission_dependency("ACCOUNT_READ"),
                _fake_permission_dependency("ACCOUNT_TAX_VERIFY"),
                _fake_permission_dependency(None),  # e.g. get_db - carries no metadata at all
            ]
        )
    )
    codes = _route_required_permission_codes(fake_route)  # type: ignore[arg-type]
    assert codes == ["ACCOUNT_READ", "ACCOUNT_TAX_VERIFY"], (
        f"expected both permission dependencies to be collected, got {codes!r}"
    )
    assert _classify_permission_codes(codes, "ACCOUNT_READ") == "multiple", (
        "a route with the expected permission plus a second permission dependency must be "
        "classified as 'multiple', not silently accepted as 'ok'"
    )


def test_route_required_permission_codes_discovers_a_permission_nested_inside_another_dependency() -> None:
    """PF-1A-E1 C3 finding 1.A: a permission dependency declared in the signature of
    another (non-permission) dependency - i.e. one level below the route's top-level
    `dependant.dependencies` - must still be discovered. Before this correction, the
    helper inspected only `route.dependant.dependencies` directly and this case was
    invisible: the top level here shows only one dependency (`outer_call`, which itself
    carries the expected permission), while a second permission dependency is hidden one
    level deeper.
    """
    outer_dependency = _fake_permission_dependency(
        "ACCOUNT_READ",
        dependencies=[_fake_permission_dependency("ACCOUNT_TAX_VERIFY")],
    )
    fake_route = SimpleNamespace(dependant=SimpleNamespace(dependencies=[outer_dependency]))

    codes = _route_required_permission_codes(fake_route)  # type: ignore[arg-type]
    assert sorted(codes) == ["ACCOUNT_READ", "ACCOUNT_TAX_VERIFY"], (
        f"expected the nested permission dependency to be discovered alongside the top-level "
        f"one, got {codes!r}"
    )
    assert _classify_permission_codes(codes, "ACCOUNT_READ") == "multiple", (
        "a route whose complete dependency graph carries the expected permission plus a "
        "second, nested permission dependency must be classified as 'multiple'"
    )


def test_route_required_permission_codes_discovers_a_permission_that_is_only_nested() -> None:
    """PF-1A-E1 C3 finding 1.A: a route whose ONLY permission dependency is nested one
    level below a non-permission top-level wrapper dependency must still resolve to
    exactly one discovered code, classified "ok" - not "missing".
    """
    wrapper_dependency = _fake_permission_dependency(
        None,
        dependencies=[_fake_permission_dependency("ACCOUNT_READ")],
    )
    fake_route = SimpleNamespace(dependant=SimpleNamespace(dependencies=[wrapper_dependency]))

    codes = _route_required_permission_codes(fake_route)  # type: ignore[arg-type]
    assert codes == ["ACCOUNT_READ"], f"expected the nested-only permission to be discovered, got {codes!r}"
    assert _classify_permission_codes(codes, "ACCOUNT_READ") == "ok"


def test_route_required_permission_codes_handles_a_cyclic_dependency_graph_without_infinite_recursion() -> None:
    """PF-1A-E1 C3 finding 1.A: a malformed/cyclic dependency graph must not cause
    infinite recursion, and must not cause the same dependency to be counted more than
    once because it is reachable through the cycle.
    """
    dependency_a = _fake_permission_dependency("ACCOUNT_READ")
    dependency_b = _fake_permission_dependency(None)
    dependency_a.dependencies = [dependency_b]
    dependency_b.dependencies = [dependency_a]  # cycle: a -> b -> a -> b -> ...

    fake_route = SimpleNamespace(dependant=SimpleNamespace(dependencies=[dependency_a]))

    codes = _route_required_permission_codes(fake_route)  # type: ignore[arg-type]
    assert codes == ["ACCOUNT_READ"], (
        f"expected the single real permission to be discovered exactly once despite the "
        f"cycle, got {codes!r}"
    )


def test_iter_all_dependencies_does_not_revisit_the_same_object_reached_twice() -> None:
    """A dependency reachable through two different paths in the graph (a diamond, not a
    cycle) must be yielded once per path traversal step but must never cause unbounded
    recursion; this also proves `_ancestors` is keyed by object identity, not by value
    equality, so two independently-constructed but equal-looking dependencies are not
    incorrectly conflated.
    """
    shared_leaf = _fake_permission_dependency("ACCOUNT_READ")
    branch_one = _fake_permission_dependency(None, dependencies=[shared_leaf])
    branch_two = _fake_permission_dependency(None, dependencies=[shared_leaf])
    fake_route = SimpleNamespace(dependant=SimpleNamespace(dependencies=[branch_one, branch_two]))

    codes = _route_required_permission_codes(fake_route)  # type: ignore[arg-type]
    assert codes == ["ACCOUNT_READ", "ACCOUNT_READ"], (
        "the shared leaf is reached via two independent top-level branches and is expected "
        f"once per branch traversal (not deduplicated across branches), got {codes!r}"
    )
    assert _classify_permission_codes(codes, "ACCOUNT_READ") == "multiple"


def test_every_protected_api_route_requests_the_expected_baseline_permission() -> None:
    live_routes: dict[tuple[str, str], APIRoute] = {}
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        if not route.path.startswith("/api/"):
            continue
        for method in sorted(route.methods or []):
            live_routes[(method, route.path)] = route

    # A sharp drop here would mean routers stopped being included in app.main, or the
    # candidate/baseline route set has silently shrunk; guard the total shape before
    # checking individual routes.
    assert len(live_routes) >= 70, (
        f"only {len(live_routes)} live /api/ routes were found; expected at least 70. "
        "Has a router stopped being included in app.main?"
    )

    # Two post-baseline structures are merged into the same lookup BASELINE_ROUTE_PERMISSION_
    # INVENTORY drives, so every route in them is checked by the exact same missing/wrong/
    # multiple classification as any baseline-protected route:
    #
    #   POST_BASELINE_TIGHTENED_ROUTES  was ungated at baseline, deliberately tightened later.
    #       Merging it here also means it never reaches the "is_baseline_ungated" branch below,
    #       which is what stops a deliberate tightening reporting as unexpected_ungated.
    #       BASELINE_UNGATED_ROUTES itself stays byte-identical - a true historical statement.
    #   POST_BASELINE_NEW_ROUTES        did not exist at baseline. Without this, such a route
    #       fell through to the "unaccounted_for" branch, which only checks that SOME permission
    #       dependency exists - so its exact permission was never pinned and two new routes could
    #       have had their permissions swapped undetected (correction pass 1, finding 5).
    expected_permission_lookup: dict[tuple[str, str], str] = {
        **BASELINE_ROUTE_PERMISSION_INVENTORY,
        **POST_BASELINE_TIGHTENED_ROUTES,
        **POST_BASELINE_NEW_ROUTES,
    }

    missing_permission: list[str] = []
    wrong_permission: list[str] = []
    multiple_permission: list[str] = []
    unexpected_ungated: list[str] = []
    unaccounted_for: list[str] = []

    for key, route in live_routes.items():
        method, path = key
        expected_permission = expected_permission_lookup.get(key)
        is_baseline_ungated = key in BASELINE_UNGATED_ROUTES
        codes = _route_required_permission_codes(route)

        if expected_permission is not None:
            classification = _classify_permission_codes(codes, expected_permission)
            if classification == "missing":
                missing_permission.append(f"{method} {path} (expected {expected_permission!r})")
            elif classification == "multiple":
                multiple_permission.append(
                    f"{method} {path}: expected exactly one permission dependency "
                    f"({expected_permission!r}), found {len(codes)}: {codes!r}"
                )
            elif classification == "wrong":
                wrong_permission.append(
                    f"{method} {path}: expected {expected_permission!r}, got {codes[0]!r}"
                )
        elif is_baseline_ungated:
            if codes:
                # Not itself wrong (a formerly-ungated route may be deliberately tightened
                # later), but it means the baseline snapshot is now stale and must be
                # updated through a reviewed change, not silently.
                unexpected_ungated.append(
                    f"{method} {path}: baseline treats this as ungated but it now requires "
                    f"{codes!r} - update BASELINE_UNGATED_ROUTES / "
                    f"BASELINE_ROUTE_PERMISSION_INVENTORY"
                )
        else:
            # A route neither the protected inventory nor the exact ungated allowlist
            # names at all: a genuinely new route added after PF-1A-E1 without updating
            # either baseline artifact. Require it to at least carry a permission
            # dependency; which exact permission is a design decision for whoever adds
            # the route; it must not silently fall through ungated.
            if not codes:
                unaccounted_for.append(f"{method} {path} (no require_permission(...) dependency)")

    assert missing_permission == [], "route(s) missing require_permission(...): " + "; ".join(missing_permission)
    assert wrong_permission == [], "route(s) requesting the wrong permission: " + "; ".join(wrong_permission)
    assert multiple_permission == [], (
        "route(s) carrying more than one require_permission(...) dependency: " + "; ".join(multiple_permission)
    )
    assert unexpected_ungated == [], "; ".join(unexpected_ungated)
    assert unaccounted_for == [], (
        "route(s) not present in either the baseline permission inventory or the exact "
        "ungated allowlist, and not permission-gated: " + "; ".join(unaccounted_for)
    )


def test_baseline_route_inventory_routes_still_exist_in_the_live_app() -> None:
    """Inverse direction of the guard above: a route the baseline inventory expects must
    still exist and still be reachable, not silently removed.
    """
    live_keys: set[tuple[str, str]] = set()
    for route in app.routes:
        if not isinstance(route, APIRoute) or not route.path.startswith("/api/"):
            continue
        for method in route.methods or []:
            live_keys.add((method, route.path))

    missing_routes = set(BASELINE_ROUTE_PERMISSION_INVENTORY.keys()) - live_keys
    assert missing_routes == set(), f"baseline-protected route(s) no longer exist: {sorted(missing_routes)}"


# =========================================================================================
# Guard 3: no route module may reintroduce direct application-role authorization logic.
# =========================================================================================
#
# Fail-closed (PF-1A-E1 C2 finding 1.B), and EXACT/structural rather than a loose
# file-scoped pattern (PF-1A-E1 C3 finding 1.B). EVERY `.role_codes` attribute access
# anywhere in a route module is an offense UNLESS it matches one of exactly two
# documented allow-shapes, each pinned to the literal real production statement it
# describes - not merely "this shape, anywhere in this file":
#
#   - accounts/routes.py, inside `_assert_tax_verification_permission(...)` only:
#     `has_permission(db, user.role_codes, ACCOUNT_TAX_VERIFY)` - a bare-name call to
#     `has_permission` (never a qualified `policy.has_permission(...)`), with exactly
#     three positional arguments and no keyword arguments, where `.role_codes` is
#     exactly the second positional argument and its base is exactly the real production
#     `user` variable (never a look-alike such as `other.role_codes`), the first
#     positional argument is exactly the local `db` session parameter, and the third
#     positional argument is exactly the `ACCOUNT_TAX_VERIFY` permission constant. The
#     authorization *decision* lives entirely inside
#     `app.modules.authorization.service.has_permission` against the ORA-owned
#     compatibility mapping, so this is not a route-local decision at all - but only when
#     it is genuinely that exact statement, not a look-alike.
#   - identity/routes.py, inside `login(...)` only: `.role_codes` on exactly the real
#     production base object `response.user`, as the value of a dict entry keyed by the
#     literal string `"role_codes"`, where that dict is itself PRECISELY the
#     `event_payload=` keyword argument of a bare-name call to `record_business_event(...)`
#     that also carries `event_name="UserLoginSucceeded"` - i.e. the actual login-success
#     audit-event emission, not a `role_codes` dict built for some other purpose and not a
#     fabricated/different event identity carrying the same payload shape. This is plain
#     audit-event data, not a decision - but again, only when it is genuinely that exact
#     statement.
#
# Both shapes are pinned to the exact enclosing function AND the exact call/keyword
# structure, not merely to the containing file: the identical-looking source shape used
# in a DIFFERENT function in the same file, a qualified call instead of a bare name, the
# wrong permission/keyword, a wrong `.role_codes` base object, or a fabricated event
# identity, are all still rejected (see the dedicated negative tests below). This closes
# the C3 finding that the C2 exceptions matched too broadly - "any `.role_codes` in a
# positional argument to anything ending in `.has_permission`" and "any `role_codes` dict
# value anywhere in the file" respectively - which would have let an unrelated
# `has_permission(..., ACCOUNT_READ)` call, a `policy.has_permission(...)` call, or a
# `role_codes` dict passed to an arbitrary authorization helper pass the guard.
#
# PF-1A-E1 C4 finding 2 closes two further, narrower bypasses the C3 shapes above still
# left open: (a) both allow-shapes matched on the CALLEE NAME SPELLING alone
# (`has_permission`, `record_business_event`), so locally rebinding that name to something
# else (`has_permission = policy.has_permission`) still matched the shape while calling an
# arbitrary function - closed by `_name_is_shadowed(...)`, which fails closed if the
# tracked helper name is bound anywhere in the module other than through the one expected,
# unaliased import of it; and (b) a dynamic `getattr(user, "role_codes")` (or
# `vars(...)["role_codes"]` / `x.__dict__["role_codes"]`) equivalent never produces an
# `ast.Attribute` node at all, so it was invisible to this attribute-scanning visitor
# entirely - closed by the unconditional, module-independent
# `_find_dynamic_literal_attribute_accesses(tree, "role_codes")` scan appended in
# `visit_and_collect`, since no legitimate production code accesses `role_codes`
# dynamically.
#
# PF-1A-E1 C5 finding 7 supersedes the C4 `_name_is_shadowed(...)` call described in (a)
# immediately above with the fuller `_helper_provenance_is_trustworthy(...)` (also requires
# a genuine expected import to actually EXIST, and fails closed on any star import), and
# additionally proves the `.role_codes` base object's own provenance, the permission
# constant's provenance (accounts), and that the enclosing target function is unique - see
# the "provenance model" comment block immediately below `_build_parent_map` for the full,
# current description. This C4 paragraph is preserved as an accurate historical record of
# what C4 itself closed; it does not describe the current call sequence.
#
# PF-1A-E1 C6 further refines two parts of the C5 provenance model without changing its
# overall shape: (1) import provenance (`_is_expected_import_binding` /
# `_count_expected_import_bindings`, used by `_helper_provenance_is_trustworthy`) is proved
# per individual `ast.alias`, not per `ImportFrom` statement, closing a same-statement
# alias-collision bypass; and (2) the occurrence-uniqueness check inside
# `_is_allowed_accounts_role_codes_usage` / `_is_allowed_identity_role_codes_usage` (and
# `_find_legitimate_response_assignment`) now walks only the target function's own
# IMMEDIATE lexical scope (`_iter_immediate_scope_nodes`), not its full `ast.walk` subtree,
# closing a bypass where the allowed statement was moved into a nested function/lambda
# under the real target function. See the module docstring findings 8-9 for the full
# bypass description and `docs/continuity/PF_1A_E1_C3_CORRECTION_HANDOFF.md` section 14.
#
# The separate `*_ROLES` route-local tuple-constant check (unrelated to `.role_codes`
# usage - it can be reintroduced with zero reference to `.role_codes`) is retained.

ROLE_TUPLE_CONSTANT_NAME_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]*_ROLES$")

ACCOUNTS_ALLOWED_ENCLOSING_FUNCTION = "_assert_tax_verification_permission"
ACCOUNTS_ALLOWED_CALL_NAME = "has_permission"
ACCOUNTS_ALLOWED_DB_ARG_NAME = "db"
ACCOUNTS_ALLOWED_PERMISSION_CONSTANT = "ACCOUNT_TAX_VERIFY"
# PF-1A-E1 C4 finding 2: the real production `.role_codes` base object, and the real
# module/name `has_permission` is imported from - see
# `backend/app/modules/accounts/routes.py`: `from app.modules.authorization.service
# import has_permission` (unaliased) and `has_permission(db, user.role_codes,
# ACCOUNT_TAX_VERIFY)` inside `_assert_tax_verification_permission`.
ACCOUNTS_ALLOWED_ROLE_CODES_BASE_NAME = "user"
ACCOUNTS_EXPECTED_IMPORT_MODULE = "app.modules.authorization.service"
ACCOUNTS_EXPECTED_IMPORT_ORIGINAL_NAME = "has_permission"

IDENTITY_ALLOWED_ENCLOSING_FUNCTION = "login"
IDENTITY_ALLOWED_CALL_NAME = "record_business_event"
IDENTITY_ALLOWED_KEYWORD_NAME = "event_payload"
IDENTITY_ALLOWED_DICT_KEY = "role_codes"
# PF-1A-E1 C4 finding 2: the real production `.role_codes` base object is `response.user`,
# the real event identity is `event_name="UserLoginSucceeded"`, and `record_business_event`
# is imported from `app.modules.events.service` (unaliased) - see
# `backend/app/modules/identity/routes.py::login`.
IDENTITY_ALLOWED_ROLE_CODES_BASE_ATTR = "user"
IDENTITY_ALLOWED_ROLE_CODES_BASE_NAME = "response"
IDENTITY_ALLOWED_EVENT_NAME_KEYWORD = "event_name"
IDENTITY_ALLOWED_EVENT_NAME_VALUE = "UserLoginSucceeded"
IDENTITY_EXPECTED_IMPORT_MODULE = "app.modules.events.service"
IDENTITY_EXPECTED_IMPORT_ORIGINAL_NAME = "record_business_event"

# PF-1A-E1 C5 finding 7: further real-production provenance facts, inspected directly from
# `backend/app/modules/accounts/routes.py` and `backend/app/modules/identity/routes.py`.
#
# Accounts: `def _assert_tax_verification_permission(db: Session, user: AuthUser,
# requested_state: str | None) -> None:` - `user` is positional parameter index 1 (`db` is
# 0). `ACCOUNT_TAX_VERIFY` is imported unaliased from `app.modules.authorization.contract`.
ACCOUNTS_ALLOWED_USER_PARAM_INDEX = 1
ACCOUNTS_EXPECTED_PERMISSION_IMPORT_MODULE = "app.modules.authorization.contract"
ACCOUNTS_EXPECTED_PERMISSION_IMPORT_ORIGINAL_NAME = "ACCOUNT_TAX_VERIFY"

# Identity: inside `def login(payload: LoginRequest, db: Session = Depends(get_db)) ->
# LoginResponse:`, `response` is not a parameter - it is bound by exactly one local
# assignment, `response = login_user(db, payload.username, payload.password)`. `login_user`
# is itself imported unaliased from `app.modules.identity.service`.
IDENTITY_ALLOWED_RESPONSE_ASSIGNMENT_CALLEE = "login_user"
IDENTITY_EXPECTED_LOGIN_USER_IMPORT_MODULE = "app.modules.identity.service"
IDENTITY_EXPECTED_LOGIN_USER_IMPORT_ORIGINAL_NAME = "login_user"


# -----------------------------------------------------------------------------------------
# PF-1A-E1 C4 finding 2, extended by PF-1A-E1 C5 finding 7: prove the documented helper name
# (`has_permission`, `record_business_event`) used by each allow-shape - and, per C5, the
# `.role_codes` base object and the ACCOUNT_TAX_VERIFY permission constant - is still the
# genuine, unshadowed, GENUINELY PRESENT expected import within the module being checked,
# not a locally rebound or reimported look-alike (e.g. `has_permission = policy.has_permission`),
# a pattern-match capture (`case has_permission:`), or a name supplied only by a star import
# whose actual contents static analysis cannot see. This is a bounded binding-site scan, not
# general dataflow analysis: `_iter_binding_names` enumerates the bounded set of Python
# binding forms it explicitly lists below (assignment/augmented-assignment/annotated-
# assignment/walrus targets, for-loop and comprehension targets, `with`/`except` bindings,
# function/class definitions and parameters, import aliases, and - added by PF-1A-E1 C5 -
# match-statement capture patterns), not a claim of exhaustive coverage of every conceivable
# way a name can be bound in Python. `_helper_provenance_is_trustworthy` (PF-1A-E1 C5) is
# what actually fails closed if the tracked name is bound anywhere other than exactly one
# genuine, unaliased `ImportFrom` of it from the exact expected module, OR if the module
# contains any star import at all.
# -----------------------------------------------------------------------------------------


def _iter_target_names(target: ast.AST):
    if isinstance(target, ast.Name):
        yield target.id
    elif isinstance(target, ast.Starred):
        yield from _iter_target_names(target.value)
    elif isinstance(target, (ast.Tuple, ast.List)):
        for elt in target.elts:
            yield from _iter_target_names(elt)
    # ast.Attribute / ast.Subscript assignment targets (e.g. `obj.attr = ...`) do not bind
    # a bare name and are intentionally not treated as rebinding a tracked helper name.


def _iter_binding_names(tree: ast.AST):
    """Yield the bare name bound at each of the BOUNDED set of binding-site forms this
    function explicitly enumerates below, alongside a marker identifying the binding site:
    assignment/augmented-assignment/annotated-assignment/walrus targets, for-loop and
    comprehension targets, `with`/`except` bindings, function and class definitions
    (including every parameter name), import aliases, lambda parameters (PF-1A-E1 C6), and
    - added by PF-1A-E1 C5 - match-statement capture patterns (`ast.MatchAs`,
    `ast.MatchStar`, `ast.MatchMapping`'s `**rest` binding, including nested inside
    `ast.MatchSequence`/`ast.MatchClass`/`ast.MatchOr`, all reached by the same `ast.walk`
    traversal since they are themselves AST nodes). This list is not a claim of exhaustive
    coverage of every way a name can be bound in Python; it is the bounded set of forms
    this guard understands.

    For every binding form EXCEPT `ImportFrom`, the yielded marker is the AST node that
    binds the name (a statement, a `FunctionDef`, etc.), and identity comparison against
    that node (`node is skip_node`) is meaningful. For `ImportFrom`, PF-1A-E1 C6 finding 1
    changes the marker to a `(import_node, alias)` tuple identifying the SPECIFIC
    `ast.alias` that produced the binding, not the ImportFrom statement as a whole - see
    `_is_expected_import_binding` for why this distinction is required.
    """
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                for name in _iter_target_names(target):
                    yield name, node
        elif isinstance(node, (ast.AugAssign, ast.AnnAssign, ast.NamedExpr)):
            for name in _iter_target_names(node.target):
                yield name, node
        elif isinstance(node, (ast.For, ast.AsyncFor)):
            for name in _iter_target_names(node.target):
                yield name, node
        elif isinstance(node, ast.comprehension):
            for name in _iter_target_names(node.target):
                yield name, node
        elif isinstance(node, ast.withitem):
            if node.optional_vars is not None:
                for name in _iter_target_names(node.optional_vars):
                    yield name, node
        elif isinstance(node, ast.ExceptHandler):
            if node.name:
                yield node.name, node
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            yield node.name, node
            all_args = (
                list(node.args.posonlyargs)
                + list(node.args.args)
                + list(node.args.kwonlyargs)
                + ([node.args.vararg] if node.args.vararg else [])
                + ([node.args.kwarg] if node.args.kwarg else [])
            )
            for arg in all_args:
                yield arg.arg, node
        elif isinstance(node, ast.Lambda):
            # PF-1A-E1 C6 lambda binding enumeration: a lambda parameter binds its local
            # name exactly like a function parameter does. This is defense in depth - the
            # primary defense against a shadowing lambda parameter is the immediate-scope
            # restriction in `_iter_immediate_scope_nodes` below, which already excludes a
            # lambda's own body from its enclosing function's immediate scope - but a
            # lambda parameter is still a genuine binding site and belongs in this bounded
            # enumeration regardless.
            all_lambda_args = (
                list(node.args.posonlyargs)
                + list(node.args.args)
                + list(node.args.kwonlyargs)
                + ([node.args.vararg] if node.args.vararg else [])
                + ([node.args.kwarg] if node.args.kwarg else [])
            )
            for arg in all_lambda_args:
                yield arg.arg, node
        elif isinstance(node, ast.ClassDef):
            yield node.name, node
        elif isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.asname or alias.name.split(".")[0], node
        elif isinstance(node, ast.ImportFrom):
            # PF-1A-E1 C6 finding 1: yield a PER-ALIAS marker `(node, alias)`, not the bare
            # ImportFrom `node` itself. A single ImportFrom statement can bind the same
            # local name more than once (`from mod import X, Y as X`), and provenance must
            # be proved against the SPECIFIC alias that produced THIS occurrence of the
            # binding, not "does this statement contain a genuine alias for this name
            # somewhere" - see `_is_expected_import_binding`.
            for alias in node.names:
                yield alias.asname or alias.name, (node, alias)
        # PF-1A-E1 C5 finding 7.C: a match-statement capture pattern (`case has_permission:`)
        # binds a name exactly like an assignment does, and must be recognized as a possible
        # shadowing site the same way. `ast.MatchAs`/`ast.MatchStar`/`ast.MatchMapping` are
        # available from Python 3.10 onward; this repository's backend runs Python 3.12
        # (`backend/Dockerfile`), so the attributes are always present, but the lookups are
        # written defensively via `getattr` for cross-version robustness of this test file.
        elif isinstance(node, getattr(ast, "MatchAs", ())):
            if node.name:
                yield node.name, node
        elif isinstance(node, getattr(ast, "MatchStar", ())):
            if node.name:
                yield node.name, node
        elif isinstance(node, getattr(ast, "MatchMapping", ())):
            if node.rest:
                yield node.rest, node


def _is_expected_import_binding(
    node: object, name: str, expected_module: str, expected_original_name: str
) -> bool:
    """`node` is the per-alias binding-site marker `_iter_binding_names` yields for an
    `ImportFrom` binding: a `(import_node, alias)` tuple identifying exactly the ONE
    `ast.alias` that produced this specific binding occurrence - never the ImportFrom
    statement as a whole (PF-1A-E1 C6 finding 1).

    This distinction is the actual fix for an independently demonstrated bypass: a single
    ImportFrom statement can bind the same local name more than once, e.g.
    `from mod import X, Y as X` - one genuine alias for `X`, and one conflicting alias
    (`Y as X`) that ALSO binds the local name `X`, overwriting it with a different symbol.
    The pre-C6 version of this check asked "does the ENCLOSING STATEMENT contain a genuine
    alias for this name ANYWHERE" - which is true for both bindings that statement
    produces, because the genuine alias is present somewhere in it - so the second,
    conflicting alias was incorrectly treated as trustworthy too, purely because it shares
    a statement with a genuine one. Checking the SPECIFIC alias that produced this
    occurrence closes that gap: only the occurrence whose own `alias.name` truly is
    `expected_original_name` passes, regardless of what else the same statement imports.
    """
    if not (isinstance(node, tuple) and len(node) == 2):
        return False
    import_node, alias = node
    if not isinstance(import_node, ast.ImportFrom) or not isinstance(alias, ast.alias):
        return False
    if import_node.module != expected_module:
        return False
    return alias.name == expected_original_name and (alias.asname or alias.name) == name


def _name_is_shadowed(tree: ast.AST, name: str, expected_module: str, expected_original_name: str) -> bool:
    """Return True if `name` is bound anywhere in `tree` other than through the single
    expected, unaliased `from expected_module import expected_original_name` - i.e. it has
    been rebound (assignment, redefinition, parameter shadowing, ...) or imported from an
    unexpected source, and a call site using `name` can therefore no longer be trusted to
    reach the genuine production helper.
    """
    for bound_name, node in _iter_binding_names(tree):
        if bound_name != name:
            continue
        if _is_expected_import_binding(node, name, expected_module, expected_original_name):
            continue
        return True
    return False


def _build_parent_map(tree: ast.AST) -> dict[ast.AST, ast.AST]:
    parents: dict[ast.AST, ast.AST] = {}
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            parents[child] = parent
    return parents


# -----------------------------------------------------------------------------------------
# PF-1A-E1 C5 finding 7: provenance model. The C4 allow-shape checks proved callee/base-object
# SPELLING and the enclosing function's NAME, but not: that the tracked helper name genuinely
# resolves to the one expected import rather than a star import; that the `.role_codes` base
# object and (for accounts) the permission constant resolve to their real production binding
# rather than an in-function rebinding; or that the enclosing target function is UNIQUE in the
# module. Each of these was independently demonstrated as a live bypass. The helpers below
# supply that missing provenance; the per-module `_is_allowed_*_role_codes_usage` functions
# compose them with a separate, reusable SHAPE-only predicate.
# -----------------------------------------------------------------------------------------


def _module_has_star_import(tree: ast.AST) -> bool:
    """Return True if `tree` contains a `from <module> import *` anywhere. A star import
    can supply an arbitrary same-named symbol whose actual origin static analysis cannot
    see or rule out, so any tracked helper/constant name's provenance is untrustworthy in
    a module that contains one at all - regardless of whether an explicit conflicting
    binding is also present (PF-1A-E1 C5 finding 7.A, independently demonstrated bypasses
    A and B).
    """
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name == "*":
                    return True
    return False


def _count_expected_import_bindings(
    tree: ast.AST, name: str, expected_module: str, expected_original_name: str
) -> int:
    """Count the number of INDIVIDUAL `ast.alias` bindings - not ImportFrom STATEMENTS -
    that genuinely bind `name` to `expected_original_name` from `expected_module`
    (PF-1A-E1 C6 finding 1). Counting per-statement (the pre-C6 behavior) let a single
    ImportFrom node contribute 1 to this count merely because it contained a genuine alias
    SOMEWHERE, even when that same statement also carried a second, conflicting alias
    binding the same local name to a different symbol - `_name_is_shadowed` is what
    actually rejects that second alias now (via the same per-alias marker), but this count
    is made per-alias too for consistency and so "genuine import count" always means what
    it says.
    """
    count = 0
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom) or node.module != expected_module:
            continue
        for alias in node.names:
            if alias.name == expected_original_name and (alias.asname or alias.name) == name:
                count += 1
    return count


def _helper_provenance_is_trustworthy(
    tree: ast.AST, name: str, expected_module: str, expected_original_name: str
) -> bool:
    """True only if `name` resolves, with full confidence, to the single genuine expected
    import: the module contains no star import at all (which could shadow ANY name,
    including one never explicitly written - PF-1A-E1 C5 finding 7.A), the expected
    `ImportFrom` binding appears EXACTLY ONCE, and `name` is not additionally bound
    anywhere else in the module (ordinary rebinding, a different import, or - per the
    `_iter_binding_names` extension above - a pattern-match capture).
    """
    if _module_has_star_import(tree):
        return False
    if _count_expected_import_bindings(tree, name, expected_module, expected_original_name) != 1:
        return False
    if _name_is_shadowed(tree, name, expected_module, expected_original_name):
        return False
    return True


def _find_function_defs_by_name(
    tree: ast.AST, name: str
) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name
    ]


def _unique_target_function(
    tree: ast.AST, name: str, *, expected_async: bool
) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
    """Return the single `FunctionDef`/`AsyncFunctionDef` named `name` in `tree`, or
    `None` if there is not EXACTLY one such definition (a decoy duplicate anywhere in the
    module - same name, either sync/async - makes the target function ambiguous and must
    fail closed, PF-1A-E1 C5 finding 7.D), or if the one definition found does not match
    the real production sync/async-ness (`expected_async`).
    """
    candidates = _find_function_defs_by_name(tree, name)
    if len(candidates) != 1:
        return None
    candidate = candidates[0]
    if isinstance(candidate, ast.AsyncFunctionDef) != expected_async:
        return None
    return candidate


# -----------------------------------------------------------------------------------------
# PF-1A-E1 C6 finding 2: bounded lexical-scope provenance. The C5 occurrence-uniqueness
# check above counted a shape-matching statement as belonging to the unique target function
# whenever `ast.walk(target_function)` reached it - and `ast.walk` descends through EVERY
# nested scope (a nested `def`, `async def`, `lambda`, or `class` body), because those are
# themselves ordinary child nodes in the AST. This let the allowed statement be moved into a
# nested function/lambda under the target function (independently demonstrated for both
# accounts and identity) and still be treated as if it were written directly in the target
# function's own body - and let a lambda PARAMETER named `user`/`response` silently shadow
# the real outer variable of the same name while the base-object NAME check still matched.
#
# `_iter_immediate_scope_nodes` is bounded lexical-scope analysis, not a general
# control-flow or symbolic engine: it answers exactly one question - "is this node written
# directly in THIS function's own body, without crossing into a nested lexical scope" - and
# nothing more. A nested `def`/`async def`/`lambda`/`class` is a new lexical scope in
# Python; this traversal yields the scope-introducing node itself (so its mere presence is
# still visible) but never descends into what it contains, so nothing written inside a
# nested function/lambda/class body is ever treated as belonging to the outer function's own
# immediate scope.
#
# PF-1A-E1 C7 finding: a further independent re-review, run after C6 was re-confirmed sound
# at the runtime level, found that the C6 scope-boundary set above was still incomplete.
# Python 3 comprehensions and generator expressions (`ast.ListComp`, `ast.SetComp`,
# `ast.DictComp`, `ast.GeneratorExp`) each execute their element/key/value expression in
# their own implicit nested scope, exactly like a nested `def` or `lambda` does - but none
# of the four were in `_SCOPE_INTRODUCING_NODE_TYPES`, so the pre-C7 traversal walked
# straight through a comprehension/generator body as if it were still the target function's
# own immediate scope. This was independently demonstrated as a live bypass for both
# allow-shapes: wrapping the real `has_permission(db, user.role_codes, ACCOUNT_TAX_VERIFY)`
# statement (or the real `record_business_event(...)` audit call) in a bare generator
# expression assigned to a local and never consumed - `check = (has_permission(...) for
# item in (1,))` - is especially dangerous at the RUNTIME level (not just this guard):
# the generator object itself is truthy, so `if not check:` is always false and the
# permission call inside it is never even executed, silently turning what looks like an
# enforced check into a no-op. The C7 correction adds all four comprehension/generator node
# types to `_SCOPE_INTRODUCING_NODE_TYPES`, so `_iter_immediate_scope_nodes` yields the
# comprehension/generator node itself (its mere presence stays visible) but never descends
# into its `elt`/`key`/`value`/`generators`, the same treatment already given to a nested
# `def`/`async def`/`lambda`/`class`. This does not change the fail-closed global
# `.role_codes` scan (`_RoleCodesFailClosedVisitor`, which uses plain `ast.NodeVisitor`
# `generic_visit` and therefore already visits every node regardless of lexical scope): a
# `.role_codes` access moved inside a comprehension/generator is still visited and reported,
# it merely no longer counts as belonging to the target function's own immediate-scope
# occurrence set, so it now falls through to being rejected as an offense - the same
# provenance-rejection path already used for a nested `def`/`lambda`. Comprehension/
# generator TARGET names (`for item in ...`) were already enumerated as binding sites by
# `_iter_binding_names` via `ast.comprehension` before this correction and needed no change.
# -----------------------------------------------------------------------------------------

_SCOPE_INTRODUCING_NODE_TYPES = (
    ast.FunctionDef,
    ast.AsyncFunctionDef,
    ast.Lambda,
    ast.ClassDef,
    # PF-1A-E1 C7: comprehensions and generator expressions each introduce their own
    # implicit nested scope in Python 3, exactly like a nested def/lambda/class.
    ast.ListComp,
    ast.SetComp,
    ast.DictComp,
    ast.GeneratorExp,
)


def _iter_immediate_scope_nodes(func_node: ast.FunctionDef | ast.AsyncFunctionDef):
    """Yield every AST node belonging to `func_node`'s OWN immediate lexical scope - its
    signature/decorators/body and every node reachable from them WITHOUT crossing into a
    nested lexical scope (PF-1A-E1 C6 finding 2, extended by PF-1A-E1 C7 to also treat a
    comprehension/generator expression body as a nested scope boundary). `func_node` itself
    is always yielded first. A nested `def`, `async def`, `lambda`, `class`, or
    comprehension/generator expression encountered anywhere inside is itself yielded once
    (so a caller can still notice it exists) but its own children are never expanded, so no
    node written inside a nested function/lambda/class body, or inside a
    comprehension/generator's element/key/value/generators, is ever yielded by this
    traversal - it does not belong to `func_node`'s own immediate scope, regardless of how
    deeply it is nested inside further scopes of its own.
    """
    stack: list[ast.AST] = [func_node]
    while stack:
        node = stack.pop()
        yield node
        for child in ast.iter_child_nodes(node):
            if isinstance(child, _SCOPE_INTRODUCING_NODE_TYPES):
                yield child
                continue
            stack.append(child)


def _function_parameter_names(func_node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    return [arg.arg for arg in list(func_node.args.posonlyargs) + list(func_node.args.args)]


def _is_expected_positional_parameter(
    func_node: ast.FunctionDef | ast.AsyncFunctionDef, name: str, expected_index: int
) -> bool:
    names = _function_parameter_names(func_node)
    if expected_index >= len(names):
        return False
    return names[expected_index] == name


def _name_is_rebound_in_subtree(subtree: ast.AST, name: str, *, skip_node: ast.AST) -> bool:
    """Return True if `name` is bound anywhere within `subtree` other than at the single
    legitimate binding site `skip_node` (e.g. the enclosing function's own parameter list,
    or the one genuine `response = login_user(...)` assignment). Reuses the same bounded
    binding-site enumeration as `_iter_binding_names`/`_name_is_shadowed`, but scoped to a
    subtree and pinned against one specific legitimate binding node rather than against an
    import statement.
    """
    for bound_name, node in _iter_binding_names(subtree):
        if bound_name != name:
            continue
        if node is skip_node:
            continue
        return True
    return False


def _user_provenance_is_trustworthy(func_node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """PF-1A-E1 C5 finding 7.C: `user` must be exactly the real production positional
    parameter of `_assert_tax_verification_permission` (position `db=0, user=1,
    requested_state=2`), and must not be rebound anywhere within the function
    (`user = other`).
    """
    if not _is_expected_positional_parameter(
        func_node, ACCOUNTS_ALLOWED_ROLE_CODES_BASE_NAME, ACCOUNTS_ALLOWED_USER_PARAM_INDEX
    ):
        return False
    return not _name_is_rebound_in_subtree(
        func_node, ACCOUNTS_ALLOWED_ROLE_CODES_BASE_NAME, skip_node=func_node
    )


def _find_legitimate_response_assignment(
    func_node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> ast.Assign | None:
    """Return the single `Assign` node matching the real production binding of
    `response` - `response = login_user(...)`, a bare-name target assigned from a bare
    call to `login_user` - or `None` if no such assignment exists directly in
    `func_node`'s own IMMEDIATE lexical scope (PF-1A-E1 C6 finding 2: this must not
    accept an otherwise-identical assignment moved inside a nested `def`/`async def`/
    `lambda`, which is a different scope with its own local `response`, not `login`'s
    real production binding).
    """
    for node in _iter_immediate_scope_nodes(func_node):
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == IDENTITY_ALLOWED_ROLE_CODES_BASE_NAME
            and isinstance(node.value, ast.Call)
            and isinstance(node.value.func, ast.Name)
            and node.value.func.id == IDENTITY_ALLOWED_RESPONSE_ASSIGNMENT_CALLEE
        ):
            return node
    return None


def _response_provenance_is_trustworthy(func_node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """PF-1A-E1 C5 finding 7.C: `response` must be bound by exactly the one legitimate
    `response = login_user(...)` assignment, and must not be additionally or instead
    bound by anything else (`response = fake_response`).
    """
    legitimate = _find_legitimate_response_assignment(func_node)
    if legitimate is None:
        return False
    return not _name_is_rebound_in_subtree(
        func_node, IDENTITY_ALLOWED_ROLE_CODES_BASE_NAME, skip_node=legitimate
    )


def _accounts_role_codes_shape_matches(node: ast.Attribute, parents: dict[ast.AST, ast.AST]) -> bool:
    """SHAPE ONLY - deliberately no provenance/uniqueness checks, so this predicate can be
    reused both to test one node and to COUNT how many matching statements exist in the
    unique target function (PF-1A-E1 C5 finding 7.D "exactly one" requirement). Matches
    `has_permission(db, X.role_codes, ACCOUNT_TAX_VERIFY)`: a bare-name call to
    `has_permission`, exactly three positional arguments and no keywords, `.role_codes` as
    exactly the second positional argument with base name `user`, first positional argument
    the local `db` parameter, and third positional argument exactly `ACCOUNT_TAX_VERIFY`.
    """
    if not (isinstance(node.value, ast.Name) and node.value.id == ACCOUNTS_ALLOWED_ROLE_CODES_BASE_NAME):
        return False

    parent = parents.get(node)
    if not isinstance(parent, ast.Call):
        return False

    func = parent.func
    if not (isinstance(func, ast.Name) and func.id == ACCOUNTS_ALLOWED_CALL_NAME):
        # Deliberately rejects a qualified call such as `policy.has_permission(...)`:
        # production uses a bare imported name, never an attribute access, so a
        # qualified look-alike is not the real statement this exception describes.
        return False

    if parent.keywords:
        # Production calls positionally only; a keyword-argument variant is not the
        # exact real shape.
        return False

    if len(parent.args) != 3:
        return False

    db_arg, role_codes_arg, permission_arg = parent.args
    if role_codes_arg is not node:
        # `.role_codes` must be exactly the second positional argument.
        return False
    if not (isinstance(db_arg, ast.Name) and db_arg.id == ACCOUNTS_ALLOWED_DB_ARG_NAME):
        return False
    if not (isinstance(permission_arg, ast.Name) and permission_arg.id == ACCOUNTS_ALLOWED_PERMISSION_CONSTANT):
        # A wrong permission constant (e.g. ACCOUNT_READ) is not the exact real
        # statement, even though the surrounding call shape otherwise matches.
        return False

    return True


def _is_allowed_accounts_role_codes_usage(
    node: ast.Attribute, parents: dict[ast.AST, ast.AST], tree: ast.AST
) -> bool:
    """Match ONLY the exact real production statement in
    `accounts/routes.py::_assert_tax_verification_permission`:
    `has_permission(db, user.role_codes, ACCOUNT_TAX_VERIFY)`, proved through the full
    PF-1A-E1 C5/C6 provenance model - shape, unique target function, statement uniqueness
    within that function's own IMMEDIATE lexical scope (PF-1A-E1 C6 finding 2), `user`
    parameter provenance, and genuine unshadowed imports for both `has_permission` and
    `ACCOUNT_TAX_VERIFY`.
    """
    if not _accounts_role_codes_shape_matches(node, parents):
        return False

    target_function = _unique_target_function(
        tree, ACCOUNTS_ALLOWED_ENCLOSING_FUNCTION, expected_async=False
    )
    if target_function is None:
        # PF-1A-E1 C5 finding 7.D: zero, or more than one, `_assert_tax_verification_permission`
        # definition in the module - the target function is not unambiguous.
        return False

    # PF-1A-E1 C6 finding 2: `_iter_immediate_scope_nodes`, not `ast.walk`, so a
    # shape-matching statement moved inside a nested `def`/`async def`/`lambda` under
    # the target function - or written inside a lambda whose OWN parameter is named
    # `user`, shadowing the real outer one - does not count as an occurrence belonging to
    # the target function's own body. `node` (the specific `.role_codes` access currently
    # being checked) is never in this list unless it genuinely lives directly in the
    # target function's immediate scope.
    occurrences = [
        n
        for n in _iter_immediate_scope_nodes(target_function)
        if isinstance(n, ast.Attribute) and n.attr == "role_codes" and _accounts_role_codes_shape_matches(n, parents)
    ]
    if len(occurrences) != 1 or occurrences[0] is not node:
        # Either the shape-matching statement is not unique inside the target function's
        # immediate scope (PF-1A-E1 C5 finding 7.D), or `node` lives in a different
        # function, or a nested scope, entirely (the identical shape used elsewhere, or
        # nested one level deeper, is not the documented exception).
        return False

    if not _user_provenance_is_trustworthy(target_function):
        return False

    # PF-1A-E1 C5 finding 7.A: `has_permission` and `ACCOUNT_TAX_VERIFY` must both still be
    # the single genuine, unshadowed, star-import-free expected import.
    if not _helper_provenance_is_trustworthy(
        tree, ACCOUNTS_ALLOWED_CALL_NAME, ACCOUNTS_EXPECTED_IMPORT_MODULE, ACCOUNTS_EXPECTED_IMPORT_ORIGINAL_NAME
    ):
        return False
    if not _helper_provenance_is_trustworthy(
        tree,
        ACCOUNTS_ALLOWED_PERMISSION_CONSTANT,
        ACCOUNTS_EXPECTED_PERMISSION_IMPORT_MODULE,
        ACCOUNTS_EXPECTED_PERMISSION_IMPORT_ORIGINAL_NAME,
    ):
        return False

    return True


def _identity_role_codes_shape_matches(node: ast.Attribute, parents: dict[ast.AST, ast.AST]) -> bool:
    """SHAPE ONLY - see `_accounts_role_codes_shape_matches` docstring for why shape and
    provenance/uniqueness are deliberately separated. Matches `.role_codes` as the
    `"role_codes"` entry of the `event_payload=` keyword argument passed to a bare-name
    `record_business_event(...)` call that also carries `event_name="UserLoginSucceeded"`,
    with `.role_codes` accessed on exactly `response.user`.
    """
    base = node.value
    if not (
        isinstance(base, ast.Attribute)
        and base.attr == IDENTITY_ALLOWED_ROLE_CODES_BASE_ATTR
        and isinstance(base.value, ast.Name)
        and base.value.id == IDENTITY_ALLOWED_ROLE_CODES_BASE_NAME
    ):
        return False

    dict_node = parents.get(node)
    if not isinstance(dict_node, ast.Dict):
        return False

    matched_key = False
    for key, value in zip(dict_node.keys, dict_node.values):
        if value is node and isinstance(key, ast.Constant) and key.value == IDENTITY_ALLOWED_DICT_KEY:
            matched_key = True
            break
    if not matched_key:
        return False

    keyword_node = parents.get(dict_node)
    if not (isinstance(keyword_node, ast.keyword) and keyword_node.arg == IDENTITY_ALLOWED_KEYWORD_NAME):
        # The dict must itself be exactly the `event_payload=` keyword argument, not a
        # `role_codes` dict assigned to a local variable or passed some other way.
        return False

    call_node = parents.get(keyword_node)
    if not isinstance(call_node, ast.Call):
        return False
    func = call_node.func
    if not (isinstance(func, ast.Name) and func.id == IDENTITY_ALLOWED_CALL_NAME):
        return False

    # The call must genuinely be emitting the login-success event, not a
    # fabricated/other event identity carrying the same payload shape.
    event_name_value = None
    for kw in call_node.keywords:
        if kw.arg == IDENTITY_ALLOWED_EVENT_NAME_KEYWORD:
            event_name_value = kw.value
            break
    if not (
        isinstance(event_name_value, ast.Constant)
        and event_name_value.value == IDENTITY_ALLOWED_EVENT_NAME_VALUE
    ):
        return False

    return True


def _is_allowed_identity_role_codes_usage(
    node: ast.Attribute, parents: dict[ast.AST, ast.AST], tree: ast.AST
) -> bool:
    """Match ONLY the exact real production statement in
    `identity/routes.py::login`: `.role_codes` as the `"role_codes"` entry of the
    `event_payload=` keyword argument passed to the genuine, unshadowed
    `record_business_event(...)` for the real `UserLoginSucceeded` event, proved through
    the full PF-1A-E1 C5/C6 provenance model - shape, unique target function, statement
    uniqueness within that function's own IMMEDIATE lexical scope (PF-1A-E1 C6 finding 2),
    `response` assignment provenance, and a genuine unshadowed import for
    `record_business_event`.
    """
    if not _identity_role_codes_shape_matches(node, parents):
        return False

    target_function = _unique_target_function(tree, IDENTITY_ALLOWED_ENCLOSING_FUNCTION, expected_async=False)
    if target_function is None:
        # PF-1A-E1 C5 finding 7.D: zero, or more than one, `login` definition (of the real
        # production sync type) in the module.
        return False

    # PF-1A-E1 C6 finding 2: `_iter_immediate_scope_nodes`, not `ast.walk`, so the audit
    # call (or a lambda parameter named `response` shadowing the real outer one) moved
    # inside a nested `def`/`async def`/`lambda` under `login` does not count as an
    # occurrence belonging to `login`'s own body.
    occurrences = [
        n
        for n in _iter_immediate_scope_nodes(target_function)
        if isinstance(n, ast.Attribute) and n.attr == "role_codes" and _identity_role_codes_shape_matches(n, parents)
    ]
    if len(occurrences) != 1 or occurrences[0] is not node:
        return False

    if not _response_provenance_is_trustworthy(target_function):
        return False

    # PF-1A-E1 C5 finding 7.A: `record_business_event` must still be the single genuine,
    # unshadowed, star-import-free expected import.
    if not _helper_provenance_is_trustworthy(
        tree, IDENTITY_ALLOWED_CALL_NAME, IDENTITY_EXPECTED_IMPORT_MODULE, IDENTITY_EXPECTED_IMPORT_ORIGINAL_NAME
    ):
        return False

    # PF-1A-E1 C5 finding 7.C, defense in depth: `response`'s provenance check above only
    # proves it is bound by a call spelled `login_user(...)` - it does not by itself prove
    # `login_user` is the genuine imported production login service function rather than a
    # same-named local decoy defined elsewhere in the module. Pin that too, using the same
    # provenance mechanism as every other tracked name.
    if not _helper_provenance_is_trustworthy(
        tree,
        IDENTITY_ALLOWED_RESPONSE_ASSIGNMENT_CALLEE,
        IDENTITY_EXPECTED_LOGIN_USER_IMPORT_MODULE,
        IDENTITY_EXPECTED_LOGIN_USER_IMPORT_ORIGINAL_NAME,
    ):
        return False

    return True


def _is_allowed_role_codes_usage(
    node: ast.Attribute, parents: dict[ast.AST, ast.AST], module_key: str, tree: ast.AST
) -> bool:
    if module_key == "accounts":
        return _is_allowed_accounts_role_codes_usage(node, parents, tree)
    if module_key == "identity":
        return _is_allowed_identity_role_codes_usage(node, parents, tree)
    return False


class _RoleCodesFailClosedVisitor(ast.NodeVisitor):
    """Walks a route module's AST looking for direct application-role authorization
    logic: any `.role_codes` usage outside the two exact whitelisted shapes, and any
    reintroduced route-local `*_ROLES` tuple constant.
    """

    def __init__(self, module_key: str) -> None:
        self.module_key = module_key
        self.offenses: list[str] = []
        self._parents: dict[ast.AST, ast.AST] = {}
        self._tree: ast.AST | None = None

    def visit_and_collect(self, tree: ast.AST) -> None:
        self._tree = tree
        self._parents = _build_parent_map(tree)
        self.visit(tree)
        # PF-1A-E1 C4 finding 2: a dynamic `getattr(user, "role_codes")` (or
        # `vars(...)["role_codes"]` / `x.__dict__["role_codes"]`) equivalent never
        # produces an `ast.Attribute` node with `.attr == "role_codes"` at all, so the
        # visitor above cannot see it. Real production code never accesses `role_codes`
        # dynamically, so any such access is an unconditional offense - there is no
        # allow-shape for it, in any module.
        self.offenses.extend(_find_dynamic_literal_attribute_accesses(tree, "role_codes"))

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if node.attr == "role_codes":
            assert self._tree is not None
            if not _is_allowed_role_codes_usage(node, self._parents, self.module_key, self._tree):
                self.offenses.append(
                    f"line {node.lineno}: `.role_codes` used outside the exact documented "
                    "allowed shape for this module"
                )
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        for target in node.targets:
            if isinstance(target, ast.Name) and ROLE_TUPLE_CONSTANT_NAME_PATTERN.match(target.id):
                self.offenses.append(f"line {node.lineno}: route-local role-tuple constant {target.id!r} reintroduced")
        self.generic_visit(node)


def test_no_route_module_contains_direct_role_authorization_logic() -> None:
    offenders: list[str] = []
    for path in sorted(ROUTE_MODULES_DIR.glob("*/routes.py")):
        # utf-8-sig transparently strips a leading UTF-8 BOM if present (several existing
        # route modules carry one) and is otherwise identical to utf-8 decoding; ast.parse
        # rejects a literal U+FEFF at the start of source, so a plain "utf-8" read would
        # raise SyntaxError on those files before this guard ever runs.
        source = path.read_text(encoding="utf-8-sig")
        tree = ast.parse(source, filename=str(path))
        visitor = _RoleCodesFailClosedVisitor(module_key=path.parent.name)
        visitor.visit_and_collect(tree)
        if visitor.offenses:
            relative = str(path.relative_to(BACKEND_ROOT))
            offenders.extend(f"{relative}: {offense}" for offense in visitor.offenses)

    assert offenders == [], "direct role-authorization logic found in route module(s): " + "; ".join(offenders)


def test_role_codes_fail_closed_guard_detects_a_reintroduced_membership_test() -> None:
    """Prove the guard itself is not a no-op: a synthetic snippet reintroducing a direct
    membership test against `.role_codes` must be rejected.
    """
    snippet = (
        "def endpoint(current_user):\n"
        "    if 'ADMIN' in current_user.role_codes:\n"
        "        return True\n"
        "    return False\n"
    )
    tree = ast.parse(snippet)
    visitor = _RoleCodesFailClosedVisitor(module_key="leads")
    visitor.visit_and_collect(tree)
    assert visitor.offenses, "guard failed to detect a direct .role_codes membership test"


def test_role_codes_fail_closed_guard_detects_local_alias_then_membership_test() -> None:
    """PF-1A-E1 C2 finding 1.D: the exact evasion the pre-correction guard missed -
    extracting `.role_codes` into a local variable before testing it.
    """
    snippet = (
        "def endpoint(current_user):\n"
        "    codes = current_user.role_codes\n"
        "    if 'ADMIN' in codes:\n"
        "        return True\n"
        "    return False\n"
    )
    tree = ast.parse(snippet)
    visitor = _RoleCodesFailClosedVisitor(module_key="leads")
    visitor.visit_and_collect(tree)
    assert visitor.offenses, "guard failed to detect a local role_codes alias assignment"


def test_role_codes_fail_closed_guard_detects_role_codes_passed_to_a_helper_function() -> None:
    """PF-1A-E1 C2 finding 1.D: passing `.role_codes` to an arbitrary helper function
    (anything other than the one documented `has_permission(...)` exception) must be
    rejected.
    """
    snippet = (
        "def endpoint(current_user):\n"
        "    return only_admin(current_user.role_codes)\n"
    )
    tree = ast.parse(snippet)
    visitor = _RoleCodesFailClosedVisitor(module_key="leads")
    visitor.visit_and_collect(tree)
    assert visitor.offenses, "guard failed to detect role_codes passed to an arbitrary helper function"


def test_role_codes_fail_closed_guard_detects_role_codes_in_a_comprehension() -> None:
    """PF-1A-E1 C2 finding 1.D: `.role_codes` used as a comprehension/generator iterable
    must be rejected.
    """
    snippet = (
        "def endpoint(current_user):\n"
        "    return any(code == 'ADMIN' for code in current_user.role_codes)\n"
    )
    tree = ast.parse(snippet)
    visitor = _RoleCodesFailClosedVisitor(module_key="leads")
    visitor.visit_and_collect(tree)
    assert visitor.offenses, "guard failed to detect role_codes used inside a comprehension"


def test_role_codes_fail_closed_guard_detects_a_reintroduced_set_intersection() -> None:
    snippet = (
        "def endpoint(current_user):\n"
        "    return bool(set(SOME_ROLES) & set(current_user.role_codes))\n"
    )
    tree = ast.parse(snippet)
    visitor = _RoleCodesFailClosedVisitor(module_key="leads")
    visitor.visit_and_collect(tree)
    assert visitor.offenses, "guard failed to detect a direct .role_codes set-intersection"


def test_role_codes_fail_closed_guard_detects_a_reintroduced_role_tuple_constant() -> None:
    snippet = "SOME_ACTION_ROLES = ('ADMIN', 'SALES_USER')\n"
    tree = ast.parse(snippet)
    visitor = _RoleCodesFailClosedVisitor(module_key="leads")
    visitor.visit_and_collect(tree)
    assert visitor.offenses, "guard failed to detect a reintroduced route-local *_ROLES constant"


ACCOUNTS_REAL_SHAPE_SNIPPET = (
    "from app.modules.authorization.contract import ACCOUNT_TAX_VERIFY\n"
    "from app.modules.authorization.service import has_permission\n"
    "\n"
    "def _assert_tax_verification_permission(db, user, requested_state):\n"
    "    state = (requested_state or '').upper()\n"
    "    if state in ACCOUNT_VERIFIED_TAX_STATES and not has_permission(\n"
    "        db, user.role_codes, ACCOUNT_TAX_VERIFY\n"
    "    ):\n"
    "        raise ValueError('nope')\n"
)

IDENTITY_REAL_SHAPE_SNIPPET = (
    "from app.modules.events.service import record_business_event\n"
    "from app.modules.identity.service import login_user\n"
    "\n"
    "def login(payload, db):\n"
    "    response = login_user(db, payload.username, payload.password)\n"
    "    record_business_event(\n"
    "        db,\n"
    "        event_name='UserLoginSucceeded',\n"
    "        event_payload={\n"
    "            'username': response.user.username,\n"
    "            'role_codes': response.user.role_codes,\n"
    "        },\n"
    "    )\n"
)


def test_role_codes_fail_closed_guard_permits_the_documented_has_permission_pattern_in_accounts() -> None:
    """The one real, narrow, documented exception (accounts/routes.py) must remain
    permitted: this is the LITERAL real production statement from
    `_assert_tax_verification_permission`, not merely a similarly-shaped one.

    PF-1A-E1 C5: this snippet now includes the two genuine production imports
    (`has_permission`, `ACCOUNT_TAX_VERIFY`) that the pre-C5 version of this test omitted.
    Under the C5 provenance model (finding 7.A) an allow-shape is rejected unless its
    helper/constant names resolve to exactly one genuine expected import, so a snippet
    that never imports them at all no longer represents "the real accepted shape" - the
    real production file always does. See
    `test_role_codes_fail_closed_guard_rejects_accounts_shape_when_the_has_permission_import_is_missing`
    for the negative counterpart proving the import really is now required.
    """
    tree = ast.parse(ACCOUNTS_REAL_SHAPE_SNIPPET)
    visitor = _RoleCodesFailClosedVisitor(module_key="accounts")
    visitor.visit_and_collect(tree)
    assert visitor.offenses == [], (
        f"guard incorrectly rejected the real accounts has_permission(...) statement: {visitor.offenses}"
    )


def test_role_codes_fail_closed_guard_rejects_accounts_has_permission_with_wrong_permission_code() -> None:
    """PF-1A-E1 C3 finding 1.B: the same call shape requesting a DIFFERENT permission
    constant (e.g. ACCOUNT_READ instead of ACCOUNT_TAX_VERIFY) is not the real
    production statement and must be rejected, even inside the exact real function.
    """
    snippet = (
        "def _assert_tax_verification_permission(db, user, requested_state):\n"
        "    if not has_permission(db, user.role_codes, ACCOUNT_READ):\n"
        "        raise ValueError('nope')\n"
    )
    tree = ast.parse(snippet)
    visitor = _RoleCodesFailClosedVisitor(module_key="accounts")
    visitor.visit_and_collect(tree)
    assert visitor.offenses, "guard incorrectly permitted has_permission(...) requesting the wrong permission code"


def test_role_codes_fail_closed_guard_rejects_a_qualified_has_permission_call_in_accounts() -> None:
    """PF-1A-E1 C3 finding 1.B: a qualified `policy.has_permission(...)` call is not the
    real production shape (which is a bare imported name) and must be rejected.
    """
    snippet = (
        "def _assert_tax_verification_permission(db, user, requested_state):\n"
        "    if not policy.has_permission(db, user.role_codes, ACCOUNT_TAX_VERIFY):\n"
        "        raise ValueError('nope')\n"
    )
    tree = ast.parse(snippet)
    visitor = _RoleCodesFailClosedVisitor(module_key="accounts")
    visitor.visit_and_collect(tree)
    assert visitor.offenses, "guard incorrectly permitted a qualified policy.has_permission(...) call"


def test_role_codes_fail_closed_guard_rejects_the_accounts_shape_in_the_wrong_function() -> None:
    """PF-1A-E1 C3 finding 1.B: the exact real call shape, verbatim, but written inside a
    DIFFERENT function than `_assert_tax_verification_permission`, is not the documented
    exception and must be rejected.
    """
    snippet = (
        "def some_other_helper(db, user, requested_state):\n"
        "    if not has_permission(db, user.role_codes, ACCOUNT_TAX_VERIFY):\n"
        "        raise ValueError('nope')\n"
    )
    tree = ast.parse(snippet)
    visitor = _RoleCodesFailClosedVisitor(module_key="accounts")
    visitor.visit_and_collect(tree)
    assert visitor.offenses, "guard incorrectly permitted the exact call shape inside the wrong enclosing function"


def test_role_codes_fail_closed_guard_permits_role_codes_as_plain_audit_event_data_in_identity() -> None:
    """The second real usage in this codebase (identity/routes.py's login-success
    `record_business_event(...)` payload) must remain permitted: this is the literal
    real production shape, not merely a similarly-shaped one.

    PF-1A-E1 C5: this snippet now includes the genuine production import
    (`record_business_event`) that the pre-C5 version of this test omitted. Under the C5
    provenance model (finding 7.A) the helper name must resolve to exactly one genuine
    expected import, so a snippet that never imports it no longer represents "the real
    accepted shape" - the real production file always does.
    """
    tree = ast.parse(IDENTITY_REAL_SHAPE_SNIPPET)
    visitor = _RoleCodesFailClosedVisitor(module_key="identity")
    visitor.visit_and_collect(tree)
    assert visitor.offenses == [], (
        f"guard incorrectly rejected the real identity audit-event statement: {visitor.offenses}"
    )


def test_role_codes_fail_closed_guard_rejects_identity_role_codes_dict_not_used_as_event_payload() -> None:
    """PF-1A-E1 C3 finding 1.B: a `{"role_codes": user.role_codes}` dict that is built
    but then used for something other than being the `event_payload=` argument of
    `record_business_event(...)` - e.g. assigned to a local and handed to an
    authorization helper - is not the documented login-audit-event exception and must be
    rejected.
    """
    snippet = (
        "def login(payload, db):\n"
        "    context = {'role_codes': response.user.role_codes}\n"
        "    authorize(context)\n"
    )
    tree = ast.parse(snippet)
    visitor = _RoleCodesFailClosedVisitor(module_key="identity")
    visitor.visit_and_collect(tree)
    assert visitor.offenses, (
        "guard incorrectly permitted a role_codes dict that is not the event_payload= "
        "argument of record_business_event(...)"
    )


def test_role_codes_fail_closed_guard_rejects_the_identity_shape_in_the_wrong_function() -> None:
    """PF-1A-E1 C3 finding 1.B: the exact real dict/call shape, verbatim, but written
    inside a DIFFERENT function than `login`, is not the documented login-success
    audit-event emission and must be rejected.
    """
    snippet = (
        "def some_other_function(payload, db):\n"
        "    record_business_event(\n"
        "        db,\n"
        "        event_payload={'role_codes': response.user.role_codes},\n"
        "    )\n"
    )
    tree = ast.parse(snippet)
    visitor = _RoleCodesFailClosedVisitor(module_key="identity")
    visitor.visit_and_collect(tree)
    assert visitor.offenses, "guard incorrectly permitted the exact dict/call shape inside the wrong enclosing function"


def test_role_codes_fail_closed_guard_rejects_the_documented_patterns_outside_their_own_module() -> None:
    """PF-1A-E1 C2 finding 1.B: the two whitelisted shapes are file-scoped, not
    pattern-scoped. The identical source shape used in any OTHER route module must still
    be rejected - otherwise the "exception" would really be a global pattern allowlist,
    which is exactly the kind of broad exception the reviewer asked to avoid.
    """
    has_permission_snippet = (
        "def _assert_tax_verification_permission(db, user, requested_state):\n"
        "    if not has_permission(db, user.role_codes, ACCOUNT_TAX_VERIFY):\n"
        "        raise ValueError('nope')\n"
    )
    tree = ast.parse(has_permission_snippet)
    visitor = _RoleCodesFailClosedVisitor(module_key="leads")
    visitor.visit_and_collect(tree)
    assert visitor.offenses, "guard incorrectly permitted the has_permission(...) pattern outside accounts/routes.py"

    audit_event_snippet = (
        "def login(payload, db):\n"
        "    record_business_event(\n"
        "        db,\n"
        "        event_payload={'role_codes': response.user.role_codes},\n"
        "    )\n"
    )
    tree2 = ast.parse(audit_event_snippet)
    visitor2 = _RoleCodesFailClosedVisitor(module_key="opportunities")
    visitor2.visit_and_collect(tree2)
    assert visitor2.offenses, "guard incorrectly permitted the audit-event pattern outside identity/routes.py"


# =========================================================================================
# PF-1A-E1 C4 finding 2: locally rebound/shadowed helper names, wrong `.role_codes` base
# objects, a fabricated event identity, and dynamic getattr(...) equivalents must all still
# be rejected even though they preserve the superficial allow-shape.
# =========================================================================================


def test_role_codes_fail_closed_guard_rejects_a_rebound_has_permission_helper_in_accounts() -> None:
    """PF-1A-E1 C4 finding 2: rebinding `has_permission` to an arbitrary callable before
    the otherwise-exact call shape must not satisfy the accounts allow-shape - the shape
    match alone (callee spelled `has_permission`) is not enough; it must still be the
    genuine, unshadowed import.
    """
    snippet = (
        "def _assert_tax_verification_permission(db, user, requested_state):\n"
        "    has_permission = policy.has_permission\n"
        "    if not has_permission(db, user.role_codes, ACCOUNT_TAX_VERIFY):\n"
        "        raise ValueError('nope')\n"
    )
    tree = ast.parse(snippet)
    visitor = _RoleCodesFailClosedVisitor(module_key="accounts")
    visitor.visit_and_collect(tree)
    assert visitor.offenses, "guard incorrectly permitted a locally rebound has_permission helper"


def test_role_codes_fail_closed_guard_rejects_a_wrong_role_codes_base_object_in_accounts() -> None:
    """PF-1A-E1 C4 finding 2: `.role_codes` on a base object other than the real
    production `user` variable (e.g. `other.role_codes`) is not the real statement, even
    though the rest of the call shape matches exactly.
    """
    snippet = (
        "def _assert_tax_verification_permission(db, user, requested_state):\n"
        "    if not has_permission(db, other.role_codes, ACCOUNT_TAX_VERIFY):\n"
        "        raise ValueError('nope')\n"
    )
    tree = ast.parse(snippet)
    visitor = _RoleCodesFailClosedVisitor(module_key="accounts")
    visitor.visit_and_collect(tree)
    assert visitor.offenses, "guard incorrectly permitted has_permission(...) with a non-'user' role_codes base"


def test_role_codes_fail_closed_guard_permits_the_real_accounts_import_and_statement_together() -> None:
    """PF-1A-E1 C4 finding 2 regression guard: the real, expected, unaliased
    `from app.modules.authorization.service import has_permission` import must NOT itself
    be treated as shadowing - only a genuine rebinding may reject the shape.

    PF-1A-E1 C5 test 13 (exact real production provenance still accepted): also includes
    the genuine `ACCOUNT_TAX_VERIFY` import, now independently required by the C5
    provenance model (finding 7.A).
    """
    snippet = (
        "from app.modules.authorization.contract import ACCOUNT_TAX_VERIFY\n"
        "from app.modules.authorization.service import has_permission\n"
        "\n"
        "def _assert_tax_verification_permission(db, user, requested_state):\n"
        "    if not has_permission(db, user.role_codes, ACCOUNT_TAX_VERIFY):\n"
        "        raise ValueError('nope')\n"
    )
    tree = ast.parse(snippet)
    visitor = _RoleCodesFailClosedVisitor(module_key="accounts")
    visitor.visit_and_collect(tree)
    assert visitor.offenses == [], (
        f"guard incorrectly rejected the real production import plus statement: {visitor.offenses}"
    )


def test_role_codes_fail_closed_guard_rejects_a_dynamic_getattr_role_codes_equivalent_in_accounts() -> None:
    """PF-1A-E1 C4 finding 2: `getattr(user, "role_codes")` never produces an
    `ast.Attribute` node with `.attr == "role_codes"`, so it would otherwise be completely
    invisible to the `.role_codes` fail-closed visitor while still extracting the same
    value passed on to `has_permission(...)`.
    """
    snippet = (
        "def _assert_tax_verification_permission(db, user, requested_state):\n"
        "    if not has_permission(db, getattr(user, 'role_codes'), ACCOUNT_TAX_VERIFY):\n"
        "        raise ValueError('nope')\n"
    )
    tree = ast.parse(snippet)
    visitor = _RoleCodesFailClosedVisitor(module_key="accounts")
    visitor.visit_and_collect(tree)
    assert visitor.offenses, "guard incorrectly permitted a dynamic getattr(user, 'role_codes') equivalent"


def test_role_codes_fail_closed_guard_rejects_a_rebound_record_business_event_helper_in_identity() -> None:
    """PF-1A-E1 C4 finding 2: rebinding `record_business_event` to an arbitrary callable
    before the otherwise-exact call/dict shape must not satisfy the identity allow-shape.
    """
    snippet = (
        "def login(payload, db):\n"
        "    record_business_event = authorize\n"
        "    record_business_event(\n"
        "        db,\n"
        "        event_name='UserLoginSucceeded',\n"
        "        event_payload={'role_codes': response.user.role_codes},\n"
        "    )\n"
    )
    tree = ast.parse(snippet)
    visitor = _RoleCodesFailClosedVisitor(module_key="identity")
    visitor.visit_and_collect(tree)
    assert visitor.offenses, "guard incorrectly permitted a locally rebound record_business_event helper"


def test_role_codes_fail_closed_guard_rejects_a_fabricated_event_identity_in_identity() -> None:
    """PF-1A-E1 C4 finding 2: the exact call/dict shape, but carrying a different (or
    missing) `event_name=`, is not the real login-success audit event and must be
    rejected even though the payload looks identical.
    """
    snippet = (
        "def login(payload, db):\n"
        "    record_business_event(\n"
        "        db,\n"
        "        event_name='SomeFabricatedAuthorizationDecision',\n"
        "        event_payload={'role_codes': response.user.role_codes},\n"
        "    )\n"
    )
    tree = ast.parse(snippet)
    visitor = _RoleCodesFailClosedVisitor(module_key="identity")
    visitor.visit_and_collect(tree)
    assert visitor.offenses, "guard incorrectly permitted a fabricated event identity carrying the same payload shape"

    missing_event_name_snippet = (
        "def login(payload, db):\n"
        "    record_business_event(\n"
        "        db,\n"
        "        event_payload={'role_codes': response.user.role_codes},\n"
        "    )\n"
    )
    tree2 = ast.parse(missing_event_name_snippet)
    visitor2 = _RoleCodesFailClosedVisitor(module_key="identity")
    visitor2.visit_and_collect(tree2)
    assert visitor2.offenses, "guard incorrectly permitted the shape with no event_name= at all"


def test_role_codes_fail_closed_guard_permits_the_real_identity_import_and_statement_together() -> None:
    """PF-1A-E1 C4 finding 2 regression guard: the real, expected, unaliased
    `from app.modules.events.service import record_business_event` import must NOT itself
    be treated as shadowing - only a genuine rebinding may reject the shape.

    PF-1A-E1 C5 test 22 (exact real production provenance still accepted): also includes
    the genuine `response = login_user(...)` assignment, now independently required by the
    C5 provenance model (finding 7.C) - the pre-C5 version of this snippet referenced
    `response` without ever binding it at all.
    """
    tree = ast.parse(IDENTITY_REAL_SHAPE_SNIPPET)
    visitor = _RoleCodesFailClosedVisitor(module_key="identity")
    visitor.visit_and_collect(tree)
    assert visitor.offenses == [], (
        f"guard incorrectly rejected the real production import plus statement: {visitor.offenses}"
    )


def test_role_codes_fail_closed_guard_rejects_a_dynamic_getattr_role_codes_equivalent_in_identity() -> None:
    """PF-1A-E1 C4 finding 2: `getattr(response.user, "role_codes")` never produces an
    `ast.Attribute` node with `.attr == "role_codes"`, so it would otherwise be completely
    invisible to the `.role_codes` fail-closed visitor while still extracting the same
    value placed into the event payload.
    """
    snippet = (
        "def login(payload, db):\n"
        "    record_business_event(\n"
        "        db,\n"
        "        event_name='UserLoginSucceeded',\n"
        "        event_payload={'role_codes': getattr(response.user, 'role_codes')},\n"
        "    )\n"
    )
    tree = ast.parse(snippet)
    visitor = _RoleCodesFailClosedVisitor(module_key="identity")
    visitor.visit_and_collect(tree)
    assert visitor.offenses, "guard incorrectly permitted a dynamic getattr(response.user, 'role_codes') equivalent"


# =========================================================================================
# PF-1A-E1 C5 finding 7: the provenance model above must reject every independently
# demonstrated bypass class (A-G in the correction brief) while still accepting the exact
# real production statement (tests 13 and 22 above, via the updated "permits" tests).
# =========================================================================================


def test_role_codes_fail_closed_guard_rejects_accounts_shape_when_the_has_permission_import_is_missing() -> None:
    """PF-1A-E1 C5 test 7: the real `ACCOUNT_TAX_VERIFY` import is present but
    `has_permission` is never imported at all - relying on it being a builtin or supplied
    some other way. Finding 7.A requires EXACTLY ONE genuine expected import to exist, not
    merely "no conflicting binding"; zero genuine imports must fail closed.
    """
    snippet = (
        "from app.modules.authorization.contract import ACCOUNT_TAX_VERIFY\n"
        "\n"
        "def _assert_tax_verification_permission(db, user, requested_state):\n"
        "    if not has_permission(db, user.role_codes, ACCOUNT_TAX_VERIFY):\n"
        "        raise ValueError('nope')\n"
    )
    tree = ast.parse(snippet)
    visitor = _RoleCodesFailClosedVisitor(module_key="accounts")
    visitor.visit_and_collect(tree)
    assert visitor.offenses, "guard incorrectly permitted the accounts shape with no has_permission import at all"


def test_role_codes_fail_closed_guard_rejects_accounts_shape_when_the_module_has_a_star_import() -> None:
    """PF-1A-E1 C5 test 8 / independently demonstrated bypass A: `from fake_policy import
    *` could silently supply `has_permission` (or `ACCOUNT_TAX_VERIFY`) from an untrusted
    module while every other check still matches the genuine real statement verbatim.
    Finding 7.A requires the whole module to be free of ANY star import.
    """
    snippet = "from fake_policy import *\n\n" + ACCOUNTS_REAL_SHAPE_SNIPPET
    tree = ast.parse(snippet)
    visitor = _RoleCodesFailClosedVisitor(module_key="accounts")
    visitor.visit_and_collect(tree)
    assert visitor.offenses, "guard incorrectly permitted the accounts shape in a module with a star import"


def test_role_codes_fail_closed_guard_rejects_accounts_shape_when_has_permission_is_captured_by_a_match_pattern() -> None:
    """PF-1A-E1 C5 test 9 / independently demonstrated bypass C: `case has_permission:`
    rebinds the local name `has_permission` via pattern-match capture, a binding site the
    pre-C5 `_iter_binding_names` did not enumerate at all. It must be treated as shadowing
    the same as an ordinary assignment, even in a completely unrelated function.
    """
    snippet = (
        ACCOUNTS_REAL_SHAPE_SNIPPET
        + "\n"
        + "def other(value):\n"
        "    match value:\n"
        "        case has_permission:\n"
        "            return has_permission\n"
        "        case _:\n"
        "            return None\n"
    )
    tree = ast.parse(snippet)
    visitor = _RoleCodesFailClosedVisitor(module_key="accounts")
    visitor.visit_and_collect(tree)
    assert visitor.offenses, "guard incorrectly permitted has_permission captured by an unrelated match pattern"


def test_role_codes_fail_closed_guard_rejects_accounts_shape_when_user_is_rebound() -> None:
    """PF-1A-E1 C5 test 10 / independently demonstrated bypass D: `user = other` inside
    the target function replaces the real parameter before the otherwise-exact call
    shape - the base-object NAME still spells `user`, but it no longer has the real
    production parameter provenance.
    """
    snippet = (
        "from app.modules.authorization.contract import ACCOUNT_TAX_VERIFY\n"
        "from app.modules.authorization.service import has_permission\n"
        "\n"
        "def _assert_tax_verification_permission(db, user, requested_state):\n"
        "    user = other\n"
        "    if not has_permission(db, user.role_codes, ACCOUNT_TAX_VERIFY):\n"
        "        raise ValueError('nope')\n"
    )
    tree = ast.parse(snippet)
    visitor = _RoleCodesFailClosedVisitor(module_key="accounts")
    visitor.visit_and_collect(tree)
    assert visitor.offenses, "guard incorrectly permitted the accounts shape after `user = other` rebinding"


def test_role_codes_fail_closed_guard_rejects_accounts_shape_when_the_permission_constant_is_rebound() -> None:
    """PF-1A-E1 C5 test 11 / independently demonstrated bypass E: `ACCOUNT_TAX_VERIFY =
    ACCOUNT_READ` inside the target function replaces the real imported permission
    constant before the otherwise-exact call shape - the argument NAME still spells
    `ACCOUNT_TAX_VERIFY`, but it no longer resolves to the genuine imported constant.
    """
    snippet = (
        "from app.modules.authorization.contract import ACCOUNT_TAX_VERIFY\n"
        "from app.modules.authorization.service import has_permission\n"
        "\n"
        "def _assert_tax_verification_permission(db, user, requested_state):\n"
        "    ACCOUNT_TAX_VERIFY = ACCOUNT_READ\n"
        "    if not has_permission(db, user.role_codes, ACCOUNT_TAX_VERIFY):\n"
        "        raise ValueError('nope')\n"
    )
    tree = ast.parse(snippet)
    visitor = _RoleCodesFailClosedVisitor(module_key="accounts")
    visitor.visit_and_collect(tree)
    assert visitor.offenses, (
        "guard incorrectly permitted the accounts shape after `ACCOUNT_TAX_VERIFY = ACCOUNT_READ` rebinding"
    )


def test_role_codes_fail_closed_guard_rejects_accounts_shape_when_the_target_function_is_duplicated() -> None:
    """PF-1A-E1 C5 test 12 / independently demonstrated bypass G: a second, decoy
    `def _assert_tax_verification_permission(...)` anywhere in the module makes the
    target function ambiguous, even though the genuine statement (in the first
    definition) is otherwise verbatim-correct.
    """
    snippet = (
        ACCOUNTS_REAL_SHAPE_SNIPPET
        + "\n"
        + "def _assert_tax_verification_permission(db, user, requested_state):\n"
        "    return None\n"
    )
    tree = ast.parse(snippet)
    visitor = _RoleCodesFailClosedVisitor(module_key="accounts")
    visitor.visit_and_collect(tree)
    assert visitor.offenses, "guard incorrectly permitted the accounts shape with a duplicate target function"


def test_role_codes_fail_closed_guard_rejects_accounts_shape_with_a_duplicate_statement_in_the_same_function() -> None:
    """PF-1A-E1 C5 design principle: the allowed statement must occur EXACTLY ONCE inside
    the unique target function. Two genuinely identical, individually-verbatim-correct
    call statements in the same function are still rejected, because the exception
    describes one specific real statement, not "this shape, any number of times".
    """
    snippet = (
        "from app.modules.authorization.contract import ACCOUNT_TAX_VERIFY\n"
        "from app.modules.authorization.service import has_permission\n"
        "\n"
        "def _assert_tax_verification_permission(db, user, requested_state):\n"
        "    if not has_permission(db, user.role_codes, ACCOUNT_TAX_VERIFY):\n"
        "        raise ValueError('nope')\n"
        "    if not has_permission(db, user.role_codes, ACCOUNT_TAX_VERIFY):\n"
        "        raise ValueError('nope again')\n"
    )
    tree = ast.parse(snippet)
    visitor = _RoleCodesFailClosedVisitor(module_key="accounts")
    visitor.visit_and_collect(tree)
    assert visitor.offenses, "guard incorrectly permitted a duplicated statement inside the same target function"


def test_role_codes_fail_closed_guard_rejects_accounts_dynamic_role_codes_with_compile_time_string_concatenation() -> None:
    """PF-1A-E1 C5 test 14: `getattr(user, "role_" + "codes")` composes the banned
    literal attribute name through ordinary string concatenation, which only the bounded
    compile-time string evaluator added in this correction resolves.
    """
    snippet = (
        "def _assert_tax_verification_permission(db, user, requested_state):\n"
        "    if not has_permission(db, getattr(user, 'role_' + 'codes'), ACCOUNT_TAX_VERIFY):\n"
        "        raise ValueError('nope')\n"
    )
    tree = ast.parse(snippet)
    visitor = _RoleCodesFailClosedVisitor(module_key="accounts")
    visitor.visit_and_collect(tree)
    assert visitor.offenses, "guard incorrectly permitted getattr(user, 'role_' + 'codes')"


def test_role_codes_fail_closed_guard_rejects_accounts_dynamic_role_codes_via_vars_get() -> None:
    """PF-1A-E1 C5 test 15: `vars(user).get("role_codes")` is the `.get(...)` method-call
    form of the dynamic-access idiom, only recognized after this correction.
    """
    snippet = (
        "def _assert_tax_verification_permission(db, user, requested_state):\n"
        "    if not has_permission(db, vars(user).get('role_codes'), ACCOUNT_TAX_VERIFY):\n"
        "        raise ValueError('nope')\n"
    )
    tree = ast.parse(snippet)
    visitor = _RoleCodesFailClosedVisitor(module_key="accounts")
    visitor.visit_and_collect(tree)
    assert visitor.offenses, "guard incorrectly permitted vars(user).get('role_codes')"


def test_role_codes_fail_closed_guard_rejects_identity_shape_when_the_record_business_event_import_is_missing() -> None:
    """PF-1A-E1 C5 test 16: `response = login_user(...)` is genuinely bound, but
    `record_business_event` is never imported at all. Finding 7.A requires EXACTLY ONE
    genuine expected import to exist, not merely "no conflicting binding".
    """
    snippet = (
        "def login(payload, db):\n"
        "    response = login_user(db, payload.username, payload.password)\n"
        "    record_business_event(\n"
        "        db,\n"
        "        event_name='UserLoginSucceeded',\n"
        "        event_payload={'role_codes': response.user.role_codes},\n"
        "    )\n"
    )
    tree = ast.parse(snippet)
    visitor = _RoleCodesFailClosedVisitor(module_key="identity")
    visitor.visit_and_collect(tree)
    assert visitor.offenses, "guard incorrectly permitted the identity shape with no record_business_event import"


def test_role_codes_fail_closed_guard_rejects_identity_shape_when_the_module_has_a_star_import() -> None:
    """PF-1A-E1 C5 test 17 / independently demonstrated bypass B: `from fake_events
    import *` could silently supply `record_business_event` from an untrusted module
    while every other check still matches the genuine real statement verbatim.
    """
    snippet = "from fake_events import *\n\n" + IDENTITY_REAL_SHAPE_SNIPPET
    tree = ast.parse(snippet)
    visitor = _RoleCodesFailClosedVisitor(module_key="identity")
    visitor.visit_and_collect(tree)
    assert visitor.offenses, "guard incorrectly permitted the identity shape in a module with a star import"


def test_role_codes_fail_closed_guard_rejects_identity_shape_when_record_business_event_is_captured_by_a_match_pattern() -> None:
    """PF-1A-E1 C5 test 18 / independently demonstrated bypass C: `case
    record_business_event:` rebinds the local name via pattern-match capture, in a
    completely unrelated function.
    """
    snippet = (
        IDENTITY_REAL_SHAPE_SNIPPET
        + "\n"
        + "def other(value):\n"
        "    match value:\n"
        "        case record_business_event:\n"
        "            return record_business_event\n"
        "        case _:\n"
        "            return None\n"
    )
    tree = ast.parse(snippet)
    visitor = _RoleCodesFailClosedVisitor(module_key="identity")
    visitor.visit_and_collect(tree)
    assert visitor.offenses, (
        "guard incorrectly permitted record_business_event captured by an unrelated match pattern"
    )


def test_role_codes_fail_closed_guard_rejects_identity_shape_when_response_is_a_fake_rebinding() -> None:
    """PF-1A-E1 C5 test 19 / independently demonstrated bypass F: `response =
    fake_response` replaces the real `response = login_user(...)` assignment - the
    `.role_codes` base object still spells `response.user`, but `response` no longer has
    the real production binding provenance.
    """
    snippet = (
        "from app.modules.events.service import record_business_event\n"
        "\n"
        "def login(payload, db):\n"
        "    response = fake_response\n"
        "    record_business_event(\n"
        "        db,\n"
        "        event_name='UserLoginSucceeded',\n"
        "        event_payload={'role_codes': response.user.role_codes},\n"
        "    )\n"
    )
    tree = ast.parse(snippet)
    visitor = _RoleCodesFailClosedVisitor(module_key="identity")
    visitor.visit_and_collect(tree)
    assert visitor.offenses, "guard incorrectly permitted the identity shape after `response = fake_response`"


def test_role_codes_fail_closed_guard_rejects_identity_shape_when_the_login_function_is_duplicated() -> None:
    """PF-1A-E1 C5 test 20 / independently demonstrated bypass G: a second, decoy
    `def login(...)` anywhere in the module makes the target function ambiguous, even
    though the genuine statement (in the first definition) is otherwise verbatim-correct.
    """
    snippet = (
        IDENTITY_REAL_SHAPE_SNIPPET
        + "\n"
        + "def login(payload, db):\n"
        "    return None\n"
    )
    tree = ast.parse(snippet)
    visitor = _RoleCodesFailClosedVisitor(module_key="identity")
    visitor.visit_and_collect(tree)
    assert visitor.offenses, "guard incorrectly permitted the identity shape with a duplicate login function"


def test_role_codes_fail_closed_guard_rejects_identity_shape_when_login_user_is_a_local_decoy() -> None:
    """PF-1A-E1 C5 finding 7.C defense in depth: `response`'s provenance check alone
    proves `response` is bound by a call spelled `login_user(...)`, but not that
    `login_user` itself is the genuine imported production login service function rather
    than a same-named local function defined elsewhere in the module. A locally-defined
    decoy `login_user` could otherwise return an arbitrary fake response object while
    every other check in this file still matches verbatim.
    """
    snippet = (
        "from app.modules.events.service import record_business_event\n"
        "\n"
        "def login_user(db, username, password):\n"
        "    return FakeResponseWithArbitraryRoleCodes()\n"
        "\n"
        "def login(payload, db):\n"
        "    response = login_user(db, payload.username, payload.password)\n"
        "    record_business_event(\n"
        "        db,\n"
        "        event_name='UserLoginSucceeded',\n"
        "        event_payload={'role_codes': response.user.role_codes},\n"
        "    )\n"
    )
    tree = ast.parse(snippet)
    visitor = _RoleCodesFailClosedVisitor(module_key="identity")
    visitor.visit_and_collect(tree)
    assert visitor.offenses, "guard incorrectly permitted a locally-defined decoy login_user function"


def test_role_codes_fail_closed_guard_rejects_identity_dynamic_role_codes_via_dunder_dict_get_with_concatenation() -> None:
    """PF-1A-E1 C5 test 23: combines both new detection paths in one statement -
    `response.user.__dict__.get("role_" + "codes")` is both the `.get(...)` method-call
    idiom and a compile-time string concatenation of the banned attribute name.
    """
    snippet = (
        "def login(payload, db):\n"
        "    record_business_event(\n"
        "        db,\n"
        "        event_name='UserLoginSucceeded',\n"
        "        event_payload={'role_codes': response.user.__dict__.get('role_' + 'codes')},\n"
        "    )\n"
    )
    tree = ast.parse(snippet)
    visitor = _RoleCodesFailClosedVisitor(module_key="identity")
    visitor.visit_and_collect(tree)
    assert visitor.offenses, "guard incorrectly permitted response.user.__dict__.get('role_' + 'codes')"


# =========================================================================================
# PF-1A-E1 C6 finding 1: import provenance must be proved per individual `ast.alias`, not
# per `ImportFrom` STATEMENT. A single ImportFrom statement can bind the same local name
# more than once (a genuine alias plus a conflicting one), and the conflicting alias must
# still be rejected even though it shares a statement with the genuine one.
# =========================================================================================


def test_role_codes_fail_closed_guard_rejects_accounts_shape_when_account_tax_verify_has_a_same_statement_alias_collision() -> None:
    """PF-1A-E1 C6 finding 1, test 1: the genuine `ACCOUNT_TAX_VERIFY` alias and a
    conflicting `ACCOUNT_READ as ACCOUNT_TAX_VERIFY` alias in the SAME ImportFrom
    statement must still be rejected. The pre-C6 guard treated the whole statement as
    trustworthy because it contained a genuine alias somewhere, even though the second
    alias in the same statement overwrites the local name with a different symbol.
    """
    snippet = (
        "from app.modules.authorization.contract import (\n"
        "    ACCOUNT_TAX_VERIFY,\n"
        "    ACCOUNT_READ as ACCOUNT_TAX_VERIFY,\n"
        ")\n"
        "from app.modules.authorization.service import has_permission\n"
        "\n"
        "def _assert_tax_verification_permission(db, user, requested_state):\n"
        "    if not has_permission(db, user.role_codes, ACCOUNT_TAX_VERIFY):\n"
        "        raise ValueError('nope')\n"
    )
    tree = ast.parse(snippet)
    visitor = _RoleCodesFailClosedVisitor(module_key="accounts")
    visitor.visit_and_collect(tree)
    assert visitor.offenses, (
        "guard incorrectly permitted ACCOUNT_TAX_VERIFY with a same-statement alias collision"
    )


def test_role_codes_fail_closed_guard_rejects_accounts_shape_when_account_tax_verify_collision_alias_appears_first() -> None:
    """PF-1A-E1 C6 finding 1, test 2: the same bypass as above, but the conflicting alias
    appears BEFORE the genuine one in the same statement. Order must not matter - the fix
    must not merely special-case "the last alias wins" or "the first alias wins"; it must
    prove provenance against the SPECIFIC alias that produced each occurrence.
    """
    snippet = (
        "from app.modules.authorization.contract import (\n"
        "    ACCOUNT_READ as ACCOUNT_TAX_VERIFY,\n"
        "    ACCOUNT_TAX_VERIFY,\n"
        ")\n"
        "from app.modules.authorization.service import has_permission\n"
        "\n"
        "def _assert_tax_verification_permission(db, user, requested_state):\n"
        "    if not has_permission(db, user.role_codes, ACCOUNT_TAX_VERIFY):\n"
        "        raise ValueError('nope')\n"
    )
    tree = ast.parse(snippet)
    visitor = _RoleCodesFailClosedVisitor(module_key="accounts")
    visitor.visit_and_collect(tree)
    assert visitor.offenses, (
        "guard incorrectly permitted ACCOUNT_TAX_VERIFY with a same-statement alias collision "
        "(conflicting alias first)"
    )


def test_role_codes_fail_closed_guard_rejects_accounts_shape_when_has_permission_has_a_same_statement_alias_collision() -> None:
    """PF-1A-E1 C6 finding 1, test 3: the same bypass class applied to `has_permission`
    instead of `ACCOUNT_TAX_VERIFY` - a genuine alias plus a conflicting
    `other_helper as has_permission` alias in the same statement.
    """
    snippet = (
        "from app.modules.authorization.contract import ACCOUNT_TAX_VERIFY\n"
        "from app.modules.authorization.service import (\n"
        "    has_permission,\n"
        "    other_helper as has_permission,\n"
        ")\n"
        "\n"
        "def _assert_tax_verification_permission(db, user, requested_state):\n"
        "    if not has_permission(db, user.role_codes, ACCOUNT_TAX_VERIFY):\n"
        "        raise ValueError('nope')\n"
    )
    tree = ast.parse(snippet)
    visitor = _RoleCodesFailClosedVisitor(module_key="accounts")
    visitor.visit_and_collect(tree)
    assert visitor.offenses, (
        "guard incorrectly permitted has_permission with a same-statement alias collision"
    )


def test_role_codes_fail_closed_guard_rejects_accounts_shape_when_has_permission_collision_alias_appears_first() -> None:
    """PF-1A-E1 C6 finding 1, test 4: same bypass as test 3, with the conflicting alias
    appearing before the genuine one.
    """
    snippet = (
        "from app.modules.authorization.contract import ACCOUNT_TAX_VERIFY\n"
        "from app.modules.authorization.service import (\n"
        "    other_helper as has_permission,\n"
        "    has_permission,\n"
        ")\n"
        "\n"
        "def _assert_tax_verification_permission(db, user, requested_state):\n"
        "    if not has_permission(db, user.role_codes, ACCOUNT_TAX_VERIFY):\n"
        "        raise ValueError('nope')\n"
    )
    tree = ast.parse(snippet)
    visitor = _RoleCodesFailClosedVisitor(module_key="accounts")
    visitor.visit_and_collect(tree)
    assert visitor.offenses, (
        "guard incorrectly permitted has_permission with a same-statement alias collision "
        "(conflicting alias first)"
    )


def test_role_codes_fail_closed_guard_rejects_identity_shape_when_record_business_event_has_a_same_statement_alias_collision() -> None:
    """PF-1A-E1 C6 finding 1, test 5: the same bypass class applied to
    `record_business_event`.
    """
    snippet = (
        "from app.modules.events.service import (\n"
        "    record_business_event,\n"
        "    other_event_helper as record_business_event,\n"
        ")\n"
        "from app.modules.identity.service import login_user\n"
        "\n"
        "def login(payload, db):\n"
        "    response = login_user(db, payload.username, payload.password)\n"
        "    record_business_event(\n"
        "        db,\n"
        "        event_name='UserLoginSucceeded',\n"
        "        event_payload={'role_codes': response.user.role_codes},\n"
        "    )\n"
    )
    tree = ast.parse(snippet)
    visitor = _RoleCodesFailClosedVisitor(module_key="identity")
    visitor.visit_and_collect(tree)
    assert visitor.offenses, (
        "guard incorrectly permitted record_business_event with a same-statement alias collision"
    )


def test_role_codes_fail_closed_guard_rejects_identity_shape_when_login_user_has_a_same_statement_alias_collision() -> None:
    """PF-1A-E1 C6 finding 1, test 6: the same bypass class applied to `login_user`, the
    helper `response`'s own provenance is anchored to (PF-1A-E1 C5 finding 7.C).
    """
    snippet = (
        "from app.modules.events.service import record_business_event\n"
        "from app.modules.identity.service import (\n"
        "    login_user,\n"
        "    other_login_helper as login_user,\n"
        ")\n"
        "\n"
        "def login(payload, db):\n"
        "    response = login_user(db, payload.username, payload.password)\n"
        "    record_business_event(\n"
        "        db,\n"
        "        event_name='UserLoginSucceeded',\n"
        "        event_payload={'role_codes': response.user.role_codes},\n"
        "    )\n"
    )
    tree = ast.parse(snippet)
    visitor = _RoleCodesFailClosedVisitor(module_key="identity")
    visitor.visit_and_collect(tree)
    assert visitor.offenses, (
        "guard incorrectly permitted login_user with a same-statement alias collision"
    )


def test_role_codes_fail_closed_guard_permits_genuine_single_aliases_for_every_tracked_name() -> None:
    """PF-1A-E1 C6 finding 1, test 7 (regression guard): a module that genuinely imports
    each tracked name exactly once, with no conflicting alias anywhere, must still be
    accepted for both modules. This is already exercised end to end by the pre-existing
    `..._permits_the_real_accounts_import_and_statement_together` and
    `..._permits_the_real_identity_import_and_statement_together` tests in this file; this
    test additionally proves the underlying per-alias provenance helper agrees with that
    outcome directly, so a future regression in it is caught at the unit level too.
    """
    accounts_tree = ast.parse(
        "from app.modules.authorization.contract import ACCOUNT_TAX_VERIFY\n"
        "from app.modules.authorization.service import has_permission\n"
    )
    assert _helper_provenance_is_trustworthy(
        accounts_tree, "has_permission", ACCOUNTS_EXPECTED_IMPORT_MODULE, ACCOUNTS_EXPECTED_IMPORT_ORIGINAL_NAME
    ), "genuine single-alias has_permission import must be trustworthy"
    assert _helper_provenance_is_trustworthy(
        accounts_tree,
        "ACCOUNT_TAX_VERIFY",
        ACCOUNTS_EXPECTED_PERMISSION_IMPORT_MODULE,
        ACCOUNTS_EXPECTED_PERMISSION_IMPORT_ORIGINAL_NAME,
    ), "genuine single-alias ACCOUNT_TAX_VERIFY import must be trustworthy"

    identity_tree = ast.parse(
        "from app.modules.events.service import record_business_event\n"
        "from app.modules.identity.service import login_user\n"
    )
    assert _helper_provenance_is_trustworthy(
        identity_tree, "record_business_event", IDENTITY_EXPECTED_IMPORT_MODULE, IDENTITY_EXPECTED_IMPORT_ORIGINAL_NAME
    ), "genuine single-alias record_business_event import must be trustworthy"
    assert _helper_provenance_is_trustworthy(
        identity_tree,
        "login_user",
        IDENTITY_EXPECTED_LOGIN_USER_IMPORT_MODULE,
        IDENTITY_EXPECTED_LOGIN_USER_IMPORT_ORIGINAL_NAME,
    ), "genuine single-alias login_user import must be trustworthy"


def test_count_expected_import_bindings_counts_per_alias_not_per_statement() -> None:
    """PF-1A-E1 C6 finding 1 direct unit test: a single ImportFrom statement carrying one
    genuine alias and one conflicting alias for the same local name must be counted as
    exactly one genuine binding (the genuine alias), matching what "exactly one genuine
    import" is actually supposed to mean.
    """
    tree = ast.parse(
        "from app.modules.authorization.contract import (\n"
        "    ACCOUNT_TAX_VERIFY,\n"
        "    ACCOUNT_READ as ACCOUNT_TAX_VERIFY,\n"
        ")\n"
    )
    count = _count_expected_import_bindings(
        tree, "ACCOUNT_TAX_VERIFY", ACCOUNTS_EXPECTED_PERMISSION_IMPORT_MODULE, "ACCOUNT_TAX_VERIFY"
    )
    assert count == 1, f"expected exactly one genuine alias binding to be counted, got {count}"


def test_name_is_shadowed_detects_a_conflicting_alias_in_the_same_importfrom_statement() -> None:
    """PF-1A-E1 C6 finding 1 direct unit test: `_name_is_shadowed` must report the tracked
    name as shadowed when the SAME ImportFrom statement carries both the genuine alias and
    a conflicting one, even though the genuine alias is also present in that statement.
    """
    tree = ast.parse(
        "from app.modules.authorization.contract import (\n"
        "    ACCOUNT_TAX_VERIFY,\n"
        "    ACCOUNT_READ as ACCOUNT_TAX_VERIFY,\n"
        ")\n"
    )
    assert _name_is_shadowed(
        tree, "ACCOUNT_TAX_VERIFY", ACCOUNTS_EXPECTED_PERMISSION_IMPORT_MODULE, "ACCOUNT_TAX_VERIFY"
    ), "guard failed to detect a same-statement alias collision as shadowing"


# =========================================================================================
# PF-1A-E1 C6 finding 2: an allowed statement moved inside a nested lexical scope (a nested
# def/async def/lambda under the target function), or a lambda parameter that shadows the
# real outer user/response, must still be rejected - and the genuine immediate-scope
# statement must remain accepted after the scope restriction is added.
# =========================================================================================


def test_role_codes_fail_closed_guard_rejects_accounts_shape_inside_a_nested_def() -> None:
    """PF-1A-E1 C6 finding 2, test 8: the exact real production statement, moved inside a
    nested `def` under `_assert_tax_verification_permission`, must be rejected - it no
    longer lives in the target function's own immediate lexical scope.
    """
    snippet = (
        "from app.modules.authorization.contract import ACCOUNT_TAX_VERIFY\n"
        "from app.modules.authorization.service import has_permission\n"
        "\n"
        "def _assert_tax_verification_permission(db, user, requested_state):\n"
        "    def _inner():\n"
        "        if not has_permission(db, user.role_codes, ACCOUNT_TAX_VERIFY):\n"
        "            raise ValueError('nope')\n"
        "    _inner()\n"
    )
    tree = ast.parse(snippet)
    visitor = _RoleCodesFailClosedVisitor(module_key="accounts")
    visitor.visit_and_collect(tree)
    assert visitor.offenses, "guard incorrectly permitted the accounts shape inside a nested def"


def test_role_codes_fail_closed_guard_rejects_accounts_shape_inside_a_nested_async_def() -> None:
    """PF-1A-E1 C6 finding 2, test 9: same as test 8 with a nested `async def`."""
    snippet = (
        "from app.modules.authorization.contract import ACCOUNT_TAX_VERIFY\n"
        "from app.modules.authorization.service import has_permission\n"
        "\n"
        "def _assert_tax_verification_permission(db, user, requested_state):\n"
        "    async def _inner():\n"
        "        if not has_permission(db, user.role_codes, ACCOUNT_TAX_VERIFY):\n"
        "            raise ValueError('nope')\n"
        "    return _inner\n"
    )
    tree = ast.parse(snippet)
    visitor = _RoleCodesFailClosedVisitor(module_key="accounts")
    visitor.visit_and_collect(tree)
    assert visitor.offenses, "guard incorrectly permitted the accounts shape inside a nested async def"


def test_role_codes_fail_closed_guard_rejects_accounts_shape_inside_a_lambda() -> None:
    """PF-1A-E1 C6 finding 2, test 10: the exact real statement moved inside a lambda
    (closing over the real outer `user`, not shadowing it) must still be rejected - a
    lambda body is its own lexical scope.
    """
    snippet = (
        "from app.modules.authorization.contract import ACCOUNT_TAX_VERIFY\n"
        "from app.modules.authorization.service import has_permission\n"
        "\n"
        "def _assert_tax_verification_permission(db, user, requested_state):\n"
        "    check = lambda: has_permission(db, user.role_codes, ACCOUNT_TAX_VERIFY)\n"
        "    if not check():\n"
        "        raise ValueError('nope')\n"
    )
    tree = ast.parse(snippet)
    visitor = _RoleCodesFailClosedVisitor(module_key="accounts")
    visitor.visit_and_collect(tree)
    assert visitor.offenses, "guard incorrectly permitted the accounts shape inside a lambda"


def test_role_codes_fail_closed_guard_rejects_accounts_shape_when_a_lambda_parameter_shadows_user() -> None:
    """PF-1A-E1 C6 finding 2, test 11: the independently demonstrated bypass - a lambda
    whose OWN parameter is named `user`, shadowing the real outer `user`, while the
    base-object name spelling still matches `user.role_codes` textually.
    """
    snippet = (
        "from app.modules.authorization.contract import ACCOUNT_TAX_VERIFY\n"
        "from app.modules.authorization.service import has_permission\n"
        "\n"
        "def _assert_tax_verification_permission(db, user, requested_state):\n"
        "    check = lambda user: has_permission(db, user.role_codes, ACCOUNT_TAX_VERIFY)\n"
        "    if not check(user):\n"
        "        raise ValueError('nope')\n"
    )
    tree = ast.parse(snippet)
    visitor = _RoleCodesFailClosedVisitor(module_key="accounts")
    visitor.visit_and_collect(tree)
    assert visitor.offenses, "guard incorrectly permitted a lambda parameter named 'user' to shadow the real one"


def test_role_codes_fail_closed_guard_rejects_identity_shape_inside_a_nested_def() -> None:
    """PF-1A-E1 C6 finding 2, test 12: the real identity audit-event call moved inside a
    nested `def` under `login`, with `response` still bound at the outer level.
    """
    snippet = (
        "from app.modules.events.service import record_business_event\n"
        "from app.modules.identity.service import login_user\n"
        "\n"
        "def login(payload, db):\n"
        "    response = login_user(db, payload.username, payload.password)\n"
        "    def _audit():\n"
        "        record_business_event(\n"
        "            db,\n"
        "            event_name='UserLoginSucceeded',\n"
        "            event_payload={'role_codes': response.user.role_codes},\n"
        "        )\n"
        "    _audit()\n"
    )
    tree = ast.parse(snippet)
    visitor = _RoleCodesFailClosedVisitor(module_key="identity")
    visitor.visit_and_collect(tree)
    assert visitor.offenses, "guard incorrectly permitted the identity audit access inside a nested def"


def test_role_codes_fail_closed_guard_rejects_identity_shape_when_response_assignment_and_audit_are_both_nested() -> None:
    """PF-1A-E1 C6 finding 2, test 13: the independently demonstrated bypass - BOTH the
    `response = login_user(...)` assignment and the audit call moved inside a nested `def`
    under `login`, so neither lives in `login`'s own immediate scope at all.
    """
    snippet = (
        "from app.modules.events.service import record_business_event\n"
        "from app.modules.identity.service import login_user\n"
        "\n"
        "def login(payload, db):\n"
        "    def _do_login():\n"
        "        response = login_user(db, payload.username, payload.password)\n"
        "        record_business_event(\n"
        "            db,\n"
        "            event_name='UserLoginSucceeded',\n"
        "            event_payload={'role_codes': response.user.role_codes},\n"
        "        )\n"
        "        return response\n"
        "    return _do_login()\n"
    )
    tree = ast.parse(snippet)
    visitor = _RoleCodesFailClosedVisitor(module_key="identity")
    visitor.visit_and_collect(tree)
    assert visitor.offenses, (
        "guard incorrectly permitted response assignment and audit access both nested inside "
        "a single nested def"
    )


def test_role_codes_fail_closed_guard_rejects_identity_shape_inside_a_nested_async_def() -> None:
    """PF-1A-E1 C6 finding 2, test 14: same as test 13 with a nested `async def`."""
    snippet = (
        "from app.modules.events.service import record_business_event\n"
        "from app.modules.identity.service import login_user\n"
        "\n"
        "def login(payload, db):\n"
        "    async def _do_login():\n"
        "        response = login_user(db, payload.username, payload.password)\n"
        "        record_business_event(\n"
        "            db,\n"
        "            event_name='UserLoginSucceeded',\n"
        "            event_payload={'role_codes': response.user.role_codes},\n"
        "        )\n"
        "        return response\n"
        "    return _do_login\n"
    )
    tree = ast.parse(snippet)
    visitor = _RoleCodesFailClosedVisitor(module_key="identity")
    visitor.visit_and_collect(tree)
    assert visitor.offenses, (
        "guard incorrectly permitted response assignment and audit access both nested inside "
        "a nested async def"
    )


def test_role_codes_fail_closed_guard_rejects_identity_shape_inside_a_lambda() -> None:
    """PF-1A-E1 C6 finding 2, test 15: the audit call moved inside a lambda closing over
    the real outer `response` (not shadowing it) must still be rejected - a lambda body is
    its own lexical scope.
    """
    snippet = (
        "from app.modules.events.service import record_business_event\n"
        "from app.modules.identity.service import login_user\n"
        "\n"
        "def login(payload, db):\n"
        "    response = login_user(db, payload.username, payload.password)\n"
        "    audit = lambda: record_business_event(\n"
        "        db,\n"
        "        event_name='UserLoginSucceeded',\n"
        "        event_payload={'role_codes': response.user.role_codes},\n"
        "    )\n"
        "    audit()\n"
    )
    tree = ast.parse(snippet)
    visitor = _RoleCodesFailClosedVisitor(module_key="identity")
    visitor.visit_and_collect(tree)
    assert visitor.offenses, "guard incorrectly permitted the identity audit access inside a lambda"


def test_role_codes_fail_closed_guard_rejects_identity_shape_when_a_lambda_parameter_shadows_response() -> None:
    """PF-1A-E1 C6 finding 2, test 16: the independently demonstrated bypass - a lambda
    whose OWN parameter is named `response`, shadowing the real outer `response`, while the
    base-object name spelling still matches `response.user.role_codes` textually.
    """
    snippet = (
        "from app.modules.events.service import record_business_event\n"
        "from app.modules.identity.service import login_user\n"
        "\n"
        "def login(payload, db):\n"
        "    response = login_user(db, payload.username, payload.password)\n"
        "    audit = lambda response: record_business_event(\n"
        "        db,\n"
        "        event_name='UserLoginSucceeded',\n"
        "        event_payload={'role_codes': response.user.role_codes},\n"
        "    )\n"
        "    audit(response)\n"
    )
    tree = ast.parse(snippet)
    visitor = _RoleCodesFailClosedVisitor(module_key="identity")
    visitor.visit_and_collect(tree)
    assert visitor.offenses, (
        "guard incorrectly permitted a lambda parameter named 'response' to shadow the real one"
    )


def test_role_codes_fail_closed_guard_permits_the_genuine_immediate_scope_accounts_statement_after_c6() -> None:
    """PF-1A-E1 C6 finding 2, test 17 (regression guard): the genuine real production
    statement, written directly in the target function's own immediate body with no nested
    scope involved at all, must remain accepted after the C6 scope restriction. This is the
    same snippet the pre-existing C5 "permits" test already covers; repeated here under an
    explicit C6 name so the scope-restriction change is directly proven not to have
    regressed the accepted case.
    """
    tree = ast.parse(ACCOUNTS_REAL_SHAPE_SNIPPET)
    visitor = _RoleCodesFailClosedVisitor(module_key="accounts")
    visitor.visit_and_collect(tree)
    assert visitor.offenses == [], (
        f"guard incorrectly rejected the genuine immediate-scope accounts statement after C6: {visitor.offenses}"
    )


def test_role_codes_fail_closed_guard_permits_the_genuine_immediate_scope_identity_statement_after_c6() -> None:
    """PF-1A-E1 C6 finding 2, test 18 (regression guard): same as test 17 for the identity
    `response = login_user(...)` assignment plus audit call, both directly in `login`'s own
    immediate body.
    """
    tree = ast.parse(IDENTITY_REAL_SHAPE_SNIPPET)
    visitor = _RoleCodesFailClosedVisitor(module_key="identity")
    visitor.visit_and_collect(tree)
    assert visitor.offenses == [], (
        f"guard incorrectly rejected the genuine immediate-scope identity statement after C6: {visitor.offenses}"
    )


def test_iter_immediate_scope_nodes_excludes_nested_function_and_lambda_bodies() -> None:
    """Direct unit test for `_iter_immediate_scope_nodes`: a call written directly in the
    outer function's own body must be yielded, while calls written inside a nested `def`
    or inside a `lambda` body must never be yielded.
    """
    tree = ast.parse(
        "def outer(user):\n"
        "    direct_call(user)\n"
        "    def inner():\n"
        "        nested_call(user)\n"
        "    check = lambda: lambda_call(user)\n"
        "    return inner, check\n"
    )
    outer_func = tree.body[0]
    assert isinstance(outer_func, ast.FunctionDef)

    immediate_call_names = {
        node.func.id
        for node in _iter_immediate_scope_nodes(outer_func)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert immediate_call_names == {"direct_call"}, (
        f"expected only the directly-nested call to be in the immediate scope, got {immediate_call_names}"
    )


def test_iter_binding_names_enumerates_lambda_parameters() -> None:
    """PF-1A-E1 C6 lambda binding enumeration direct unit test: a lambda parameter must be
    yielded as a binding site the same way a function parameter is, for every parameter
    kind this guard already tracks for ordinary functions (positional-only, ordinary
    positional, vararg, keyword-only, kwarg). This is defense in depth alongside the
    immediate-scope restriction proven above, not the primary defense against a shadowing
    lambda parameter.
    """
    tree = ast.parse("f = lambda a, /, b, *args, c, **kwargs: None\n")
    tracked = {"a", "b", "args", "c", "kwargs"}
    bound_names = {name for name, _ in _iter_binding_names(tree) if name in tracked}
    assert bound_names == tracked, (
        f"expected every lambda parameter kind to be enumerated as a binding site, got {bound_names}"
    )


# =========================================================================================
# PF-1A-E1 C7 finding 10: a comprehension or generator expression each introduce their own
# implicit nested scope in Python 3, exactly like a nested def/lambda/class - but none of the
# four (ListComp/SetComp/DictComp/GeneratorExp) were in the C6 scope-boundary set. An allowed
# statement moved inside any of the four must still be rejected as an offense by the
# production-style fail-closed global `.role_codes` scan, and the genuine immediate-scope
# statement must remain accepted after the scope boundary is added.
# =========================================================================================


def test_role_codes_fail_closed_guard_rejects_accounts_shape_inside_a_generator_expression() -> None:
    """PF-1A-E1 C7 finding 10, regression 1: the exact real production statement, wrapped in
    a bare generator expression assigned to a local and never consumed, must be rejected -
    the generator body is its own lexical scope, and the wrapped call is never even executed
    at runtime (the generator object itself is truthy, so `if not check:` never raises).
    """
    snippet = (
        "from app.modules.authorization.contract import ACCOUNT_TAX_VERIFY\n"
        "from app.modules.authorization.service import has_permission\n"
        "\n"
        "def _assert_tax_verification_permission(db, user, requested_state):\n"
        "    check = (\n"
        "        has_permission(db, user.role_codes, ACCOUNT_TAX_VERIFY)\n"
        "        for item in (1,)\n"
        "    )\n"
        "    if not check:\n"
        "        raise ValueError('nope')\n"
    )
    tree = ast.parse(snippet)
    visitor = _RoleCodesFailClosedVisitor(module_key="accounts")
    visitor.visit_and_collect(tree)
    assert visitor.offenses, "guard incorrectly permitted the accounts shape inside a generator expression"


def test_role_codes_fail_closed_guard_rejects_accounts_shape_inside_a_list_comprehension() -> None:
    """PF-1A-E1 C7 finding 10, regression 2: same bypass shape using a list comprehension."""
    snippet = (
        "from app.modules.authorization.contract import ACCOUNT_TAX_VERIFY\n"
        "from app.modules.authorization.service import has_permission\n"
        "\n"
        "def _assert_tax_verification_permission(db, user, requested_state):\n"
        "    check = [\n"
        "        has_permission(db, user.role_codes, ACCOUNT_TAX_VERIFY)\n"
        "        for item in (1,)\n"
        "    ]\n"
        "    if not check:\n"
        "        raise ValueError('nope')\n"
    )
    tree = ast.parse(snippet)
    visitor = _RoleCodesFailClosedVisitor(module_key="accounts")
    visitor.visit_and_collect(tree)
    assert visitor.offenses, "guard incorrectly permitted the accounts shape inside a list comprehension"


def test_role_codes_fail_closed_guard_rejects_accounts_shape_inside_a_set_comprehension() -> None:
    """PF-1A-E1 C7 finding 10, regression 3: same bypass shape using a set comprehension."""
    snippet = (
        "from app.modules.authorization.contract import ACCOUNT_TAX_VERIFY\n"
        "from app.modules.authorization.service import has_permission\n"
        "\n"
        "def _assert_tax_verification_permission(db, user, requested_state):\n"
        "    check = {\n"
        "        has_permission(db, user.role_codes, ACCOUNT_TAX_VERIFY)\n"
        "        for item in (1,)\n"
        "    }\n"
        "    if not check:\n"
        "        raise ValueError('nope')\n"
    )
    tree = ast.parse(snippet)
    visitor = _RoleCodesFailClosedVisitor(module_key="accounts")
    visitor.visit_and_collect(tree)
    assert visitor.offenses, "guard incorrectly permitted the accounts shape inside a set comprehension"


def test_role_codes_fail_closed_guard_rejects_accounts_shape_inside_a_dict_comprehension() -> None:
    """PF-1A-E1 C7 finding 10, regression 4: same bypass shape using a dict comprehension
    (the real statement placed as the comprehension's value expression).
    """
    snippet = (
        "from app.modules.authorization.contract import ACCOUNT_TAX_VERIFY\n"
        "from app.modules.authorization.service import has_permission\n"
        "\n"
        "def _assert_tax_verification_permission(db, user, requested_state):\n"
        "    check = {\n"
        "        item: has_permission(db, user.role_codes, ACCOUNT_TAX_VERIFY)\n"
        "        for item in (1,)\n"
        "    }\n"
        "    if not check:\n"
        "        raise ValueError('nope')\n"
    )
    tree = ast.parse(snippet)
    visitor = _RoleCodesFailClosedVisitor(module_key="accounts")
    visitor.visit_and_collect(tree)
    assert visitor.offenses, "guard incorrectly permitted the accounts shape inside a dict comprehension"


def test_role_codes_fail_closed_guard_rejects_identity_shape_inside_a_generator_expression() -> None:
    """PF-1A-E1 C7 finding 10, regression 5: the real identity audit-event call, wrapped in a
    bare generator expression assigned to a local and never consumed, must be rejected - the
    same runtime no-op danger as the accounts case above (the generator object is truthy, so
    `if not audit:` never raises and the audit call inside it is never executed).
    """
    snippet = (
        "from app.modules.events.service import record_business_event\n"
        "from app.modules.identity.service import login_user\n"
        "\n"
        "def login(payload, db):\n"
        "    response = login_user(db, payload.username, payload.password)\n"
        "    audit = (\n"
        "        record_business_event(\n"
        "            db,\n"
        "            event_name='UserLoginSucceeded',\n"
        "            event_payload={'role_codes': response.user.role_codes},\n"
        "        )\n"
        "        for item in (1,)\n"
        "    )\n"
        "    if not audit:\n"
        "        raise ValueError('nope')\n"
    )
    tree = ast.parse(snippet)
    visitor = _RoleCodesFailClosedVisitor(module_key="identity")
    visitor.visit_and_collect(tree)
    assert visitor.offenses, "guard incorrectly permitted the identity shape inside a generator expression"


def test_role_codes_fail_closed_guard_rejects_identity_shape_inside_a_list_comprehension() -> None:
    """PF-1A-E1 C7 finding 10, regression 6: same bypass shape using a list comprehension."""
    snippet = (
        "from app.modules.events.service import record_business_event\n"
        "from app.modules.identity.service import login_user\n"
        "\n"
        "def login(payload, db):\n"
        "    response = login_user(db, payload.username, payload.password)\n"
        "    audit = [\n"
        "        record_business_event(\n"
        "            db,\n"
        "            event_name='UserLoginSucceeded',\n"
        "            event_payload={'role_codes': response.user.role_codes},\n"
        "        )\n"
        "        for item in (1,)\n"
        "    ]\n"
        "    if not audit:\n"
        "        raise ValueError('nope')\n"
    )
    tree = ast.parse(snippet)
    visitor = _RoleCodesFailClosedVisitor(module_key="identity")
    visitor.visit_and_collect(tree)
    assert visitor.offenses, "guard incorrectly permitted the identity shape inside a list comprehension"


def test_role_codes_fail_closed_guard_rejects_identity_shape_inside_a_set_comprehension() -> None:
    """PF-1A-E1 C7 finding 10, regression 7: same bypass shape using a set comprehension."""
    snippet = (
        "from app.modules.events.service import record_business_event\n"
        "from app.modules.identity.service import login_user\n"
        "\n"
        "def login(payload, db):\n"
        "    response = login_user(db, payload.username, payload.password)\n"
        "    audit = {\n"
        "        record_business_event(\n"
        "            db,\n"
        "            event_name='UserLoginSucceeded',\n"
        "            event_payload={'role_codes': response.user.role_codes},\n"
        "        )\n"
        "        for item in (1,)\n"
        "    }\n"
        "    if not audit:\n"
        "        raise ValueError('nope')\n"
    )
    tree = ast.parse(snippet)
    visitor = _RoleCodesFailClosedVisitor(module_key="identity")
    visitor.visit_and_collect(tree)
    assert visitor.offenses, "guard incorrectly permitted the identity shape inside a set comprehension"


def test_role_codes_fail_closed_guard_rejects_identity_shape_inside_a_dict_comprehension() -> None:
    """PF-1A-E1 C7 finding 10, regression 8: same bypass shape using a dict comprehension
    (the real statement placed as the comprehension's value expression).
    """
    snippet = (
        "from app.modules.events.service import record_business_event\n"
        "from app.modules.identity.service import login_user\n"
        "\n"
        "def login(payload, db):\n"
        "    response = login_user(db, payload.username, payload.password)\n"
        "    audit = {\n"
        "        item: record_business_event(\n"
        "            db,\n"
        "            event_name='UserLoginSucceeded',\n"
        "            event_payload={'role_codes': response.user.role_codes},\n"
        "        )\n"
        "        for item in (1,)\n"
        "    }\n"
        "    if not audit:\n"
        "        raise ValueError('nope')\n"
    )
    tree = ast.parse(snippet)
    visitor = _RoleCodesFailClosedVisitor(module_key="identity")
    visitor.visit_and_collect(tree)
    assert visitor.offenses, "guard incorrectly permitted the identity shape inside a dict comprehension"


def test_role_codes_fail_closed_guard_permits_the_genuine_immediate_scope_accounts_statement_after_c7() -> None:
    """PF-1A-E1 C7 finding 10, regression 9 (positive path): the genuine real production
    statement, written directly in the target function's own immediate body with no
    comprehension/generator involved at all, must remain accepted after the C7 scope
    boundary is added. This is the same snippet the pre-existing C5/C6 "permits" tests
    already cover; repeated here under an explicit C7 name so the comprehension/generator
    scope-boundary change is directly proven not to have regressed the accepted case.
    """
    tree = ast.parse(ACCOUNTS_REAL_SHAPE_SNIPPET)
    visitor = _RoleCodesFailClosedVisitor(module_key="accounts")
    visitor.visit_and_collect(tree)
    assert visitor.offenses == [], (
        f"guard incorrectly rejected the genuine immediate-scope accounts statement after C7: {visitor.offenses}"
    )


def test_role_codes_fail_closed_guard_permits_the_genuine_immediate_scope_identity_statement_after_c7() -> None:
    """PF-1A-E1 C7 finding 10, regression 10 (positive path): same as the accounts positive
    regression above, for the identity `response = login_user(...)` assignment plus audit
    call, both directly in `login`'s own immediate body.
    """
    tree = ast.parse(IDENTITY_REAL_SHAPE_SNIPPET)
    visitor = _RoleCodesFailClosedVisitor(module_key="identity")
    visitor.visit_and_collect(tree)
    assert visitor.offenses == [], (
        f"guard incorrectly rejected the genuine immediate-scope identity statement after C7: {visitor.offenses}"
    )


def test_iter_immediate_scope_nodes_excludes_comprehension_and_generator_bodies() -> None:
    """Direct unit test for `_iter_immediate_scope_nodes` (PF-1A-E1 C7): a call written
    directly in the outer function's own body must be yielded, while a call written inside
    the element expression of a list comprehension, set comprehension, dict comprehension,
    or generator expression must never be yielded - each introduces its own implicit nested
    scope in Python 3, exactly like a nested def/lambda already excluded by C6.
    """
    tree = ast.parse(
        "def outer(user):\n"
        "    direct_call(user)\n"
        "    a = [list_call(user) for item in (1,)]\n"
        "    b = {set_call(user) for item in (1,)}\n"
        "    c = {item: dict_call(user) for item in (1,)}\n"
        "    d = (gen_call(user) for item in (1,))\n"
        "    return a, b, c, d\n"
    )
    outer_func = tree.body[0]
    assert isinstance(outer_func, ast.FunctionDef)

    immediate_call_names = {
        node.func.id
        for node in _iter_immediate_scope_nodes(outer_func)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert immediate_call_names == {"direct_call"}, (
        f"expected only the directly-nested call to be in the immediate scope, got {immediate_call_names}"
    )
