from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition
from kivy.lang import Builder
import os
from models import *

# Загружаем все KV файлы
for kv_file in ['views/auth.kv','views/login.kv','views/main.kv']:  # Убедитесь что путь правильный
    if os.path.exists(kv_file):
        Builder.load_file(kv_file)


class LoginScreen(Screen):
    def on_enter(self):
        App.get_running_app().title = "Вход в систему"
class AuthScreen(Screen):
    def on_enter(self):
        App.get_running_app().title = "Регистрация"
    def register(self):
        set_password(self.ids.password.text)
        self.manager.current = 'MainScreen'

class MainScreen(Screen):
    def on_enter(self):
        App.get_running_app().title = "Главная"
        self.ids.balance.text = str(get_balance())
        self.ids.monthly_profit.text = str(get_monthly_profit())


class MainApp(App):
    def build(self):
        engine = create_database('sqlite:///finance.db', drop_existing=True)

        sm = ScreenManager(transition=SlideTransition())
        
        sm.add_widget(AuthScreen(name='AuthScreen'))
        sm.add_widget(LoginScreen(name='LoginScreen'))
        sm.add_widget(MainScreen(name= 'MainScreen'))

        if is_registered():
            sm.current = 'LoginScreen'
        else:
            sm.current = 'AuthScreen'

        return sm

if __name__ == '__main__':
    MainApp().run()