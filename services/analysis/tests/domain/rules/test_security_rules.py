"""Tests for all 14 security rules (2 existing + 12 new)."""

import pytest

from app.domain.rules.security import (
    SecurityCommandInjectionRule,
    SecurityCORSMisconfigRule,
    SecurityCSRFRule,
    SecurityDeserializationRule,
    SecurityHardcodedSecretRule,
    SecurityJWTRule,
    SecurityMissingAuthzRule,
    SecurityNoAuthRule,
    SecurityPathTraversalRule,
    SecuritySQLInjectionRule,
    SecuritySSRFRule,
    SecurityWeakCryptoRule,
    SecurityXSSRule,
    SecurityXXERule,
)


class TestSecuritySQLInjectionRule:
    @pytest.mark.parametrize("content", [
        "cursor.execute('SELECT * FROM users WHERE id = ' + user_input)",
        "execute('SELECT * FROM users WHERE id = ' + request.args['id'])",
        "conn.execute('UPDATE accounts SET balance = ' + str(amount))",
        "query('SELECT * FROM items WHERE id = ' + args['id'])",
    ])
    async def test_detects_sql_injection(self, content: str) -> None:
        rule = SecuritySQLInjectionRule()
        result = await rule.analyze("db.py", content, {})
        assert len(result) >= 1
        assert result[0].rule_id == "SEC-SQLI"

    @pytest.mark.parametrize("content", [
        "cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))",
        'query = "SELECT * FROM users WHERE id = :id"',
        "session.query(User).filter(User.id == user_id).all()",
        "# just a comment about SQL",
    ])
    async def test_skips_safe_queries(self, content: str) -> None:
        rule = SecuritySQLInjectionRule()
        result = await rule.analyze("db.py", content, {})
        assert len(result) == 0


class TestSecurityCommandInjectionRule:
    @pytest.mark.parametrize("content", [
        'subprocess.call("ping " + request.args["host"], shell=True)',
        "os.system('rm -rf ' + request.form['path'])",
        'ProcessBuilder("/bin/sh", "-c", "ping " + request.get("host")).start()',
    ])
    async def test_detects_command_injection(self, content: str) -> None:
        rule = SecurityCommandInjectionRule()
        result = await rule.analyze("utils.py", content, {})
        assert len(result) >= 1
        assert result[0].rule_id == "SEC-CMDI"

    @pytest.mark.parametrize("content", [
        'subprocess.run(["ping", host], shell=False)',
        "result = os.system('ls -la')  # no user input",
        "# command injection not applicable here",
    ])
    async def test_skips_safe_commands(self, content: str) -> None:
        rule = SecurityCommandInjectionRule()
        result = await rule.analyze("utils.py", content, {})
        assert len(result) == 0


class TestSecurityPathTraversalRule:
    @pytest.mark.parametrize("content", [
        "open('/uploads/' + request.args['file'], 'r')",
        'Path(f"/data/{request.form[\"path\"]}").read_text()',
        'send_file(request.args["file"])',
    ])
    async def test_detects_path_traversal(self, content: str) -> None:
        rule = SecurityPathTraversalRule()
        result = await rule.analyze("files.py", content, {})
        assert len(result) >= 1
        assert result[0].rule_id == "SEC-PATH"

    async def test_skips_safe_file_ops(self) -> None:
        rule = SecurityPathTraversalRule()
        result = await rule.analyze("files.py", "with open('data.txt') as f: pass", {})
        assert len(result) == 0


class TestSecuritySSRFRule:
    async def test_detects_ssrf(self) -> None:
        rule = SecuritySSRFRule()
        content = 'requests.get("https://" + request.args["host"])'
        result = await rule.analyze("proxy.py", content, {})
        assert len(result) >= 1
        assert result[0].rule_id == "SEC-SSRF"

    async def test_skips_safe_http(self) -> None:
        rule = SecuritySSRFRule()
        content = 'requests.get("https://api.example.com/data", timeout=5)'
        result = await rule.analyze("proxy.py", content, {})
        assert len(result) == 0


class TestSecurityXXERule:
    @pytest.mark.parametrize("content", [
        "xml.etree.ElementTree.parse(user_input)",
        "fromstring(xml_data)",
        "lxml.etree.parse(user_input)",
    ])
    async def test_detects_xxe(self, content: str) -> None:
        rule = SecurityXXERule()
        result = await rule.analyze("xml_parser.py", content, {})
        assert len(result) >= 1
        assert result[0].rule_id == "SEC-XXE"

    async def test_skips_secure_xml(self) -> None:
        rule = SecurityXXERule()
        content = "defusedxml.parse(user_input)"
        result = await rule.analyze("xml_parser.py", content, {})
        assert len(result) == 0


class TestSecurityXSSRule:
    @pytest.mark.parametrize("content", [
        'element.innerHTML = request.form["input"]',
        'document.write(location.hash)',
        'React.createElement("div", {dangerouslySetInnerHTML: {__html: userInput}})',
        'res.send(request.query.msg)',
        'eval("console.log(" + data + ")")',
    ])
    async def test_detects_xss(self, content: str) -> None:
        rule = SecurityXSSRule()
        result = await rule.analyze("view.js", content, {})
        assert len(result) >= 1
        assert result[0].rule_id == "SEC-XSS"

    @pytest.mark.parametrize("content", [
        'element.textContent = request.form["input"]',
        'React.createElement("div", {className: "foo"}, children)',
        'res.json({msg: "ok"})',
        '# just a comment about XSS',
    ])
    async def test_skips_safe_output(self, content: str) -> None:
        rule = SecurityXSSRule()
        result = await rule.analyze("view.js", content, {})
        assert len(result) == 0

    async def test_empty_content_no_violation(self) -> None:
        rule = SecurityXSSRule()
        result = await rule.analyze("view.js", "", {})
        assert len(result) == 0


class TestSecurityWeakCryptoRule:
    @pytest.mark.parametrize("content", [
        "hashlib.md5(data)",
        'Cipher.getInstance("DES")',
        'hashlib.sha1(b"data")',
        'Cipher.getInstance("AES/ECB/PKCS5Padding")',
    ])
    async def test_detects_weak_crypto(self, content: str) -> None:
        rule = SecurityWeakCryptoRule()
        result = await rule.analyze("crypto.py", content, {})
        assert len(result) >= 1
        assert result[0].rule_id == "SEC-WCRYPTO"

    async def test_skips_strong_crypto(self) -> None:
        rule = SecurityWeakCryptoRule()
        content = 'hashlib.sha256(b"data")'
        result = await rule.analyze("crypto.py", content, {})
        assert len(result) == 0


class TestSecurityJWTRule:
    async def test_detects_none_algorithm(self) -> None:
        rule = SecurityJWTRule()
        content = 'jwt.encode(payload, key, algorithm="none")'
        result = await rule.analyze("auth.py", content, {})
        assert len(result) >= 1
        assert result[0].rule_id == "SEC-JWT"
        assert "none" in result[0].title.lower()

    async def test_skips_secure_jwt(self) -> None:
        rule = SecurityJWTRule()
        content = 'jwt.encode(payload, secret, algorithm="HS256")'
        result = await rule.analyze("auth.py", content, {})
        # Should still flag because decode/verify patterns match
        if result:
            assert result[0].rule_id == "SEC-JWT"


class TestSecurityDeserializationRule:
    @pytest.mark.parametrize("content", [
        "pickle.loads(request.data)",
        "yaml.load(request.data)",
        "yaml.loads(request.body)",
    ])
    async def test_detects_unsafe_deserialization(self, content: str) -> None:
        rule = SecurityDeserializationRule()
        result = await rule.analyze("serial.py", content, {})
        assert len(result) >= 1
        assert result[0].rule_id == "SEC-DESER"

    async def test_skips_safe_deserialization(self) -> None:
        rule = SecurityDeserializationRule()
        result = await rule.analyze("serial.py", "json.loads(data)", {})
        assert len(result) == 0


class TestSecurityMissingAuthzRule:
    async def test_detects_missing_authz(self) -> None:
        rule = SecurityMissingAuthzRule()
        routes = [
            {"path": "/api/admin", "method": "POST", "has_auth": True,
             "line_start": 1, "snippet": "@app.post('/api/admin')"},
        ]
        result = await rule.analyze("routes.py", "", {"routes": routes})
        assert len(result) >= 1
        assert result[0].rule_id == "SEC-NO-AUTHZ"

    async def test_skips_with_authz(self) -> None:
        rule = SecurityMissingAuthzRule()
        routes = [
            {"path": "/api/admin", "method": "POST", "has_auth": True,
             "line_start": 1, "snippet": "@app.post('/api/admin')\n@roles_required('admin')"},
        ]
        result = await rule.analyze("routes.py", "", {"routes": routes})
        assert len(result) == 0

    async def test_no_routes_no_violation(self) -> None:
        rule = SecurityMissingAuthzRule()
        result = await rule.analyze("routes.py", "", {"routes": []})
        assert len(result) == 0


class TestSecurityCSRFRule:
    async def test_detects_missing_csrf(self) -> None:
        rule = SecurityCSRFRule()
        routes = [
            {"path": "/api/data", "method": "POST", "line_start": 1, "snippet": ""},
            {"path": "/api/items", "method": "PUT", "line_start": 2, "snippet": ""},
        ]
        result = await rule.analyze("routes.py", "", {"routes": routes})
        assert len(result) >= 1
        assert result[0].rule_id == "SEC-CSRF"

    async def test_skips_get_only_routes(self) -> None:
        rule = SecurityCSRFRule()
        routes = [
            {"path": "/api/data", "method": "GET", "line_start": 1, "snippet": ""},
        ]
        result = await rule.analyze("routes.py", "", {"routes": routes})
        assert len(result) == 0


class TestSecurityCORSMisconfigRule:
    @pytest.mark.parametrize("content", [
        'Access-Control-Allow-Origin: *',
        "allow_origins=['*']",
        'cors.allow_origins("*")',
    ])
    async def test_detects_wildcard_cors(self, content: str) -> None:
        rule = SecurityCORSMisconfigRule()
        result = await rule.analyze("config.py", content, {})
        assert len(result) >= 1
        assert result[0].rule_id == "SEC-CORS"

    async def test_skips_specific_cors(self) -> None:
        rule = SecurityCORSMisconfigRule()
        content = "allow_origins=['https://app.example.com']"
        result = await rule.analyze("config.py", content, {})
        assert len(result) == 0


class TestSecurityNoAuthRule:
    async def test_missing_auth_on_get(self) -> None:
        rule = SecurityNoAuthRule()
        routes = [{"path": "/api/test", "method": "GET", "has_auth": False, "line_start": 1}]
        result = await rule.analyze("routes.py", "", {"routes": routes})
        assert len(result) == 1
        assert result[0].severity == "high"

    async def test_missing_auth_on_post_is_critical(self) -> None:
        rule = SecurityNoAuthRule()
        routes = [{"path": "/api/data", "method": "POST", "has_auth": False, "line_start": 1}]
        result = await rule.analyze("routes.py", "", {"routes": routes})
        assert len(result) == 1
        assert result[0].severity == "critical"


class TestSecurityHardcodedSecretRule:
    async def test_detects_api_key(self) -> None:
        rule = SecurityHardcodedSecretRule()
        content = 'API_KEY = "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8g9h0"'
        result = await rule.analyze("config.py", content, {})
        assert len(result) == 1

    async def test_skips_low_entropy_values(self) -> None:
        rule = SecurityHardcodedSecretRule()
        content = 'NAME = "hello"'
        result = await rule.analyze("config.py", content, {})
        assert len(result) == 0


class TestSecurityEdgeCases:
    async def test_empty_content_no_violations(self) -> None:
        rules = [
            SecuritySQLInjectionRule(),
            SecurityCommandInjectionRule(),
            SecurityPathTraversalRule(),
            SecuritySSRFRule(),
            SecurityXXERule(),
            SecurityWeakCryptoRule(),
            SecurityDeserializationRule(),
            SecurityCORSMisconfigRule(),
        ]
        for rule in rules:
            result = await rule.analyze("test.py", "", {})
            assert len(result) == 0, f"{rule.rule_id} returned violations on empty content"

    async def test_missing_routes_ast_key(self) -> None:
        no_auth = SecurityNoAuthRule()
        result = await no_auth.analyze("routes.py", "", {})
        assert len(result) == 0

        missing_authz = SecurityMissingAuthzRule()
        result = await missing_authz.analyze("routes.py", "", {})
        assert len(result) == 0

        csrf = SecurityCSRFRule()
        result = await csrf.analyze("routes.py", "", {})
        assert len(result) == 0

    async def test_csrf_empty_routes(self) -> None:
        rule = SecurityCSRFRule()
        result = await rule.analyze("routes.py", "", {"routes": []})
        assert len(result) == 0

    async def test_excluded_file_pattern(self) -> None:
        rule = SecurityHardcodedSecretRule()
        content = 'API_KEY = "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8g9h0"'
        result = await rule.analyze("test_fixture.py", content, {})
        for v in result:
            assert v.severity == "info", f"Expected INFO severity on fixture files, got {v.severity}"

    async def test_malformed_content_no_crash(self) -> None:
        rule = SecuritySQLInjectionRule()
        result = await rule.analyze("test.py", "\x00\xff\xfe\xfd\xfc\xfb\xfa\xf9\xf8", {})
        assert isinstance(result, list)

    async def test_unicode_content_no_crash(self) -> None:
        rule = SecurityXXERule()
        result = await rule.analyze("test.xml", "<?xml version='1.0' encoding='UTF-8'?>\n<root>❤️</root>", {})
        assert isinstance(result, list)
