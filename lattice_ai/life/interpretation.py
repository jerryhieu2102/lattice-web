"""Bounded EN/VI/ZH demo interpreter. Unknown financial facts stay unknown.

This module receives text and a clock only. It has no financial tools or database access.
"""

import calendar
import re
import unicodedata
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from lattice_ai.adversarial.detection import security_flags
from lattice_core.currencies import CURRENCIES, SCALE
from lattice_core.life.schemas import Proposal

ALIASES = {
    "€": "EUR",
    "$": "USD",
    "人民币": "CNY",
    "nhân dân tệ": "CNY",
    "đồng": "VND",
    "vnđ": "VND",
    "dollar": "USD",
    "đô la": "USD",
    "美元": "USD",
    "欧元": "EUR",
    "越南盾": "VND",
    "日元": "JPY",
}
CURRENCY = (
    r"(?:" + "|".join(CURRENCIES) + r"|€|\$|人民币|nhân dân tệ|đồng|vnđ|dollar|đô la|美元|欧元|越南盾|日元)"
)
NUMBER = r"\d+(?:[.,]\d+)*"
MONEY = re.compile(
    rf"(?P<c1>{CURRENCY})\s*(?P<n1>{NUMBER})(?:\s*[–—-]\s*(?P<x1>{NUMBER}))?|(?P<n2>{NUMBER})(?:\s*[–—-]\s*(?P<x2>{NUMBER}))?\s*(?P<c2>{CURRENCY})",
    re.I,
)


def money_values(text, locale):
    result = []
    for m in MONEY.finditer(text):
        if re.search(r"[-−]\s*$", text[: m.start()]):
            continue
        currency = m.group("c1") or m.group("c2")
        currency = ALIASES.get(currency.lower(), currency.upper())
        try:

            def number(raw):
                # Explicit locale governs separators; grouped triples and decimal fractions are distinct.
                if re.fullmatch(r"\d{1,3}(?:[,.]\d{3})+", raw):
                    raw = raw.replace(",", "").replace(".", "")
                elif locale == "vi" and "," in raw:
                    raw = raw.replace(".", "").replace(",", ".")
                elif "," in raw:
                    raise ValueError("Ambiguous decimal separator")
                value = Decimal(raw) * SCALE[currency]
                if (
                    value != value.to_integral_value()
                    or value < 0
                    or value > min(100_000_000_000, 1_000_000_000 * SCALE[currency])
                ):
                    raise ValueError("Unsupported amount")
                return int(value)

            low = number(m.group("n1") or m.group("n2"))
            high_raw = m.group("x1") or m.group("x2")
            result.append((low, number(high_raw) if high_raw else None, currency))
        except (ValueError, InvalidOperation):
            continue
    return result


def interpret(text, clock, locale="en"):
    raw = unicodedata.normalize("NFKC", text)
    s = raw.casefold()

    def has(*words):
        return any(w in s for w in words)

    today = date.fromisoformat(clock)
    p = Proposal(title="Life event", confidence=0.65)
    flags = security_flags(raw)
    if has("bank account", "beneficiary", "tài khoản trường", "người thụ hưởng", "学校账户", "收款人"):
        flags.append("BENEFICIARY_REVIEW_REQUIRED")
    p.security_flags = sorted(set(flags))
    hypothetical = has(
        "what if",
        "if i",
        "want",
        "thinking",
        "might",
        "can i",
        "muốn",
        "nếu",
        "dự định",
        "có thể",
        "định mua",
        "假如",
        "如果",
        "想",
        "能否",
        "可以",
        "考虑",
        "可能",
    )
    p.mode = "HYPOTHETICAL" if hypothetical else "ACTUAL"
    kind = "OTHER"
    if flags or has("scam", "suspicious", "lừa đảo", "可疑", "诈骗"):
        kind = "SECURITY_INCIDENT"
    elif has(
        "lost card",
        "blocked account",
        "mất thẻ",
        "khóa tài khoản",
        "丢卡",
        "卡丢",
        "卡丢失",
        "银行卡丢失",
        "账户冻结",
    ):
        kind = "ACCOUNT_UNAVAILABLE"
    elif has("transfer failed", "chuyển tiền thất bại", "转账失败"):
        kind = "TRANSFER_FAILED"
    elif has("late", "delay", "trễ", "chậm", "延迟", "晚到", "推迟"):
        kind = "FUNDING_DELAYED"
    elif has("reduced", "less funding", "giảm hỗ trợ", "资助减少"):
        kind = "FUNDING_REDUCED"
    elif has("refund", "hoàn tiền", "退款"):
        kind = "REFUND_EXPECTED"
    elif has("borrowed", "vay", "借了", "借入"):
        kind = "BORROWING"
    elif has("lent", "cho vay", "cho bạn mượn", "借给", "借出"):
        kind = "LENDING"
    elif has(
        "per month",
        "/month",
        "monthly",
        "hàng tháng",
        "mỗi tháng",
        "/tháng",
        "每月",
        "per year",
        "yearly",
        "hàng năm",
        "每年",
        "per week",
        "mỗi tuần",
        "每周",
    ):
        kind = "RECURRING_EXPENSE"
        p.recurrence_rule = (
            "YEARLY"
            if has("per year", "yearly", "hàng năm", "每年")
            else "WEEKLY"
            if has("per week", "mỗi tuần", "每周")
            else "MONTHLY"
        )
    elif (
        has(
            "paid",
            "bought",
            "spent",
            "đã trả",
            "đã mua",
            "đã chi",
            "vừa trả",
            "vừa mua",
            "买了",
            "支付了",
            "付了",
            "花了",
        )
        and not hypothetical
    ):
        kind = "EXPENSE_OCCURRED"
    elif has(
        "travel",
        "bangkok",
        "japan",
        "fly home",
        "trip",
        "du lịch",
        "về quê",
        "đi nhật",
        "旅行",
        "曼谷",
        "回国",
        "日本",
    ):
        kind = "TRAVEL_PLAN"
        p.mode = "HYPOTHETICAL"
    elif has("save", "savings goal", "tiết kiệm", "存钱", "储蓄") and not has(
        "without touching", "không đụng", "不动用"
    ):
        kind = "SAVINGS_GOAL"
        p.mode = "HYPOTHETICAL"
    elif has(
        "repair",
        "broke",
        "medical",
        "hospital",
        "emergency",
        "sửa",
        "hỏng",
        "khẩn cấp",
        "viện phí",
        "sự cố",
        "thiết bị cần",
        "hóa đơn bất ngờ",
        "学习必需",
        "意外账单",
        "维修",
        "坏了",
        "医院",
        "紧急",
        "医疗",
    ):
        kind = "EMERGENCY"
        p.essentiality, p.priority = "ESSENTIAL", "CRITICAL"
    elif has(
        "increases", "increase by", "rent rises", "tiền thuê tăng", "tăng tiền thuê", "房租上涨", "涨租"
    ):
        kind, p.amount_is_delta = "OBLIGATION_CHANGED", True
    elif has("need to pay", "must pay", "cần trả", "phải trả", "cần đóng", "需要支付", "必须交"):
        kind, p.essentiality, p.priority = "NEW_OBLIGATION", "ESSENTIAL", "HIGH"
    elif has("received", "sent", "got ", "đã nhận", "đã gửi", "到账", "收到了", "已寄"):
        kind = "FUNDING_RECEIVED"
    elif has(
        "will send",
        "salary",
        "freelance",
        "stipend",
        "bonus",
        "gift",
        "scholarship",
        "sẽ gửi",
        "lương",
        "học bổng",
        "quà",
        "sẽ chuyển",
        "会寄",
        "工资",
        "奖学金",
        "资助",
    ):
        kind = "FUNDING_EXPECTED"
    elif has("owes me", "nợ tôi", "nợ mình", "欠我"):
        kind = "REIMBURSEMENT_EXPECTED"
    elif hypothetical or has("afford", "mua", "耳机", "spend", "chi tiêu"):
        kind = "PURCHASE_INTENT"
        p.mode = "HYPOTHETICAL"
    p.event_type = kind
    if (
        kind
        in {
            "FUNDING_EXPECTED",
            "REFUND_EXPECTED",
            "REIMBURSEMENT_EXPECTED",
            "TRANSFER_PENDING",
            "FAMILY_SUPPORT",
        }
        and not hypothetical
    ):
        p.mode = "EXPECTED"
    p.category = (
        "EDUCATION"
        if has("laptop", "học", "study", "学", "software")
        else "HOUSING"
        if has("rent", "housing", "nhà", "房租")
        else "HEALTH"
        if has("medical", "viện", "医疗")
        else "OTHER"
    )
    if kind == "PURCHASE_INTENT":
        p.essentiality, p.priority = "DISCRETIONARY", "OPTIONAL"
    p.title = kind.replace("_", " ").capitalize()
    values = money_values(raw, locale)
    if values:
        lo, hi, p.currency = values[0]
        if hi is not None and hi >= lo:
            p.amount_min_minor, p.amount_max_minor = lo, hi
        else:
            p.amount_minor = lo
        if (
            kind == "EXPENSE_OCCURRED"
            and len(values) > 1
            and has("owes", "nợ", "欠")
            and values[1][2] == p.currency
        ):
            p.receivable_minor = values[1][0]
    if has("dad", "father", "bố", "ba ", "爸爸", "父亲"):
        p.counterparty = "Father"
    if has("david"):
        p.counterparty = "David"
    exact_dates = re.findall(r"\b\d{4}-\d{2}-\d{2}\b", s)
    try:
        if exact_dates:
            p.event_date = date.fromisoformat(exact_dates[0])
            if len(exact_dates) > 1:
                p.repayment_date = date.fromisoformat(exact_dates[1])
        elif has("tomorrow", "ngày mai", "明天"):
            p.event_date = today + timedelta(days=1)
        elif has("today", "hôm nay", "今天"):
            p.event_date = today
        elif has("yesterday", "hôm qua", "昨天"):
            p.event_date = today - timedelta(days=1)
        elif has("this weekend", "cuối tuần", "这个周末"):
            p.date_window_start = today + timedelta(days=(5 - today.weekday()) % 7)
            p.date_window_end = p.date_window_start + timedelta(days=1)
        elif has("next month", "tháng sau", "下个月"):
            p.date_window_start = (today.replace(day=28) + timedelta(days=4)).replace(day=1)
            p.date_window_end = p.date_window_start.replace(
                day=calendar.monthrange(p.date_window_start.year, p.date_window_start.month)[1]
            )
    except ValueError:
        p.event_date = None
    if kind == "FUNDING_DELAYED":
        normalized = s
        for word, n in [
            ("five", 5),
            ("two", 2),
            ("one", 1),
            ("năm", 5),
            ("hai", 2),
            ("một", 1),
            ("五", 5),
            ("两", 2),
            ("二", 2),
            ("一", 1),
        ]:
            normalized = normalized.replace(word, str(n))
        match = re.search(r"(\d+)\s*(days?|weeks?|ngày|tuần|天|周)", normalized)
        if match:
            delay = int(match[1]) * (7 if match[2] in {"week", "weeks", "tuần", "周"} else 1)
            if 1 <= delay <= 365:
                p.delay_days = delay
    p.question = (
        kind in {"OTHER", "PURCHASE_INTENT"}
        and not values
        and ("?" in s or has("how much", "how long", "bao nhiêu", "bao lâu", "多少", "多久"))
    )
    if p.question:
        p.mode = "HYPOTHETICAL"
    return Proposal.model_validate(p.model_dump())
