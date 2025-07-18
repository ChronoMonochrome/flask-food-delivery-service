# app/yookassa_service.py
import os
import requests
import base64
import json
from flask import current_app
import uuid # Для ключа идемпотентности
from .logger import logger

class YookassaService:
    def __init__(self, shop_id, secret_key, webhook_base_url):
        self.shop_id = shop_id
        self.secret_key = secret_key
        # URL, куда ЮKassa будет отправлять вебхуки
        self.webhook_url = f"{webhook_base_url}/payment/callback"
        self.api_base_url = "https://api.yookassa.ru/v3"
        self.auth_header = "Basic " + base64.b64encode(f"{self.shop_id}:{self.secret_key}".encode()).decode()

    def _make_request(self, method, path, data=None, headers=None):
        url = f"{self.api_base_url}{path}"
        default_headers = {
            "Content-Type": "application/json",
            "Idempotence-Key": str(uuid.uuid4()), # Уникальный ключ для каждого запроса
            "Authorization": self.auth_header
        }
        if headers:
            default_headers.update(headers)

        try:
            if method == 'POST':
                response = requests.post(url, json=data, headers=default_headers, timeout=10)
            elif method == 'GET':
                response = requests.get(url, headers=default_headers, timeout=10)
            else:
                raise ValueError("Unsupported HTTP method")

            response.raise_for_status() # Вызывает исключение для HTTP ошибок (4xx или 5xx)
            return response.json()
        except requests.exceptions.HTTPError as e:
            current_app.logger.error(f"Yookassa HTTP Error: {e.response.status_code} - {e.response.text}")
            raise
        except requests.exceptions.ConnectionError as e:
            current_app.logger.error(f"Yookassa Connection Error: {e}")
            raise
        except requests.exceptions.Timeout as e:
            current_app.logger.error(f"Yookassa Timeout Error: {e}")
            raise
        except Exception as e:
            current_app.logger.error(f"An unexpected error occurred with Yookassa API: {e}")
            raise

    def create_payment(self, amount, description, order_id, return_url):
        # ЮKassa ожидает сумму в виде строки с двумя знаками после запятой
        amount_str = f"{amount:.2f}"

        # FIX: Truncate the description to Yookassa's maximum allowed length (e.g., 128 characters)
        # This is the most critical part of the fix.
        max_description_length = 128
        truncated_description = description[:max_description_length]
        if len(description) > max_description_length:
            current_app.logger.warning(
                f"Yookassa payment description truncated from {len(description)} to {max_description_length} characters."
            )

        payload = {
            "amount": {
                "value": amount_str,
                "currency": "RUB" # Предполагаем RUB, при необходимости измените
            },
            "confirmation": {
                "type": "redirect",
                "return_url": return_url # Куда пользователь будет перенаправлен после оплаты
            },
            "capture": True, # Автоматически захватывать средства после успешной оплаты
            "description": truncated_description, # Use the truncated description
            "metadata": {
                "order_id": str(order_id), # Храним наш внутренний ID заказа для обработки вебхуков
                "source": "MandarinWebApp"
            },
            "receipt": { # Пример данных для чека (может потребоваться более детальная настройка)
                "customer": {
                    "email": "customer@example.com" # Замените на реальный email пользователя (TODO)
                },
                "items": [
                    {
                        "description": truncated_description, # Use the truncated description here too
                        "quantity": "1.00",
                        "amount": {
                            "value": amount_str,
                            "currency": "RUB"
                        },
                        "vat_code": "1" # Код НДС, уточните в вашей бухгалтерии (TODO)
                    }
                ]
            }
            # "client_ip": request.remote_addr # Это потребует передачи контекста запроса, если нужно
        }
        current_app.logger.info(f"Попытка создания платежа ЮKassa для заказа {order_id} на сумму {amount_str}...")
        try:
            # Используем order_id как ключ идемпотентности, чтобы избежать дублирования платежей
            response_data = self._make_request('POST', '/payments', data=payload, headers={"Idempotence-Key": str(order_id)})
            current_app.logger.info(f"Ответ от создания платежа ЮKassa: {response_data}")
            return response_data
        except Exception as e:
            current_app.logger.error(f"Не удалось создать платеж ЮKassa: {e}")
            # Re-raise the exception here as well, so the /api/orders endpoint can catch it
            raise

    def get_payment_status(self, payment_id):
        current_app.logger.info(f"Проверка статуса платежа ЮKassa для ID: {payment_id}")
        try:
            response_data = self._make_request('GET', f'/payments/{payment_id}')
            current_app.logger.info(f"Ответ статуса платежа ЮKassa: {response_data}")
            return response_data
        except Exception as e:
            current_app.logger.error(f"Не удалось получить статус платежа ЮKassa для {payment_id}: {e}")
            return None
            
# Yookassa
yookassa_shop_id = os.environ.get('YOOKASSA_SHOP_ID')
yookassa_secret_key = os.environ.get('YOOKASSA_SECRET_KEY')
webhook_base_url = os.environ.get('APP_PUBLIC_URL')
yookassa_service = None

if yookassa_shop_id and yookassa_secret_key and webhook_base_url:
    yookassa_service = YookassaService(yookassa_shop_id, yookassa_secret_key, webhook_base_url)
    logger.info("Yookassa Service инициализирован.")
else:
    logger.warning("Yookassa Service не полностью настроен. Проверьте переменные окружения YOOKASSA_SHOP_ID, YOOKASSA_SECRET_KEY, APP_PUBLIC_URL.")

          