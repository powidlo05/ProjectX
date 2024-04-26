import telebot
from telebot import types
import requests
import json
import datetime


bot = telebot.TeleBot(BOT_TOKEN)

# Словарь для хранения избранных городов
favorite_cities = {}


# Функция для записи запросов в txt
def write_req(city):
    try:
        with open("requests.txt", "a") as file:
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            file.write(f"{now}: Requested city - {city}\n")  # Запись времени запроса и города
    except Exception as e:
        print(f"Error writing to file: {str(e)}")


# Функция для получения погоды
def get_weather(city, day="today"):
    # Формирование URL запроса для текущей погоды или прогноза на завтра
    api_url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={OPENWEATHER_TOKEN}&units=metric&lang=ru"
    if day == "tomorrow":
        api_url = f"http://api.openweathermap.org/data/2.5/forecast?q={city}&appid={OPENWEATHER_TOKEN}&units=metric&" \
                  f"lang=ru&cnt=2"
    write_req(city)  # Запись запроса в файл
    response = requests.get(api_url)   # Отправка запроса
    if response.status_code == 200:  # Успешный запрос
        data = json.loads(response.content)  # Парсинг json ответа
        # Извлечение данных о погоде
        if day == "today":
            # извлечение данных для текущей погоды
            temp = data['main']['temp']
            feels_like = data['main']['feels_like']
            temp_min = data['main']['temp_min']
            temp_max = data['main']['temp_max']
            humidity = data['main']['humidity']
            description = data['weather'][0]['description']
            wind_speed = data['wind']['speed']
            icon = data['weather'][0]['icon']
            return temp, feels_like, temp_min, temp_max, humidity, description, wind_speed, icon
        else:
            # извлечение данных для прогноза на завтра
            temp = data['list'][1]['main']['temp']
            feels_like = data['list'][1]['main']['feels_like']
            temp_min = data['list'][1]['main']['temp_min']
            temp_max = data['list'][1]['main']['temp_max']
            humidity = data['list'][1]['main']['humidity']
            description = data['list'][1]['weather'][0]['description']
            wind_speed = data['list'][1]['wind']['speed']
            icon = data['list'][1]['weather'][0]['icon']
            return temp, feels_like, temp_min, temp_max, humidity, description, wind_speed, icon
    else:
        return None, None, None, None, None, None, None, None  # Возврат None при ошибке


# Функция для определения города по координатам
def get_city_by_location(latitude, longitude):
    # формирование URL запроса к Яндекс Геокодеру
    api_url = f"https://geocode-maps.yandex.ru/1.x/?apikey={YANDEX_GEOCODER_TOKEN}&geocode={longitude},{latitude}&" \
              f"format=json"
    try:
        response = requests.get(api_url)
        if response.status_code == 200:
            data = json.loads(response.content)
            # извлечение названия города из JSON ответа
            city = data['response']['GeoObjectCollection']['featureMember'][0]['GeoObject']['metaDataProperty'][
                'GeocoderMetaData']['Address']['Components'][4]['name']
            return city
        else:
            return None
    except ConnectionError as err:
        print(f"ConnectionError: {err}")
        return None


# Обработчик команды start
@bot.message_handler(commands=['start'])
def start(message):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    button1 = types.KeyboardButton("Ввести город")
    button2 = types.KeyboardButton("Определить местоположение", request_location=True)
    button3 = types.KeyboardButton("Избранные города")  # Добавили кнопку для избранных городов
    keyboard.add(button1, button2, button3)
    bot.send_message(message.chat.id, "Привет! Как хочешь узнать погоду?", reply_markup=keyboard)


# Обработчик геолокации
@bot.message_handler(content_types=['location'])
def location(message):
    if message.location is not None:
        latitude = message.location.latitude
        longitude = message.location.longitude
        city = get_city_by_location(latitude, longitude)
        if city:
            show_weather(message, city)
        else:
            bot.send_message(message.chat.id, "Не удалось определить город")


# Обработчик текстовых сообщений
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    if message.text == "Ввести город":
        msg = bot.send_message(message.chat.id, "Введите название города:")
        bot.register_next_step_handler(msg, show_weather)  # Регистрация следующего сообщения для обработки show_weather
    elif message.text == "Избранные города":
        show_favorite_cities(message)
    else:
        bot.send_message(message.chat.id, "Не понимаю команду.")


# Функция для вывода погоды
def show_weather(message, city=None):
    if city is None:
        city = message.text
    temp, feels_like, temp_min, temp_max, humidity, description, wind_speed, icon = get_weather(city)
    if temp:
        weather_message = f"Погода в городе {city}:\n" \
                          f"🌡️ Температура: {temp:.1f}°C (ощущается как {feels_like:.1f}°C)\n" \
                          f"⬇️ Минимум: {temp_min:.1f}°C, ⬆️ Максимум: {temp_max:.1f}°C\n" \
                          f"💧 Влажность: {humidity}%\n" \
                          f"🌬️ Ветер: {wind_speed} м/с\n" \
                          f"☁️Описание погоды: {description}"
        keyboard = types.InlineKeyboardMarkup()
        button1 = types.InlineKeyboardButton("Погода на завтра", callback_data="tomorrow")
        add_button = types.InlineKeyboardButton("В избранное", callback_data=f"add_{city}")
        remove_button = types.InlineKeyboardButton("Удалить из избранных", callback_data=f"remove_{city}")
        keyboard.add(button1, add_button, remove_button)
        bot.send_message(message.chat.id, weather_message, reply_markup=keyboard)
    else:
        bot.send_message(message.chat.id, "Не удалось получить погоду.")


@bot.callback_query_handler(func=lambda query: query.data == "tomorrow")
def show_tomorrow_weather(query):
    city = query.message.text.split("\n")[0].split(":")[0].split()[-1]
    temp, feels_like, temp_min, temp_max, humidity, description, wind_speed, icon = get_weather(city, "tomorrow")
    if temp:
        bot.send_message(chat_id=query.message.chat.id,
                         text=f"Погода в городе {city} завтра:\n"
                              f"🌡️ Температура: {temp:.1f}°C (ощущается как {feels_like:.1f}°C)\n"
                              f"⬇️ Минимум: {temp_min:.1f}°C, ⬆️ Максимум: {temp_max:.1f}°C\n"
                              f"💧 Влажность: {humidity}%\n"
                              f"🌬️ Ветер: {wind_speed} м/с\n"
                              f"☁️Описание погоды: {description}")
        bot.send_photo(query.message.chat.id, f"http://openweathermap.org/img/wn/{icon}@2x.png")
    else:
        bot.answer_callback_query(query.id, "Ошибка получения данных")


# Функция для вывода избранных городов
def show_favorite_cities(message):
    if favorite_cities:
        keyboard = types.InlineKeyboardMarkup()
        for city in favorite_cities:
            button = types.InlineKeyboardButton(city, callback_data=f"city_{city}")
            keyboard.add(button)
        bot.send_message(message.chat.id, "Избранные города:", reply_markup=keyboard)
    else:
        bot.send_message(message.chat.id, "У вас нет избранных городов.")


# Обработчик нажатий на inline-кнопки
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    data = call.data.split("_")
    action = data[0]

    if len(data) > 1:
        city = data[1]
    else:
        city = None  # Если город не указан, устанавливаем None

    if action == "city":
        show_weather(call.message, city)
    elif action == "add":
        if city not in favorite_cities:
            favorite_cities[city] = True  # Добавляем город в словарь
            bot.answer_callback_query(call.id, "Город добавлен в избранные")
        else:
            bot.answer_callback_query(call.id, "Город уже находится в списке избранных мест")
    elif action == "remove":
        if city in favorite_cities:
            del favorite_cities[city]
            bot.answer_callback_query(call.id, "Город удален из избранных")
        else:
            bot.answer_callback_query(call.id, "Этот город не находится в избранном")


bot.polling()
