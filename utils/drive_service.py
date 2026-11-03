from googleapiclient.discovery import build
from google.oauth2 import service_account
import streamlit as st


def get_drive_service():
    """Ініціалізація сервісу Google Drive через gcp_service_account у secrets."""
    creds_info = st.secrets["gcp_service_account"]
    credentials = service_account.Credentials.from_service_account_info(
        creds_info, scopes=["https://www.googleapis.com/auth/drive"]
    )
    return build("drive", "v3", credentials=credentials)


def list_subfolders(service, parent_id: str):
    """Допоміжна функція: повертає список папок всередині parent_id."""
    try:
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
    except Exception:
        return []


def get_drive_hierarchy(root_folder_id: str):
    """Сканує ієрархію папок на Диску: Країна -> Місто -> Об'єкт.

    Ігнорує папки 'Інше', щоб уникнути дублювання при формуванні випадаючих списків.
    """
    service = get_drive_service()
    hierarchy = {}
    folder_ids = {}

    if not root_folder_id:
        return hierarchy, folder_ids

    try:
        countries = list_subfolders(service, root_folder_id)
        for country in countries:
            c_name = country["name"]
            if c_name.strip().lower() == "інше":
                continue  # Ігноруємо папку "Інше" при зчитуванні структури

            c_id = country["id"]
            folder_ids[c_name] = c_id
            hierarchy[c_name] = {}

            cities = list_subfolders(service, c_id)
            for city in cities:
                ci_name = city["name"]
                if ci_name.strip().lower() == "інше":
                    continue

                ci_id = city["id"]
                folder_ids[f"{c_name}/{ci_name}"] = ci_id
                hierarchy[c_name][ci_name] = []

                objects = list_subfolders(service, ci_id)
                for obj in objects:
                    o_name = obj["name"]
                    if o_name.strip().lower() == "інше":
                        continue

                    o_id = obj["id"]
                    folder_ids[f"{c_name}/{ci_name}/{o_name}"] = o_id
                    hierarchy[c_name][ci_name].append(o_name)
    except Exception as e:
        st.error(f"Помилка сканування ієрархії Google Диску: {e}")

    return hierarchy, folder_ids


def ensure_folder(service, parent_id: str, folder_name: str) -> str:
    """Шукає папку за ім'ям усередині parent_id, якщо немає — створює."""
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
    """Створює повну ієрархію папок для замовлення."""
    try:
        service = get_drive_service()

        country_id = ensure_folder(service, root_folder_id, country)
        city_id = ensure_folder(service, country_id, city)
        object_id = ensure_folder(service, city_id, object_name)
        order_folder_id = ensure_folder(service, object_id, order_folder_name)

        standard_subfolders = [
            "Дизайн",
            "Конструктив",
            "Фінанси",
            "Інше",
            "Фотозвіт",
        ]
        for sub in standard_subfolders:
            ensure_folder(service, order_folder_id, sub)

        folder_meta = (
            service.files()
            .get(fileId=order_folder_id, fields="webViewLink")
            .execute()
        )
        return folder_meta.get("webViewLink", "")

    except Exception as e:
        st.error(f"Помилка створення папок на Google Диску: {e}")
        return ""
