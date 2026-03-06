# main.py
from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition
from kivy.lang import Builder
import os

# Загружаем все KV файлы
for kv_file in ['views/css.kv', 'views/login.kv', 'views/main.kv', 'views/reports_screen.kv']:
    if os.path.exists(kv_file):
        Builder.load_file(kv_file)

# Экраны (Python классы)
class LoginScreen(Screen):
    """Экран входа"""
    def check_pin(self, pin):
        if pin == "1234":  # временно для примера
            self.manager.current = 'main'
            return True
        return False

class MainScreen(Screen):
    """Главный экран"""
    def on_enter(self):
        print('Добро пожаловать в главное меню!')

class ReportsScreen(Screen):
    """Экран отчетов"""
    def generate_report(self):
        print('Генерация отчета...')

class MainApp(App):
    def build(self):
        # Создаем менеджер экранов
        sm = ScreenManager(transition=SlideTransition())
        
        # Добавляем экраны
        sm.add_widget(LoginScreen(name='login'))
        sm.add_widget(MainScreen(name='main'))
        sm.add_widget(ReportsScreen(name='reports'))
        
        return sm

if __name__ == '__main__':
    MainApp().run()
    print()
    print()