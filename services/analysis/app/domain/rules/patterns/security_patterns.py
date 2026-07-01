import re
from dataclasses import dataclass, field


@dataclass
class SecuritySignature:
    rule_id: str
    title: str
    description: str
    recommendation: str
    enterprise_pattern: str
    severity: str
    patterns: list[re.Pattern[str]] = field(default_factory=list)


SQL_INJECTION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r'(?i)(select|insert|update|delete|drop|alter|create|truncate|exec)\s+.*\b(from|into|set|values|where)\b.*[\'"]\s*[+%.]'),
    re.compile(r'(?i)(?:execute|exec|raw_sql|query)\s*\(\s*[f"\'][^)]*[+{][^)]*(?:request|params?|data|input|body|args|kwargs|form|get|post)'),
    re.compile(r'(?i)\.format\(\s*(?:request|params?|data|input|body|args|kwargs|form|get|post)'),
    re.compile(r'(?i)(?:select|insert|update|delete|drop|alter).*f[\'\"].*\{[^}]*?(?:request|params?|data|input|body|args|kwargs|form|get|post)}'),
]

COMMAND_INJECTION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r'(?i)(?:subprocess(?:\.\w+)?|os\.system|os\.popen|commands|shlex)\s*\([^)]*[\'\"][^)]*(?:request|params?|data|input|body|args|kwargs|form|get|post)'),
    re.compile(r'(?i)exec\s*\(\s*[\'\"].*[+{]\s*(?:request|params?|data|input|body|args|kwargs|form|get|post)'),
    re.compile(r'(?i)(?:ProcessBuilder|Runtime\.exec|Process\.start)\s*\([^)]*[\'\"][^)]*[+%{][^)]*(?:request|input|param|get|body|data)'),
]

PATH_TRAVERSAL_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r'(?i)(?:open|file|Path|File\.Read|File\.Write|read_text|write_text)\s*\([^)]*[\'\"][^)]*[+{][^)]*(?:request|params?|data|input|body|args|kwargs|form|get|post)'),
    re.compile(r'(?i)os\.path\.(?:join|abspath|realpath)\s*\([^)]*[\'\"][^)]*[+{][^)]*(?:request|params?|data|input)'),
    re.compile(r'(?i)send_file\s*\([^)]*[\'\"][^)]*[+{][^)]*(?:request|params?|data|input)'),
    re.compile(r'(?i)send_file\s*\(\s*request'),
]

SSRF_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r'(?i)(?:requests|httpx|urllib|aiohttp|http_client|HttpClient|WebClient)\.\w*\s*\([^)]*[\'\"].*[+{].*(?:request|params?|data|input|body|args|kwargs|form|get|post|url)'),
    re.compile(r'(?i)urlopen\s*\([^)]*[\'\"].*[+{].*(?:request|params?|data|input)'),
]

XXE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r'(?i)(?:xml\.etree|ElementTree|SAXParser|DocumentBuilder|XmlReader|XmlDocument|SimpleXML|loadXML|parseXML)\.?(?:parse|fromstring|load|Parse)\s*\('),
    re.compile(r'(?i)(?:lxml|etree)\.(?:parse|fromstring|XML)\s*\('),
    re.compile(r'(?i)(?<!\.)(?:fromstring|parseString)\s*\('),
]

WEAK_CRYPTO_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r'(?i)(?:md5|sha1|sha-1|des_ecb|des_cbc|RC2|RC4|Blowfish)\s*\('),
    re.compile(r'(?i)hashlib\.(?:md5|sha1)\s*\('),
    re.compile(r'(?i)Cipher\.(?:getInstance)\s*\(\s*[\'"]DES|[\'"]RC2|[\'"]RC4|[\'"]Blowfish|[\'"]AES/ECB'),
    re.compile(r'(?i)\.update\s*\(\s*[\'"]sha1|[\'"]md5'),
]

JWT_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r'(?i)jwt\.(?:encode|decode|sign|verify)\s*\([^)]*algorithm\s*=\s*[\'"]none'),
    re.compile(r'(?i)algorithms\s*=\s*\[\s*[\'"]none|algorithms\s*=\s*\[\s*\]'),
    re.compile(r'(?i)JWTVerifier|jwt\.verify|verify_jwt|decode_jwt'),
]

DESERIALIZATION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r'(?i)(?:pickle|cPickle|PyYAML)\.(?:loads|load)\s*\('),
    re.compile(r'(?i)(?:yaml)\.(?:load|loads)\s*\('),
    re.compile(r'(?i)JSON\.parse\s*\([^)]*(?:request|params?|data|input|body)'),
    re.compile(r'(?i)ObjectMapper\.(?:enableDefaultTyping|enableDefaultTypingAsProperty)'),
    re.compile(r'(?i)@JsonTypeInfo|@JsonSubTypes'),
]

XSS_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r'(?i)(?:innerHTML|outerHTML|document\.write|writeln)\s*\([^)]*(?:request|params?|data|input|body|args|kwargs|form|get|post|location|hash|search)'),
    re.compile(r'(?i)(?:innerHTML|outerHTML)\s*=\s*.*(?:request|params?|data|input|body|args|kwargs|form|get|post|location|hash|search)'),
    re.compile(r'(?i)(?:React\.dangerouslySetInnerHTML|dangerouslySetInnerHTML)\s*[=:]'),
    re.compile(r'(?i)(?:response\.write|response\.send|res\.send|res\.write|out\.print|out\.write)\s*\([^)]*(?:request|params?|data|input|body|args|kwargs|form|get|post)'),
    re.compile(r'(?i)\.(?:html|append|prepend|after|before)\s*\([^)]*(?:request|params?|data|input|body|args|kwargs|form|get|post)'),
    re.compile(r'(?i)(?:eval|setTimeout|setInterval|new Function)\s*\([^)]*(?:request|params?|data|input|body|args|kwargs|form|get|post)'),
    re.compile(r'(?i)location\.(?:href|replace|assign)\s*=\s*.*(?:request|params?|data|input|body|args|kwargs|form|get|post)'),
    re.compile(r'(?i)window\.location\s*=.*(?:request|params?|data|input|body|args|kwargs|form|get|post)'),
]

CSRF_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r'(?i)(?:@csrf\.exempt|csrf_exempt|CSRFProtect\.exempt|@csrf\.exclude)'),
    re.compile(r'(?i)\.meta\([\'"]csrf[\'"]\)'),
]

CORS_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r'(?i)(?:Access-Control-Allow-Origin)\s*:\s*\*'),
    re.compile(r'(?i)(?:allow_origins|origins)\s*=\s*\[[\'"]\*[\'"]'),
    re.compile(r'(?i)\.allow_origins\(\s*[\'"]\*[\'"]'),
]
