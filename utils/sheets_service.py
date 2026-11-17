from datetime import datetime
import gspread
import streamlit as st


@st.cache_resource
def get_gspread_client():
    """Ініціалізація та кешування клієнта Google Sheets через secrets."""
    creds_dict = dict(st.secrets["gcp_service_account"])
    return gspread.service_account_from_dict(creds_dict)


@st.cache_data(ttl=60)
def get_orders_data(spreadsheet_id: str, sheet_name: str = "Orders"):
    """Отримує всі рядки з вказаного аркуша у вигляді списку словників із кешуванням на 60 сек."""
    client = get_gspread_client()
    try:
        sh = client.open_by_key(spreadsheet_id)
        worksheet = sh.worksheet(sheet_name)
        return worksheet.get_all_records()
    except Exception as e:
        st.warning(f"⚠️ Помилка зчитування аркуша '{sheet_name}': {e}")
        return []


@st.cache_data(ttl=60)
def get_all_contacts_records(spreadsheet_id: str) -> list:
    """Зчитує всі записи з аркуша Contacts один раз і кешує на 60 секунд."""
    client = get_gspread_client()
    try:
        sh = client.open_by_key(spreadsheet_id)
        worksheet = sh.worksheet("Contacts")
        return worksheet.get_all_records()
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
    """Створює нове замовлення або оновлює існуючий рядок за ID Замовлення."""
    client = get_gspread_client()
    try:
        sh = client.open_by_key(spreadsheet_id)
        worksheet = sh.worksheet("Orders")

        raw_headers = worksheet.row_values(1)
        headers = [str(h).strip() for h in raw_headers]

        existing_id = str(order_data.get("ID Замовлення", "")).strip()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if existing_id:
            # Режим редагування: шукаємо рядок за ID Замовлення у 1-й колонці
            col_vals = worksheet.col_values(1)
            row_idx = None
            for idx, val in enumerate(col_vals[1:], start=2):
                if str(val).strip() == existing_id:
                    row_idx = idx
                    break

            if not row_idx:
                st.error(f"❌ Замовлення з ID '{existing_id}' не знайдено для оновлення.")
                return ""

            # Зчитуємо поточні значення рядка, щоб зберегти колонки, які не редагувалися
            current_row_vals = worksheet.row_values(row_idx)
            merged_data = {
                headers[i]: (current_row_vals[i] if i < len(current_row_vals) else "")
                for i in range(len(headers))
            }

            merged_data.update(order_data)
            merged_data["ID Замовлення"] = existing_id
            merged_data["Час останнього редагування"] = order_data.get(
                "Час останнього редагування", now_str
            )

            # Не перезаписуємо Час створення, якщо воно вже є в таблиці
            if not str(merged_data.get("Час створення", "")).strip():
                merged_data["Час створення"] = now_str

            final_row = [str(merged_data.get(h, "")) for h in headers]
            cell_range = f"A{row_idx}:{gspread.utils.rowcol_to_a1(row_idx, len(headers))}"
            worksheet.update(cell_range, [final_row])

            get_orders_data.clear()
            return existing_id

        # Режим створення нового замовлення
        order_id = generate_next_order_id(spreadsheet_id)
        created_at = order_data.get("Час створення", now_str)

        full_data = {
            "ID Замовлення": order_id,
            "Поточний статус": "Нове замовлення",
            "Архів": "",
            "Час створення": created_at,
            "Час останнього редагування": created_at,
        }
        full_data.update(order_data)
        full_data["ID Замовлення"] = order_id

        final_row = [str(full_data.get(h, "")) for h in headers]
        worksheet.append_row(final_row)

        get_orders_data.clear()
        return order_id

    except Exception as e:
        st.error(f"Помилка при збереженні замовлення в Таблицю: {e}")
        return ""


def save_new_contact(spreadsheet_id: str, contact_data: dict) -> bool:
    """Створює новий контакт або оновлює існуючий у таблиці Contacts."""
    client = get_gspread_client()
    try:
        sh = client.open_by_key(spreadsheet_id)
        worksheet = sh.worksheet("Contacts")
        raw_headers = worksheet.row_values(1)
        headers = [str(h).strip() for h in raw_headers]

        existing_id = contact_data.get("ID Контакту")

        if existing_id:
            col_vals = worksheet.col_values(1)
            row_idx = None
            for idx, val in enumerate(col_vals[1:], start=2):
                if str(val).strip() == str(existing_id).strip():
                    row_idx = idx
                    break

            if row_idx:
                final_row = [str(contact_data.get(h, "")) for h in headers]
                cell_range = f"A{row_idx}:{gspread.utils.rowcol_to_a1(row_idx, len(headers))}"
                worksheet.update(cell_range, [final_row])
            else:
                st.error(f"❌ Контакт з ID '{existing_id}' не знайдено для оновлення.")
                return False
        else:
            col_vals = worksheet.col_values(1)
            existing_numbers = []
            for val in col_vals[1:]:
                if str(val).startswith("CONT-"):
                    try:
                        num_part = int(str(val).replace("CONT-", ""))
                        existing_numbers.append(num_part)
                    except ValueError:
                        continue
            next_num = max(existing_numbers, default=0) + 1
            next_id = f"CONT-{next_num:03d}"

            full_data = {"ID Контакту": next_id}
            full_data.update(contact_data)

            final_row = [str(full_data.get(h, "")) for h in headers]
            worksheet.append_row(final_row)

        get_all_contacts_records.clear()
        return True

    except Exception as e:
        st.error(f"Помилка збереження контакту: {e}")
        return False
