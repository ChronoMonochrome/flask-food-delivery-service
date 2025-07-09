## Структура проекта

```
├── app/
│   ├── __init__.py
│   ├── logger.py
│   ├── models.py
│   ├── routes.py
│   └── templates/
├── bot/
│   ├── __init__.py
│   └── main.py
├── certs/
│   ├── fullchain.pem     # SSL-сертификат
│   └── privkey.pem       # закрытый ключ SSL
├── Dockerfile.nginx
├── Dockerfile.bot
├── Dockerfile.web
├── docker-compose.yml
├── nginx.conf
└── requirements.txt

```

## Настройка

### SSL-сертификаты

Для работы Nginx с HTTPS потребуются SSL-сертификаты. Создайте каталог `certs` в корне проекта и поместите в него файлы `fullchain.pem` и `privkey.pem`.

```
mkdir certs
# Поместите fullchain.pem и privkey.pem в каталог certs

```

### Переменные окружения

Некоторые конфигурации передаются в контейнеры через переменные окружения, определенные в `docker-compose.yml`. 

-   `db` сервис:
    
    -   `MYSQL_ROOT_PASSWORD`: пароль для пользователя root MySQL.
        
    -   `MYSQL_DATABASE`: Имя базы данных (по умолчанию `mydatabase`).
        
    -   `MYSQL_USER`: Пользователь базы данных (по умолчанию `user`).
        
    -   `MYSQL_PASSWORD`: Пароль для пользователя базы данных.
        
-   `web` сервис:
    
    -   `DATABASE_URL`: Строка подключения к базе данных.
        
    -   `BOT_TOKEN`: Токен Telegram-бота, полученный от BotFather.
        
    -   `WEB_APP_URL`: URL веб-приложения (должен соответствовать `server_name` в `nginx.conf`).
        
    -   `SECRET_KEY`: Секретный ключ для Flask-приложения.
        
-   `IIKO` API:
    -   `IIKO_API_URL`: URL API IIKO.
        
    -   `IIKO_API_TOKEN`: Токен API IIKO.

## Запуск приложения

Для сборки и запуска всего стека приложения выполните следующую команду в корневом каталоге проекта:

```
docker compose up --build -d

```

-   `--build`: Перестраивает образы Docker для сервисов `web`, `bot` и `nginx`. Это необходимо при каждом изменении в `Dockerfile.*`, `requirements.txt` или исходном коде приложения/фронтенда.
    
-   `-d`: Запускает контейнеры в отсоединенном режиме (в фоновом режиме).

### Первичная инициализация базы данных

**Выполните миграции изнутри контейнера `web`**:

```
docker compose run --rm web flask db upgrade
```

## Доступ к приложению

-   **Веб-приложение:** После запуска веб-приложение доступно через Nginx по адресу, указанному в `nginx.conf` 
-   **Telegram-бот:** Бот начнет опрашивать Telegram API. Взаимодействуйте с ним, отправив `/start` в Telegram.


## API

Веб-приложение предоставляет RESTful API для взаимодействия фронтенда с бэкендом. API реализован с использованием Flask-RESTx, и его документация доступна по адресу `/api/doc` после запуска приложения.

### Доступные эндпоинты:

-   **`/api/categories`**
    
    -   **Метод:** `GET`
    -   **Описание:** Получить список всех категорий продуктов.
    -   **Пример ответа (JSON):**
        
        JSON
        
        ```
        [
            { "id": "1", "name": "Пицца", "icon": "🍕", "color": "from-red-400 to-red-600" },
            { "id": "2", "name": "Бургеры", "icon": "🍔", "color": "from-yellow-400 to-orange-500" }
        ]
        
        ```
        
-   **`/api/products`**
    
    -   **Метод:** `GET`
    -   **Описание:** Получить список всех продуктов. Поддерживает фильтрацию по ID категории.
    -   **Параметры запроса:**
        -   `categoryId` (строка, опционально): ID категории для фильтрации продуктов.
    -   **Пример ответа (JSON):**
        
        JSON
        
        ```
        [
            {
                "id": "1",
                "name": "Маргарита",
                "description": "Классическая пицца...",
                "price": 590,
                "image": "...",
                "categoryId": "1",
                "nutrition": { "calories": 250, "protein": 12, "fat": 10, "carbs": 30 },
                "ingredients": ["тесто", "томатный соус"],
                "availableAddons": [{"id": "ketchup", "name": "Кетчуп", "price": 15}],
                "recommendations": [{"id": "cola", "name": "Кола 0.5л", "price": 120, "image": "..."}]
            }
        ]
        
        ```
        
-   **`/api/products/<string:product_id>`**
    
    -   **Метод:** `GET`
    -   **Описание:** Получить информацию об одном продукте по его ID.
    -   **Пример ответа (JSON):** (аналогично элементу из `/api/products` списка, но для одного продукта)
-   **`/api/orders`**
    
    -   **Метод:** `GET`
    -   **Описание:** Получить список всех заказов.
    -   **Пример ответа (JSON):**
        
        JSON
        
        ```
        [
            {
                "id": "1",
                "items": [
                    {
                        "product": { "id": "1", "name": "Маргарита", "price": 590, "image": "...", "categoryId": "1" },
                        "quantity": 1,
                        "selectedAddons": [{"id": "ketchup", "name": "Кетчуп", "price": 15}],
                        "selectedRecommendations": [{"id": "cola", "name": "Кола 0.5л", "price": 120, "image": "..."}]
                    }
                ],
                "total": 725,
                "deliveryInfo": { "address": "ул. Пушкина, д. 10, кв. 5", "phone": "+7 (999) 123-45-67", "paymentMethod": "cash", "comment": "Домофон не работает" },
                "status": "delivering",
                "createdAt": "2025-06-25T11:52:53.000Z",
                "estimatedDelivery": "2025-06-25T12:27:53.000Z"
            }
        ]
        
        ```
        
    -   **Метод:** `POST`
    -   **Описание:** Создать новый заказ. Тело запроса должно содержать детали заказа, включая товары и информацию о доставке.
    -   **Ожидаемое тело запроса (JSON):**
        
        JSON
        
        ```
        {
            "items": [
                {
                    "product": { "id": "1" }, // Достаточно ID продукта
                    "quantity": 1,
                    "selectedAddons": [{"id": "ketchup"}], // Достаточно ID аддона
                    "selectedRecommendations": [{"id": "cola"}] // Достаточно ID рекомендации
                }
            ],
            "deliveryInfo": {
                "address": "ул. Пушкина, д. 10, кв. 5",
                "phone": "+7 (999) 123-45-67",
                "paymentMethod": "cash",
                "comment": "Домофон не работает"
            },
            "total": 725 // Опционально, будет пересчитан на сервере
        }
        
        ```
        
    -   **Пример успешного ответа (JSON):** (Аналогично GET-ответу для одного заказа, со статусом `201 Created`)
-   **`/api/addons`**
    
    -   **Метод:** `GET`
    -   **Описание:** Предоставляет данные о доступных дополнениях (аддонах) для приложения.
    -   **Пример ответа (JSON):**
        
        JSON
        
        ```
        [
            { "id": "ketchup", "name": "Кетчуп", "price": 15 },
            { "id": "mayo", "name": "Майонез", "price": 15 }
        ]
        
        ```
        
-   **`/api/recommendations`**
    
    -   **Метод:** `GET`
    -   **Описание:** Возвращает список рекомендованных товаров.
    -   **Пример ответа (JSON):**
        
        JSON
        
        ```
        [
            { "id": "cola", "name": "Кола 0.5л", "price": 120, "image": "..." },
            { "id": "fries", "name": "Картофель фри", "price": 180, "image": "..." }
        ]
        ```

## Логи

-   Для Flask-приложения (web):
    
    ```
    docker compose logs web
    
    ```
    
-   Для Telegram-бота (bot):
    
    ```
    docker compose logs bot
    
    ```
    
-   Для Nginx:
    
    ```
    docker compose logs nginx
    
    ```
    
-   Для базы данных MySQL:
    
    ```
    docker compose logs db
    
    ```
    
-   Для просмотра логов в реальном времени:
    
    ```
    docker compose logs -f <имя_сервиса> # Например, docker compose logs -f web
    docker compose logs -f             # Для всех сервисов
    
    ```
    

## Остановка приложения

Чтобы остановить и удалить контейнеры, сети и тома (если они не названы специально для сохранения данных), выполните:

```
docker compose down

```

Если вы хотите удалить также тома данных (и потерять данные базы данных), используйте:

```
docker compose down -v
```
