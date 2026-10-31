import gspread
import streamlit as st
from utils.sheets_service import get_gspread_client


def create_order_folder_structure(parent_folder_id: str, order_name: str) -> str:
  """Створює структуру папок на Google Диску для нового замовлення

  та повертає веб-посилання на створену головну папку замовлення.
  """
  client = get_gspread_client()
  # Використовуємо gspread/gdrive інтеграцію через той самий клієнт сервісного акаунта
  # (у gspread є доступ до API Google Drive через client.drive_service або прямі виклики)

  try:
    drive_service = client.auth.http  # або стандартний googleapiclient виклик
    # Для простоти і сумісності з gspread використаємо офіційний гугл клієнт чи gspread обгортки
    # Але найпростіше використати gspread.Client.create_folder якщо доступно, або через googleapiclient.

    # Альтернативно через googleapiclient (якщо підключено в requirements):
    from googleapiclient.discovery import build

    service = build("drive", "v3", credentials=client.auth)

    # 1. Створюємо головну папку замовлення всередині батьківської папки напрямку
    folder_metadata = {
        "name": order_name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parent_folder_id] if parent_folder_id else [],
    }

    main_folder = (
        service.files().create(body=folder_metadata, fields="id, webViewLink").execute()
    )
    main_folder_id = main_folder.get("id")
    main_folder_link = main_folder.get("webViewLink")

    # 2. Створюємо стандартні підпапки
    subfolders = ["Дизайн", "Конструктив", "Фінанси", "Інше", "Фотозвіт"]
    for sub_name in subfolders:
      sub_metadata = {
          "name": sub_name,
          "mimeType": "application/vnd.google-apps.folder",
          "parents": [main_folder_id],
      }
      service.files().create(body=sub_metadata, fields="id").execute()

    return main_folder_link

  except Exception as e:
    st.error(f"Помилка створення папок на Google Диску: {e}")
    return ""
