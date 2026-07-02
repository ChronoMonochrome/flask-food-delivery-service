import os
import json
import logging
from datetime import datetime
from flask import Flask, render_template_string, request, jsonify, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func

# Настройка системного логирования для Docker-контейнера
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')

app = Flask(__name__)

# Изолированная база данных для аналитики
# Изменяем путь, чтобы хранить файлы в отдельной папке /app/data
DATA_DIR = '/app/data'
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR, exist_ok=True)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(DATA_DIR, 'analytics.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

db = SQLAlchemy(app)

# --- МОДЕЛИ ДАННЫХ ДЛЯ АНАЛИТИКИ ---
class AnalyticsOrder(db.Model):
    __tablename__ = 'analytics_orders'
    id = db.Column(db.String(50), primary_key=True)
    user_id = db.Column(db.String(50), nullable=False)
    total = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    city = db.Column(db.String(100), nullable=True)

    items = db.relationship('AnalyticsOrderItem', backref='order', lazy=True, cascade="all, delete-orphan")

class AnalyticsOrderItem(db.Model):
    __tablename__ = 'analytics_order_items'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    order_id = db.Column(db.String(50), db.ForeignKey('analytics_orders.id'), nullable=False)
    product_name = db.Column(db.String(150), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)


# --- ВСПОМОГАТЕЛЬНАЯ ФУНКЦИЯ СБОРА ДАННЫХ АНАЛИТИКИ ---
def get_aggregated_analytics_data():
    """Собирает все метрики из БД для передачи в HTML или JSON API"""
    total_orders = AnalyticsOrder.query.count()
    total_revenue = db.session.query(func.sum(AnalyticsOrder.total)).scalar() or 0.0
    avg_check = total_revenue / total_orders if total_orders > 0 else 0.0

    # Топ-5 популярных товаров
    top_products_query = db.session.query(
        AnalyticsOrderItem.product_name,
        func.sum(AnalyticsOrderItem.quantity).label('total_qty')
    ).group_by(AnalyticsOrderItem.product_name).order_by(func.sum(AnalyticsOrderItem.quantity).desc()).limit(5).all()

    # Сбор данных для графика распределения выручки по городам
    city_stats = db.session.query(
        AnalyticsOrder.city,
        func.sum(AnalyticsOrder.total).label('city_revenue')
    ).group_by(AnalyticsOrder.city).all()

    return {
        "metrics": {
            "total_orders": total_orders,
            "total_revenue": round(total_revenue, 2),
            "avg_check": round(avg_check, 2)
        },
        "top_products": [{"product_name": p[0], "total_qty": int(p[1])} for p in top_products_query],
        "chart_data": {
            "cities": [str(c[0]) for c in city_stats],
            "revenue": [float(c[1]) for c in city_stats]
        }
    }


# --- API ЭНДПОИНТ ДЛЯ ПРИЕМА ДАННЫХ ИЗ МОНОЛИТА ---
@app.route('/api/analytics/orders', methods=['POST'])
def receive_order():
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400

    # [ЛОГИРОВАНИЕ]: Выводим структурированный JSON от монолита для отладки полей
    app.logger.info("=== [ANALYTICS] ПОЛУЧЕН СВЕЖИЙ ЗАКАЗ ИЗ МОНОЛИТА ===")
    app.logger.info(json.dumps(data, indent=2, ensure_ascii=False))

    try:
        # Проверяем защиту от дублей
        existing_order = AnalyticsOrder.query.get(str(data.get('id')))
        if existing_order:
            existing_order.status = data.get('status', 'pending')
            db.session.commit()
            app.logger.info(f"Статус заказа {existing_order.id} успешно обновлен на {existing_order.status}")
            return jsonify({"status": "updated"}), 200

        # [ИСПРАВЛЕНИЕ ГОРОДА]: Проверяем все возможные варианты маппинга ключей от монолита
        delivery_info = data.get('deliveryInfo') or {}
        city_name = (
            data.get('city') or
            delivery_info.get('city_name') or
            delivery_info.get('city') or
            delivery_info.get('cityName') or
            data.get('cityName') or
            "Не указан"
        )

        app.logger.info(f"Определен город для записи в аналитику: {city_name}")

        created_at_str = data.get('createdAt')
        created_at_dt = datetime.fromisoformat(created_at_str.replace('Z', '+00:00')) if created_at_str else datetime.utcnow()

        new_analytics_order = AnalyticsOrder(
            id=str(data.get('id')),
            user_id=str(data.get('userId')),
            total=float(data.get('total', 0.0)),
            status=data.get('status', 'pending'),
            created_at=created_at_dt,
            city=city_name
        )
        db.session.add(new_analytics_order)

        # Распаковываем позиции товаров
        for item in data.get('items', []):
            product_data = item.get('product')
            if product_data:
                product_name = product_data.get('name')
                product_price = float(product_data.get('price', 0.0))
            elif item.get('customWokData'):
                product_name = item.get('customName') or "Кастомный Вок"
                product_price = float(item.get('customPrice', 0.0))
            else:
                continue

            analytics_item = AnalyticsOrderItem(
                order_id=new_analytics_order.id,
                product_name=product_name,
                quantity=int(item.get('quantity', 1)),
                price=product_price
            )
            db.session.add(analytics_item)

        db.session.commit()
        app.logger.info(f"Заказ {new_analytics_order.id} сохранен в базу аналитики.")
        return jsonify({"status": "success", "message": "Order analytical data saved"}), 201

    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Ошибка при сохранении аналитики: {str(e)}")
        return jsonify({"error": str(e)}), 500


# --- API ЭНДПОИНТ ДЛЯ ПЕРИОДИЧЕСКОГО ОБНОВЛЕНИЯ ДАННЫХ (AJAX POLLING) ---
@app.route('/api/analytics/stats', methods=['GET'])
def get_stats_json():
    """Возвращает свежие агрегированные данные для JS таймера"""
    return jsonify(get_aggregated_analytics_data())


# --- UI НА BOOTSTRAP 5 + CHART.JS (БЕЗ ПЛАШКИ POC И С ДИНАМИЧЕСКИМ ТАЙМЕРОМ) ---
BOOTSTRAP_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>Mandarin Delivery | Панель Аналитики</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body class="bg-light">

    <nav class="navbar navbar-dark bg-dark shadow-sm mb-4">
        <div class="container">
            <a class="navbar-brand" href="#">
                <i class="bi bi-bar-chart-line-fill me-2 text-warning"></i>
                Mandarin Analytics
            </a>
            <span class="navbar-text text-white-50">
                <span class="spinner-grow spinner-grow-sm text-success me-1" role="status" style="animation-duration: 1.5s;"></span>
                Данные обновляются в реальном времени
            </span>
        </div>
    </nav>

    <div class="container mb-5">
        <div class="row g-3 mb-4">
            <div class="col-md-4">
                <div class="card border-0 shadow-sm text-white bg-primary">
                    <div class="card-body d-flex justify-content-between align-items-center">
                        <div>
                            <h6 class="text-uppercase text-white-50 mutable-label m-0">Общая Выручка</h6>
                            <h2 class="fw-bold m-0 mt-1" id="total-revenue">{{ "%.2f"|format(metrics.total_revenue) }} ₽</h2>
                        </div>
                        <i class="bi bi-currency-ruble fs-1 text-white-50"></i>
                    </div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="card border-0 shadow-sm text-white bg-success">
                    <div class="card-body d-flex justify-content-between align-items-center">
                        <div>
                            <h6 class="text-uppercase text-white-50 mutable-label m-0">Всего заказов</h6>
                            <h2 class="fw-bold m-0 mt-1" id="total-orders">{{ metrics.total_orders }}</h2>
                        </div>
                        <i class="bi bi-box-seam fs-1 text-white-50"></i>
                    </div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="card border-0 shadow-sm text-white bg-warning">
                    <div class="card-body d-flex justify-content-between align-items-center">
                        <div>
                            <h6 class="text-uppercase text-dark-50 mutable-label text-dark m-0">Средний Чек</h6>
                            <h2 class="fw-bold text-dark m-0 mt-1" id="avg-check">{{ "%.2f"|format(metrics.avg_check) }} ₽</h2>
                        </div>
                        <i class="bi bi-wallet2 fs-1 text-dark-50 text-dark"></i>
                    </div>
                </div>
            </div>
        </div>

        <div class="row g-4">
            <div class="col-lg-7">
                <div class="card border-0 shadow-sm p-3 mb-4">
                    <h5 class="card-title fw-bold text-secondary mb-3">Динамика продаж по городам</h5>
                    <div style="height: 300px;"><canvas id="cityChart"></canvas></div>
                </div>
            </div>

            <div class="col-lg-5">
                <div class="card border-0 shadow-sm p-3 h-100">
                    <h5 class="card-title fw-bold text-secondary mb-3">Топ-5 популярных блюд</h5>
                    <ul class="list-group list-group-flush" id="top-products-list">
                        {% for item in top_products %}
                        <li class="list-group-item d-flex justify-content-between align-items-center px-0">
                            <div>
                                <span class="fw-semibold text-dark">{{ item.product_name }}</span>
                            </div>
                            <span class="badge bg-secondary rounded-pill">Продано: {{ item.total_qty }} шт.</span>
                        </li>
                        {% else %}
                        <li class="list-group-item text-center text-muted py-4">Нет данных о проданных товарах</li>
                        {% endfor %}
                    </ul>
                </div>
            </div>
        </div>
    </div>

    <script>
        // Инициализация базовых массивов из шаблонизатора Flask при первой загрузке
        let cityLabels = {{ chart_data.cities | tojson }};
        let cityValues = {{ chart_data.revenue | tojson }};

        const ctx = document.getElementById('cityChart').getContext('2d');
        const cityChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: cityLabels,
                datasets: [{
                    label: 'Выручка по городам (₽)',
                    data: cityValues,
                    backgroundColor: 'rgba(54, 162, 235, 0.7)',
                    borderColor: 'rgba(54, 162, 235, 1)',
                    borderWidth: 1,
                    borderRadius: 5
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: { y: { beginAtZero: true } }
            }
        });

        // Функция опроса API аналитики для обновления в реальном времени без перезагрузки
        function pollAnalyticsAPI() {
            fetch('/api/analytics/stats')
                .then(response => response.json())
                .then(data => {
                    // 1. Обновляем блоки основных метрик
                    document.getElementById('total-revenue').innerText = data.metrics.total_revenue.toFixed(2) + ' ₽';
                    document.getElementById('total-orders').innerText = data.metrics.total_orders;
                    document.getElementById('avg-check').innerText = data.metrics.avg_check.toFixed(2) + ' ₽';

                    // 2. Обновляем график распределения по городам
                    cityChart.data.labels = data.chart_data.cities;
                    cityChart.data.datasets[0].data = data.chart_data.revenue;
                    cityChart.update(); // Плавное обновление анимации столбцов

                    // 3. Динамически пересобираем список популярных блюд
                    const listContainer = document.getElementById('top-products-list');
                    listContainer.innerHTML = '';

                    if (data.top_products.length === 0) {
                        listContainer.innerHTML = '<li class="list-group-item text-center text-muted py-4">Нет данных о проданных товарах</li>';
                    } else {
                        data.top_products.forEach(item => {
                            const li = document.createElement('li');
                            li.className = 'list-group-item d-flex justify-content-between align-items-center px-0';
                            li.innerHTML = `
                                <div>
                                    <span class="fw-semibold text-dark">${item.product_name}</span>
                                </div>
                                <span class="badge bg-secondary rounded-pill">Продано: ${item.total_qty} шт.</span>
                            `;
                            listContainer.appendChild(li);
                        });
                    }
                })
                .catch(err => console.error('Ошибка автоматического обновления аналитики:', err));
        }

        // Интервал выполнения: запрашивать данные каждые 5 секунд (5000 миллисекунд)
        setInterval(pollAnalyticsAPI, 5000);
    </script>
</body>
</html>
"""

# --- ФИКС: РЕДИРЕКТ С ГЛАВНОЙ СТРАНИЦЫ НА DASHBOARD ---
@app.route('/')
def root_redirect():
    """Перенаправляет пользователя с корня сайта на панель аналитики"""
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    # Получаем актуальный срез данных из БД при открытии страницы
    data = get_aggregated_analytics_data()
    return render_template_string(
        BOOTSTRAP_TEMPLATE,
        metrics=data["metrics"],
        top_products=data["top_products"],
        chart_data=data["chart_data"]
    )


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5002, debug=True)
