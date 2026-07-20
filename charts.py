"""Виджеты диаграмм на чистом Kivy Canvas с Translate."""
from kivy.uix.widget import Widget
from kivy.clock import Clock
from kivy.graphics import Color, Rectangle, Line, Ellipse, Mesh, PushMatrix, PopMatrix, Translate
from kivy.uix.label import Label
from kivy.metrics import dp, sp
import math


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
        
        # --- Определяем области с улучшенными отступами ---
        # Минимальная высота легенды – 70 dp, но не более 30% от высоты
        legend_height = max(dp(70), min(h * 0.30, dp(120)))
        # Оставляем отступы по бокам и сверху/снизу
        margin = dp(10)
        circle_area_h = h - legend_height - margin * 2
        circle_area_w = w - margin * 2
        circle_x = margin
        circle_y = margin
        radius = min(circle_area_w, circle_area_h) * 0.42   # чуть меньше половины
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
        legend_y = self.y + circle_area_h + margin
        legend_x_start = self.x + margin
        # Вычисляем количество элементов
        items = [(cat, val) for cat, val in zip(categories, values) if val > 0]
        if not items:
            return
        
        # Определяем количество столбцов, чтобы поместить все
        # Максимальная ширина одного элемента ~150 dp, иначе переносим
        max_item_width = dp(140)
        cols = max(1, int((w - margin * 2) / (max_item_width + dp(10))))
        rows = (len(items) + cols - 1) // cols
        
        # Высота одной строки легенды
        row_height = min(legend_height / rows, dp(28))
        #font_size = max(sp(8), row_height * 0.6)
        font_size = sp(9)   # уменьшенный шрифт легенды
        
        for idx, (cat, val) in enumerate(items):
            percent = (val / total) * 100
            row = idx // cols
            col = idx % cols
            # Распределяем ширину равномерно
            cell_width = (w - margin * 2) / cols
            x_pos = legend_x_start + col * cell_width
            y_pos = legend_y + row * row_height
            
            # Цветной квадрат
            color = self.colors[idx % len(self.colors)]
            square_size = row_height * 0.7
            color_box = Widget(size_hint=(None,None), size=(square_size, square_size),
                               pos=(x_pos, y_pos + (row_height - square_size)/2))
            with color_box.canvas:
                Color(*color)
                Rectangle(pos=color_box.pos, size=color_box.size)
            self.add_widget(color_box)
            
            # Текст
            lbl = Label(
                text=f"{cat} ({percent:.1f}%)",
                font_size=font_size,
                color=[0.2,0.2,0.2,1],
                size_hint=(None,None),
                size=(cell_width - square_size - dp(4), row_height),
                pos=(x_pos + square_size + dp(4), y_pos),
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