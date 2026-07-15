"""Виджеты диаграмм на чистом Kivy Canvas с Translate."""
from kivy.uix.widget import Widget
from kivy.clock import Clock
from kivy.graphics import Color, Rectangle, Line, Ellipse, Mesh, PushMatrix, PopMatrix, Translate
from kivy.uix.label import Label
import math


class ChartImage(Widget):
    """Линейный график доходов и расходов."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._last_data = None
        self.bind(size=self._on_size_change)
    
    def _on_size_change(self, *args):
        if self._last_data and self.width > 10 and self.height > 10:
            self.render(*self._last_data)
    
    def render_line_chart(self, labels, income_data, expense_data, title="Доходы и расходы"):
        self._last_data = ('line', labels, income_data, expense_data, title)
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
            
            # Фон (белый, чтобы график был виден на любом фоне)
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
            
            # Легенда (прямоугольники)
            legend_x = chart_x + chart_w - 130
            legend_y = chart_y + chart_h - 30
            Color(0.2, 0.8, 0.4, 1)
            Rectangle(pos=(legend_x, legend_y), size=(12, 12))
            Color(0.9, 0.3, 0.2, 1)
            Rectangle(pos=(legend_x + 75, legend_y), size=(12, 12))
            
            PopMatrix()
        
        # ---- Текстовые подписи (виджеты, позиция с учётом self.x, self.y) ----
        # Подписи по Y
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
        
        # Подписи по X
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
        print(f" Линейный график отрисован, pos={self.pos}, size={w}x{h}")


class PieChart(Widget):
    """Круговая диаграмма расходов по категориям."""
    
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
        
        # ---- Рисуем круг с Translate ----
        # Определяем область для круга: 60% ширины, оставшееся для легенды
        circle_width = w * 0.6
        circle_height = h
        circle_x = 10
        circle_y = 10
        
        # Рисуем сектора на canvas с Translate
        with self.canvas:
            PushMatrix()
            Translate(self.x, self.y, 0)
            # Смещаем начало координат к центру круга
            center_x = circle_x + circle_width / 2
            center_y = circle_y + circle_height / 2
            radius = min(circle_width, circle_height) * 0.4  # 40% от размера
            
            start_angle = 0
            for i, val in enumerate(values):
                if val > 0:
                    angle = (val / total) * 360
                    color = self.colors[i % len(self.colors)]
                    Color(*color)
                    self._draw_sector(center_x, center_y, radius, start_angle, angle)
                    start_angle += angle
            PopMatrix()
        
        # ---- Легенда (виджеты) ----
        legend_x = self.x + circle_width + 20
        legend_y = self.y + 20
        for i, (cat, val) in enumerate(zip(categories, values)):
            if val > 0:
                percent = (val / total) * 100
                color = self.colors[i % len(self.colors)]
                # Цветной квадрат
                color_box = Widget(size_hint=(None,None), size=(16,16),
                                   pos=(legend_x, legend_y + i*25))
                with color_box.canvas:
                    Color(*color)
                    Rectangle(pos=color_box.pos, size=color_box.size)
                self.add_widget(color_box)
                # Текст
                lbl = Label(
                    text=f"{cat} ({percent:.1f}%)",
                    font_size=10,
                    color=[0.2,0.2,0.2,1],
                    size_hint=(None,None), size=(120, 16),
                    pos=(legend_x + 22, legend_y + i*25 - 2),
                    halign='left'
                )
                self.add_widget(lbl)
        
        self.canvas.ask_update()
        print(f" Круговая диаграмма отрисована, pos={self.pos}, size={w}x{h}")
    
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
        # Добавляем mesh в текущий canvas (он уже в контексте Translate)
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