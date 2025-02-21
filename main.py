import hashlib
import json
import sqlite3
import uuid
import webbrowser  # Added for opening donation links

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.utils import platform
from plyer import filechooser

is_android = platform == 'android'

GEN1_POKEMON = [
    "Bulbasaur", "Ivysaur", "Venusaur", "Charmander", "Charmeleon", "Charizard",
    "Squirtle", "Wartortle", "Blastoise", "Caterpie", "Metapod", "Butterfree",
    "Weedle", "Kakuna", "Beedrill", "Pidgey", "Pidgeotto", "Pidgeot",
    "Rattata", "Raticate", "Spearow", "Fearow", "Ekans", "Arbok",
    "Pikachu", "Raichu", "Sandshrew", "Sandslash", "Nidoran♀", "Nidorina",
    "Nidoqueen", "Nidoran♂", "Nidorino", "Nidoking", "Clefairy", "Clefable",
    "Vulpix", "Ninetales", "Jigglypuff", "Wigglytuff", "Zubat", "Golbat",
    "Oddish", "Gloom", "Vileplume", "Paras", "Parasect", "Venonat", "Venomoth",
    "Diglett", "Dugtrio", "Meowth", "Persian", "Psyduck", "Golduck",
    "Mankey", "Primeape", "Growlithe", "Arcanine", "Poliwag", "Poliwhirl",
    "Poliwrath", "Abra", "Kadabra", "Alakazam", "Machop", "Machoke", "Machamp",
    "Bellsprout", "Weepinbell", "Victreebel", "Tentacool", "Tentacruel",
    "Geodude", "Graveler", "Golem", "Ponyta", "Rapidash", "Slowpoke", "Slowbro",
    "Magnemite", "Magneton", "Farfetch'd", "Doduo", "Dodrio", "Seel", "Dewgong",
    "Grimer", "Muk", "Shellder", "Cloyster", "Gastly", "Haunter", "Gengar",
    "Onix", "Drowzee", "Hypno", "Krabby", "Kingler", "Voltorb", "Electrode",
    "Exeggcute", "Exeggutor", "Cubone", "Marowak", "Hitmonlee", "Hitmonchan",
    "Lickitung", "Koffing", "Weezing", "Rhyhorn", "Rhydon", "Chansey",
    "Tangela", "Kangaskhan", "Horsea", "Seadra", "Goldeen", "Seaking",
    "Staryu", "Starmie", "Mr. Mime", "Scyther", "Jynx", "Electabuzz",
    "Magmar", "Pinsir", "Tauros", "Magikarp", "Gyarados", "Lapras", "Ditto",
    "Eevee", "Vaporeon", "Jolteon", "Flareon", "Porygon", "Omanyte", "Omastar",
    "Kabuto", "Kabutops", "Aerodactyl", "Snorlax", "Articuno", "Zapdos",
    "Moltres", "Dratini", "Dragonair", "Dragonite", "Mewtwo", "Mew"
]


def init_db():
    conn = sqlite3.connect("shinyquest.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (id INTEGER PRIMARY KEY, username TEXT UNIQUE, email TEXT UNIQUE, password TEXT, bio TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS hunts 
                 (id INTEGER PRIMARY KEY, user_id TEXT, pokemon TEXT, game TEXT, 
                  method TEXT, counter INTEGER, success BOOLEAN)''')
    c.execute('''CREATE TABLE IF NOT EXISTS guest_hunts 
                 (id INTEGER PRIMARY KEY, guest_id TEXT, pokemon TEXT, game TEXT, 
                  method TEXT, counter INTEGER, success BOOLEAN)''')
    c.execute('''CREATE TABLE IF NOT EXISTS living_dex 
                 (id INTEGER PRIMARY KEY, user_id TEXT, pokemon TEXT, game TEXT, UNIQUE(user_id, pokemon))''')
    conn.commit()
    conn.close()


def update_living_dex(user_id):
    conn = sqlite3.connect("shinyquest.db")
    c = conn.cursor()
    table = "guest_hunts" if user_id.startswith("guest_") else "hunts"
    c.execute(f"SELECT DISTINCT pokemon, game FROM {table} WHERE user_id=? AND success=1", (user_id,))
    successful_hunts = c.fetchall()
    for pokemon, game in successful_hunts:
        try:
            c.execute("INSERT OR IGNORE INTO living_dex (user_id, pokemon, game) VALUES (?, ?, ?)",
                      (user_id, pokemon, game))
        except sqlite3.IntegrityError:
            pass
    conn.commit()
    conn.close()


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


class MainMenuScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', padding=20, spacing=10)
        layout.add_widget(Label(text="Welcome to ShinyQuest!", font_size=24))
        login_btn = Button(text="Login", size_hint=(1, 0.2))
        login_btn.bind(on_press=self.go_to_login)
        layout.add_widget(login_btn)
        register_btn = Button(text="Register", size_hint=(1, 0.2))
        register_btn.bind(on_press=self.go_to_register)
        layout.add_widget(register_btn)
        guest_btn = Button(text="Continue as Guest", size_hint=(1, 0.2))
        guest_btn.bind(on_press=self.guest_mode)
        layout.add_widget(guest_btn)
        credits_btn = Button(text="Credits", size_hint=(1, 0.2))  # New button
        credits_btn.bind(on_press=self.go_to_credits)
        layout.add_widget(credits_btn)
        self.add_widget(layout)

    def go_to_login(self, instance):
        self.manager.current = 'login'

    def go_to_register(self, instance):
        self.manager.current = 'register'

    def guest_mode(self, instance):
        App.get_running_app().current_user = f"guest_{uuid.uuid4().hex}"
        self.manager.current = 'hunt'

    def go_to_credits(self, instance):
        self.manager.current = 'credits'


class LoginScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', padding=20, spacing=10)
        layout.add_widget(Label(text="Login", font_size=20))
        self.username_input = TextInput(hint_text="Username")
        layout.add_widget(self.username_input)
        self.password_input = TextInput(hint_text="Password", password=True)
        layout.add_widget(self.password_input)
        login_btn = Button(text="Login")
        login_btn.bind(on_press=self.login)
        layout.add_widget(login_btn)
        back_btn = Button(text="Back")
        back_btn.bind(on_press=self.go_back)
        layout.add_widget(back_btn)
        self.add_widget(layout)

    def go_back(self, instance):
        self.manager.current = 'main'

    def login(self, instance):
        username = self.username_input.text
        password = hash_password(self.password_input.text)
        conn = sqlite3.connect("shinyquest.db")
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
        user = c.fetchone()
        conn.close()
        if user:
            App.get_running_app().current_user = username
            update_living_dex(username)  # Update living dex on login
            self.manager.get_screen('hunt').update_user()
            self.manager.get_screen('profile').update_user()
            self.manager.get_screen('history').update_user()
            self.manager.get_screen('living_dex').update_user()
            self.manager.current = 'hunt'
        else:
            popup = Popup(title='Error', content=Label(text='Invalid credentials'), size_hint=(0.8, 0.3))
            popup.open()


class RegisterScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', padding=20, spacing=10)
        layout.add_widget(Label(text="Register", font_size=20))
        self.username_input = TextInput(hint_text="Username")
        layout.add_widget(self.username_input)
        self.email_input = TextInput(hint_text="Email")
        layout.add_widget(self.email_input)
        self.password_input = TextInput(hint_text="Password", password=True)
        layout.add_widget(self.password_input)
        register_btn = Button(text="Register")
        register_btn.bind(on_press=self.register)
        layout.add_widget(register_btn)
        import_btn = Button(text="Import Guest Hunts")
        import_btn.bind(on_press=self.import_guest_hunts_prompt)
        layout.add_widget(import_btn)
        back_btn = Button(text="Back")
        back_btn.bind(on_press=self.go_back)
        layout.add_widget(back_btn)
        self.add_widget(layout)

    def go_back(self, instance):
        self.manager.current = 'main'

    def register(self, instance):
        username = self.username_input.text
        email = self.email_input.text
        password = hash_password(self.password_input.text)
        conn = sqlite3.connect("shinyquest.db")
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users (username, email, password, bio) VALUES (?, ?, ?, ?)",
                      (username, email, password, ""))
            conn.commit()
            App.get_running_app().current_user = username
            update_living_dex(username)  # Update living dex on register
            self.manager.get_screen('hunt').update_user()
            self.manager.get_screen('profile').update_user()
            self.manager.get_screen('history').update_user()
            self.manager.get_screen('living_dex').update_user()
            self.manager.current = 'hunt'
        except sqlite3.IntegrityError:
            popup = Popup(title='Error', content=Label(text='Username or email already exists'), size_hint=(0.8, 0.3))
            popup.open()
        finally:
            conn.close()

    def import_guest_hunts_prompt(self, instance):
        filechooser.open_file(on_selection=self.import_guest_hunts)

    def import_guest_hunts(self, selection):
        if not selection:
            return
        filepath = selection[0]
        conn = sqlite3.connect("shinyquest.db")
        c = conn.cursor()
        try:
            with open(filepath, 'r') as f:
                guest_hunts = json.load(f)
                username = App.get_running_app().current_user
                if username.startswith("guest_"):
                    popup = Popup(title='Error', content=Label(text='Register first to import hunts'),
                                  size_hint=(0.8, 0.3))
                    popup.open()
                    return
                for hunt in guest_hunts:
                    c.execute(
                        "INSERT INTO hunts (user_id, pokemon, game, method, counter, success) VALUES (?, ?, ?, ?, ?, ?)",
                        (username, hunt['pokemon'], hunt['game'], hunt['method'], hunt['counter'], hunt['success']))
                conn.commit()
                popup = Popup(title='Success', content=Label(text='Guest hunts imported!'), size_hint=(0.8, 0.3))
                popup.open()
        except Exception as e:
            popup = Popup(title='Error', content=Label(text=f'Import failed: {str(e)}'), size_hint=(0.8, 0.3))
            popup.open()
        finally:
            conn.close()


class ProfileScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_user = App.get_running_app().current_user or "Unknown"
        self.refresh_profile()

    def refresh_profile(self):
        layout = BoxLayout(orientation='vertical', padding=20, spacing=10)
        self.user_label = Label(text=f"Profile: {self.current_user}", font_size=20)
        layout.add_widget(self.user_label)
        conn = sqlite3.connect("shinyquest.db")
        c = conn.cursor()
        c.execute("SELECT username, email, bio FROM users WHERE username=?", (self.current_user,))
        user_info = c.fetchone()
        if user_info and not self.current_user.startswith("guest_"):
            username, email, bio = user_info
            layout.add_widget(Label(text=f"Username: {username}", font_size=16))
            layout.add_widget(Label(text=f"Email: {email}", font_size=16))
            self.bio_input = TextInput(text=bio or "", hint_text="Bio", multiline=True)
            layout.add_widget(self.bio_input)
            save_bio_btn = Button(text="Save Bio")
            save_bio_btn.bind(on_press=self.save_bio)
            layout.add_widget(save_bio_btn)
            c.execute(
                "SELECT COUNT(*), SUM(counter), SUM(CASE WHEN success THEN 1 ELSE 0 END), method FROM hunts WHERE user_id=? GROUP BY method",
                (self.current_user,))
            hunt_data = c.fetchall()
            total_hunts = sum(row[0] for row in hunt_data) or 0
            total_attempts = sum(row[1] for row in hunt_data) or 0
            successful_hunts = sum(row[2] for row in hunt_data) or 0
            c.execute("SELECT COUNT(DISTINCT pokemon) FROM hunts WHERE user_id=? AND success=1", (self.current_user,))
            unique_pokemon = c.fetchone()[0] or 0
            favorite_method = max(hunt_data, key=lambda x: x[0], default=(0, 0, 0, "None"))[3]
            avg_attempts = total_attempts / successful_hunts if successful_hunts > 0 else 0
            layout.add_widget(Label(text=f"Total Hunts: {total_hunts}", font_size=16))
            layout.add_widget(Label(text=f"Total Attempts: {total_attempts}", font_size=16))
            layout.add_widget(Label(text=f"Successful Hunts: {successful_hunts}", font_size=16))
            layout.add_widget(Label(text=f"Unique Pokémon Caught: {unique_pokemon}", font_size=16))
            layout.add_widget(Label(text=f"Avg Attempts per Success: {avg_attempts:.2f}", font_size=16))
            layout.add_widget(Label(text=f"Favorite Method: {favorite_method}", font_size=16))
        conn.close()
        back_btn = Button(text="Back")
        back_btn.bind(on_press=self.go_back)
        layout.add_widget(back_btn)
        self.clear_widgets()
        self.add_widget(layout)

    def save_bio(self, instance):
        new_bio = self.bio_input.text
        conn = sqlite3.connect("shinyquest.db")
        c = conn.cursor()
        c.execute("UPDATE users SET bio=? WHERE username=?", (new_bio, self.current_user))
        conn.commit()
        conn.close()
        popup = Popup(title='Success', content=Label(text='Bio updated!'), size_hint=(0.8, 0.3))
        popup.open()

    def go_back(self, instance):
        self.manager.current = 'hunt'  # Changed from 'main' to 'hunt'

    def update_user(self):
        self.current_user = App.get_running_app().current_user or "Unknown"
        self.refresh_profile()


class HuntScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_user = App.get_running_app().current_user or "Unknown"
        self.refresh_layout()

    def refresh_layout(self):
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        self.user_label = Label(text=f"New Shiny Hunt (User: {self.current_user})")
        layout.add_widget(self.user_label)
        if self.current_user.startswith("guest_"):
            warning = Label(text="Guest Mode: Hunts are session-only. Export to save them!", color=(1, 0, 0, 1),
                            font_size=16)
            layout.add_widget(warning)
        self.pokemon_input = TextInput(hint_text="Pokémon (e.g., Pikachu)")
        layout.add_widget(self.pokemon_input)
        save_btn = Button(text="Save Hunt")
        save_btn.bind(on_press=self.save_hunt)
        layout.add_widget(save_btn)
        success_btn = Button(text="Mark as Successful")
        success_btn.bind(on_press=self.mark_successful)
        layout.add_widget(success_btn)
        history_btn = Button(text="View Hunt History")
        history_btn.bind(on_press=self.go_to_history)
        layout.add_widget(history_btn)
        dex_btn = Button(text="View Living Dex")
        dex_btn.bind(on_press=self.go_to_living_dex)
        layout.add_widget(dex_btn)
        if self.current_user.startswith("guest_"):
            export_btn = Button(text="Export Hunts")
            export_btn.bind(on_press=self.export_hunts_prompt)
            layout.add_widget(export_btn)
        profile_btn = Button(text="View Profile")
        profile_btn.bind(on_press=self.go_to_profile)
        layout.add_widget(profile_btn)
        back_btn = Button(text="Back")
        back_btn.bind(on_press=self.go_back)
        layout.add_widget(back_btn)
        self.clear_widgets()
        self.add_widget(layout)

    def update_user(self):
        self.current_user = App.get_running_app().current_user or "Unknown"
        self.refresh_layout()

    def save_hunt(self, instance):
        conn = sqlite3.connect("shinyquest.db")
        c = conn.cursor()
        if self.current_user.startswith("guest_"):
            c.execute(
                "INSERT INTO guest_hunts (guest_id, pokemon, game, method, counter, success) VALUES (?, ?, ?, ?, ?, ?)",
                (self.current_user, self.pokemon_input.text, "Unknown", "Unknown", 0, False))
        else:
            c.execute("INSERT INTO hunts (user_id, pokemon, game, method, counter, success) VALUES (?, ?, ?, ?, ?, ?)",
                      (self.current_user, self.pokemon_input.text, "Unknown", "Unknown", 0, False))
        conn.commit()
        conn.close()
        popup = Popup(title='Success', content=Label(text='Hunt saved!'), size_hint=(0.8, 0.3))
        popup.open()

    def mark_successful(self, instance):
        pokemon = self.pokemon_input.text
        if not pokemon:
            popup = Popup(title='Error', content=Label(text='Enter a Pokémon first!'), size_hint=(0.8, 0.3))
            popup.open()
            return
        conn = sqlite3.connect("shinyquest.db")
        c = conn.cursor()
        if self.current_user.startswith("guest_"):
            c.execute(
                "UPDATE guest_hunts SET success=1, counter=counter+1 WHERE guest_id=? AND pokemon=? AND success=0",
                (self.current_user, pokemon))
        else:
            c.execute("UPDATE hunts SET success=1, counter=counter+1 WHERE user_id=? AND pokemon=? AND success=0",
                      (self.current_user, pokemon))
        conn.commit()
        update_living_dex(self.current_user)
        conn.close()
        popup = Popup(title='Success', content=Label(text='Hunt marked as successful!'), size_hint=(0.8, 0.3))
        popup.open()

    def go_to_history(self, instance):
        self.manager.current = 'history'

    def go_to_profile(self, instance):
        self.manager.current = 'profile'

    def go_to_living_dex(self, instance):
        self.manager.current = 'living_dex'

    def go_back(self, instance):
        self.manager.current = 'hunt'


class HuntHistoryScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_user = App.get_running_app().current_user or "Unknown"
        self.refresh_history()

    def refresh_history(self):
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        self.user_label = Label(text=f"Hunt History (User: {self.current_user})", font_size=20)
        layout.add_widget(self.user_label)
        if self.current_user.startswith("guest_"):
            warning = Label(text="Guest Mode: Hunts are session-only. Export to save them!", color=(1, 0, 0, 1),
                            font_size=16)
            layout.add_widget(warning)
        scroll = ScrollView()
        grid = GridLayout(cols=1, spacing=10, size_hint_y=None)
        grid.bind(minimum_height=grid.setter('height'))
        conn = sqlite3.connect("shinyquest.db")
        c = conn.cursor()
        if self.current_user.startswith("guest_"):
            c.execute("SELECT id, pokemon, game, method, counter, success FROM guest_hunts WHERE guest_id=?",
                      (self.current_user,))
        else:
            c.execute("SELECT id, pokemon, game, method, counter, success FROM hunts WHERE user_id=?",
                      (self.current_user,))
        hunts = c.fetchall()
        conn.close()
        for hunt in hunts:
            hunt_id, pokemon, game, method, counter, success = hunt
            hunt_text = f"{pokemon} | Game: {game} | Method: {method} | Attempts: {counter} | Success: {'Yes' if success else 'No'}"
            hunt_box = BoxLayout(orientation='horizontal', size_hint_y=None, height=40)
            hunt_box.add_widget(Label(text=hunt_text))
            if success:
                share_btn = Button(text="Share", size_hint_x=0.2)
                share_btn.bind(on_press=lambda instance, p=pokemon, c=counter: self.share_hunt(p, c))
                hunt_box.add_widget(share_btn)
            delete_btn = Button(text="Delete", size_hint_x=0.2)
            delete_btn.bind(on_press=lambda instance, hid=hunt_id: self.delete_hunt(hid))
            hunt_box.add_widget(delete_btn)
            grid.add_widget(hunt_box)
        scroll.add_widget(grid)
        layout.add_widget(scroll)
        back_btn = Button(text="Back", size_hint=(1, 0.1))
        back_btn.bind(on_press=self.go_back)
        layout.add_widget(back_btn)
        self.clear_widgets()
        self.add_widget(layout)

    def delete_hunt(self, hunt_id):
        conn = sqlite3.connect("shinyquest.db")
        c = conn.cursor()
        if self.current_user.startswith("guest_"):
            c.execute("DELETE FROM guest_hunts WHERE id=?", (hunt_id,))
        else:
            c.execute("DELETE FROM hunts WHERE id=?", (hunt_id,))
        conn.commit()
        conn.close()
        self.refresh_history()
        popup = Popup(title='Success', content=Label(text='Hunt deleted!'), size_hint=(0.8, 0.3))
        popup.open()

    def share_hunt(self, pokemon, counter):
        share_text = f"Caught a shiny {pokemon} after {counter} attempts!"
        popup = Popup(title='Share', content=Label(text=share_text), size_hint=(0.8, 0.3))
        popup.open()

    def go_back(self, instance):
        self.manager.current = 'hunt'

    def update_user(self):  # Added to fix the AttributeError
        self.current_user = App.get_running_app().current_user or "Unknown"
        self.refresh_history()


class LivingDexScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_user = App.get_running_app().current_user or "Unknown"
        self.sort_by = "name"
        self.refresh_dex()

    def refresh_dex(self):
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        layout.add_widget(Label(text=f"Shiny Living Dex (User: {self.current_user})", font_size=20))

        sort_box = BoxLayout(orientation='horizontal', size_hint_y=0.1)
        name_btn = Button(text="Sort by Name")
        name_btn.bind(on_press=lambda x: self.set_sort("name"))
        sort_box.add_widget(name_btn)
        game_btn = Button(text="Sort by Game")
        game_btn.bind(on_press=lambda x: self.set_sort("game"))
        sort_box.add_widget(game_btn)
        layout.add_widget(sort_box)

        scroll = ScrollView()
        self.grid = GridLayout(cols=3, spacing=10, size_hint_y=None)
        self.grid.bind(minimum_height=self.grid.setter('height'))

        update_living_dex(self.current_user)
        conn = sqlite3.connect("shinyquest.db")
        c = conn.cursor()
        table = "guest_hunts" if self.current_user.startswith("guest_") else "hunts"
        c.execute(f"SELECT pokemon, game, method, counter FROM {table} WHERE user_id=? AND success=1",
                  (self.current_user,))
        caught_pokemon = {row[0]: {"game": row[1], "method": row[2], "counter": row[3]} for row in c.fetchall()}
        conn.close()

        pokemon_list = GEN1_POKEMON.copy()
        if self.sort_by == "name":
            pokemon_list.sort()
        elif self.sort_by == "game":
            pokemon_list = sorted(pokemon_list, key=lambda p: caught_pokemon.get(p, {"game": "ZZZ"})["game"])

        for pokemon in pokemon_list:
            card = Button(size_hint_y=None, height=100,
                          background_color=(0.2, 0.2, 0.2, 1) if pokemon not in caught_pokemon else (0, 1, 0, 1))
            card_layout = BoxLayout(orientation='vertical')
            card_layout.add_widget(Label(text=pokemon, font_size=16))
            if pokemon in caught_pokemon:
                card_layout.add_widget(Label(text=f"Game: {caught_pokemon[pokemon]['game']}", font_size=12))
                card.bind(on_press=lambda instance, p=pokemon: self.show_details(p))
            else:
                card_layout.add_widget(Label(text="Not Caught", font_size=12))
            card.add_widget(card_layout)
            self.grid.add_widget(card)

        scroll.add_widget(self.grid)
        layout.add_widget(scroll)

        share_btn = Button(text="Share Dex", size_hint=(1, 0.1))
        share_btn.bind(on_press=self.share_dex)
        layout.add_widget(share_btn)

        back_btn = Button(text="Back", size_hint=(1, 0.1))
        back_btn.bind(on_press=self.go_back)
        layout.add_widget(back_btn)
        self.clear_widgets()
        self.add_widget(layout)

    def set_sort(self, sort_type):
        self.sort_by = sort_type
        self.refresh_dex()

    def show_details(self, pokemon):
        conn = sqlite3.connect("shinyquest.db")
        c = conn.cursor()
        table = "guest_hunts" if self.current_user.startswith("guest_") else "hunts"
        c.execute(f"SELECT game, method, counter FROM {table} WHERE user_id=? AND pokemon=? AND success=1 LIMIT 1",
                  (self.current_user, pokemon))
        details = c.fetchone()
        conn.close()
        if details:
            game, method, counter = details
            details_text = f"Pokemon: {pokemon}\nGame: {game}\nMethod: {method}\nAttempts: {counter}"
            popup_layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
            popup_layout.add_widget(Label(text=details_text))
            delete_btn = Button(text="Delete from Dex", size_hint_y=0.3)
            delete_btn.bind(on_press=lambda x: self.confirm_delete(pokemon))
            popup_layout.add_widget(delete_btn)
            popup = Popup(title=f"{pokemon} Details", content=popup_layout, size_hint=(0.8, 0.4))
            popup.open()

    def confirm_delete(self, pokemon):
        confirm_layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        confirm_layout.add_widget(Label(text=f"Are you sure you want to remove {pokemon} from your Living Dex?"))
        btn_box = BoxLayout(orientation='horizontal', spacing=10)
        yes_btn = Button(text="Yes")
        yes_btn.bind(on_press=lambda x: self.delete_from_dex(pokemon))
        btn_box.add_widget(yes_btn)
        no_btn = Button(text="No")
        no_btn.bind(on_press=lambda x: self.dismiss_popup())
        btn_box.add_widget(no_btn)
        confirm_layout.add_widget(btn_box)
        self.confirm_popup = Popup(title="Confirm Deletion", content=confirm_layout, size_hint=(0.8, 0.3))
        self.confirm_popup.open()

    def delete_from_dex(self, pokemon):
        conn = sqlite3.connect("shinyquest.db")
        c = conn.cursor()
        c.execute("DELETE FROM living_dex WHERE user_id=? AND pokemon=?", (self.current_user, pokemon))
        conn.commit()
        conn.close()
        self.confirm_popup.dismiss()
        self.refresh_dex()
        popup = Popup(title='Success', content=Label(text=f"{pokemon} removed from Living Dex!"), size_hint=(0.8, 0.3))
        popup.open()

    def dismiss_popup(self):
        self.confirm_popup.dismiss()

    def share_dex(self, instance):
        conn = sqlite3.connect("shinyquest.db")
        c = conn.cursor()
        c.execute("SELECT pokemon, game FROM living_dex WHERE user_id=?", (self.current_user,))
        dex_list = c.fetchall()
        conn.close()
        if not dex_list:
            popup = Popup(title='Info', content=Label(text='Your Living Dex is empty!'), size_hint=(0.8, 0.3))
            popup.open()
            return
        share_text = f"My Shiny Living Dex:\n" + "\n".join([f"{p} ({g})" for p, g in dex_list])
        popup = Popup(title='Share Dex', content=Label(text=share_text), size_hint=(0.8, 0.5))
        popup.open()

    def go_back(self, instance):
        self.manager.current = 'hunt'

    def update_user(self):
        self.current_user = App.get_running_app().current_user or "Unknown"
        self.refresh_dex()


class CreditsScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', padding=20, spacing=10)

        # Username and bio (placeholders)
        layout.add_widget(Label(text="Created by: CoyoteCoding", font_size=24))
        layout.add_widget(Label(text="A passionate Pokémon fan and developer who loves building tools "
                                     "for the shiny hunting community. ShinyQuest is my way of giving back!",
                                font_size=16, halign='center', valign='middle', text_size=(400, None)))

        # Donation links (placeholders)
        crypto_btn = Button(text="Donate Crypto (BTC)", size_hint=(1, 0.2))
        crypto_btn.bind(on_press=lambda x: webbrowser.open("bitcoin:1ExampleBTCAddress123456789"))
        layout.add_widget(crypto_btn)

        fiat_btn = Button(text="Donate via PayPal", size_hint=(1, 0.2))
        fiat_btn.bind(on_press=lambda x: webbrowser.open("https://paypal.me/exampleuser"))
        layout.add_widget(fiat_btn)

        # Back button
        back_btn = Button(text="Back", size_hint=(1, 0.2))
        back_btn.bind(on_press=self.go_back)
        layout.add_widget(back_btn)

        self.add_widget(layout)

    def go_back(self, instance):
        self.manager.current = 'main'


class ShinyQuestApp(App):
    current_user = None

    def build(self):
        init_db()
        sm = ScreenManager()
        sm.add_widget(MainMenuScreen(name='main'))
        sm.add_widget(LoginScreen(name='login'))
        sm.add_widget(RegisterScreen(name='register'))
        sm.add_widget(HuntScreen(name='hunt'))
        sm.add_widget(ProfileScreen(name='profile'))
        sm.add_widget(HuntHistoryScreen(name='history'))
        sm.add_widget(LivingDexScreen(name='living_dex'))
        sm.add_widget(CreditsScreen(name='credits'))  # Add new screen
        return sm

if __name__ == '__main__':
    ShinyQuestApp().run()
