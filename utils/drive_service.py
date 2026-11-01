from googleapiclient.discovery import build
import streamlit as st
from utils.sheets_service import get_gspread_client


def get_drive_service():
  """Ініціалізація сервісу Google Drive через авторизацію gspread client."""
  client = get_gspread_client()
  return build("drive", "v3", credentials=client.auth)


def list_subfolders(service, parent_id: str):
  """Допоміжна функція: повертає список папок всередині parent_id."""
  query = (
      f"'{parent_id}' in parents and mimeType='application/vnd.google-apps.folder'"
      " and trashed=false"
  )
  results = (
      service.files()
      .list(q=query, pageSize=100, fields="files(id, name)")
      .execute()
  )
  return results.get("files", [])


def get_drive_hierarchy(root_folder_id: str):
  """Сканує ієрархію папок на Диску: Країна -> Місто -> Об'єкт.

  Повертає словник структури та словник мапінгу 'шлях/до/папки' -> ID.
  """
  service = get_drive_service()
  hierarchy = {}
  folder_ids = {}

  # 1. Рівень: Країни
  countries = list_subfolders(service, root_folder_id)
  for country in countries:
    c_name = country["name"]
    c_id = country["id"]
    folder_ids[c_name] = c_id
    hierarchy[c_name] = {}

    # 2. Рівень: Міста
    cities = list_subfolders(service, c_id)
    for city in cities:
      ci_name = city["name"]
      ci_id = city["id"]
      folder_ids[f"{c_name}/{ci_name}"] = ci_id
      hierarchy[c_name][ci_name] = []

      # 3. Рівень: Об'єкти
      objects = list_subfolders(service, ci_id)
      for obj in objects:
        o_name = obj["name"]
        o_id = obj["id"]
        folder_ids[f"{c_name}/{ci_name}/{o_name}"] = o_id
        hierarchy[c_name][ci_name].append(o_name)

  return hierarchy, folder_ids


def ensure_folder(service, parent_id: str, folder_name: str) -> str:
  """Шукає папку за ім'ям усередині parent_id.

  Якщо не знайдено — створює нову.
  """
  query = (
      f"'{parent_id}' in parents and name='{folder_name}' and"
      " mimeType='application/vnd.google-apps.folder' and trashed=false"
  )
  results = service.files().list(q=query, fields="files(id, name)").execute()
  files = results.get("files", [])

  if files:
    return files[0]["id"]

  file_metadata = {
      "name": folder_name,
      "mimeType": "application/vnd.google-apps.folder",
      "parents": [parent_id],
  }
  folder = service.files().create(body=file_metadata, fields="id").execute()
  return folder.get("id")


def create_order_folder_structure(
    root_folder_id: str,
    country: str,
    city: str,
    object_name: str,
    order_folder_name: str,
) -> str:
  """Створює повну ієрархію папок для замовлення з урахуванням вибору 'Інше'

  та розгортає типові підпапки. Повертає пряме веб-посилання на папку.
  """
  try:
    service = get_drive_service()

    # 1. Створення/перевірка папки Країни
    country_id = ensure_folder(service, root_folder_id, country)

    # 2. Створення/перевірка папки Міста
    city_id = ensure_folder(service, country_id, city)

    # 3. Створення/перевірка папки Об'єкта
    object_id = ensure_folder(service, city_id, object_name)

    # 4. Папка замовлення всередині об'єкта
    order_folder_id = ensure_folder(service, object_id, order_folder_name)

    # 5. Створення типових підпапок
    standard_subfolders = [
        "Дизайн",
        "Конструктив",
        "Фінанси",
        "Інше",
        "Фотозвіт",
    ]
    for sub in standard_subfolders:
      ensure_folder(service, order_folder_id, sub)

    # Отримуємо webViewLink для папки замовлення
    folder_meta = (
        service.files()
        .get(fileId=order_folder_id, fields="webViewLink")
        .execute()
    )
    return folder_meta.get("webViewLink", "")

  except Exception as e:
    st.error(f"Помилка створення папок на Google Диску: {e}")
    return ""
