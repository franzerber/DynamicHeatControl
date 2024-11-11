import requests
from datetime import datetime, timedelta
from influxdb import InfluxDBClient
import json

SHUTDOWN_PRICE = 15 # Cent/kWh
MINIMUM_FREE_PV_POWER = 2500 # W    
INTERVAL = 30 # minutes

with open("settings.json", "r") as f:
    settings = json.load(f)
    INFLUX_USER = settings["influx_user"]
    INFLUX_PASSWORD = settings["influx_password"]

def get_current_pv_power(measurement, fieldname) -> int:
    """
    query the free PV power from influxdb
    """
    client = InfluxDBClient(host='10.88.88.1', port=8086, username=INFLUX_USER, 
                            password=INFLUX_PASSWORD, database='evn_db_token')
    query = f'SELECT last("{fieldname}") FROM "{measurement}" WHERE time > now() - 1h'
    result = client.query(query)
    points = list(result.get_points())
    if points:
        return int(points[0]['last'])
    else:
        return 0


def get_awattar_prices() -> list:
    """
    query awattar for the next available prices, returns a list of dictionaries
    with the following keys: 'start_time', 'end_time', 'price'
    """
    url = "https://api.awattar.de/v1/marketdata"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        prices = []
        for entry in data['data']:
            start_time = datetime.fromtimestamp(entry['start_timestamp'] / 1000)
            end_time = datetime.fromtimestamp(entry['end_timestamp'] / 1000)
            price = round(entry['marketprice'] / 10, 2)  # Convert from €/MWh to €/kWh and round to 2 decimal places
            prices.append({
                'start_time': start_time,
                'end_time': end_time,
                'price': price
            })
        return prices
    else:
        response.raise_for_status()

# Example usage
if __name__ == "__main__":
    prices = get_awattar_prices()
    for price in prices:
        print(f"From {price['start_time']} to {price['end_time']}: {price['price']} €/kWh")
    power_consumtion = get_current_pv_power('evn_bg3_1_token','MomentanleistungP')
    print(f"BG3 current power consumtion: {power_consumtion} W")
    free_power = get_current_pv_power('evn_bg1_token','MomentanleistungN')
    print(f"BG1 current free power: {free_power} W")
    free_energy = free_power - power_consumtion
    print(f"current free energy: {free_energy} W")