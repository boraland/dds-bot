"""
Парсер выписок: Сбербанк, Т-Банк, Модульбанк, ВТБ
Без pandas — только стандартная библиотека + openpyxl
"""
import csv
from datetime import datetime
from typing import List, Tuple, Dict, Any
import openpyxl

Transaction = Dict[str, Any]

def parse_csv(file_path: str) -> Tuple[List[Transaction], str]:
    if file_path.endswith(".xlsx") or file_path.endswith(".xls"):
        return parse_excel(file_path)

    for enc in ["utf-8-sig", "cp1251", "utf-8"]:
        try:
            with open(file_path, "r", encoding=enc, errors="replace") as f:
                header = f.read(2000)
            break
        except Exception:
            header = ""

    if "Сбербанк" in header or "Сбер" in header:
        return parse_sber(file_path), "Сбербанк"
    elif "Тинькофф" in header or "Т-Банк" in header or "TINKOFF" in header.upper():
        return parse_tbank(file_path), "Т-Банк"
    elif "Модуль" in header or "modulbank" in header.lower():
        return parse_modulbank(file_path), "Модульбанк"
    elif "ВТБ" in header or "VTB" in header.upper():
        return parse_vtb(file_path), "ВТБ"
    else:
        return parse_generic(file_path), "Неизвестный банк"

def parse_excel(file_path: str) -> Tuple[List[Transaction], str]:
    wb = openpyxl.load_workbook(file_path, data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))

    # Найти строку заголовков
    header_idx = 0
    for i, row in enumerate(rows):
        row_str = " ".join(str(v) for v in row if v)
        if any(w in row_str for w in ["Дата", "Сумма", "Назначение"]):
            header_idx = i
            break

    headers = [str(h).strip() if h else f"col{i}" for i, h in enumerate(rows[header_idx])]
    transactions = []
    for row in rows[header_idx + 1:]:
        row_dict = {headers[i]: str(v).strip() if v is not None else "" for i, v in enumerate(row)}
        result = parse_generic_rows([row_dict])
        transactions.extend(result)

    top_text = " ".join(str(v) for v in rows[:3] if v)
    bank = "ВТБ" if "ВТБ" in top_text else "Сбербанк"
    return transactions, bank

def parse_sber(file_path: str) -> List[Transaction]:
    transactions = []
    for enc in ["utf-8-sig", "cp1251", "utf-8"]:
        try:
            with open(file_path, "r", encoding=enc, errors="replace") as f:
                lines = f.readlines()
            break
        except Exception:
            continue

    header_idx = next((i for i, l in enumerate(lines) if "Дата" in l and "Сумма" in l), 0)
    reader = csv.DictReader(lines[header_idx:], delimiter=";")
    for row in reader:
        try:
            date_str = row.get("Дата операции", row.get("Дата", ""))
            debit = clean_num(row.get("Дебет", row.get("Сумма списания", "")))
            credit = clean_num(row.get("Кредит", row.get("Сумма пополнения", "")))
            description = row.get("Назначение платежа", row.get("Информация", ""))
            if debit:
                amount = -abs(debit)
            elif credit:
                amount = abs(credit)
            else:
                continue
            date = parse_date(date_str)
            if date:
                transactions.append(make_txn(date, amount, description))
        except Exception:
            continue
    return transactions

def parse_tbank(file_path: str) -> List[Transaction]:
    transactions = []
    for enc in ["utf-8-sig", "cp1251", "utf-8"]:
        try:
            with open(file_path, "r", encoding=enc, errors="replace") as f:
                lines = f.readlines()
            break
        except Exception:
            continue

    header_idx = next((i for i, l in enumerate(lines) if "Дата" in l and ("Сумма" in l or "Описание" in l)), 0)
    reader = csv.DictReader(lines[header_idx:], delimiter=";")
    for row in reader:
        try:
            date_str = row.get("Дата операции", row.get("Дата платежа", ""))
            amount = clean_num(row.get("Сумма операции", row.get("Сумма", "0"))) or 0
            description = row.get("Описание", row.get("Категория", ""))
            date = parse_date(date_str)
            if date:
                transactions.append(make_txn(date, amount, description))
        except Exception:
            continue
    return transactions

def parse_modulbank(file_path: str) -> List[Transaction]:
    transactions = []
    for enc in ["utf-8-sig", "cp1251", "utf-8"]:
        try:
            with open(file_path, "r", encoding=enc, errors="replace") as f:
                lines = f.readlines()
            break
        except Exception:
            continue

    header_idx = next((i for i, l in enumerate(lines) if "Дата" in l and ("Дебет" in l or "Кредит" in l)), 0)
    reader = csv.DictReader(lines[header_idx:], delimiter=";")
    for row in reader:
        try:
            date_str = row.get("Дата", "")
            debit = clean_num(row.get("Дебет", ""))
            credit = clean_num(row.get("Кредит", ""))
            description = row.get("Назначение платежа", row.get("Контрагент", ""))
            if debit:
                amount = -abs(debit)
            elif credit:
                amount = abs(credit)
            else:
                continue
            date = parse_date(date_str)
            if date:
                transactions.append(make_txn(date, amount, description))
        except Exception:
            continue
    return transactions

def parse_vtb(file_path: str) -> List[Transaction]:
    return parse_generic(file_path)

def parse_generic(file_path: str) -> List[Transaction]:
    for enc in ["utf-8-sig", "cp1251", "utf-8"]:
        try:
            with open(file_path, "r", encoding=enc, errors="replace") as f:
                lines = f.readlines()
            for delimiter in [";", ",", "\t"]:
                reader = csv.DictReader(lines, delimiter=delimiter)
                rows = list(reader)
                if rows and len(reader.fieldnames or []) > 2:
                    return parse_generic_rows(rows)
        except Exception:
            continue
    return []

def parse_generic_rows(rows: list) -> List[Transaction]:
    transactions = []
    for row in rows:
        keys = list(row.keys())
        date_key = next((k for k in keys if "дата" in k.lower()), None)
        sum_key = next((k for k in keys if "сумм" in k.lower()), None)
        desc_key = next((k for k in keys if any(w in k.lower() for w in ["назначение", "описание", "контрагент"])), None)
        if not date_key or not sum_key:
            continue
        try:
            date = parse_date(row.get(date_key, ""))
            amount = clean_num(row.get(sum_key, "0")) or 0
            description = row.get(desc_key, "") if desc_key else ""
            if date:
                transactions.append(make_txn(date, amount, description))
        except Exception:
            continue
    return transactions

def make_txn(date, amount, description):
    return {
        "date": date,
        "amount": amount,
        "description": str(description).strip(),
        "category": "",
        "type": "income" if amount > 0 else "expense",
    }

def clean_num(s: str) -> float:
    try:
        return float(str(s).replace(" ", "").replace(",", ".").replace("\xa0", ""))
    except Exception:
        return 0.0

def parse_date(date_str: str):
    date_str = str(date_str).strip()
    for fmt in ["%d.%m.%Y", "%d.%m.%Y %H:%M:%S", "%d.%m.%Y %H:%M", "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%d/%m/%Y"]:
        try:
            return datetime.strptime(date_str[:len(fmt)], fmt)
        except ValueError:
            continue
    return None
