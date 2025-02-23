import openai
import json
import requests
import re  # Regex modülü, kullanıcı girişinden sayıları ayırmak için kullanılacak

# API Anahtarları
OPENAI_API_KEY = "xxx"
WEATHER_API_KEY = "xxx44cee5"
CURRENCY_API_KEY = "xxxI"  # Kur çevirme API anahtarı

client = openai.OpenAI(api_key=OPENAI_API_KEY)

def get_weather(city):
    """Hava durumu API'sine istek gönderir ve sonucu döndürür."""
    url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_API_KEY}"
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        
        # API yanıtını kontrol et
        if "main" in data and "weather" in data and "wind" in data:
            return {
                "city": city,
                "temperature": data["main"].get("temp", "Bilinmiyor"),
                "feels_like": data["main"].get("feels_like", "Bilinmiyor"),
                "condition": data["weather"][0].get("description", "Bilinmiyor"),
                "humidity": data["main"].get("humidity", "Bilinmiyor"),
                "wind_speed": data["wind"].get("speed", "Bilinmiyor")
            }
        else:
            return {"error": "Hava durumu verileri eksik"}
    else:
        return {"error": "Hava durumu alınamadı"}

def get_exchange_rate(from_currency, to_currency):
    """Kur çevirme API'sine istek gönderir ve sonucu döndürür."""
    url = f"https://api.freecurrencyapi.com/v1/latest?apikey={CURRENCY_API_KEY}&currencies={from_currency},{to_currency}"
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        
        # API yanıtını kontrol et
        if "data" in data and from_currency in data["data"] and to_currency in data["data"]:
            exchange_rate = data["data"][to_currency] / data["data"][from_currency]
            return {
                "from_currency": from_currency,
                "to_currency": to_currency,
                "exchange_rate": exchange_rate
            }
        else:
            return {"error": "Kur verileri alınamadı"}
    else:
        return {"error": "Kur verileri alınamadı"}

def extract_amount_and_currencies(user_input):
    """Kullanıcıdan gelen girdiden miktar ve para birimlerini ayıklar."""
    # Regex ile sayıları ve para birimlerini ayıklıyoruz
    match = re.search(r"(\d+)\s*(\w+)\s*kaç\s*(\w+)", user_input)
    
    if match:
        amount = float(match.group(1))  # Miktar
        from_currency = match.group(2).upper()  # Başlangıç para birimi (örneğin, USD)
        to_currency = match.group(3).upper()  # Hedef para birimi (örneğin, TRY)
        return amount, from_currency, to_currency
    return None, None, None

def chat_with_gpt(user_input):
    """OpenAI'ye kullanıcı girişini gönderir ve yanıtı döndürür."""
    response = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[{"role": "user", "content": user_input}],
        functions=[
            {
                "name": "get_weather",
                "description": "Belirtilen şehir için hava durumu bilgisini getirir.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "city": {"type": "string", "description": "Şehir adı"}
                    },
                    "required": ["city"]
                }
            },
            {
                "name": "get_exchange_rate",
                "description": "Belirtilen para biriminden diğerine döviz kuru bilgisini getirir.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "from_currency": {"type": "string", "description": "Başlangıç para birimi (örn. USD)"},
                        "to_currency": {"type": "string", "description": "Hedef para birimi (örn. EUR)"}
                    },
                    "required": ["from_currency", "to_currency"]
                }
            }
        ],
        function_call="auto"  # OpenAI kendi karar verir
    )
    return response

def handle_response(response, user_input):
    """OpenAI yanıtını işler ve gerekli API çağrısını yapar."""
    message = response.choices[0].message

    if message.function_call:
        function_name = message.function_call.name
        arguments = json.loads(message.function_call.arguments)

        if function_name == "get_weather":
            weather_data = get_weather(arguments["city"])
            
            # Hata kontrolü
            if "error" in weather_data:
                return f"Hata: {weather_data['error']}"
            
            return (f"{arguments['city']} hava durumu: {weather_data['temperature']}°C, "
                    f"Hissedilen: {weather_data['feels_like']}°C, {weather_data['condition']}, "
                    f"Nem: {weather_data['humidity']}%, Rüzgar: {weather_data['wind_speed']} m/s")
        
        elif function_name == "get_exchange_rate":
            exchange_data = get_exchange_rate(arguments["from_currency"], arguments["to_currency"])
            
            # Hata kontrolü
            if "error" in exchange_data:
                return f"Hata: {exchange_data['error']}"
            
            # Miktar ve döviz kuru üzerinden hesaplama yapalım
            amount, from_currency, to_currency = extract_amount_and_currencies(user_input)
            
            if amount and from_currency and to_currency:
                exchange_result = amount * exchange_data["exchange_rate"]
                return (f"{amount} {from_currency} = {exchange_result:.2f} {to_currency} "
                        f"({from_currency} - {to_currency} kuru: {exchange_data['exchange_rate']:.2f})")
            else:
                return f"Döviz kuru hesaplaması için geçerli bir miktar ve para birimi girilmedi."
    else:
        return message.content

# Kullanıcıdan giriş al ve yanıtı işle
while True:
    user_input = input("Mesajınızı girin ('çıkış' yazınca kapanır): ")
    
    if user_input.lower() == "çıkış":
        break

    response = chat_with_gpt(user_input)
    result = handle_response(response, user_input)  # user_input burada iletiliyor

    print("Yanıt:", result)
