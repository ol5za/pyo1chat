import kivy
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.clock import Clock
from kivy.uix.spinner import Spinner
import requests
import threading
import json
import os

kivy.require('2.1.0')

# Сервери для підключення
SERVERS = [
    "https://o1zar.pythonanywhere.com",
    "https://kyrlikgolub.pythonanywhere.com"
]

CONFIG_FILE = "config.json"

LANG_DATA = {
    "en": {
        "subscription_ended": "Free subscription ended 🥲 (its joke 🤣)",
        "login": "Login",
        "enter_username": "Enter username",
        "users": "Users",
        "send": "Send",
        "type_message": "Type message...",
        "select_user": "Select user",
        "language": "Language",
        "close": "Close",
        "error": "Error",
        "failed_connect": "Failed to connect to servers.",
    },
    "ru": {
        "subscription_ended": "Подписка бесплатная закончилась 🥲(это шутка 🤣)",
        "login": "Вход",
        "enter_username": "Введите имя пользователя",
        "users": "Пользователи",
        "send": "Отправить",
        "type_message": "Введите сообщение...",
        "select_user": "Выберите пользователя",
        "language": "Язык",
        "close": "Закрыть",
        "error": "Ошибка",
        "failed_connect": "Не удалось подключиться к серверам.",
    }
}

class SubscriptionPopup(Popup):
    def __init__(self, text, lang, **kwargs):
        super().__init__(**kwargs)
        self.title = ""
        self.size_hint = (0.6, 0.4)
        self.auto_dismiss = False

        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        layout.add_widget(Label(text=text))
        btn = Button(text=LANG_DATA[lang]["close"], size_hint=(1, 0.3))
        btn.bind(on_press=self.dismiss)
        layout.add_widget(btn)
        self.add_widget(layout)

class LoginScreen(BoxLayout):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self.orientation = "vertical"
        self.padding = 20
        self.spacing = 20

        self.label = Label(text=LANG_DATA[self.app.lang]["enter_username"])
        self.add_widget(self.label)

        self.username_input = TextInput(multiline=False, font_size=24)
        self.add_widget(self.username_input)

        self.login_btn = Button(text=LANG_DATA[self.app.lang]["login"])
        self.login_btn.bind(on_press=self.login)
        self.add_widget(self.login_btn)

    def login(self, instance):
        username = self.username_input.text.strip()
        if not username:
            return
        # Перевірка реєстрації на серверах (перший доступний сервер)
        def try_login():
            for server in SERVERS:
                try:
                    res = requests.post(server + "/register", json={"username": username}, timeout=5)
                    if res.status_code == 200:
                        self.app.username = username
                        self.app.current_server = server
                        self.app.save_config()
                        self.app.show_chat_screen()
                        return
                except:
                    continue
            self.app.show_error(LANG_DATA[self.app.lang]["failed_connect"])

        threading.Thread(target=try_login).start()

class ChatScreen(BoxLayout):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self.orientation = "vertical"
        self.padding = 10
        self.spacing = 10

        # Верхній бар з вибором користувача і мовою
        top_bar = BoxLayout(size_hint_y=None, height=40, spacing=10)
        self.user_spinner = Spinner(text=LANG_DATA[self.app.lang]["select_user"], values=[])
        self.user_spinner.bind(text=self.on_user_selected)
        top_bar.add_widget(self.user_spinner)

        self.lang_btn = Button(text=LANG_DATA[self.app.lang]["language"])
        self.lang_btn.bind(on_press=self.app.switch_language)
        top_bar.add_widget(self.lang_btn)

        self.add_widget(top_bar)

        # Чат - список повідомлень
        self.chat_log = Label(size_hint_y=1, text="", markup=True)
        self.chat_log.text_size = (self.width, None)
        self.chat_log.bind(width=self.update_chat_height)
        self.add_widget(self.chat_log)

        # Введення повідомлення
        bottom_bar = BoxLayout(size_hint_y=None, height=40, spacing=10)
        self.message_input = TextInput(hint_text=LANG_DATA[self.app.lang]["type_message"], multiline=False)
        bottom_bar.add_widget(self.message_input)

        send_btn = Button(text=LANG_DATA[self.app.lang]["send"], size_hint_x=None, width=100)
        send_btn.bind(on_press=self.send_message)
        bottom_bar.add_widget(send_btn)

        self.add_widget(bottom_bar)

        self.selected_user = None
        Clock.schedule_interval(lambda dt: threading.Thread(target=self.refresh_users).start(), 5)
        Clock.schedule_interval(lambda dt: threading.Thread(target=self.refresh_messages).start(), 2)

    def update_chat_height(self, instance, value):
        self.chat_log.texture_update()
        self.chat_log.height = self.chat_log.texture_size[1]

    def on_user_selected(self, spinner, text):
        if text != LANG_DATA[self.app.lang]["select_user"]:
            self.selected_user = text
            self.refresh_messages()

    def refresh_users(self):
        for server in SERVERS:
            try:
                res = requests.get(server + "/users", timeout=5)
                if res.status_code == 200:
                    users = res.json().get("users", [])
                    if self.app.username in users:
                        users.remove(self.app.username)
                    self.user_spinner.values = users
                    return
            except:
                continue

    def refresh_messages(self):
        if not self.selected_user:
            return
        for server in SERVERS:
            try:
                params = {"user1": self.app.username, "user2": self.selected_user}
                res = requests.get(server + "/messages", params=params, timeout=5)
                if res.status_code == 200:
                    messages = res.json().get("messages", [])
                    text = ""
                    for msg in messages:
                        sender = msg["sender"]
                        content = msg["message"]
                        if sender == self.app.username:
                            text += f"[b][color=00ff00]{sender}:[/color][/b] {content}\n"
                        else:
                            text += f"[b]{sender}:[/b] {content}\n"
                    self.chat_log.text = text
                    return
            except:
                continue

    def send_message(self, instance):
        msg = self.message_input.text.strip()
        if not msg or not self.selected_user:
            return
        data = {
            "sender": self.app.username,
            "recipient": self.selected_user,
            "message": msg
        }
        for server in SERVERS:
            try:
                res = requests.post(server + "/send", json=data, timeout=5)
                if res.status_code == 200:
                    self.message_input.text = ""
                    self.refresh_messages()
                    return
            except:
                continue

class PyO1ChatApp(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.username = None
        self.current_server = None
        self.lang = "en"
        self.root_widget = None

    def build(self):
        self.load_config()
        self.root_widget = BoxLayout()
        self.show_subscription_popup()
        if self.username:
            self.show_chat_screen()
        else:
            self.show_login_screen()
        return self.root_widget

    def show_subscription_popup(self):
        text = LANG_DATA[self.lang]["subscription_ended"]
        popup = SubscriptionPopup(text=text, lang=self.lang)
        popup.open()

    def show_login_screen(self):
        self.root_widget.clear_widgets()
        login = LoginScreen(app=self)
        self.root_widget.add_widget(login)

    def show_chat_screen(self):
        self.root_widget.clear_widgets()
        chat = ChatScreen(app=self)
        self.root_widget.add_widget(chat)

    def save_config(self):
        data = {
            "username": self.username,
            "lang": self.lang
        }
        with open(CONFIG_FILE, "w") as f:
            json.dump(data, f)

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r") as f:
                data = json.load(f)
                self.username = data.get("username")
                self.lang = data.get("lang", "en")

    def switch_language(self, instance):
        self.lang = "ru" if self.lang == "en" else "en"
        self.save_config()
        # Перезапустити поточний екран
        if self.username:
            self.show_chat_screen()
        else:
            self.show_login_screen()

    def show_error(self, message):
        popup = Popup(title=LANG_DATA[self.lang]["error"],
                      content=Label(text=message),
                      size_hint=(0.6, 0.4))
        popup.open()

if __name__ == "__main__":
    PyO1ChatApp().run()