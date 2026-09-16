<img src="https://capsule-render.vercel.app/api?type=waving&color=0:0f2027,50:203a43,100:38BDF8&height=200&section=header&text=WEATHER%20APP&fontSize=52&fontColor=ffffff&animation=fadeIn&fontAlignY=35&desc=Check%20the%20weather%20for%20any%20city&descAlignY=55&descSize=16" width="100%"/>

<div align="center">

![Python](https://img.shields.io/badge/Python-3.x-3776AB?logo=python&logoColor=white&labelColor=0f2027)
![Tkinter](https://img.shields.io/badge/GUI-Tkinter-38BDF8?labelColor=0f2027)
![Status](https://img.shields.io/badge/Status-%20Complete-brightgreen?labelColor=0f2027)

</div>

Desktop application in Python to check current and upcoming weather for any city, save favorite cities, and view weather history and temperature charts.

---

## About the Project

Weather App lets you search for any city and view current weather conditions and the hourly forecast, save favorite cities for quick access, check weather history, and visualize temperature trends. The interface features a custom dark theme.

---

## Features

- Weather search by city (geocoding + weather data)
- Dashboard with current conditions and hourly forecast
- Manage saved cities (add/remove)
- Weather alerts page
- Weather history
- Temperature charts
- Simple user account (name and location), stored locally
- Dark themed interface

---

## Technologies

| Technology | Description |
|---|---|
| [Python](https://www.python.org) | Main language |
| [Tkinter](https://docs.python.org/3/library/tkinter.html) | Graphical interface |
| [Requests](https://requests.readthedocs.io) | HTTP requests to the APIs |
| [Pandas](https://pandas.pydata.org) | Data handling |
| [Matplotlib](https://matplotlib.org) | Temperature charts |
| [OpenWeatherMap API](https://openweathermap.org/api) | City geocoding |
| [Open-Meteo API](https://open-meteo.com) | Weather data |

---

## How to Run

### Prerequisites
- Python 3 installed
- A free API key from [OpenWeatherMap](https://openweathermap.org/api)

### Configuration

In the `App.py` file, set your OpenWeatherMap API key:

```python
OPENWEATHERMAP_API_KEY = "your-api-key-here"
```

### Run

```bash
python App.py
```

---

## Project Structure

```
App.py                    # entry point and application logic
dados_usuario.json        # account data stored locally (generated at runtime)
cidades_guardadas.json    # saved favorite cities (generated at runtime)
```


<img src="https://capsule-render.vercel.app/api?type=waving&color=0:0f2027,50:203a43,100:38BDF8&height=100&section=footer&animation=fadeIn&reversal=true" width="100%"/>
