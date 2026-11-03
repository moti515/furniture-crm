from datetime import datetime
import gspread
import streamlit as st


@st.cache_resource
def get_gspread_client():
    """Ініціалізація та кешування клієнта Google Sheets через secrets."""
    creds_dict = dict(st.secrets["gcp_service_account"])
    return gspread.service_account_from_dict(creds_dict)


def get_orders_data(spreadsheet_id: str, sheet_name: str = "Orders"):
    """Отримує всі рядки з вказаного аркуша у вигляді списку словників."""
    client = get_gspread_client()
    try:
        sh = client.open_by_key(spreadsheet_id)
        worksheet = sh.worksheet(sheet_name)
        return worksheet.get_all_records()
    except Exception as e:
        st.warning(f"⚠️ Помилка зчитування аркуша '{sheet_name}': {e}")
        return []


def get_contacts_list(spreadsheet_id: str, role_filter: str = None) -> list:
    """Отримує список ПІБ / Назв з аркуша Contacts.

    Якщо вказано role_filter, повертає тільки контакти, що мають цю роль у колонці 'Роль / Категорія'.
    """
    client = get_gspread_client()
    try:
        sh = client.open_by_key(spreadsheet_id)
        worksheet = sh.worksheet("Contacts")
        records = worksheet.get_all_records()

        contacts = []
        for row in records:
            name = str(row.get("ПІБ / Назва", "")).strip()
            roles_str = str(row.get("Роль / Категорія", "")).strip()

            if name:
                if role_filter:
                    # Розбиваємо перелік ролей за комою
                    roles_list = [r.strip().lower() for r in roles_str.split(",")]
                    if role_filter.lower() in roles_list:
                        contacts.append(name)
                else:
                    contacts.append(name)

        return sorted(list(set(contacts)))
    except Exception as e:
        st.error(f"Помилка завантаження контактів: {e}")
        return []


def generate_next_order_id(spreadsheet_id: str) -> str:
    """Генерує наступний унікальний ID замовлення у форматі ORD-YYYY-XXX."""
    client = get_gspread_client()
    current_year = datetime.now().strftime("%Y")
    prefix = f"ORD-{current_year}-"

    try:
        sh = client.open_by_key(spreadsheet_id)
        worksheet = sh.worksheet("Orders")
        col_values = worksheet.col_values(1)

        existing_numbers = []
        for val in col_values[1:]:
            if str(val).startswith(prefix):
                try:
                    num_part = int(str(val).replace(prefix, ""))
                    existing_numbers.append(num_part)
                except ValueError:
                    continue

        next_num = max(existing_numbers, default=0) + 1
        return f"{prefix}{next_num:03d}"

    except Exception:
        return f"{prefix}001"


def save_new_order(spreadsheet_id: str, order_data: dict) -> str:
    """Генерує ID, заповнює службові поля та додає новий рядок у Orders."""
    client = get_gspread_client()
    try:
        sh = client.open_by_key(spreadsheet_id)
        worksheet = sh.worksheet("Orders")

        order_id = generate_next_order_id(spreadsheet_id)
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Зчитуємо актуальні заголовки аркуша Orders і очищаємо від зайвих пробілів
        raw_headers = worksheet.row_values(1)
        headers = [str(h).strip() for h in raw_headers]

        # Готуємо повний словник даних
        full_data = {
            "ID Замовлення": order_id,
            "Поточний статус": "Нове замовлення",
            "Архів": False,
            "Час створення": created_at,
            "Час останнього редагування": created_at,
        }
        full_data.update(order_data)

        # Формуємо рядок строго відповідно до порядку колонок у таблиці
        final_row = [str(full_data.get(h, "")) for h in headers]

        worksheet.append_row(final_row)
        return order_id

    except Exception as e:
        st.error(f"Помилка при збереженні замовлення в Таблицю: {e}")
        return ""


def save_new_contact(spreadsheet_id: str, contact_data: dict) -> bool:
    """Додає новий контакт у таблицю Contacts."""
    client = get_gspread_client()
    try:
        sh = client.open_by_key(spreadsheet_id)
        worksheet = sh.worksheet("Contacts")
        raw_headers = worksheet.row_values(1)
        headers = [str(h).strip() for h in raw_headers]

        col_vals = worksheet.col_values(1)
        next_id = f"CONT-{len(col_vals):03d}"

        full_data = {"ID Контакту": next_id}
        full_data.update(contact_data)

        final_row = [str(full_data.get(h, "")) for h in headers]
        worksheet.append_row(final_row)
        return True
    except Exception as e:
        st.error(f"Помилка збереження контакту: {e}")
        return False
