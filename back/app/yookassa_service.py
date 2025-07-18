# app/yookassa_service.py
import os
import requests
import base64
import json
from flask import current_app
import uuid # Для ключа идемпотентности

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
            "description": description,
            "metadata": {
                "order_id": str(order_id), # Храним наш внутренний ID заказа для обработки вебхуков
                "source": "MandarinWebApp"
            },
            "receipt": { # Пример данных для чека (может потребоваться более детальная настройка)
                "customer": {
                    "email": "customer@example.com" # Замените на реальный email пользователя
                },
                "items": [
                    {
                        "description": description,
                        "quantity": "1.00",
                        "amount": {
                            "value": amount_str,
                            "currency": "RUB"
                        },
                        "vat_code": "1" # Код НДС, уточните в вашей бухгалтерии
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
            return None

    def get_payment_status(self, payment_id):
        current_app.logger.info(f"Проверка статуса платежа ЮKassa для ID: {payment_id}")
        try:
            response_data = self._make_request('GET', f'/payments/{payment_id}')
            current_app.logger.info(f"Ответ статуса платежа ЮKassa: {response_data}")
            return response_data
        except Exception as e:
            current_app.logger.error(f"Не удалось получить статус платежа ЮKassa для {payment_id}: {e}")
            return None