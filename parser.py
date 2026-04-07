"""
Парсер выписок: Сбербанк, Т-Банк, Модульбанк, ВТБ
"""
import csv
from datetime import datetime
from typing import List, Tuple, Dict, Any
import pandas as pd

Transaction = Dict[str, Any]

def parse_csv(file_path: str) -> Tuple[List[Transaction], str]:
    if file_path.endswith(".xlsx") or file_path.endswith(".xls"):
        return parse_excel(file_path)
    with open(file_path, "r", encoding="utf-8-sig", errors="replace") as f:
        header = f.read(2000)
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
    df = pd.read_excel(file_path, header=None)
    header_row = 0
    for i, row in df.iterrows():
        row_str = " ".join(str(v) for v in row.values)
        if any(w in row_str for w in ["Дата", "Сумма", "Назначение"]):
            header_row = i
            break
    df.columns = df.iloc[header_row]
    df = df.iloc[header_row + 1:].reset_index(drop=True)
    top_text = " ".join(str(v) for v in df.head(3).values.flatten())
    bank = "ВТБ" if "ВТБ" in top_text else "Сбербанк"
    return parse_generic_df(df), bank

def parse_sber(file_path: str) -> List[Transaction]:
    transactions = []
    with open(file_path, "r", encoding="utf-8-sig", errors="replace") as f:
        lines = f.readlines()
    header_idx = next((i for i, l in enumerate(lines) if "Дата" in l and "Сумма" in l), 0)
    reader = csv.DictReader(lines[header_idx:], delimiter=";")
    for row in reader:
        try:
            date_str = row.get("Дата операции", row.get("Дата", ""))
            debit = row.get("Дебет", row.get("Сумма списания", "")).replace(" ", "").replace(",", ".")
            credit = row.get("Кредит", row.get("Сумма пополнения", "")).replace(" ", "").replace(",", ".")
            description = row.get("Назначение платежа", row.get("Информация", ""))
            if debit and float(debit or 0):
                amount = -abs(float(debit))
            elif credit and float(credit or 0):
                amount = abs(float(credit))
            else:
                continue
            date = parse_date(date_str)
            if date:
                transactions.append({"date": date, "amount": amount, "description": description.strip(), "category": "", "type": "income" if amount > 0 else "expense"})
        except Exception:
            continue
    return transactions

def parse_tbank(file_path: str) -> List[Transaction]:
    transactions = []
    with open(file_path, "r", encoding="utf-8-sig", errors="replace") as f:
        lines = f.readlines()
    header_idx = next((i for i, l in enumerate(lines) if "Дата" in l and ("Сумма" in l or "Описание" in l)), 0)
    reader = csv.DictReader(lines[header_idx:], delimiter=";")
    for row in reader:
        try:
            date_str = row.get("Дата операции", row.get("Дата платежа", ""))
            amount_str = row.get("Сумма операции", row.get("Сумма", "0")).replace(" ", "").replace(",", ".")
            description = row.get("Описание", row.get("Категория", ""))
            amount = float(amount_str)
            date = parse_date(date_str)
            if date:
                transactions.append({"date": date, "amount": amount, "description": description.strip(), "category": "", "type": "income" if amount > 0 else "expense"})
        except Exception:
            continue
    return transactions

def parse_modulbank(file_path: str) -> List[Transaction]:
    transactions = []
    with open(file_path, "r", encoding="utf-8-sig", errors="replace") as f:
        lines = f.readlines()
    header_idx = next((i for i, l in enumerate(lines) if "Дата" in l and ("Дебет" in l or "Кредит" in l)), 0)
    reader = csv.DictReader(lines[header_idx:], delimiter=";")
    for row in reader:
        try:
            date_str = row.get("Дата", "")
            debit = row.get("Дебет", "").replace(" ", "").replace(",", ".")
            credit = row.get("Кредит", "").replace(" ", "").replace(",", ".")
            description = row.get("Назначение платежа", row.get("Контрагент", ""))
            if debit and float(debit or 0):
                amount = -abs(float(debit))
            elif credit and float(credit or 0):
                amount = abs(float(credit))
            else:
                continue
            date = parse_date(date_str)
            if date:
                transactions.append({"date": date, "amount": amount, "description": description.strip(), "category": "", "type": "income" if amount > 0 else "expense"})
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
            amount = float(row.get(sum_key, "0").replace(" ", "").replace(",", "."))
            description = row.get(desc_key, "") if desc_key else ""
            if date:
                transactions.append({"date": date, "amount": amount, "description": description.strip(), "category": "", "type": "income" if amount > 0 else "expense"})
        except Exception:
            continue
    return transactions

def parse_generic_df(df) -> List[Transaction]:
    transactions = []
    for _, row in df.iterrows():
        row_dict = {str(k): str(v) for k, v in row.items() if str(v) != 'nan'}
        transactions.extend(parse_generic_rows([row_dict]))
    return transactions

def parse_date(date_str: str):
    date_str = str(date_str).strip()
    for fmt in ["%d.%m.%Y", "%d.%m.%Y %H:%M:%S", "%d.%m.%Y %H:%M", "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%d/%m/%Y"]:
        try:
            return datetime.strptime(date_str[:len(fmt)], fmt)
        except ValueError:
            continue
    return None
