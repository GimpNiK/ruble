from datetime import datetime, timedelta

from kivy.app import App
from kivy.lang import Builder
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen, ScreenManager, SlideTransition
from kivy.clock import Clock

from charts import ChartImage, PieChart
from crypto_utils import decrypt_database, encrypt_database, remove_plain_database
from models import (
    Category,
    FinancialGoal,
    FormatPeriod,
    Notification,
    RegularTransaction,
    Transaction,
    TransactionType,
    add_financial_goal,
    add_regular_transaction,
    add_transaction,
    check_password,
    create_database,
    delete_by_model,
    get_balance,
    get_categories,
    get_daily_totals,
    get_expenses_by_category,
    get_monthly_profit,
    get_transactions,
    is_registered,
    set_password,
    sync_payment_notifications,
    process_due_regular_transactions,  # <--- ДОБАВЛЕНО
    db,
)

# Загрузка KV файлов
for kv_file in ("views/css.kv", "views/auth.kv", "views/login.kv", "views/main.kv"):
    Builder.load_file(kv_file)


def _default_period():
    end = datetime.now()
    start = end - timedelta(days=30)
    return start, end


def _fmt_date(value):
    if isinstance(value, datetime):
        return value.strftime("%d.%m.%Y")
    return str(value)


def _fmt_sum(value, sign=""):
    return f"{sign}{float(value):,.2f} ₽".replace(",", " ")


class ListItem(BoxLayout):
    item_id = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def setup(self, item_id, date_text, sum_text, descr_text, on_delete):
        self.item_id = item_id
        self.ids.date_label.text = date_text
        self.ids.sum_label.text = sum_text
        self.ids.descr_label.text = descr_text
        self.ids.delete_btn.bind(on_press=lambda *_: on_delete(self.item_id))


class LoginScreen(Screen):
    def on_enter(self):
        App.get_running_app().title = "Вход в систему"

    def try_login(self):
        password = self.ids.password.text
        app = App.get_running_app()
        if not check_password(password):
            self.ids.message.text = "Неверный PIN-код. Повторите попытку."
            return
        if not decrypt_database(password):
            self.ids.message.text = "Не удалось расшифровать базу данных."
            return
        app.unlock(password)
        create_database(drop_existing=False)
        self.manager.current = "MainScreen"


class AuthScreen(Screen):
    def on_enter(self):
        App.get_running_app().title = "Регистрация"

    def register(self):
        pin = self.ids.password.text
        if len(pin) != 4 or not pin.isdigit():
            self.ids.message.text = "PIN-код должен состоять из 4 цифр."
            return
        if pin != self.ids.password_repeat.text:
            self.ids.message.text = "PIN-коды не совпадают."
            return
        set_password(pin)
        app = App.get_running_app()
        app.unlock(pin)
        create_database(drop_existing=True)
        self.manager.current = "MainScreen"


class MainScreen(Screen):
    page_size = 5
    tx_offset = 0
    regular_offset = 0

    def on_enter(self):
        App.get_running_app().title = "Ruble — личные финансы"
        sync_payment_notifications()
        self.refresh_all()
        # Обновляем графики с задержкой, чтобы они успели получить размер
        Clock.schedule_once(lambda dt: self._update_charts_with_period(), 0.3)

    def _update_charts_with_period(self):
        start, end = self._period()
        self.update_charts(start, end)

    def refresh_all(self):
        db.commit()
        self.ids.balance.text = _fmt_sum(get_balance())
        profit = get_monthly_profit()
        sign = "+" if profit >= 0 else ""
        self.ids.monthly_profit.text = _fmt_sum(profit, sign)

        start, end = self._period()

        self.tx_offset = 0
        self.regular_offset = 0
        self.load_notifications()
        self.load_transactions()
        self.load_regular_transactions()
        #self.load_goals()
        self.update_charts(start, end)

    def _period(self):
        try:
            start = datetime.strptime(self.ids.start_date_input.text, "%d.%m.%Y")
            end = datetime.strptime(self.ids.end_date_input.text, "%d.%m.%Y")
            end = end.replace(hour=23, minute=59, second=59)
            return start, end
        except (ValueError, AttributeError):
            start, end = _default_period()
            if hasattr(self, "ids"):
                self.ids.start_date_input.text = start.strftime("%d.%m.%Y")
                self.ids.end_date_input.text = end.strftime("%d.%m.%Y")
            return start, end

    def apply_period(self):
        self.refresh_all()
        # После обновления данных перерисовываем графики
        start, end = self._period()
        self.update_charts(start, end)

    def reset_period(self):
        start, end = _default_period()
        self.ids.start_date_input.text = start.strftime("%d.%m.%Y")
        self.ids.end_date_input.text = end.strftime("%d.%m.%Y")
        self.refresh_all()
        self.update_charts(start, end)

    def load_notifications(self):
        self.ids.notifications.clear_widgets()
        items = (
            db.query(Notification)
            .order_by(Notification.date.asc())
            .limit(20)
            .all()
        )
        for item in items:
            widget = ListItem()
            widget.setup(
                item.id,
                _fmt_date(item.date),
                _fmt_sum(item.sum),
                item.descr or "",
                self.delete_notification,
            )
            self.ids.notifications.add_widget(widget)

    def load_transactions(self, direction=0):
        if direction == 0:
            self.tx_offset = max(0, self.tx_offset)
        else:
            self.tx_offset = max(0, self.tx_offset + direction * self.page_size)

        start, end = self._period()
        all_items = get_transactions(start, end)
        total = len(all_items)

        if total > 0:
            self.tx_offset = min(self.tx_offset, total - 1)
        else:
            self.tx_offset = 0

        chunk = all_items[self.tx_offset : self.tx_offset + self.page_size]

        self.ids.transactions.clear_widgets()
        for item in chunk:
            sign = "+" if item.transaction_type == TransactionType.INCOME else "-"
            cat = item.category.name if item.category else "—"
            widget = ListItem()
            widget.setup(
                item.id,
                _fmt_date(item.date),
                _fmt_sum(item.sum, sign),
                f"{item.name or '—'} | {cat}",
                self.delete_transaction,
            )
            self.ids.transactions.add_widget(widget)

        if total == 0:
            self.ids.tx_page_label.text = "0 из 0"
        else:
            shown_to = min(self.tx_offset + self.page_size, total)
            self.ids.tx_page_label.text = f"{self.tx_offset + 1}-{shown_to} из {total}"

    def load_regular_transactions(self, direction=0):
        if direction == 0:
            self.regular_offset = max(0, self.regular_offset)
        else:
            self.regular_offset = max(0, self.regular_offset + direction * self.page_size)

        all_items = db.query(RegularTransaction).order_by(RegularTransaction.id.desc()).all()
        total = len(all_items)

        if total > 0:
            self.regular_offset = min(self.regular_offset, total - 1)
        else:
            self.regular_offset = 0

        chunk = all_items[self.regular_offset : self.regular_offset + self.page_size]

        self.ids.regular_transactions.clear_widgets()
        for item in chunk:
            sign = "+" if item.transaction_type == TransactionType.INCOME else "-"
            due = _fmt_date(item.next_due_date())
            cat = item.category.name if item.category else "—"
            widget = ListItem()
            widget.setup(
                item.id,
                due,
                _fmt_sum(item.sum, sign),
                f"{item.name or '—'} | {item.format_period.value if hasattr(item.format_period, 'value') else item.format_period} | {cat}",
                self.delete_regular,
            )
            self.ids.regular_transactions.add_widget(widget)

        if total == 0:
            self.ids.reg_page_label.text = "0 из 0"
        else:
            shown_to = min(self.regular_offset + self.page_size, total)
            self.ids.reg_page_label.text = f"{self.regular_offset + 1}-{shown_to} из {total}"

    def load_goals(self):
        self.ids.goals.clear_widgets()
        for goal in db.query(FinancialGoal).order_by(FinancialGoal.deadline.asc()).all():
            progress = 0 if goal.target_sum == 0 else min(goal.current_sum / goal.target_sum * 100, 100)
            deadline = _fmt_date(goal.deadline) if goal.deadline else "—"
            row = GoalItem()
            row.setup(goal.id, goal.name, goal.current_sum, goal.target_sum, progress, deadline)
            self.ids.goals.add_widget(row)

    def update_charts(self, start, end):
        # Линейный график
        labels, income, expense = get_daily_totals(start, end)
        self.ids.line_chart.render_line_chart(labels, income, expense)

        # Круговая диаграмма
        data = get_expenses_by_category(start, end)
        if not data:
            categories, values = ["Нет данных"], [0]
        else:
            categories, values = zip(*data)
            categories, values = list(categories), list(values)
            # Убираем нулевые значения для красоты
            filtered = [(c, v) for c, v in zip(categories, values) if v > 0]
            if filtered:
                categories, values = zip(*filtered)
                categories, values = list(categories), list(values)
            else:
                categories, values = ["Нет данных"], [0]
        self.ids.pie_chart.render(categories, values)

    def delete_notification(self, item_id):
        delete_by_model(Notification, item_id)
        self.load_notifications()

    def delete_transaction(self, item_id):
        delete_by_model(Transaction, item_id)
        self.refresh_all()

    def delete_regular(self, item_id):
        # Удаляем связанные уведомления
        db.query(Notification).filter(Notification.regular_transaction_id == item_id).delete()
        delete_by_model(RegularTransaction, item_id)
        sync_payment_notifications()
        self.refresh_all()

    def open_transaction_popup(self):
        TransactionPopup(on_save=self.refresh_all).open()

    def open_regular_popup(self):
        RegularTransactionPopup(on_save=self.refresh_all).open()

    def open_goal_popup(self):
        GoalPopup(on_save=self.load_goals).open()


class GoalItem(BoxLayout):
    goal_id = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def setup(self, goal_id, name, current, target, progress, deadline):
        self.goal_id = goal_id
        self.ids.name_label.text = name
        self.ids.progress_label.text = f"{progress:.0f}% ({_fmt_sum(current)} / {_fmt_sum(target)})"
        self.ids.deadline_label.text = f"Срок: {deadline}"


class BaseFormPopup(Popup):
    def __init__(self, on_save=None, **kwargs):
        super().__init__(**kwargs)
        self.on_save_callback = on_save

    def _category_spinner_values(self, transaction_type):
        cats = get_categories(transaction_type)
        if not cats:
            return ["Прочее"]
        return [c.name for c in cats]

    def _category_id_by_name(self, name, transaction_type):
        cats = get_categories(transaction_type)
        if not cats:
            # Создаём категорию "Прочее"
            cat = Category(name="Прочее", transaction_type=transaction_type)
            db.add(cat)
            db.commit()
            return cat.id
        
        for cat in cats:
            if cat.name == name:
                return cat.id
        
        # Если категория не найдена, возвращаем первую
        return cats[0].id


class TransactionPopup(BaseFormPopup):
    def __init__(self, on_save=None, **kwargs):
        super().__init__(
            title="Новая транзакция",
            size_hint=(0.92, 0.75),
            auto_dismiss=False,
            on_save=on_save,
            **kwargs,
        )
        from kivy.uix.textinput import TextInput
        from kivy.uix.spinner import Spinner
        from kivy.uix.button import Button
        from kivy.uix.label import Label

        layout = BoxLayout(orientation="vertical", spacing=8, padding=10)

        self.date_input = TextInput(text=datetime.now().strftime("%d.%m.%Y"), multiline=False)
        self.sum_input = TextInput(text="", multiline=False, input_filter="float")
        self.desc_input = TextInput(text="", multiline=False)
        self.type_spinner = Spinner(
            text="Расход",
            values=("Доход", "Расход"),
            size_hint_y=None,
            height="40dp",
        )
        self.cat_spinner = Spinner(
            text="Прочее",
            values=self._category_spinner_values(TransactionType.EXPENSE),
            size_hint_y=None,
            height="40dp",
        )
        self.type_spinner.bind(text=self._on_type_change)

        for label, widget in (
            ("Дата (ДД.ММ.ГГГГ)", self.date_input),
            ("Сумма", self.sum_input),
            ("Тип", self.type_spinner),
            ("Категория", self.cat_spinner),
            ("Описание", self.desc_input),
        ):
            layout.add_widget(Label(text=label, size_hint_y=None, height="24dp"))
            layout.add_widget(widget)

        buttons = BoxLayout(size_hint_y=None, height="44dp", spacing=8)
        buttons.add_widget(Button(text="Отмена", on_press=lambda *_: self.dismiss()))
        buttons.add_widget(Button(text="Сохранить", on_press=self.save))
        layout.add_widget(buttons)
        self.content = layout

    def _on_type_change(self, spinner, value):
        ttype = TransactionType.INCOME if value == "Доход" else TransactionType.EXPENSE
        self.cat_spinner.values = self._category_spinner_values(ttype)
        self.cat_spinner.text = self.cat_spinner.values[0]

    def save(self, *_):
        try:
            amount = float(self.sum_input.text.replace(",", "."))
            if amount <= 0:
                raise ValueError
            date = datetime.strptime(self.date_input.text, "%d.%m.%Y")
        except ValueError:
            return
        
        ttype = TransactionType.INCOME if self.type_spinner.text == "Доход" else TransactionType.EXPENSE
        cat_id = self._category_id_by_name(self.cat_spinner.text, ttype)
        
        add_transaction(
            name=self.desc_input.text or "Без описания",
            amount=amount,
            category_id=cat_id,
            transaction_type=ttype,
            date=date
        )
        
        if self.on_save_callback:
            self.on_save_callback()
        self.dismiss()


class RegularTransactionPopup(BaseFormPopup):
    def __init__(self, on_save=None, **kwargs):
        super().__init__(
            title="Постоянный платёж",
            size_hint=(0.92, 0.85),
            auto_dismiss=False,
            on_save=on_save,
            **kwargs,
        )
        from kivy.uix.textinput import TextInput
        from kivy.uix.spinner import Spinner
        from kivy.uix.button import Button
        from kivy.uix.label import Label
        from kivy.uix.scrollview import ScrollView

        # Основной контейнер для всех полей - компактный
        layout = BoxLayout(orientation="vertical", spacing=4, padding=8, size_hint_y=None)
        layout.height = 550  # Чуть меньше, чтобы влезло
        
        self.name_input = TextInput(text="", multiline=False, height="30dp", size_hint_y=None)
        self.sum_input = TextInput(text="", multiline=False, input_filter="float", height="30dp", size_hint_y=None)
        self.desc_input = TextInput(text="", multiline=False, height="30dp", size_hint_y=None)
        self.start_input = TextInput(text=datetime.now().strftime("%d.%m.%Y"), multiline=False, height="30dp", size_hint_y=None)
        self.days_input = TextInput(text="30", multiline=False, input_filter="int", height="30dp", size_hint_y=None)
        self.notify_input = TextInput(text="3", multiline=False, input_filter="int", height="30dp", size_hint_y=None)
        self.period_spinner = Spinner(
            text="Ежемесячно",
            values=[p.value for p in FormatPeriod],
            size_hint_y=None,
            height="30dp",
        )
        self.type_spinner = Spinner(
            text="Расход",
            values=("Доход", "Расход"),
            size_hint_y=None,
            height="30dp"
        )
        self.cat_spinner = Spinner(
            text="Прочее",
            values=self._category_spinner_values(TransactionType.EXPENSE),
            size_hint_y=None,
            height="30dp",
        )
        
        # Привязываем события
        self.type_spinner.bind(text=self._on_type_change)
        self.period_spinner.bind(text=self._on_period_change)

        # Поля с компактными лейблами
        fields = [
            ("Название", self.name_input),
            ("Сумма", self.sum_input),
            ("Тип", self.type_spinner),
            ("Категория", self.cat_spinner),
            ("Периодичность", self.period_spinner),
            ("Дней (custom)", self.days_input),
            ("Первый платёж", self.start_input),
            ("Напомнить за (дней)", self.notify_input),
            ("Описание", self.desc_input),
        ]
        for label, widget in fields:
            lbl = Label(text=label, size_hint_y=None, height="16dp", font_size=12, halign='left')
            layout.add_widget(lbl)
            layout.add_widget(widget)

        buttons = BoxLayout(size_hint_y=None, height="40dp", spacing=8)
        buttons.add_widget(Button(text="Отмена", on_press=lambda *_: self.dismiss()))
        buttons.add_widget(Button(text="Сохранить", on_press=self.save))
        layout.add_widget(buttons)
        
        # Оборачиваем layout в ScrollView
        scroll = ScrollView(size_hint=(1, 1))
        scroll.add_widget(layout)
        self.content = scroll
        
        self._on_period_change(None, self.period_spinner.text)

    def _on_type_change(self, spinner, value):
        """Обновляет категории при смене типа (Доход/Расход)."""
        ttype = TransactionType.INCOME if value == "Доход" else TransactionType.EXPENSE
        self.cat_spinner.values = self._category_spinner_values(ttype)
        self.cat_spinner.text = self.cat_spinner.values[0] if self.cat_spinner.values else "Прочее"

    def _on_period_change(self, spinner, value):
        """Включает/отключает поле 'Дней'."""
        self.days_input.disabled = value != "Произвольно"

    def save(self, *_):
        try:
            amount = float(self.sum_input.text.replace(",", "."))
            if amount <= 0:
                raise ValueError
            start = datetime.strptime(self.start_input.text, "%d.%m.%Y")
            numdays = int(self.days_input.text or "30")
            notify_days = int(self.notify_input.text or "3")
        except ValueError:
            return
        
        ttype = TransactionType.INCOME if self.type_spinner.text == "Доход" else TransactionType.EXPENSE
        cat_id = self._category_id_by_name(self.cat_spinner.text, ttype)
        
        # Преобразуем русское название в Enum
        period_map = {
            "Ежедневно": FormatPeriod.DAILY,
            "Еженедельно": FormatPeriod.WEEKLY,
            "Ежемесячно": FormatPeriod.MONTHLY,
            "Ежеквартально": FormatPeriod.QUARTERLY,
            "Ежегодно": FormatPeriod.YEARLY,
            "Произвольно": FormatPeriod.CUSTOM,
        }
        period = period_map.get(self.period_spinner.text, FormatPeriod.MONTHLY)
        
        add_regular_transaction(
            name=self.name_input.text,
            description=self.desc_input.text,
            sum=amount,
            start_date=start,
            numdays=numdays,
            notify_days=notify_days,
            format_period=period,
            transaction_type=ttype,
            category_id=cat_id,
        )
        
        if self.on_save_callback:
            self.on_save_callback()
        self.dismiss()


class GoalPopup(BaseFormPopup):
    def __init__(self, on_save=None, **kwargs):
        super().__init__(
            title="Финансовая цель",
            size_hint=(0.92, 0.7),
            auto_dismiss=False,
            on_save=on_save,
            **kwargs,
        )
        from kivy.uix.textinput import TextInput
        from kivy.uix.button import Button
        from kivy.uix.label import Label

        layout = BoxLayout(orientation="vertical", spacing=8, padding=10)
        self.name_input = TextInput(text="", multiline=False)
        self.target_input = TextInput(text="", multiline=False, input_filter="float")
        self.current_input = TextInput(text="0", multiline=False, input_filter="float")
        self.deadline_input = TextInput(text="", multiline=False, hint_text="ДД.ММ.ГГГГ")
        self.desc_input = TextInput(text="", multiline=False)

        for label, widget in (
            ("Название", self.name_input),
            ("Целевая сумма", self.target_input),
            ("Уже накоплено", self.current_input),
            ("Срок (необязательно)", self.deadline_input),
            ("Описание", self.desc_input),
        ):
            layout.add_widget(Label(text=label, size_hint_y=None, height="24dp"))
            layout.add_widget(widget)

        buttons = BoxLayout(size_hint_y=None, height="44dp", spacing=8)
        buttons.add_widget(Button(text="Отмена", on_press=lambda *_: self.dismiss()))
        buttons.add_widget(Button(text="Сохранить", on_press=self.save))
        layout.add_widget(buttons)
        self.content = layout

    def save(self, *_):
        try:
            target = float(self.target_input.text.replace(",", "."))
            current = float(self.current_input.text.replace(",", ".") or "0")
            if target <= 0 or current < 0:
                raise ValueError
        except ValueError:
            return
        
        deadline = None
        if self.deadline_input.text.strip():
            try:
                deadline = datetime.strptime(self.deadline_input.text.strip(), "%d.%m.%Y")
            except ValueError:
                return
        
        add_financial_goal(
            self.name_input.text,
            target,
            deadline=deadline,
            description=self.desc_input.text,
            current_sum=current,
        )
        
        if self.on_save_callback:
            self.on_save_callback()
        self.dismiss()


class MainApp(App):
    _pin = None
    _check_event = None  # <--- ДОБАВЛЕНО

    def build(self):
        sm = ScreenManager(transition=SlideTransition())
        sm.add_widget(AuthScreen(name="AuthScreen"))
        sm.add_widget(LoginScreen(name="LoginScreen"))
        sm.add_widget(MainScreen(name="MainScreen"))
        sm.current = "LoginScreen" if is_registered() else "AuthScreen"
        
        # Запускаем планировщик <--- ДОБАВЛЕНО
        self.schedule_regular_checks()
        
        return sm

    # <--- ДОБАВЛЕНО --->
    def schedule_regular_checks(self):
        """Запускает проверку постоянных платежей каждые 60 секунд."""
        # Проверяем сразу при запуске
        self.check_regular_transactions()
        # И затем каждые 60 секунд
        self._check_event = Clock.schedule_interval(
            lambda dt: self.check_regular_transactions(), 
            60  # каждую минуту
        )

    # <--- ДОБАВЛЕНО --->
    def check_regular_transactions(self):
        """Проверяет и создаёт просроченные транзакции."""
        if self._pin:  # Только если приложение разблокировано
            try:
                process_due_regular_transactions()
            except Exception as e:
                print(f"Ошибка при проверке платежей: {e}")

    def unlock(self, pin: str):
        self._pin = pin

    def on_stop(self):
        # Останавливаем планировщик <--- ДОБАВЛЕНО
        if self._check_event:
            self._check_event.cancel()
        
        if self._pin:
            db.commit()
            db.close()
            encrypt_database(self._pin)
            remove_plain_database()


if __name__ == "__main__":
    MainApp().run()