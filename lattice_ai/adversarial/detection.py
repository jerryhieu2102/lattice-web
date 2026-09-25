import re
import unicodedata

PATTERNS = [
    r"ignore.{0,40}(instructions|rules|previous)",
    r"(system|developer)\s*(message|prompt|:)",
    r"(execute|invoke|call).{0,30}(tool|payment|transfer)",
    r"(bypass|skip).{0,20}(approval|verification)",
    r"ATTACKER",
    r"(urgent|immediately).{0,40}(pay|transfer)",
    r"(bỏ qua|phớt lờ).{0,40}(chỉ dẫn|hướng dẫn|quy tắc|xác minh|phê duyệt)",
    r"(bỏ qua|phớt lờ).{0,40}(chuyen|chuyển).{0,20}(tiền|tien)",
    r"(忽略|绕过|跳过).{0,30}(指令|规则|核实|验证|批准|审批)",
    r"(gọi|thực thi).{0,20}(công cụ|chuyển tiền)",
    r"(调用|执行).{0,20}(工具|付款|转账)",
]


def security_flags(text):
    normalized = unicodedata.normalize("NFKC", text)
    flags = ["PROMPT_INJECTION"] if any(re.search(p, normalized, re.I | re.S) for p in PATTERNS) else []
    if any(unicodedata.category(c) in {"Cf", "Cc"} and c not in "\n\t\r" for c in text):
        flags.append("HIDDEN_CONTROL_CHARACTERS")
    for line in text.splitlines():
        if line.lower().startswith("beneficiary:") and not re.fullmatch(
            r"[A-Za-z0-9 _-]+", line.split(":", 1)[1].strip()
        ):
            flags.append("BENEFICIARY_UNICODE_SPOOF")
    return sorted(set(flags))
