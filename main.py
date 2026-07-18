from datetime import datetime, timedelta

from kivy.app import App
from kivy.lang import Builder
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.screenmanager import Screen, ScreenManager, SlideTransition
from kivy.clock import Clock
from kivy.metrics import dp, sp
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView

from charts import ChartImage, PieChart
from notify import init_notifications
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
    process_due_regular_transactions,
    db,
)

# Загрузка KV файлов
for kv_file in ("views/css.kv", "views/auth.kv", "views/login.kv", "views/main.kv", "views/form_screens.kv"):
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


# ---------- Общие вспомогательные методы для форм ----------
def _category_spinner_values(transaction_type):
    cats = get_categories(transaction_type)
    if not cats:
        return ["Прочее"]
    return [c.name for c in cats]


def _category_id_by_name(name, transaction_type):
    cats = get_categories(transaction_type)
    if not cats:
        cat = Category(name="Прочее", transaction_type=transaction_type)
        db.add(cat)
        db.commit()
        return cat.id
    for cat in cats:
        if cat.name == name:
            return cat.id
    return cats[0].id


# ---------- Главный экран ----------
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


class MainScreen(Screen):
    page_size = 5
    tx_offset = 0
    regular_offset = 0

    def on_enter(self):
        App.get_running_app().title = "Ruble — личные финансы"
        sync_payment_notifications()
        self.refresh_all()
        Clock.schedule_once(lambda dt: self._update_charts_with_period(), 0.3)

    def _update_charts_with_period(self):
        start, end = self._period()
        self.update_charts(start, end)

    def refresh_all(self):
        db.commit()
        self.ids['balance'].text = _fmt_sum(get_balance())
        profit = get_monthly_profit()
        sign = "+" if profit >= 0 else ""
        self.ids['monthly_profit'].text = _fmt_sum(profit, sign)

        start, end = self._period()

        self.tx_offset = 0
        self.regular_offset = 0
        self.load_notifications()
        self.load_transactions()
        self.load_regular_transactions()
        self.update_charts(start, end)
        self.update_list_heights()
        self.update_scroll_height()

    def _period(self):
        try:
            start = datetime.strptime(self.ids['start_date_input'].text, "%d.%m.%Y")
            end = datetime.strptime(self.ids['end_date_input'].text, "%d.%m.%Y")
            end = end.replace(hour=23, minute=59, second=59)
            return start, end
        except (ValueError, AttributeError):
            start, end = _default_period()
            if hasattr(self, "ids"):
                self.ids['start_date_input'].text = start.strftime("%d.%m.%Y")
                self.ids['end_date_input'].text = end.strftime("%d.%m.%Y")
            return start, end

    def apply_period(self):
        self.refresh_all()
        start, end = self._period()
        self.update_charts(start, end)

    def reset_period(self):
        start, end = _default_period()
        self.ids['start_date_input'].text = start.strftime("%d.%m.%Y")
        self.ids['end_date_input'].text = end.strftime("%d.%m.%Y")
        self.refresh_all()
        self.update_charts(start, end)

    def update_scroll_height(self):
        content = self.ids.get('scroll_content')
        if not content:
            return
        total_height = 0
        for child in content.children:
            if hasattr(child, 'height'):
                total_height += child.height
        total_height += content.padding[0] + content.padding[2] if hasattr(content, 'padding') else 0
        total_height += content.spacing * (len(content.children) - 1) if content.spacing else 0
        content.height = max(total_height, 600)

    def update_list_heights(self):
        for container in (self.ids['notifications'], self.ids['transactions'], self.ids['regular_transactions']):
            if container.children:
                count = len(container.children)
                height = count * dp(34) + (count - 1) * dp(4) + dp(8)
                container.height = max(height, dp(50))
            else:
                container.height = dp(50)

    def load_notifications(self):
        self.ids['notifications'].clear_widgets()
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
            self.ids['notifications'].add_widget(widget)
        self.update_list_heights()
        self.update_scroll_height()

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

        self.ids['transactions'].clear_widgets()
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
            self.ids['transactions'].add_widget(widget)

        if total == 0:
            self.ids['tx_page_label'].text = "0 из 0"
        else:
            shown_to = min(self.tx_offset + self.page_size, total)
            self.ids['tx_page_label'].text = f"{self.tx_offset + 1}-{shown_to} из {total}"
        self.update_list_heights()
        self.update_scroll_height()

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

        self.ids['regular_transactions'].clear_widgets()
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
            self.ids['regular_transactions'].add_widget(widget)

        if total == 0:
            self.ids['reg_page_label'].text = "0 из 0"
        else:
            shown_to = min(self.regular_offset + self.page_size, total)
            self.ids['reg_page_label'].text = f"{self.regular_offset + 1}-{shown_to} из {total}"
        self.update_list_heights()
        self.update_scroll_height()

    def update_charts(self, start, end):
        labels, income, expense = get_daily_totals(start, end)
        self.ids['line_chart'].render_line_chart(labels, income, expense)

        data = get_expenses_by_category(start, end)
        if not data:
            categories, values = ["Нет данных"], [0]
        else:
            categories, values = zip(*data)
            categories, values = list(categories), list(values)
            filtered = [(c, v) for c, v in zip(categories, values) if v > 0]
            if filtered:
                categories, values = zip(*filtered)
                categories, values = list(categories), list(values)
            else:
                categories, values = ["Нет данных"], [0]
        self.ids['pie_chart'].render(categories, values)

    def delete_notification(self, item_id):
        delete_by_model(Notification, item_id)
        self.load_notifications()
        self.update_scroll_height()

    def delete_transaction(self, item_id):
        delete_by_model(Transaction, item_id)
        self.refresh_all()

    def delete_regular(self, item_id):
        db.query(Notification).filter(Notification.regular_transaction_id == item_id).delete()
        delete_by_model(RegularTransaction, item_id)
        sync_payment_notifications()
        self.refresh_all()

    def go_to_transaction(self):
        self.manager.current = "TransactionScreen"

    def go_to_regular(self):
        self.manager.current = "RegularScreen"

    def go_to_goal(self):
        self.manager.current = "GoalScreen"


# ---------- Базовый экран для форм ----------
class BaseFormScreen(Screen):
    def go_back(self):
        self.manager.current = "MainScreen"


# ---------- Экран добавления транзакции (исправлен отступ сверху) ----------
class TransactionScreen(BaseFormScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.build_form()

    def build_form(self):
        # Родительский layout – будет иметь фиксированную высоту
        layout = BoxLayout(orientation='vertical', spacing=0, padding=0)
        layout.size_hint_y = None  # отключаем растяжение

        # Заголовок
        title_layout = BoxLayout(size_hint_y=None, height=dp(34), padding=[dp(12), dp(4)])
        with title_layout.canvas.before:
            from kivy.graphics import Color, RoundedRectangle
            Color(0.2, 0.55, 0.9, 1)
            RoundedRectangle(pos=title_layout.pos, size=title_layout.size, radius=[dp(8), dp(8), 0, 0])
        title_label = Label(text="Новая транзакция", font_size=sp(16), bold=True, color=[1,1,1,1], size_hint=(1,1))
        title_layout.add_widget(title_label)
        layout.add_widget(title_layout)

        # Контейнер с фиксированной высотой
        content = BoxLayout(orientation='vertical', padding=[dp(12), dp(4), dp(12), dp(4)], spacing=dp(4))
        content.size_hint_y = None

        # Блок полей
        fields_box = BoxLayout(orientation='vertical', spacing=dp(4), size_hint_y=None)
        fields_box.height = dp(276)   # 5 полей

        self.date_input = TextInput(text=datetime.now().strftime("%d.%m.%Y"), multiline=False,
                                    size_hint_y=None, height=dp(32), font_size=sp(13))
        self.sum_input = TextInput(text="", multiline=False, input_filter="float",
                                   size_hint_y=None, height=dp(32), font_size=sp(13))
        self.desc_input = TextInput(text="", multiline=False, size_hint_y=None, height=dp(32), font_size=sp(13))
        self.type_spinner = Spinner(text="Расход", values=("Доход","Расход"),
                                    size_hint_y=None, height=dp(32), font_size=sp(13))
        self.cat_spinner = Spinner(text="Прочее",
                                   values=_category_spinner_values(TransactionType.EXPENSE),
                                   size_hint_y=None, height=dp(32), font_size=sp(13))
        self.type_spinner.bind(text=self._on_type_change)

        fields = [
            ("Дата (ДД.ММ.ГГГГ)", self.date_input),
            ("Сумма", self.sum_input),
            ("Тип", self.type_spinner),
            ("Категория", self.cat_spinner),
            ("Описание", self.desc_input),
        ]
        for label, widget in fields:
            lbl = Label(text=label, size_hint_y=None, height=dp(16), color=[0,0,0,1], font_size=sp(11))
            fields_box.add_widget(lbl)
            fields_box.add_widget(widget)

        content.add_widget(fields_box)

        # Кнопки
        buttons = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(8), padding=[dp(6), dp(2)])
        btn_cancel = Button(text="Отмена", on_press=lambda *_: self.go_back(),
                            background_color=[0.7,0.3,0.3,1], size_hint_x=0.4, font_size=sp(13))
        btn_save = Button(text="Сохранить", on_press=self.save,
                          background_color=[0.2,0.6,0.9,1], size_hint_x=0.6, font_size=sp(13))
        buttons.add_widget(btn_cancel)
        buttons.add_widget(btn_save)
        content.add_widget(buttons)

        # Вычисляем высоту content
        content_height = (fields_box.height + buttons.height +
                          content.padding[1] + content.padding[3] +
                          content.spacing)
        content.height = content_height

        layout.add_widget(content)

        # Вычисляем общую высоту layout (заголовок + content + маленький запас)
        layout.height = title_layout.height + content.height + dp(6)

        self.add_widget(layout)

    def _on_type_change(self, spinner, value):
        ttype = TransactionType.INCOME if value == "Доход" else TransactionType.EXPENSE
        self.cat_spinner.values = _category_spinner_values(ttype)
        self.cat_spinner.text = self.cat_spinner.values[0] if self.cat_spinner.values else "Прочее"

    def save(self, *_):
        try:
            amount = float(self.sum_input.text.replace(",", "."))
            if amount <= 0:
                raise ValueError
            date = datetime.strptime(self.date_input.text, "%d.%m.%Y")
        except ValueError:
            return
        ttype = TransactionType.INCOME if self.type_spinner.text == "Доход" else TransactionType.EXPENSE
        cat_id = _category_id_by_name(self.cat_spinner.text, ttype)
        add_transaction(
            name=self.desc_input.text or "Без описания",
            amount=amount,
            category_id=cat_id,
            transaction_type=ttype,
            date=date
        )
        self.go_back()
        main_screen = self.manager.get_screen("MainScreen")
        if main_screen:
            main_screen.refresh_all()


# ---------- Экран постоянного платежа (исправлен обрез сверху) ----------
class RegularScreen(BaseFormScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.scroll = None
        self.build_form()

    def build_form(self):
        layout = BoxLayout(orientation='vertical', spacing=0, padding=0)

        title_layout = BoxLayout(size_hint_y=None, height=dp(34), padding=[dp(12), dp(4)])
        with title_layout.canvas.before:
            from kivy.graphics import Color, RoundedRectangle
            Color(0.2, 0.55, 0.9, 1)
            RoundedRectangle(pos=title_layout.pos, size=title_layout.size, radius=[dp(8), dp(8), 0, 0])
        title_label = Label(text="Постоянный платёж", font_size=sp(16), bold=True, color=[1,1,1,1], size_hint=(1,1))
        title_layout.add_widget(title_label)
        layout.add_widget(title_layout)

        # Исправлено: увеличен верхний отступ, чтобы подпись "Название" была видна
        content = BoxLayout(orientation='vertical', padding=[dp(12), dp(6), dp(12), dp(4)], spacing=dp(4))
        scroll = ScrollView(size_hint=(1,1), do_scroll_x=False, bar_width=dp(3))
        scroll.bar_color = [0.2,0.5,0.8,0.3]
        scroll.bar_inactive_color = [0.2,0.5,0.8,0.1]
        self.scroll = scroll

        fields_box = BoxLayout(orientation='vertical', spacing=dp(4), size_hint_y=None)
        # Увеличена высота для комфортного размещения всех полей
        fields_box.height = dp(500)

        self.name_input = TextInput(text="", multiline=False, size_hint_y=None, height=dp(32), font_size=sp(13))
        self.sum_input = TextInput(text="", multiline=False, input_filter="float", size_hint_y=None, height=dp(32), font_size=sp(13))
        self.desc_input = TextInput(text="", multiline=False, size_hint_y=None, height=dp(32), font_size=sp(13))
        self.start_input = TextInput(text=datetime.now().strftime("%d.%m.%Y"), multiline=False,
                                     size_hint_y=None, height=dp(32), font_size=sp(13))
        self.days_input = TextInput(text="30", multiline=False, input_filter="int",
                                    size_hint_y=None, height=dp(32), font_size=sp(13))
        self.notify_input = TextInput(text="3", multiline=False, input_filter="int",
                                      size_hint_y=None, height=dp(32), font_size=sp(13))
        self.period_spinner = Spinner(text="Ежемесячно", values=[p.value for p in FormatPeriod],
                                      size_hint_y=None, height=dp(32), font_size=sp(13))
        self.type_spinner = Spinner(text="Расход", values=("Доход","Расход"),
                                    size_hint_y=None, height=dp(32), font_size=sp(13))
        self.cat_spinner = Spinner(text="Прочее",
                                   values=_category_spinner_values(TransactionType.EXPENSE),
                                   size_hint_y=None, height=dp(32), font_size=sp(13))

        self.type_spinner.bind(text=self._on_type_change)
        self.period_spinner.bind(text=self._on_period_change)

        fields = [
            ("Название", self.name_input),
            ("Сумма", self.sum_input),
            ("Тип", self.type_spinner),
            ("Категория", self.cat_spinner),
            ("Периодичность", self.period_spinner),
            ("Дней (для произвольного)", self.days_input),
            ("Первый платёж", self.start_input),
            ("Напомнить за (дней)", self.notify_input),
            ("Описание", self.desc_input),
        ]
        for label, widget in fields:
            lbl = Label(text=label, size_hint_y=None, height=dp(16), font_size=sp(11), color=[0,0,0,1])
            fields_box.add_widget(lbl)
            fields_box.add_widget(widget)

        scroll.add_widget(fields_box)
        content.add_widget(scroll)

        buttons = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(8), padding=[dp(6), dp(2)])
        btn_cancel = Button(text="Отмена", on_press=lambda *_: self.go_back(),
                            background_color=[0.7,0.3,0.3,1], size_hint_x=0.4, font_size=sp(13))
        btn_save = Button(text="Сохранить", on_press=self.save,
                          background_color=[0.2,0.6,0.9,1], size_hint_x=0.6, font_size=sp(13))
        buttons.add_widget(btn_cancel)
        buttons.add_widget(btn_save)
        content.add_widget(buttons)

        layout.add_widget(content)
        self.add_widget(layout)
        self._on_period_change(None, self.period_spinner.text)

    def on_enter(self):
        if self.scroll:
            Clock.schedule_once(lambda dt: setattr(self.scroll, 'scroll_y', 1), 0.2)

    def _on_type_change(self, spinner, value):
        ttype = TransactionType.INCOME if value == "Доход" else TransactionType.EXPENSE
        self.cat_spinner.values = _category_spinner_values(ttype)
        self.cat_spinner.text = self.cat_spinner.values[0] if self.cat_spinner.values else "Прочее"

    def _on_period_change(self, spinner, value):
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
        cat_id = _category_id_by_name(self.cat_spinner.text, ttype)
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
        self.go_back()
        main_screen = self.manager.get_screen("MainScreen")
        if main_screen:
            main_screen.refresh_all()

# ---------- Экран финансовой цели (исправлен отступ сверху) ----------
class GoalScreen(BaseFormScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.build_form()

    def build_form(self):
        layout = BoxLayout(orientation='vertical', spacing=0, padding=0)

        title_layout = BoxLayout(size_hint_y=None, height=dp(34), padding=[dp(12), dp(4)])
        with title_layout.canvas.before:
            from kivy.graphics import Color, RoundedRectangle
            Color(0.2, 0.55, 0.9, 1)
            RoundedRectangle(pos=title_layout.pos, size=title_layout.size, radius=[dp(8), dp(8), 0, 0])
        title_label = Label(text="Финансовая цель", font_size=sp(16), bold=True, color=[1,1,1,1], size_hint=(1,1))
        title_layout.add_widget(title_label)
        layout.add_widget(title_layout)

        content = BoxLayout(orientation='vertical', padding=[dp(12), dp(2), dp(12), dp(6)], spacing=dp(4))
        fields_box = BoxLayout(orientation='vertical', spacing=dp(4), size_hint_y=None)
        fields_box.height = dp(220)

        self.name_input = TextInput(text="", multiline=False, size_hint_y=None, height=dp(32), font_size=sp(13))
        self.target_input = TextInput(text="", multiline=False, input_filter="float", size_hint_y=None, height=dp(32), font_size=sp(13))
        self.current_input = TextInput(text="0", multiline=False, input_filter="float", size_hint_y=None, height=dp(32), font_size=sp(13))
        self.deadline_input = TextInput(text="", multiline=False, hint_text="ДД.ММ.ГГГГ",
                                        size_hint_y=None, height=dp(32), font_size=sp(13))
        self.desc_input = TextInput(text="", multiline=False, size_hint_y=None, height=dp(32), font_size=sp(13))

        fields = [
            ("Название", self.name_input),
            ("Целевая сумма", self.target_input),
            ("Уже накоплено", self.current_input),
            ("Срок (необязательно)", self.deadline_input),
            ("Описание", self.desc_input),
        ]
        for label, widget in fields:
            lbl = Label(text=label, size_hint_y=None, height=dp(16), color=[0,0,0,1], font_size=sp(11))
            fields_box.add_widget(lbl)
            fields_box.add_widget(widget)

        content.add_widget(fields_box)

        buttons = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(8), padding=[dp(6), dp(2)])
        btn_cancel = Button(text="Отмена", on_press=lambda *_: self.go_back(),
                            background_color=[0.7,0.3,0.3,1], size_hint_x=0.4, font_size=sp(13))
        btn_save = Button(text="Сохранить", on_press=self.save,
                          background_color=[0.2,0.6,0.9,1], size_hint_x=0.6, font_size=sp(13))
        buttons.add_widget(btn_cancel)
        buttons.add_widget(btn_save)
        content.add_widget(buttons)

        layout.add_widget(content)
        self.add_widget(layout)

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
        self.go_back()
        main_screen = self.manager.get_screen("MainScreen")
        if main_screen:
            main_screen.refresh_all()


# ---------- Экран входа и регистрации ----------
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


# ---------- Приложение ----------
class MainApp(App):
    _pin = None
    _check_event = None

    def build(self):
        Clock.max_iteration = 50
        init_notifications()
        sm = ScreenManager(transition=SlideTransition())
        sm.add_widget(AuthScreen(name="AuthScreen"))
        sm.add_widget(LoginScreen(name="LoginScreen"))
        sm.add_widget(MainScreen(name="MainScreen"))
        sm.add_widget(TransactionScreen(name="TransactionScreen"))
        sm.add_widget(RegularScreen(name="RegularScreen"))
        sm.add_widget(GoalScreen(name="GoalScreen"))
        sm.current = "LoginScreen" if is_registered() else "AuthScreen"
        self.schedule_regular_checks()
        return sm

    def schedule_regular_checks(self):
        self.check_regular_transactions()
        self._check_event = Clock.schedule_interval(
            lambda dt: self.check_regular_transactions(),
            60
        )

    def check_regular_transactions(self):
        if self._pin:
            try:
                if not db.is_active:
                    db.begin()
                process_due_regular_transactions()
            except Exception as e:
                print(f"Ошибка при проверке платежей: {e}")
                db.rollback()

    def unlock(self, pin: str):
        self._pin = pin

    def on_stop(self):
        if self._check_event:
            self._check_event.cancel()
        if self._pin:
            try:
                db.commit()
            except:
                db.rollback()
            finally:
                db.close()
                encrypt_database(self._pin)
                remove_plain_database()


if __name__ == "__main__":
    MainApp().run()