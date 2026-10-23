# Aéza Churn Risk Analyzer

> **"Aéza - это быстрый хостинг"**

Аналитическая система выявления клиентов хостинга с высоким риском оттока (Middle RND). Помогает маркетологам и аналитикам заранее находить пользователей, которые могут не продлить услуги, объясняет причины возникновения риска и рассчитывает потенциальные финансовые потери бизнеса.

---

## 🚀 Быстрый запуск (Docker Compose)

Решение полностью контейнеризировано и запускается одной командой:

```bash
docker compose up --build -d
```

После старта будут доступны:
- 🌐 **Веб-панель (UI):** [http://localhost:3000](http://localhost:3000)
- ⚙️ **FastAPI Backend & Swagger:** [http://localhost:8000/api/v1/docs](http://localhost:8000/api/v1/docs)
- 📊 **Prometheus Metrics:** [http://localhost:8000/metrics](http://localhost:8000/metrics)
- 🗄 **PostgreSQL Database:** `localhost:5432` (user: `postgres`, pass: `postgres`, db: `aezachurn`)

### Данные для входа в панель:
- **Логин:** `admin`
- **Пароль:** `admin123`

---

## 🧠 Описание математической модели (Risk-Score)

### 1. Формула Risk-Score
Модель оценивает вероятность оттока каждого клиента на основе 5 нормализованных факторов $f_i \in [0, 1]$ и настраиваемых весов $w_i$:

$$\text{Risk-Score} = \frac{\sum_{i=1}^{n} w_i \cdot f_i}{\sum_{i=1}^{n} w_i}$$

#### Факторы риска:
1. **$f_{\text{no\_autoprolong}}$ (Отключение автопродления):** Доля активных/приостановленных услуг клиента с `autoProlong = false`.
2. **$f_{\text{balance\_insufficient}}$ (Нехватка баланса):** Дефицит средств для продления услуг, срок которых истекает в ближайший горизонт прогноза:
   $$\text{Deficit} = \max\left(0, \frac{\text{RequiredRenewal} - \text{EffectiveBalance}}{\text{RequiredRenewal}}\right)$$
   где $\text{EffectiveBalance} = \text{balance} + (\text{bonusBalance if unlocked else } 0)$.
3. **$f_{\text{prolong\_wait}}$ (Зависшие услуги):** Наличие и доля услуг в критическом статусе `prolong_wait` (до удаления остается $\le 5$ дней).
4. **$f_{\text{expiring\_soon}}$ (Срочное истечение):** Доля услуг со сроком окончания $\le 48$ часов при отсутствии автопродления.
5. **$f_{\text{failed\_tx}}$ (Ошибки транзакций):** Отношение неуспешных транзакций (`not_performed`) к общему числу транзакций клиента.

### 2. Пороги классификации:
- **Высокий риск (`high`):** $\text{Risk-Score} \ge 0.65$
- **Средний риск (`medium`):** $0.35 \le \text{Risk-Score} < 0.65$
- **Низкий риск (`low`):** $\text{Risk-Score} < 0.35$
- **Без оценки (`unrated`):** Клиенты без услуг и пополнений (недостаток данных).
- **Шкала лояльности:** $\text{Loyalty-Score} = 1.0 - \text{Risk-Score}$.

### 3. Денежная оценка потерь (Financial Impact)
Потери оцениваются в еврокопейках (1 € = 100 единиц) через взвешенный ежемесячный доход (Monthly Recurring Revenue):
$$\text{MRR} = \sum_{\text{active services}} \text{price} \cdot \text{MonthlyMultiplier}$$
$$\text{Potential Loss} = \text{MRR} \cdot \text{Risk-Score}$$

---

## ⚡ Живое обновление (Live Updates)

При изменении коэффициентов модели через панель или загрузке нового датасета (`PUT /api/v1/source/snapshot`) сервер оповещает UI через **WebSocket** (`/ws`). Пересчет рейтингов, графиков и денежных сумм на клиенте происходит **мгновенно без перезагрузки страницы**.

---

## 🔌 API Эндпоинты

Все обязательные эндпоинты защищены JWT Bearer токеном:

| Метод | Эндпоинт | Назначение |
|---|---|---|
| `POST` | `/api/v1/auth/login` | Авторизация по логину/паролю |
| `GET` | `/api/v1/auth/me` | Получение профиля текущего пользователя |
| `POST` | `/api/v1/auth/logout` | Завершение сессии |
| `GET` | `/api/v1/customers` | Список клиентов (сортировка по всем полям, пагинация, фильтры) |
| `GET` | `/api/v1/customers/{id}` | Полная карточка клиента, список услуг, факторы риска и объяснения |
| `GET` | `/api/v1/analytics/summary` | Сводная аналитика потерь, распределение риска, график оттока |
| `GET` | `/api/v1/model/settings` | Текущие веса и пороги модели |
| `PATCH`| `/api/v1/model/settings` | Изменение настроек с автоматическим пересчетом и WS-уведомлением |
| `PUT` | `/api/v1/source/snapshot` | Загрузка/замена датасета (`data.json`) с пересчетом |
| `GET` | `/metrics` | Метрики Prometheus (клиенты по уровням риска, сумма потерь) |
| `GET` | `/api/v1/docs` | Интерактивная документация Swagger UI |

OpenAPI спецификация доступна в файле [openapi.yaml](openapi.yaml).

---

## 🧩 Расширяемость (Добавление нового признака)

Архитектура системы спроектирована по принципу открытости к расширению:
1. В `backend/app/schemas/all_schemas.py` добавить поле в `WeightsConfig`:
   ```python
   w_my_new_feature: float = Field(0.15, description="Новый признак")
   ```
2. В `backend/app/services/risk_engine.py` рассчитать признак $f \in [0, 1]$ и добавить в расчет `score`:
   ```python
   f_my_new_feature = ...
   ```
3. Новый признак автоматически появится в Swagger схеме, форме настроек веб-панели и расчетах.
