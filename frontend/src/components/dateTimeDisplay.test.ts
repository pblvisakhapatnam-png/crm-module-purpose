import { readdirSync, readFileSync } from "node:fs";
import { join, relative } from "node:path";
import { fileURLToPath } from "node:url";

import ts from "typescript";
import { describe, expect, it } from "vitest";

import { formatDateTime, readApiDateTime } from "./dateTimeDisplay";

// TB-1 finding TB1-604: four CRM pages formatted a business time with a bare toLocaleString(), reading the API's
// zoneless UTC time as the browser's own and showing it 5 hours 30 minutes early. Every page now shows India's time
// whatever the browser's zone; this fails when a page formats a time without naming the zone again.
//
// TB-1 register note N-06 (October 2026): that check caught only a bare toLocaleString(). Eleven files kept their own
// way of showing a time: ten copies of this module's reader and formatter (nine pages and the Documents panel), and
// the dashboard's, which read a time with no zone as the browser's own and showed the Recent Work Orders' Created time
// 5 hours 30 minutes early. All now use this module. The check below reads every source file with TypeScript's own
// type checker and fails when any file but the two shared time modules reads a time from text (any Date made from a
// string, whatever was done about its zone first) or shows a time of day itself.

const SRC = fileURLToPath(new URL("..", import.meta.url));
const FRONTEND = join(SRC, "..");
// This module reads and shows API times; enteredDateTime.ts turns a typed India time into UTC by adding +05:30, and
// enteredDateTime.test.ts guards it.
const SHARED = [join("components", "dateTimeDisplay.ts"), join("components", "enteredDateTime.ts")];

function sourceFiles(dir: string): string[] {
  return readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const path = join(dir, entry.name);
    if (entry.isDirectory()) return sourceFiles(path);
    return /\.tsx?$/.test(entry.name) && !/\.test\.tsx?$/.test(entry.name) ? [path] : [];
  });
}

/** Intl options that put a time of day (or a zone's name) into the text. */
const TIME_OF_DAY_OPTIONS = new Set([
  "hour", "minute", "second", "fractionalSecondDigits", "dayPeriod", "hour12", "hourCycle", "timeStyle", "timeZoneName",
]);
/** Date methods that give a time of day, in the browser's zone or in UTC (toLocaleString: on anything but a number). */
const TIME_OF_DAY_METHODS = new Set([
  "toLocaleTimeString", "toString", "toTimeString", "toUTCString", "toGMTString",
  "getHours", "getMinutes", "getSeconds", "getMilliseconds", "getUTCHours", "getUTCMinutes", "getUTCSeconds", "getUTCMilliseconds",
]);
/** The shared functions that take a time as the API sent it. */
const API_TIME_TAKERS = new Set(["formatDateTime", "apiDateTimeToIndiaInput"]);
/** A date-only value read at a fixed time of the browser's day, as formatDateOnly does: `${value}T00:00:00`. */
const FIXED_TIME_OF_DAY = /^T\d{2}:\d{2}(?::\d{2})?$/;
const ZONE_PATTERN = /\[(?:\+\\?-|\\?-\+)\]\\d/;
const ZONE_WRITTEN_OUT = /^(?:[Zz]|[+-]\d{2}:?\d{2})$/;
const ZONE_AFTER_A_VALUE = /^(?:[Zz]|[+-]\d{2}:?\d{2})(?![\w:])/;

type Finding = { line: number; what: string };

/** The frontend's own compiler settings and source files (tsconfig.json). */
function frontendProject(): { options: ts.CompilerOptions; fileNames: string[] } {
  const config = ts.readConfigFile(join(FRONTEND, "tsconfig.json"), ts.sys.readFile);
  const parsed = ts.parseJsonConfigFileContent(config.config, ts.sys, FRONTEND);
  return { options: { ...parsed.options, noEmit: true }, fileNames: parsed.fileNames };
}

/**
 * What in a source file reads an API time or shows a time of day, as only the shared time modules may.
 *
 * Reading: every way of reading a time from text ends in a Date made from a string, so that is what is refused - a
 * `new Date(...)` given a string (or anything not shown to be a number or a Date), `Date.parse`, and readApiDateTime
 * itself - whatever the code did about the zone first. Allowed: now (`new Date()`, and a string made from it), a
 * number or a Date, and a date-only value read at a fixed time of day. Text a page prepares itself cannot reach the
 * shared functions either: formatDateTime and apiDateTimeToIndiaInput are only called directly, given a record's field.
 * Showing: a Date's time of day by any method, and Intl.DateTimeFormat or toLocaleDateString given time-of-day options.
 * The zone patterns and zone strings the old copies used are reported too, as an early sign.
 */
function ownTimeHandling(file: ts.SourceFile, checker: ts.TypeChecker): Finding[] {
  const found: Finding[] = [];
  const report = (node: ts.Node, what: string) =>
    found.push({ line: file.getLineAndCharacterOfPosition(node.getStart(file)).line + 1, what });
  const strip = (node: ts.Expression): ts.Expression => {
    let inner = node;
    while (ts.isParenthesizedExpression(inner) || ts.isAsExpression(inner) || ts.isSatisfiesExpression(inner) || ts.isNonNullExpression(inner) || ts.isTypeAssertionExpression(inner)) {
      inner = inner.expression;
    }
    return inner;
  };
  const symbolOf = (node: ts.Node) => {
    const symbol = checker.getSymbolAtLocation(node);
    return symbol && symbol.flags & ts.SymbolFlags.Alias ? checker.getAliasedSymbol(symbol) : symbol;
  };
  const parts = (type: ts.Type) => {
    const solid = checker.getNonNullableType(type);
    return solid.isUnion() ? solid.types : [solid];
  };
  const isNumber = (type: ts.Type) => parts(type).every((part) => (part.flags & (ts.TypeFlags.NumberLike | ts.TypeFlags.BigIntLike)) !== 0);
  const isDate = (type: ts.Type) => parts(type).some((part) => part.getSymbol()?.getName() === "Date");
  const isNumberOrDate = (type: ts.Type) =>
    parts(type).every((part) => (part.flags & (ts.TypeFlags.NumberLike | ts.TypeFlags.BigIntLike)) !== 0 || part.getSymbol()?.getName() === "Date");
  const typeName = (node: ts.Expression) => checker.typeToString(checker.getTypeAtLocation(node));
  const isDateConstructor = (node: ts.Expression) => typeName(node) === "DateConstructor";
  const isNow = (node: ts.Expression) => {
    const inner = strip(node);
    return ts.isNewExpression(inner) && isDateConstructor(inner.expression) && !inner.arguments?.length;
  };
  // A string made from now, as allocationState.ts finds India's date: new Date(new Date().toLocaleString(...)).
  const madeFromNow = (node: ts.Expression) => {
    let inner = strip(node);
    while (ts.isCallExpression(inner) || ts.isPropertyAccessExpression(inner) || ts.isElementAccessExpression(inner)) inner = strip(inner.expression);
    return isNow(inner);
  };
  const dateOnlyAtAFixedTime = (node: ts.Expression) => {
    const inner = strip(node);
    return ts.isTemplateExpression(inner) && inner.head.text === "" && inner.templateSpans.length === 1 && FIXED_TIME_OF_DAY.test(inner.templateSpans[0].literal.text);
  };
  const calledMethod = (call: ts.CallExpression) => {
    const callee = strip(call.expression);
    if (ts.isPropertyAccessExpression(callee)) return { name: callee.name.text, receiver: callee.expression, at: callee.name };
    if (ts.isElementAccessExpression(callee) && ts.isStringLiteralLike(callee.argumentExpression)) {
      return { name: callee.argumentExpression.text, receiver: callee.expression, at: callee.argumentExpression };
    }
    return undefined;
  };
  // The options' own properties where the code shows them (an object literal, or a constant holding one); otherwise
  // what their type allows. Options that cannot be read at all count as showing a time of day.
  const literalOptions = (node: ts.Expression): ts.ObjectLiteralExpression | undefined => {
    const inner = strip(node);
    if (ts.isObjectLiteralExpression(inner)) return inner;
    const declaration = ts.isIdentifier(inner) ? symbolOf(inner)?.valueDeclaration : undefined;
    if (declaration && ts.isVariableDeclaration(declaration) && declaration.initializer && ts.getCombinedNodeFlags(declaration) & ts.NodeFlags.Const) {
      return literalOptions(declaration.initializer);
    }
    return undefined;
  };
  const showsTimeOfDay = (options: ts.Expression | undefined): boolean => {
    if (!options) return false;
    const literal = literalOptions(options);
    if (literal) {
      return literal.properties.some((property) => {
        if (ts.isSpreadAssignment(property)) return showsTimeOfDay(property.expression);
        const name = property.name;
        if (!name) return true;
        if (ts.isComputedPropertyName(name)) return !ts.isStringLiteralLike(name.expression) || TIME_OF_DAY_OPTIONS.has(name.expression.text);
        return ts.isPrivateIdentifier(name) ? false : TIME_OF_DAY_OPTIONS.has(name.text);
      });
    }
    const type = checker.getTypeAtLocation(options);
    if (type.flags & (ts.TypeFlags.Any | ts.TypeFlags.Unknown)) return true;
    return checker.getPropertiesOfType(type).some((property) => TIME_OF_DAY_OPTIONS.has(property.getName()));
  };
  const isDateTimeFormat = (callee: ts.Expression) => typeName(callee).includes("DateTimeFormatConstructor");
  // What formatDateTime is given is a record's field as the API sent it (`row.created_at`, `items[0].at`), or nothing -
  // never text the page has built, which could carry a zone of its own making.
  const readStraightFromData = (node: ts.Expression | undefined): boolean => {
    if (!node) return true;
    const inner = strip(node);
    if (inner.kind === ts.SyntaxKind.NullKeyword || (ts.isIdentifier(inner) && inner.text === "undefined")) return true;
    if (ts.isConditionalExpression(inner)) return readStraightFromData(inner.whenTrue) && readStraightFromData(inner.whenFalse);
    const operator = ts.isBinaryExpression(inner) ? inner.operatorToken.kind : undefined;
    if (ts.isBinaryExpression(inner) && (operator === ts.SyntaxKind.QuestionQuestionToken || operator === ts.SyntaxKind.BarBarToken)) {
      return readStraightFromData(inner.left) && readStraightFromData(inner.right);
    }
    if (!ts.isPropertyAccessExpression(inner) && !ts.isElementAccessExpression(inner)) return false;
    let root: ts.Expression = inner;
    while (ts.isPropertyAccessExpression(root) || ts.isElementAccessExpression(root)) root = strip(root.expression);
    return ts.isIdentifier(root) || root.kind === ts.SyntaxKind.ThisKeyword;
  };
  // A name being declared or imported, rather than used: `function formatDateTime`, `import { formatDateTime }`.
  const isDeclaredOrImported = (node: ts.Node) => {
    const parent = node.parent;
    if (ts.isImportSpecifier(parent) || ts.isExportSpecifier(parent) || ts.isImportClause(parent) || ts.isNamespaceImport(parent)) return true;
    if (ts.isTypeQueryNode(parent)) return true;
    const declares = ts.isFunctionDeclaration(parent) || ts.isVariableDeclaration(parent) || ts.isParameter(parent) || ts.isBindingElement(parent)
      || ts.isPropertyAssignment(parent) || ts.isMethodDeclaration(parent) || ts.isPropertyDeclaration(parent) || ts.isPropertySignature(parent);
    return declares && (parent as ts.NamedDeclaration).name === node;
  };
  // The call a name is the callee of - `name(...)`, `module.name(...)`, `module["name"](...)`, `(name)(...)` - if any.
  const directCall = (node: ts.Node): ts.CallExpression | undefined => {
    let callee: ts.Node = node;
    if ((ts.isPropertyAccessExpression(node.parent) && node.parent.name === node) || (ts.isElementAccessExpression(node.parent) && node.parent.argumentExpression === node)) {
      callee = node.parent;
    }
    while (ts.isParenthesizedExpression(callee.parent) || ts.isNonNullExpression(callee.parent) || ts.isAsExpression(callee.parent) || ts.isSatisfiesExpression(callee.parent)) {
      callee = callee.parent;
    }
    return ts.isCallExpression(callee.parent) && callee.parent.expression === callee ? callee.parent : undefined;
  };

  const visit = (node: ts.Node): void => {
    // Reading.
    if (ts.isNewExpression(node) && isDateConstructor(node.expression)) {
      const args = node.arguments ?? [];
      const first = args[0];
      if (args.length === 1 && first && !isNumberOrDate(checker.getTypeAtLocation(first)) && !dateOnlyAtAFixedTime(first) && !madeFromNow(first)) {
        report(node, "makes a Date from a string");
      }
    }
    // The shared functions: readApiDateTime not at all; the ones that take an API time only called directly, and given a
    // record's field. Every use of the name counts, however it was imported or renamed.
    const isReference = ts.isIdentifier(node) || (ts.isStringLiteralLike(node) && ts.isElementAccessExpression(node.parent) && node.parent.argumentExpression === node);
    const shared = isReference && !isDeclaredOrImported(node) ? symbolOf(node)?.getName() : undefined;
    if (shared === "readApiDateTime") report(node, "uses readApiDateTime");
    if (shared && API_TIME_TAKERS.has(shared)) {
      const call = directCall(node);
      if (!call) report(node, `uses ${shared} other than by calling it`);
      else if (!readStraightFromData(call.arguments[0])) report(call, `gives ${shared} text it built`);
    }
    if (ts.isCallExpression(node)) {
      const method = calledMethod(node);
      if (method?.name === "parse" && isDateConstructor(method.receiver)) report(node, "Date.parse");
      // Showing.
      if (method && !isNow(method.receiver)) {
        const type = checker.getTypeAtLocation(method.receiver);
        const shows = method.name === "toLocaleString" ? !isNumber(type) : TIME_OF_DAY_METHODS.has(method.name) && isDate(type);
        if (shows) report(node, `${method.name} on ${checker.typeToString(type)}`);
      }
      if (method?.name === "toLocaleDateString" && showsTimeOfDay(node.arguments[1])) report(node, "toLocaleDateString with a time of day");
    }
    const options = (ts.isNewExpression(node) || ts.isCallExpression(node)) && node.arguments?.[1];
    if (options && isDateTimeFormat((node as ts.NewExpression | ts.CallExpression).expression) && showsTimeOfDay(options)) {
      report(node, "Intl.DateTimeFormat with a time of day");
    }
    // Early signs: a pattern for a time's zone, or a zone written into a string.
    if (ts.isRegularExpressionLiteral(node) || ts.isStringLiteralLike(node)) {
      if (ZONE_PATTERN.test(node.text)) report(node, "looks for a time's zone");
      else if (ts.isStringLiteralLike(node) && ZONE_WRITTEN_OUT.test(node.text)) report(node, "writes a zone out");
    }
    if ((ts.isTemplateMiddle(node) || ts.isTemplateTail(node)) && ZONE_AFTER_A_VALUE.test(node.text)) report(node, "adds a zone to a time");
    ts.forEachChild(node, visit);
  };
  visit(file);
  return found;
}

// Each snippet is its own module, type-checked like the source, with these names in scope.
const SNIPPET_PRELUDE = [
  "declare const value: string;",
  "declare const date: Date;",
  "declare const count: number;",
  "declare function locale(): string;",
  "declare function formatDateTime(value: string | null | undefined): string;",
  "declare function readApiDateTime(value: string | null | undefined): Date | null;",
  "declare function apiDateTimeToIndiaInput(value: string | null | undefined): string;",
  "declare const row: { created_at: string | null; items: { at: string }[] } | undefined;",
  "export {};",
].join("\n");

/** The findings for each snippet, checked together in one program. */
function findingsFor(snippets: string[]): string[][] {
  const { options } = frontendProject();
  const host = ts.createCompilerHost(options);
  const files = new Map(snippets.map((text, i) => [join(SRC, `n06-snippet-${i}.ts`).replace(/\\/g, "/"), `${SNIPPET_PRELUDE}\n${text}\n`]));
  const { getSourceFile, fileExists, readFile } = host;
  host.getSourceFile = (name, language, ...rest) =>
    files.has(name) ? ts.createSourceFile(name, files.get(name) as string, language, true) : getSourceFile.call(host, name, language, ...rest);
  host.fileExists = (name) => files.has(name) || fileExists.call(host, name);
  host.readFile = (name) => files.get(name) ?? readFile.call(host, name);
  const program = ts.createProgram([...files.keys()], options, host);
  const checker = program.getTypeChecker();
  return [...files.keys()].map((name) => ownTimeHandling(program.getSourceFile(name) as ts.SourceFile, checker).map((found) => found.what));
}

describe("formatDateTime", () => {
  it("reads a time without a zone as UTC and shows it in India's time", () => {
    // 10:00 UTC is 15:30 in India, the same day.
    expect(formatDateTime("2026-10-04T10:00:00")).toBe(formatDateTime("2026-10-04T10:00:00Z"));
    expect(formatDateTime("2026-10-04T10:00:00")).toMatch(/04 Oct 2026, 0?3:30\s?pm/i);
    expect(formatDateTime("2026-10-04T10:00:00.123456")).toMatch(/0?3:30\s?pm/i);
  });

  it("keeps a zone it is given", () => {
    expect(formatDateTime("2026-10-04T15:30:00+05:30")).toBe(formatDateTime("2026-10-04T10:00:00Z"));
  });

  it("moves to the next day in India when UTC is still on the day before", () => {
    expect(formatDateTime("2026-10-04T20:00:00")).toMatch(/05 Oct 2026, 0?1:30\s?am/i);
  });

  it("shows a dash for nothing and leaves text it cannot read as it is", () => {
    expect(formatDateTime(null)).toBe("-");
    expect(formatDateTime(undefined)).toBe("-");
    expect(formatDateTime("")).toBe("-");
    expect(formatDateTime("not a date")).toBe("not a date");
    // Blank text is shown as it came, as each page's own copy did.
    expect(formatDateTime(" ")).toBe(" ");
  });
});

describe("readApiDateTime", () => {
  it("reads a time without a zone as UTC, keeps one with a zone, and gives null for nothing", () => {
    expect(readApiDateTime(" 2026-10-04T10:00:00 ")?.toISOString()).toBe("2026-10-04T10:00:00.000Z");
    expect(readApiDateTime("2026-10-04T15:30:00+05:30")?.toISOString()).toBe("2026-10-04T10:00:00.000Z");
    expect(readApiDateTime(null)).toBeNull();
    expect(readApiDateTime(" ")).toBeNull();
    expect(readApiDateTime("not a date")).toBeNull();
  });
});

describe("date-and-time display", () => {
  it("no page formats a time with a bare toLocaleString(), which uses the browser's zone", () => {
    const files = sourceFiles(SRC);
    expect(files.length).toBeGreaterThan(50);
    const bare = files.filter((file) => /\.toLocaleString\(\s*\)/.test(readFileSync(file, "utf-8"))).map((file) => relative(SRC, file));
    expect(bare).toEqual([]);
  });

  it("finds each way a page could read an API time or show a time of day itself, and leaves the rest alone", { timeout: 120_000 }, () => {
    const cases: [string, string[]][] = [
      // Reading: the copy nine pages and the Documents panel kept, and other ways of writing it. Each ends in a Date
      // made from a string, which is what the guard refuses; the zone patterns are reported too, as early signs.
      [
        "const zoned = /(?:Z|[+-]\\d{2}:?\\d{2})$/i.test(value); const moment = new Date(zoned ? value : `${value}Z`);",
        ["looks for a time's zone", "makes a Date from a string", "adds a zone to a time"],
      ],
      [
        'const normalized = /(?:Z$|\\+\\d{2}:?\\d{2}$|-\\d{2}:?\\d{2}$)/i.test(value) ? value : value.replace(/$/, "$&Z"); const moment = new Date(normalized);',
        ["makes a Date from a string"],
      ],
      ['const moment = new Date(value.concat("Z"));', ["makes a Date from a string", "writes a zone out"]],
      ["const moment = new Date(value as any);", ["makes a Date from a string"]],
      ["const moment = Date.parse(value);", ["Date.parse"]],
      ["const moment = readApiDateTime(value); const read = readApiDateTime;", ["uses readApiDateTime", "uses readApiDateTime"]],
      // Text the page built handed to the shared formatter, however the zone was added.
      [
        'const normalized = /(?:Z$|\\+\\d{2}:?\\d{2}$|-\\d{2}:?\\d{2}$)/i.test(value) ? value : value.replace(/$/, "$&Z"); const shown = formatDateTime(normalized);',
        ["gives formatDateTime text it built"],
      ],
      ["const shown = formatDateTime(`${value}Z`);", ["gives formatDateTime text it built", "adds a zone to a time"]],
      ["const shown = formatDateTime(value.trim()) + formatDateTime(row?.created_at ?? value);", ["gives formatDateTime text it built", "gives formatDateTime text it built"]],
      ["const box = apiDateTimeToIndiaInput(`${value}Z`);", ["gives apiDateTimeToIndiaInput text it built", "adds a zone to a time"]],
      // ...or by reaching the shared formatter other than by a direct call.
      ['const shown = formatDateTime.call(undefined, row?.created_at + "+" + "05:30");', ["uses formatDateTime other than by calling it"]],
      [
        "const show = formatDateTime; const shown = show(value) + [value].map(formatDateTime).join() + formatDateTime.apply(null, [value]) + formatDateTime.bind(null)(value);",
        [
          "uses formatDateTime other than by calling it",
          "uses formatDateTime other than by calling it",
          "uses formatDateTime other than by calling it",
          "uses formatDateTime other than by calling it",
        ],
      ],
      ["const tools = { show: formatDateTime }; const shown = tools.show(value);", ["uses formatDateTime other than by calling it"]],
      ["const zoned = /[+\\-]\\d{2}:\\d{2}$/.test(value);", ["looks for a time's zone"]],
      ['const zoned = new RegExp("[+-]\\\\d{2}$").test(value);', ["looks for a time's zone"]],
      ["const normalized = `${value}+00:00`;", ["adds a zone to a time"]],
      ['const normalized = value + "Z";', ["writes a zone out"]],
      // Showing a time of day: the pages' formatter, the dashboard's, and other ways.
      ['date.toLocaleString("en-IN", { timeZone: "Asia/Kolkata", hour: "2-digit", minute: "2-digit" });', ["toLocaleString on Date"]],
      ['new Date(value).toLocaleString("en-IN", { timeZone: "Asia/Kolkata" });', ["toLocaleString on Date", "makes a Date from a string"]],
      ['new Date(value)["toLocaleString"]("en-IN", { timeZone: "Asia/Kolkata" });', ["toLocaleString on Date", "makes a Date from a string"]],
      ['date.toLocaleString("en-IN", { useGrouping: false });', ["toLocaleString on Date"]],
      ['const what: any = value; what.toLocaleString("en-IN");', ["toLocaleString on any"]],
      ['date.toLocaleTimeString("en-IN");', ["toLocaleTimeString on Date"]],
      ["const text = date.toTimeString() + date.getHours();", ["toTimeString on Date", "getHours on Date"]],
      [
        'const text = date.toUTCString() + date.getUTCHours() + date["getUTCMinutes"]();',
        ["toUTCString on Date", "getUTCHours on Date", "getUTCMinutes on Date"],
      ],
      ['new Intl.DateTimeFormat("en-IN", { "hour": "2-digit", "minute": "2-digit" }).format(date);', ["Intl.DateTimeFormat with a time of day"]],
      ['Intl.DateTimeFormat("en-IN", { second: "2-digit" }).format(date);', ["Intl.DateTimeFormat with a time of day"]],
      ['const options = { dayPeriod: "short" } as const; new Intl.DateTimeFormat("en-IN", options).format(date);', ["Intl.DateTimeFormat with a time of day"]],
      ['const Format = Intl.DateTimeFormat; new Format("en-IN", { ...{ fractionalSecondDigits: 3 } }).format(date);', ["Intl.DateTimeFormat with a time of day"]],
      // Options it cannot see count as a time of day when their type allows one.
      [
        'function show(options: Intl.DateTimeFormatOptions) { return new Intl.DateTimeFormat("en-IN", options).format(date); }',
        ["Intl.DateTimeFormat with a time of day"],
      ],
      ['date.toLocaleDateString("en-IN", { timeStyle: "short" });', ["toLocaleDateString with a time of day"]],
      ['const hourOption = { hour: "numeric" } as const; date.toLocaleDateString("en-IN", { ...hourOption });', ["toLocaleDateString with a time of day"]],
      // Left alone: numbers, dates without a time, India's today, calendar dates, and the shared formatter.
      ['count.toLocaleString("en-IN");', []],
      ['count.toLocaleString("en-IN", { maximumFractionDigits: 2 });', []],
      ['count.toLocaleString(locale(), { maximumFractionDigits: 2 });', []],
      ['new Date(`${value}T00:00:00`).toLocaleDateString("en-IN", { year: "numeric", month: "short", day: "2-digit" });', []],
      ["const expired = new Date(`${value}T23:59:59`) < new Date();", []],
      [
        'const options: Intl.DateTimeFormatOptions = { year: "numeric", month: "short", day: "2-digit" }; new Intl.DateTimeFormat("en-IN", options).format(date);',
        [],
      ],
      [
        'const india: Intl.DateTimeFormatOptions = { timeZone: "Asia/Kolkata", year: "numeric", month: "2-digit", day: "2-digit" }; new Intl.DateTimeFormat("en-CA", india).format(new Date());',
        [],
      ],
      ['new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Kolkata" }).format(new Date());', []],
      ['const today = new Date(new Date().toLocaleString("en-US", { timeZone: "Asia/Kolkata" })); today.setDate(today.getDate() + 1);', []],
      ["const next = new Date(Date.UTC(2026, 9, 12)).toISOString().slice(0, 10); const later = new Date(date.getTime() + 1000); const same = new Date(date);", []],
      [
        "const shown = formatDateTime(row?.created_at) + formatDateTime(row!.items[0].at) + formatDateTime(row ? row.created_at : null) + (formatDateTime)(null); const box = apiDateTimeToIndiaInput(row?.created_at); const id = value.toString() + count.toString();",
        [],
      ],
    ];
    expect(findingsFor(cases.map(([snippet]) => snippet))).toEqual(cases.map(([, expected]) => expected));
  });

  it("only the shared time modules read an API time or show a time of day", { timeout: 120_000 }, () => {
    const { options, fileNames } = frontendProject();
    const program = ts.createProgram(fileNames, options);
    const checker = program.getTypeChecker();
    const sources = program
      .getSourceFiles()
      .filter((file) => !file.isDeclarationFile && !/\.test\.tsx?$/.test(file.fileName) && relative(SRC, file.fileName).split(/[\\/]/)[0] !== "..");
    expect(sources.length).toBeGreaterThan(50);
    expect(sources.filter((file) => SHARED.includes(relative(SRC, file.fileName)))).toHaveLength(SHARED.length);
    // The check still finds the shared module's own reading and formatting, so it is looking at real source.
    const display = sources.find((file) => relative(SRC, file.fileName) === SHARED[0]) as ts.SourceFile;
    expect(ownTimeHandling(display, checker).map((found) => found.what)).toEqual(
      expect.arrayContaining(["makes a Date from a string", "looks for a time's zone", "adds a zone to a time", "toLocaleString on Date"]),
    );
    const own = sources
      .filter((file) => !SHARED.includes(relative(SRC, file.fileName)))
      .flatMap((file) => ownTimeHandling(file, checker).map((found) => `${relative(SRC, file.fileName)}:${found.line}: ${found.what}`));
    expect(own).toEqual([]);
  });
});
