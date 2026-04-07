"""Категоризация транзакций через Claude AI."""
import json, os, re
from typing import List, Dict, Any
import httpx

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

ALL_CATEGORIES = [
    "Выручка от продаж", "Поступление от клиентов", "Возврат от поставщиков",
    "Займы полученные", "Прочие поступления",
    "Зарплата и выплаты сотрудникам", "Налоги и сборы", "Аренда",
    "Реклама и маркетинг", "Поставщики и подрядчики", "Банковские комиссии",
    "Офис и хозяйственные расходы", "IT и программное обеспечение",
    "Транспорт и логистика", "Займы и кредиты (погашение)", "Прочие расходы",
]

async def categorize_transactions(transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not ANTHROPIC_API_KEY:
        return categorize_by_keywords(transactions)
    for i in range(0, len(transactions), 30):
        batch = transactions[i:i + 30]
        try:
            categorized = await categorize_batch_ai(batch)
            for j, t in enumerate(batch):
                t["category"] = categorized.get(str(j), guess_category(t))
        except Exception:
            for t in batch:
                t["category"] = guess_category(t)
    return transactions

async def categorize_batch_ai(batch: List[Dict]) -> Dict[str, str]:
    items = "\n".join(f"{i}. [{'+'  if t['amount']>0 else '-'}{abs(t['amount']):.2f}] {t['description']}" for i, t in enumerate(batch))
    cats = "\n".join(f"- {c}" for c in ALL_CATEGORIES)
    prompt = f"Категоризируй транзакции малого бизнеса.\n\nКатегории:\n{cats}\n\nТранзакции:\n{items}\n\nОтвет ТОЛЬКО JSON: {{\"0\": \"категория\", ...}}"
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post("https://api.anthropic.com/v1/messages",
            headers={"x-api-key": ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json={"model": "claude-haiku-4-5-20251001", "max_tokens": 1000, "messages": [{"role": "user", "content": prompt}]})
        text = r.json()["content"][0]["text"]
        match = re.search(r'\{[^{}]+\}', text, re.DOTALL)
        return json.loads(match.group() if match else text)

def categorize_by_keywords(transactions):
    for t in transactions:
        t["category"] = guess_category(t)
    return transactions

def guess_category(t: Dict) -> str:
    desc = t.get("description", "").lower()
    rules = {
        "Зарплата и выплаты сотрудникам": ["зарплат", "аванс", "выплата сотрудн"],
        "Налоги и сборы": ["налог", "ифнс", "фнс", "ндс", "ндфл", "пфр"],
        "Аренда": ["аренд", "помещени"],
        "Реклама и маркетинг": ["реклам", "маркетинг", "яндекс", "google"],
        "Банковские комиссии": ["комисси", "обслуживани"],
        "IT и программное обеспечение": ["хостинг", "домен", "1с", "saas"],
        "Транспорт и логистика": ["такси", "доставк", "логистик", "cdek", "сдэк"],
        "Займы и кредиты (погашение)": ["кредит", "займ", "погашени"],
    }
    for category, keywords in rules.items():
        if any(kw in desc for kw in keywords):
            return category
    return "Прочие поступления" if t["amount"] > 0 else "Прочие расходы"
