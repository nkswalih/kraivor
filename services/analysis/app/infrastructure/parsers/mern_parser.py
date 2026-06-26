import re

from app.domain.contracts.parser import (
    AbstractParser,
    ParsedClass,
    ParsedFile,
    ParsedFunction,
    ParsedImport,
    ParsedRoute,
)


class MernParser(AbstractParser):
    language: str = "javascript"
    supported_extensions: list[str] = [".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"]

    # ---- JS Core ----
    _FUNC_DECL = re.compile(
        r"(?:export\s+)?(?:async\s+)?function\s+\*?\s*(\w+)\s*\("
    )
    _ARROW_FUNC = re.compile(
        r"(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?(?:\([^)]*\)|\w+)\s*=>"
    )
    _CLASS_DECL = re.compile(
        r"(?:export\s+)?(?:abstract\s+)?class\s+(\w+)(?:\s+extends\s+(\w+))?(?:\s+implements\s+(\w+(?:\s*,\s*\w+)*))?"
    )
    _IMPORT_DEFAULT = re.compile(
        r"import\s+(\w+)\s+from\s+[\"']([^\"']+)[\"']"
    )
    _IMPORT_NAMED = re.compile(
        r"import\s+\{\s*([^}]+)\s*\}\s+from\s+[\"']([^\"']+)[\"']"
    )
    _IMPORT_STAR = re.compile(
        r"import\s+\*\s+as\s+(\w+)\s+from\s+[\"']([^\"']+)[\"']"
    )
    _IMPORT_SIDE_EFFECT = re.compile(
        r"import\s+[\"']([^\"']+)[\"']"
    )
    _REQUIRE = re.compile(
        r"(?:const|let|var)\s+(?:(\w+)|\{\s*([^}]+)\s*\})\s*=\s*require\([\"']([^\"']+)[\"']\)"
    )
    _EXPORT_DEFAULT = re.compile(r"export\s+default\s+(\w+)")
    _EXPORT_NAMED = re.compile(r"export\s+\{\s*([^}]+)\s*\}")
    _EXPORT_DECL = re.compile(
        r"export\s+(const|let|var|function|class|interface|type|enum)\s+(\w+)"
    )
    _EXPORT_MODULE = re.compile(r"module\.exports\s*=")
    _EXPORT_NAMED_ASSIGN = re.compile(r"exports\.(\w+)\s*=")
    _EXPRESS_ROUTE = re.compile(
        r"(?:app|router|route|server|fastify|api)\.(get|post|put|delete|patch|options|all|head)\([\"']([^\"']+)[\"']"
    )
    _COMPLEXITY_KEYWORDS = re.compile(
        r"\b(?:if|for|while|switch|case|catch)\b"
    )
    _JSX_TAG = re.compile(r"<[A-Z][\w.]*(?:\s+\w+\s*=|/>)|</[A-Z]")

    # ---- TS Core ----
    _INTERFACE_DECL = re.compile(
        r"(?:export\s+)?(?:abstract\s+)?interface\s+(\w+)(?:\s+extends\s+(\w+(?:\s*,\s*\w+)*))?"
    )
    _ENUM_DECL = re.compile(
        r"(?:export\s+)?(?:const\s+)?enum\s+(\w+)"
    )
    _TYPE_ALIAS = re.compile(
        r"(?:export\s+)?type\s+(\w+)(?:<[^>]+>)?\s*="
    )
    _DECORATOR = re.compile(r"@(\w+(?:\.\w+)?)\s*(?:\([^)]*\))?")
    _NESTJS_ROUTE = re.compile(
        r"@(?:Get|Post|Put|Delete|Patch|Options|Head|All)(?:\([\"']([^\"']+)[\"']\)|\(\))"
    )

    # ---- MERN: Mongoose ----
    _MONGOOSE_SCHEMA = re.compile(
        r"(?:const|let|var)\s+(\w+Schema)\s*=\s*new\s+(?:mongoose\.)?Schema\s*\("
    )
    _MONGOOSE_MODEL = re.compile(
        r"mongoose\.model\([\"'](\w+)[\"']\s*,\s*(\w+)"
    )

    # ---- MERN: Express ----
    _EXPRESS_MIDDLEWARE = re.compile(
        r"(?:app|router)\.use\s*\(([^)]+)\)"
    )
    _EXPRESS_ROUTER = re.compile(
        r"(?:express|require\([\"']express[\"']\))\.Router\s*\(\)"
    )
    _EXPRESS_ERROR_MW = re.compile(
        r"function\s+\w*\s*\(err\s*,\s*req\s*,\s*res\s*,\s*next"
    )

    # ---- MERN: React ----
    _REACT_HOOKS = re.compile(
        r"(?:useState|useEffect|useContext|useReducer|useMemo|useCallback|useRef|useLayoutEffect|useImperativeHandle|useDebugValue|useTransition|useDeferredValue|useId)\s*\("
    )
    _CUSTOM_HOOK = re.compile(
        r"(?:export\s+)?(?:const|let|var|function)\s+(use[A-Z]\w+)\s*"
    )
    _REACT_IMPORT = re.compile(
        r"from\s+[\"']react[\"']"
    )

    # ---- MERN: Node.js ----
    _CJS_INDICATOR = re.compile(r"(?:module\.exports|exports\.|require\s*\()")
    _PROCESS_ENV = re.compile(r"process\.env\.(\w+)")

    _COMMON_FS_PATTERNS = re.compile(
        r"(?:fs|fs/promises)\.(?:readFile|writeFile|readdir|mkdir|exists|stat|unlink|readFileSync|writeFileSync)"
    )

    async def parse(self, file_path: str, content: str) -> ParsedFile:
        parsed = ParsedFile(
            path=file_path,
            language=self.language,
            content=content,
            size_bytes=len(content.encode("utf-8")),
            lines_count=content.count("\n") + 1,
        )

        # JS core extraction
        self._extract_functions(content, parsed)
        self._extract_classes(content, parsed)
        self._extract_imports(content, parsed)
        self._extract_exports(content, parsed)
        self._extract_routes(content, parsed)
        self._detect_jsx(content, parsed)

        # TS core extraction
        self._extract_interfaces(content, parsed)
        self._extract_enums(content, parsed)
        self._extract_type_aliases(content, parsed)
        self._extract_decorators(content, parsed)
        self._extract_nestjs_routes(content, parsed)

        # MERN-specific extraction
        self._extract_mongoose(content, parsed)
        self._extract_express(content, parsed)
        self._extract_react(content, parsed)
        self._extract_nodejs(content, parsed)

        return parsed

    # ========== JS Core ==========

    def _extract_functions(self, content: str, parsed: ParsedFile) -> None:
        for match in self._FUNC_DECL.finditer(content):
            name = match.group(1)
            line_start = content[: match.start()].count("\n") + 1
            body = self._extract_body(content, match.end())
            line_end = line_start + body.count("\n")
            parsed.functions.append(
                ParsedFunction(
                    name=name,
                    line_start=line_start,
                    line_end=line_end,
                    complexity=self._calculate_complexity(body),
                )
            )

        for match in self._ARROW_FUNC.finditer(content):
            name = match.group(1)
            line_start = content[: match.start()].count("\n") + 1
            parsed.functions.append(
                ParsedFunction(name=name, line_start=line_start, line_end=line_start, complexity=1)
            )

    def _extract_classes(self, content: str, parsed: ParsedFile) -> None:
        for match in self._CLASS_DECL.finditer(content):
            name = match.group(1)
            bases = []
            if match.group(2):
                bases.append(match.group(2))
            if match.group(3):
                bases.extend(b.strip() for b in match.group(3).split(","))
            line_start = content[: match.start()].count("\n") + 1

            body_start = content.find("{", match.end())
            if body_start == -1:
                continue
            body_end = self._find_matching_brace(content, body_start)
            body = content[body_start + 1 : body_end]
            line_end = content[:body_end].count("\n") + 1

            method_names = []
            clean_body = re.sub(r"^\s*@\w+(?:\([^)]*\))?\s*$", "", body, flags=re.MULTILINE)
            no_decorator_body = re.sub(r"@\w+(?:\([^)]*\))?", "", clean_body)
            for m in re.finditer(
                r"^\s*(?:(?:public|private|protected|static|readonly|async)\s+)*(\w+)\s*\([^)]*\)\s*(?:\{|\:)",
                no_decorator_body,
                re.MULTILINE,
            ):
                method_name = m.group(1)
                if method_name not in {"if", "for", "while", "switch", "catch", "with"}:
                    method_names.append(method_name)

            parsed.classes.append(
                ParsedClass(
                    name=name,
                    line_start=line_start,
                    line_end=line_end,
                    bases=bases,
                    methods=method_names,
                )
            )

    def _extract_imports(self, content: str, parsed: ParsedFile) -> None:
        for match in self._IMPORT_DEFAULT.finditer(content):
            name, source = match.group(1), match.group(2)
            line = content[: match.start()].count("\n") + 1
            parsed.imports.append(
                ParsedImport(name=name, source=source, line=line, is_from=True)
            )

        for match in self._IMPORT_NAMED.finditer(content):
            names = [n.strip().split(" as ")[0].strip() for n in match.group(1).split(",")]
            source = match.group(2)
            line = content[: match.start()].count("\n") + 1
            for name in names:
                if name:
                    parsed.imports.append(
                        ParsedImport(name=name, source=source, line=line, is_from=True)
                    )

        for match in self._IMPORT_STAR.finditer(content):
            name, source = match.group(1), match.group(2)
            line = content[: match.start()].count("\n") + 1
            parsed.imports.append(
                ParsedImport(name=f"* as {name}", source=source, line=line, is_from=True)
            )

        for match in self._IMPORT_SIDE_EFFECT.finditer(content):
            source = match.group(1)
            line = content[: match.start()].count("\n") + 1
            parsed.imports.append(
                ParsedImport(name="", source=source, line=line, is_from=True)
            )

        for match in self._REQUIRE.finditer(content):
            source = match.group(3)
            line = content[: match.start()].count("\n") + 1
            if match.group(1):
                parsed.imports.append(
                    ParsedImport(name=match.group(1), source=source, line=line, is_from=False)
                )
            elif match.group(2):
                names = [n.strip().split(":")[0].strip() for n in match.group(2).split(",")]
                for name in names:
                    parsed.imports.append(
                        ParsedImport(name=name, source=source, line=line, is_from=False)
                    )

        for match in re.finditer(
            r"import\s+type\s+\{\s*([^}]+)\s*\}\s+from\s+[\"']([^\"']+)[\"']", content
        ):
            names = [n.strip() for n in match.group(1).split(",")]
            source = match.group(2)
            line = content[: match.start()].count("\n") + 1
            for name in names:
                if name:
                    parsed.imports.append(
                        ParsedImport(name=name, source=source, line=line, is_from=True)
                    )

    def _extract_exports(self, content: str, parsed: ParsedFile) -> None:
        for match in self._EXPORT_DEFAULT.finditer(content):
            parsed.exports.append(f"default {match.group(1)}")
        for match in self._EXPORT_NAMED.finditer(content):
            names = [n.strip() for n in match.group(1).split(",")]
            parsed.exports.extend(names)
        for match in self._EXPORT_DECL.finditer(content):
            parsed.exports.append(match.group(2))
        for _match in self._EXPORT_MODULE.finditer(content):
            parsed.exports.append("module.exports")
        for match in self._EXPORT_NAMED_ASSIGN.finditer(content):
            parsed.exports.append(match.group(1))

    def _extract_routes(self, content: str, parsed: ParsedFile) -> None:
        for match in self._EXPRESS_ROUTE.finditer(content):
            method, path = match.group(1).upper(), match.group(2)
            line_start = content[: match.start()].count("\n") + 1
            parsed.routes.append(
                ParsedRoute(path=path, method=method, handler_name="", line_start=line_start, line_end=line_start)
            )

    def _detect_jsx(self, content: str, parsed: ParsedFile) -> None:
        if self._JSX_TAG.search(content):
            parsed.ast_data["jsx"] = True

    # ========== TS Core ==========

    def _extract_interfaces(self, content: str, parsed: ParsedFile) -> None:
        for match in self._INTERFACE_DECL.finditer(content):
            name = match.group(1)
            bases: list[str] = []
            if match.group(2):
                bases.extend(b.strip() for b in match.group(2).split(","))
            line_start = content[: match.start()].count("\n") + 1
            body_start = content.find("{", match.end())
            if body_start == -1:
                continue
            body_end = self._find_matching_brace(content, body_start)
            line_end = content[:body_end].count("\n") + 1
            properties = []
            for m in re.finditer(r"^\s*(\w+)\??\s*(?:\?)?\s*:", content[body_start + 1 : body_end], re.MULTILINE):
                properties.append(m.group(1))
            parsed.classes.append(
                ParsedClass(name=name, line_start=line_start, line_end=line_end, bases=bases, decorators=["interface"], methods=properties)
            )

    def _extract_enums(self, content: str, parsed: ParsedFile) -> None:
        for match in self._ENUM_DECL.finditer(content):
            name = match.group(1)
            line_start = content[: match.start()].count("\n") + 1
            body_start = content.find("{", match.end())
            if body_start == -1:
                continue
            body_end = self._find_matching_brace(content, body_start)
            line_end = content[:body_end].count("\n") + 1
            members = []
            for m in re.finditer(r"^\s*(\w+)", content[body_start + 1 : body_end], re.MULTILINE):
                members.append(m.group(1))
            parsed.classes.append(
                ParsedClass(name=name, line_start=line_start, line_end=line_end, decorators=["enum"], methods=members)
            )

    def _extract_type_aliases(self, content: str, parsed: ParsedFile) -> None:
        for match in self._TYPE_ALIAS.finditer(content):
            parsed.exports.append(f"type {match.group(1)}")

    def _extract_decorators(self, content: str, parsed: ParsedFile) -> None:
        decorators = set()
        for match in self._DECORATOR.finditer(content):
            decorators.add(match.group(1))
        if decorators:
            parsed.ast_data["decorators"] = sorted(decorators)

    def _extract_nestjs_routes(self, content: str, parsed: ParsedFile) -> None:
        for match in self._NESTJS_ROUTE.finditer(content):
            path = match.group(1) if match.group(1) else "/"
            method = match.group(0).lstrip("@").split("(")[0].upper()
            line_start = content[: match.start()].count("\n") + 1
            parsed.routes.append(
                ParsedRoute(path=path, method=method, handler_name="", line_start=line_start, line_end=line_start)
            )

    # ========== MERN: Mongoose ==========

    def _extract_mongoose(self, content: str, parsed: ParsedFile) -> None:
        schemas: list[dict] = []
        models: list[dict] = []

        for match in self._MONGOOSE_SCHEMA.finditer(content):
            schema_name = match.group(1)
            line_start = content[: match.start()].count("\n") + 1

            body_start = content.find("{", match.end())
            if body_start == -1:
                continue
            body_end = self._find_matching_brace(content, body_start)
            schema_body = content[body_start + 1 : body_end]

            fields = self._parse_mongoose_fields(schema_body)

            schemas.append({
                "name": schema_name,
                "fields": fields,
                "line_start": line_start,
            })

        for match in self._MONGOOSE_MODEL.finditer(content):
            model_name = match.group(1)
            schema_ref = match.group(2)
            line_start = content[: match.start()].count("\n") + 1
            models.append({
                "name": model_name,
                "schema": schema_ref,
                "line_start": line_start,
            })

        if schemas:
            parsed.ast_data["mongoose_schemas"] = schemas
        if models:
            parsed.ast_data["mongoose_models"] = models

    _MONGOOSE_TYPES = {
        "String", "Number", "Date", "Boolean", "Buffer", "Mixed",
        "ObjectId", "Decimal128", "Map", "BigInt",
        "Schema.Types.String", "Schema.Types.Number", "Schema.Types.Date",
        "Schema.Types.Boolean", "Schema.Types.ObjectId", "Schema.Types.Mixed",
        "Schema.Types.Buffer", "Schema.Types.Decimal128", "Schema.Types.BigInt",
        "mongoose.Schema.Types.ObjectId", "mongoose.Schema.Types.Mixed",
    }

    _FIELD_DEF_SIMPLE = re.compile(r"^\s*(\w+)\s*:\s*(String|Number|Date|Boolean|Mixed|Buffer|ObjectId|Decimal128|BigInt|Map)\s*[,\)]?\s*$", re.MULTILINE)
    _FIELD_DEF_COMPLEX = re.compile(r"^\s*(\w+)\s*:\s*\{", re.MULTILINE)
    _FIELD_DEF_ARRAY = re.compile(r"^\s*(\w+)\s*:\s*\[")

    def _parse_mongoose_fields(self, body: str) -> list[dict]:
        fields: list[dict] = []
        seen: set[str] = set()

        for match in self._FIELD_DEF_SIMPLE.finditer(body):
            name, ftype = match.group(1), match.group(2)
            if name not in seen:
                seen.add(name)
                fields.append({"name": name, "type": ftype, "constraints": {}})

        for match in self._FIELD_DEF_COMPLEX.finditer(body):
            name = match.group(1)
            if name in seen:
                continue
            seen.add(name)
            field_start = match.end() - 1
            field_end = self._find_matching_brace(body, field_start)
            field_body = body[field_start + 1 : field_end]

            ftype = "Mixed"
            constraints: dict = {}
            type_match = re.search(r"type\s*:\s*(String|Number|Date|Boolean|Mixed|Buffer|ObjectId|Decimal128|BigInt|Map|Schema\.Types\.\w+|mongoose\.Schema\.Types\.\w+)", field_body)
            if type_match:
                ftype = type_match.group(1)
            if re.search(r"required\s*:\s*true", field_body):
                constraints["required"] = True
            if re.search(r"unique\s*:\s*true", field_body):
                constraints["unique"] = True
            ref_match = re.search(r"ref\s*:\s*[\"'](\w+)[\"']", field_body)
            if ref_match:
                constraints["ref"] = ref_match.group(1)
            default_match = re.search(r"default\s*:", field_body)
            if default_match:
                constraints["has_default"] = True
            enum_match = re.search(r"enum\s*:", field_body)
            if enum_match:
                constraints["has_enum"] = True

            fields.append({"name": name, "type": ftype, "constraints": constraints})

        for match in self._FIELD_DEF_ARRAY.finditer(body):
            name = match.group(1)
            if name in seen:
                continue
            seen.add(name)
            fields.append({"name": name, "type": "Array", "constraints": {}})

        return fields

    # ========== MERN: Express ==========

    def _extract_express(self, content: str, parsed: ParsedFile) -> None:
        middlewares: list[str] = []
        for match in self._EXPRESS_MIDDLEWARE.finditer(content):
            middlewares.append(match.group(1).strip())

        if self._EXPRESS_ROUTER.search(content):
            parsed.ast_data["has_express_router"] = True

        if self._EXPRESS_ERROR_MW.search(content):
            parsed.ast_data["has_error_middleware"] = True

        if middlewares:
            parsed.ast_data["middleware_chain"] = middlewares

    # ========== MERN: React ==========

    def _extract_react(self, content: str, parsed: ParsedFile) -> None:
        has_react = bool(self._REACT_IMPORT.search(content))

        hooks: list[str] = []
        for match in self._REACT_HOOKS.finditer(content):
            hook_name = match.group(0).split("(")[0]
            if hook_name not in hooks:
                hooks.append(hook_name)

        custom_hooks: list[str] = []
        for match in self._CUSTOM_HOOK.finditer(content):
            custom_hooks.append(match.group(1))

        components: list[str] = []
        for func in parsed.functions:
            if self._JSX_TAG.search(content) or func.name[0].isupper():
                body = self._extract_body(content, content.find(func.name) + len(func.name))
                if self._JSX_TAG.search(body):
                    components.append(func.name)

        if has_react:
            parsed.ast_data["react"] = True
        if hooks:
            parsed.ast_data["react_hooks"] = hooks
        if custom_hooks:
            parsed.ast_data["custom_hooks"] = custom_hooks
        if components:
            parsed.ast_data["react_components"] = components

    # ========== MERN: Node.js ==========

    def _extract_nodejs(self, content: str, parsed: ParsedFile) -> None:
        import_count = len([i for i in parsed.imports if i.is_from])
        require_count = len([i for i in parsed.imports if not i.is_from])

        if import_count > 0 and require_count > 0:
            module_system = "mixed"
        elif import_count > 0:
            module_system = "esm"
        elif require_count > 0:
            module_system = "cjs"
        else:
            module_system = "unknown"

        parsed.ast_data["module_system"] = module_system

        env_vars: list[str] = []
        for match in self._PROCESS_ENV.finditer(content):
            env_vars.append(match.group(1))
        if env_vars:
            parsed.ast_data["env_vars"] = env_vars

        fs_calls: list[str] = []
        for match in self._COMMON_FS_PATTERNS.finditer(content):
            fs_calls.append(match.group(0))
        if fs_calls:
            parsed.ast_data["fs_calls"] = fs_calls

    # ========== Utilities ==========

    def _extract_body(self, content: str, start_pos: int) -> str:
        brace_pos = content.find("{", start_pos)
        if brace_pos == -1:
            return ""
        end_pos = self._find_matching_brace(content, brace_pos)
        return content[brace_pos : end_pos + 1]

    @staticmethod
    def _find_matching_brace(content: str, open_pos: int) -> int:
        depth = 1
        i = open_pos + 1
        while i < len(content) and depth > 0:
            if content[i] == "{":
                depth += 1
            elif content[i] == "}":
                depth -= 1
            i += 1
        return i - 1 if depth == 0 else len(content) - 1

    @staticmethod
    def _calculate_complexity(body: str) -> int:
        complexity = 1
        complexity += len(MernParser._COMPLEXITY_KEYWORDS.findall(body))
        complexity += len(re.findall(r"&&", body))
        complexity += len(re.findall(r"\|\|", body))
        return complexity
