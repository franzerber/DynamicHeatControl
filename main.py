import json
from datetime import datetime, timedelta
from typing import List, Dict, Union
from influxdb import InfluxDBClient
import requests

SHUTDOWN_PRICE = 15 # Cent/kWh
MINIMUM_FREE_PV_POWER = 2500 # W    
INTERVAL = 15 # minutes

with open("settings.json", "r", encoding="utf-8") as f:
    settings = json.load(f)
    INFLUX_USER = settings["influx_user"]
    INFLUX_PASSWORD = settings["influx_password"]
    INFLUX_HOST = settings["influx_host"]
    TELEGRAM_TOKEN = settings["telegram_token"]
    TELEGRAM_CHAT_ID = settings["telegram_chat_id"]

def get_current_pv_power(measurement, fieldname) -> int:
    """
    query the free PV power from influxdb
    """
    client = InfluxDBClient(host='10.88.88.1', port=8086,username=INFLUX_USER,password=INFLUX_PASSWORD, database='evn_db_token')
    query = f'SELECT last("{fieldname}") FROM "{measurement}" WHERE time > now() - 1h'
    result = client.query(query)
    points = list(result.get_points())
    if points:
        return int(points[0]['last'])
    else:
        return 0

def get_awattar_prices() -> List[Dict]:
    """
    query awattar for the next available prices, returns a list of dictionaries
    with the following keys: 'start_time', 'end_time', 'price'
    """
    url = "https://api.awattar.de/v1/marketdata"
    response = requests.get(url, timeout=10)
    if response.status_code == 200:
        data = response.json()
        current_prices = []
        for entry in data['data']:
            start_time = datetime.fromtimestamp(entry['start_timestamp'] / 1000)
            end_time = datetime.fromtimestamp(entry['end_timestamp'] / 1000)
            price = round(entry['marketprice'] / 10, 2)  # Convert from €/MWh to €/kWh and round to 2 decimal places
            current_prices.append({
                'start_time': start_time,
                'end_time': end_time,
                'price': price
            })
        return current_prices
    else:
        return []

def send_telegram_message(token: str, chat_id: str, message: str) -> None:
    """
    Send a message to a Telegram bot.
    """
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': message
    }
    response = requests.post(url, json=payload, timeout=10)
    if response.status_code != 200:
        raise requests.exceptions.RequestException(f"Failed to send message: {response.text}")


# Example usage
if __name__ == "__main__":
    prices = get_awattar_prices()
    PRICE_TABLE = ""
    if prices:
        sorted_prices = sorted(p['price'] for p in prices)
        n = len(sorted_prices)
        if n % 2 == 1:
            median_price = sorted_prices[n // 2]
        else:
            median_price = (sorted_prices[n // 2 - 1] + sorted_prices[n // 2]) / 2
        print(f"Median price: {median_price:.2f} €/kWh")
        PRICE_TABLE += f"Median price: {median_price:.2f} €/kWh\n"
    if prices:
        avg_price = sum(p['price'] for p in prices) / len(prices)
        print(f"Average price: {avg_price:.2f} €/kWh")
        PRICE_TABLE += f"Average price: {avg_price:.2f} €/kWh\n"
    for price in prices:
        print(f"From {price['start_time']} to {price['end_time']}: {price['price']} €/kWh")
        PRICE_TABLE += (
            f"{price['start_time'].strftime('%y-%m-%d %H')}:00 - "
            f"{price['end_time'].strftime('%H:%M')}: {price['price']} €/kWh\n"
        )
    power_consumtion = get_current_pv_power('evn_bg3_1_token','MomentanleistungP')
    print(f"BG3 current power consumtion: {power_consumtion} W")
    free_power = get_current_pv_power('evn_bg1_token','MomentanleistungN')
    print(f"BG1 current free power: {free_power} W")
    free_energy = free_power - power_consumtion
    print(f"current free energy: {free_energy} W")
    send_telegram_message(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID,
                          f"BG3 current power consumtion: {power_consumtion} W\n"
                          f"BG1 current free power: {free_power} W\n"
                          f"current free energy: {free_energy} W\n{PRICE_TABLE}")