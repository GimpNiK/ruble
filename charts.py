"""Виджеты диаграмм на чистом Kivy Canvas с Translate."""
from kivy.uix.widget import Widget
from kivy.clock import Clock
from kivy.graphics import Color, Rectangle, Line, Ellipse, Mesh, PushMatrix, PopMatrix, Translate
from kivy.uix.label import Label
from kivy.metrics import dp
import math


class ChartImage(Widget):
    """Линейный график доходов и расходов."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._last_data = None
        self.bind(size=self._on_size_change)
    
    def _on_size_change(self, *args):
        if self._last_data and self.width > 10 and self.height > 10:
            # Исправлено: вызываем render_line_chart, а не render
            self.render_line_chart(*self._last_data)
    
    def render_line_chart(self, labels, income_data, expense_data, title="Доходы и расходы"):
        self._last_data = (labels, income_data, expense_data, title)
        Clock.schedule_once(lambda dt: self._render(labels, income_data, expense_data, title), 0.3)
    
    def _render(self, labels, income_data, expense_data, title):
        self.canvas.clear()
        self.clear_widgets()
        
        w = self.width
        h = self.height
        if w < 50 or h < 50:
            Clock.schedule_once(lambda dt: self._render(labels, income_data, expense_data, title), 0.3)
            return
        
        # Данные
        if not labels or len(labels) == 0:
            labels = ["Янв", "Фев", "Мар", "Апр", "Май", "Июн", "Июл"]
            income_data = [1000, 2000, 1500, 3000, 2500, 4000, 3500]
            expense_data = [500, 800, 600, 1200, 900, 1500, 1000]
        income_data = [float(x) if x is not None else 0 for x in income_data]
        expense_data = [float(x) if x is not None else 0 for x in expense_data]
        if max(income_data + expense_data) == 0:
            labels = ["Янв", "Фев", "Мар", "Апр", "Май", "Июн", "Июл"]
            income_data = [1000, 2000, 1500, 3000, 2500, 4000, 3500]
            expense_data = [500, 800, 600, 1200, 900, 1500, 1000]
        
        all_values = income_data + expense_data
        max_val = max(all_values) if all_values else 1
        if max_val == 0:
            max_val = 1
        
        pad_left, pad_right, pad_bottom, pad_top = 55, 20, 45, 35
        chart_x, chart_y = pad_left, pad_bottom
        chart_w = w - pad_left - pad_right
        chart_h = h - pad_bottom - pad_top
        
        # ---- Отрисовка с Translate ----
        with self.canvas:
            PushMatrix()
            Translate(self.x, self.y, 0)
            
            # Фон (белый)
            Color(1, 1, 1, 1)
            Rectangle(pos=(0, 0), size=(w, h))
            
            # Оси
            Color(0.2, 0.2, 0.2, 1)
            Line(points=[chart_x, chart_y, chart_x + chart_w, chart_y], width=2)
            Line(points=[chart_x, chart_y, chart_x, chart_y + chart_h], width=2)
            
            # Сетка по Y
            num_ticks = 5
            for i in range(num_ticks + 1):
                y_pos = chart_y + (chart_h * i / num_ticks)
                Color(0.85, 0.85, 0.85, 1)
                Line(points=[chart_x, y_pos, chart_x + chart_w, y_pos], width=0.5)
            
            # Линии доходов и расходов
            if len(income_data) > 1:
                pts = []
                for i, val in enumerate(income_data):
                    x = chart_x + (chart_w * i / (len(income_data) - 1))
                    y = chart_y + (chart_h * val / max_val)
                    pts.extend([x, y])
                Color(0.2, 0.8, 0.4, 1)
                Line(points=pts, width=3)
                for i, val in enumerate(income_data):
                    if val > 0:
                        x = chart_x + (chart_w * i / (len(income_data) - 1))
                        y = chart_y + (chart_h * val / max_val)
                        Color(0.2, 0.8, 0.4, 1)
                        Ellipse(pos=(x - 5, y - 5), size=(10, 10))
            
            if len(expense_data) > 1:
                pts = []
                for i, val in enumerate(expense_data):
                    x = chart_x + (chart_w * i / (len(expense_data) - 1))
                    y = chart_y + (chart_h * val / max_val)
                    pts.extend([x, y])
                Color(0.9, 0.3, 0.2, 1)
                Line(points=pts, width=3)
                for i, val in enumerate(expense_data):
                    if val > 0:
                        x = chart_x + (chart_w * i / (len(expense_data) - 1))
                        y = chart_y + (chart_h * val / max_val)
                        Color(0.9, 0.3, 0.2, 1)
                        Ellipse(pos=(x - 5, y - 5), size=(10, 10))
            
            # Легенда
            legend_x = chart_x + chart_w - 130
            legend_y = chart_y + chart_h - 30
            Color(0.2, 0.8, 0.4, 1)
            Rectangle(pos=(legend_x, legend_y), size=(12, 12))
            Color(0.9, 0.3, 0.2, 1)
            Rectangle(pos=(legend_x + 75, legend_y), size=(12, 12))
            
            PopMatrix()
        
        # ---- Текстовые подписи ----
        for i in range(num_ticks + 1):
            y_pos = chart_y + (chart_h * i / num_ticks)
            val = max_val * i / num_ticks
            lbl = Label(
                text=f"{val:.0f}", font_size=9,
                color=[0.3,0.3,0.3,1],
                size_hint=(None,None), size=(pad_left-5, 15),
                pos=(self.x + 2, self.y + y_pos - 7),
                halign='right'
            )
            self.add_widget(lbl)
        
        if len(labels) > 1:
            step = max(1, len(labels) // 8)
            for i in range(0, len(labels), step):
                x_pos = chart_x + (chart_w * i / (len(labels) - 1))
                lbl = Label(
                    text=labels[i], font_size=8,
                    color=[0.3,0.3,0.3,1],
                    size_hint=(None,None), size=(40, 15),
                    pos=(self.x + x_pos - 20, self.y + 2),
                    halign='center'
                )
                self.add_widget(lbl)
        
        # Текст легенды
        lbl = Label(
            text="Доходы", font_size=10,
            color=[0.2,0.2,0.2,1],
            size_hint=(None,None), size=(50,15),
            pos=(self.x + legend_x + 16, self.y + legend_y - 2),
            halign='left'
        )
        self.add_widget(lbl)
        lbl = Label(
            text="Расходы", font_size=10,
            color=[0.2,0.2,0.2,1],
            size_hint=(None,None), size=(55,15),
            pos=(self.x + legend_x + 91, self.y + legend_y - 2),
            halign='left'
        )
        self.add_widget(lbl)
        
        self.canvas.ask_update()


class PieChart(Widget):
    """Круговая диаграмма расходов по категориям (легенда внизу)."""
    
    colors = [
        [0.9, 0.3, 0.3, 1],
        [0.3, 0.6, 0.9, 1],
        [0.2, 0.8, 0.4, 1],
        [1.0, 0.7, 0.1, 1],
        [0.7, 0.3, 0.8, 1],
        [0.1, 0.7, 0.8, 1],
        [0.9, 0.5, 0.1, 1],
        [0.8, 0.1, 0.4, 1],
        [0.4, 0.8, 0.3, 1],
        [0.5, 0.3, 0.7, 1],
    ]
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._last_data = None
        self.bind(size=self._on_size_change)
    
    def _on_size_change(self, *args):
        if self._last_data and self.width > 10 and self.height > 10:
            self.render(*self._last_data)
    
    def render(self, categories, values, title="Расходы по категориям"):
        self._last_data = (categories, values, title)
        Clock.schedule_once(lambda dt: self._render(categories, values, title), 0.3)
    
    def _render(self, categories, values, title):
        self.clear_widgets()
        self.canvas.clear()
        
        w = self.width
        h = self.height
        if w < 50 or h < 50:
            Clock.schedule_once(lambda dt: self._render(categories, values, title), 0.3)
            return
        
        if not categories or not values or sum(values) == 0:
            lbl = Label(text="Нет данных", font_size=20, color=[0.5,0.5,0.5,1],
                        pos=(self.x + 10, self.y + h/2 - 10))
            self.add_widget(lbl)
            return
        
        values = [float(v) if v is not None else 0 for v in values]
        total = sum(values)
        if total == 0:
            lbl = Label(text="Нет данных", font_size=20, color=[0.5,0.5,0.5,1],
                        pos=(self.x + 10, self.y + h/2 - 10))
            self.add_widget(lbl)
            return
        
        # --- Определяем области ---
        # Легенда внизу, занимает 25% высоты, остальное – круг
        legend_height = min(dp(80), h * 0.25)   # максимум 80dp, иначе 25% высоты
        circle_area_h = h - legend_height - 10   # 10px отступа снизу
        circle_area_w = w - 20                  # отступы по бокам
        circle_x = 10
        circle_y = 10
        radius = min(circle_area_w, circle_area_h) * 0.42   # чуть меньше половины, чтобы не касаться краёв
        center_x = circle_x + circle_area_w / 2
        center_y = circle_y + circle_area_h / 2
        
        # --- Рисуем круг ---
        with self.canvas:
            PushMatrix()
            Translate(self.x, self.y, 0)
            start_angle = 0
            for i, val in enumerate(values):
                if val > 0:
                    angle = (val / total) * 360
                    color = self.colors[i % len(self.colors)]
                    Color(*color)
                    self._draw_sector(center_x, center_y, radius, start_angle, angle)
                    start_angle += angle
            PopMatrix()
        
        # --- Легенда внизу (горизонтально) ---
        legend_y = self.y + circle_area_h + 5
        legend_x_start = self.x + 10
        item_height = legend_height * 0.7
        item_spacing = 12
        # Вычисляем ширину каждого элемента легенды, чтобы они поместились
        max_items = len([v for v in values if v > 0])
        if max_items == 0:
            return
        # Попробуем разместить в несколько рядов, если не помещаются
        items_per_row = max(1, int((w - 20) / (120 + item_spacing)))
        rows = (max_items + items_per_row - 1) // items_per_row
        # Если слишком много рядов, уменьшим размер шрифта и квадратов
        if rows > 2:
            item_height = max(16, (legend_height - 10) / rows)
        # Отображаем элементы
        for idx, (cat, val) in enumerate(zip(categories, values)):
            if val <= 0:
                continue
            percent = (val / total) * 100
            row = idx // items_per_row
            col = idx % items_per_row
            x_pos = legend_x_start + col * (w / items_per_row)
            y_pos = legend_y + row * (item_height + 4)
            # Цветной квадрат
            color = self.colors[idx % len(self.colors)]
            color_box = Widget(size_hint=(None,None), size=(item_height*0.8, item_height*0.8),
                               pos=(x_pos, y_pos))
            with color_box.canvas:
                Color(*color)
                Rectangle(pos=color_box.pos, size=color_box.size)
            self.add_widget(color_box)
            # Текст
            lbl = Label(
                text=f"{cat} ({percent:.1f}%)",
                font_size=max(8, item_height * 0.6),
                color=[0.2,0.2,0.2,1],
                size_hint=(None,None), size=(w / items_per_row - item_height, item_height),
                pos=(x_pos + item_height*0.8 + 4, y_pos),
                halign='left',
                valign='middle'
            )
            self.add_widget(lbl)
        
        self.canvas.ask_update()
    
    def _draw_sector(self, cx, cy, radius, start_angle, angle):
        segments = 40
        vertices = []
        indices = []
        start_rad = math.radians(start_angle - 90)
        end_rad = math.radians(start_angle + angle - 90)
        
        vertices.extend([cx, cy, 0, 0])
        for i in range(segments + 1):
            t = start_rad + (end_rad - start_rad) * (i / segments)
            px = cx + radius * math.cos(t)
            py = cy + radius * math.sin(t)
            vertices.extend([px, py, 0, 0])
        
        for i in range(1, segments + 1):
            indices.extend([0, i, i + 1])
        
        mesh = Mesh(vertices=vertices, indices=indices, mode='triangles')
        self.canvas.add(mesh)
        # Контур
        points = [cx, cy]
        for i in range(segments + 1):
            t = start_rad + (end_rad - start_rad) * (i / segments)
            px = cx + radius * math.cos(t)
            py = cy + radius * math.sin(t)
            points.extend([px, py])
        points.extend([cx, cy])
        Color(0.2, 0.2, 0.2, 0.8)
        Line(points=points, width=1.2)