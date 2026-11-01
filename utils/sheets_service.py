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
    st.error(f"Помилка підключення до аркуша '{sheet_name}' (ID: {spreadsheet_id}): {e}")
    return []


def get_contacts_list(spreadsheet_id: str, role_filter: str = None) -> list:
  """Отримує список ПІБ / Назв з аркуша Contacts.

  За потреби фільтрує за роллю.
  """
  client = get_gspread_client()
  try:
    sh = client.open_by_key(spreadsheet_id)
    worksheet = sh.worksheet("Contacts")
    records = worksheet.get_all_records()

    contacts = []
    for row in records:
      name = str(row.get("ПІБ / Назва", "")).strip()
      roles = str(row.get("Роль / Категорія", "")).strip()

      if name:
        if role_filter:
          if role_filter.lower() in roles.lower():
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
    col_values = worksheet.col_values(1)  # Зчитуємо тільки першу колонку (ID)

    # Фільтруємо існуючі ID за поточним роком
    existing_numbers = []
    for val in col_values[1:]:  # Пропускаємо заголовок
      if val.startswith(prefix):
        try:
          num_part = int(val.replace(prefix, ""))
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

    # Зчитуємо актуальні заголовки аркуша Orders
    headers = worksheet.row_values(1)
    
    # Готуємо словник даних
    full_data = {
        "ID Замовлення": order_id,
        "Архів": False,
        "Час створення": created_at,
        "Час останнього редагування": created_at,
    }
    full_data.update(order_data)

    # Впорядковуємо масив значень згідно з колонками в таблиці
    final_row = [full_data.get(h, "") for h in headers]

    worksheet.append_row(final_row)
    return order_id

  except Exception as e:
    st.error(f"Помилка при збереженні замовлення в Таблицю: {e}")
    return ""
