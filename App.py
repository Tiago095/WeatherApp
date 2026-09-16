import ctypes
import json
import os
import platform
from datetime import datetime

import pandas as pd
import requests
import tkinter as tk
from tkinter import ttk, messagebox, BooleanVar

try:
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
except ImportError:
    plt = None
    FigureCanvasTkAgg = None

try:
    from PIL import ImageTk
except ImportError:
    ImageTk = None

OPENWEATHERMAP_API_KEY = "your_api_key_here"  # substitui pela tua key ao correr localmente
ICON_PATH = r"weather-2019-02-07.ico"

DADOS_USUARIO_JSON = "dados_usuario.json"
CIDADES_JSON_PATH = "cidades_guardadas.json"

class Colors:
    bg_app = "#0B0F19"
    bg_sidebar = "#0D1220"
    bg_topbar = "#0F1524"
    bg_card = "#141a2b"
    bg_card_alt = "#1b2236"
    border = "#242c42"

    text_primary = "#f4f6fa"
    text_secondary = "#94a2bd"
    text_muted = "#5b6478"

    accent = "#38BDF8"
    accent_soft = "#123049"

    warning = "#F59E0B"
    warning_bg = "#2b2110"

    tertiary = "#818CF8"
    tertiary_soft = "242a4d"

    danger = "#ef4444"
    success = "#22c55e"


FONT_FAMILY = "Segoe UI"


def make_card(parent, bg=Colors.bg_card, border=True, **kwargs):
    return tk.Frame(parent, bg=bg, highlightthickness=1 if border else 0,
                     highlightbackground=Colors.border, highlightcolor=Colors.border,
                     **kwargs)


def make_label(parent, text, size=11, weight="normal", color=Colors.text_primary,
               bg=Colors.bg_card, anchor="w", **kwargs):
    return tk.Label(parent, text=text, font=(FONT_FAMILY, size, weight),
                     fg=color, bg=bg, anchor=anchor, **kwargs)

class ContaStorage:
    def __init__(self, path=DADOS_USUARIO_JSON):
        self.path = path

    def tem_conta(self):
        return os.path.exists(self.path)

    def carregar_conta(self):
        if not self.tem_conta():
            return None
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return None

    def guardar_conta(self, nome, morada):
        dados_usuario = {"Nome": nome, "Morada": morada}
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(dados_usuario, f, ensure_ascii=False)
        print("Informações da conta salvas com sucesso.")
        return dados_usuario

class CidadesStorage:
    def __init__(self, path=CIDADES_JSON_PATH):
        self.path = path

    def carregar_cidades(self):
        if not os.path.exists(self.path):
            return []
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return []

    def guardar_cidades(self, cidades):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(cidades, f, ensure_ascii=False, indent=2)
        print("Cidades guardadas com sucesso.")

    def adicionar_cidade(self, dados_cidade):
        cidades = self.carregar_cidades()
        cidades = [c for c in cidades if c["name"] != dados_cidade["name"]]
        cidades.append(dados_cidade)
        self.guardar_cidades(cidades)
        return cidades

    def remover_cidade(self, nome):
        cidades = self.carregar_cidades()
        cidades = [c for c in cidades if c["name"] != nome]
        self.guardar_cidades(cidades)
        return cidades

class WeatherService:

    PAISES_EUROPA = [
        "AL", "AD", "AT", "BY", "BE", "BA", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", "DE",
        "GR", "HU", "IS", "IE", "IT", "LV", "LI", "LT", "LU", "MK", "MT", "MD", "MC", "ME", "NL",
        "NO", "PL", "PT", "RO", "SM", "RS", "SK", "SI", "ES", "SE", "CH", "TR", "UA", "GB", "VA",
    ]
    PAISES_ASIA = [
        "AF", "AM", "AZ", "BH", "BD", "BT", "BN", "KH", "CN", "CY", "GE", "IN", "ID", "IR", "IQ",
        "IL", "JP", "JO", "KZ", "KW", "KG", "LA", "LB", "MY", "MV", "MN", "MM", "NP", "KP", "OM",
        "RU", "PK", "PS", "PH", "QA", "SA", "SG", "KR", "LK", "SY", "TW", "TJ", "TH", "TR", "TM",
        "AE", "UZ", "VN", "YE",
    ]
    PAISES_AFRICA = [
        "DZ", "AO", "BJ", "BW", "BF", "BI", "CV", "CM", "CF", "TD", "KM", "CG", "CD", "DJ", "EG",
        "GQ", "ER", "ET", "SZ", "GA", "GM", "GH", "GN", "GW", "CI", "KE", "LS", "LR", "LY", "MG",
        "MW", "ML", "MR", "MU", "MA", "MZ", "NA", "NE", "NG", "RW", "ST", "SN", "SC", "SL", "SO",
        "ZA", "SS", "SD", "TZ", "TG", "TN", "UG", "EH", "ZM", "ZW",
    ]
    PAISES_AMERICA_SUL = ["AR", "BO", "BR", "CL", "CO", "EC", "GY", "PE", "PY", "SR", "UY", "VE"]
    PAISES_AMERICA_NORTE = [
        "CA", "US", "MX", "GT", "CU", "HT", "DO", "HN", "NI", "CR", "PA", "BS", "JM", "BZ", "SV",
        "TT", "VC", "AG", "BB", "GD", "DM", "KN", "LC",
    ]
    PAISES_AMERICA_CENTRAL = [
        "BZ", "CR", "SV", "GT", "HN", "NI", "PA", "BS", "CU", "HT", "DO", "TT", "VC", "AG", "BB",
        "GD", "DM", "KN", "LC",
    ]

    def obter_coordenadas(self, cidade):
        if not OPENWEATHERMAP_API_KEY:
            print("Falta a OPENWEATHERMAP_API_KEY (define-a no topo do ficheiro).")
            return None, None
        url = f"http://api.openweathermap.org/geo/1.0/direct?q={cidade}&limit=1&appid={OPENWEATHERMAP_API_KEY}"
        try:
            resposta = requests.get(url, timeout=10)
            dados = resposta.json()
            if resposta.status_code == 200 and dados:
                return dados[0]["lat"], dados[0]["lon"]
        except requests.RequestException as e:
            print(f"Erro ao obter coordenadas: {e}")
        return None, None

    def obter_sigla(self, cidade):
        if not OPENWEATHERMAP_API_KEY:
            return None
        url = f"http://api.openweathermap.org/geo/1.0/direct?q={cidade}&limit=1&appid={OPENWEATHERMAP_API_KEY}"
        try:
            resposta = requests.get(url, timeout=10)
            dados = resposta.json()
            if dados:
                return dados[0]["country"]
        except requests.RequestException as e:
            print(f"Erro ao obter sigla: {e}")
        return None

    def verificar_continente(self, sigla):
        if sigla in self.PAISES_EUROPA:
            return "Europa"
        if sigla in self.PAISES_ASIA:
            return "Ásia"
        if sigla in self.PAISES_AFRICA:
            return "África"
        if sigla in self.PAISES_AMERICA_SUL:
            return "América do Sul"
        if sigla in self.PAISES_AMERICA_NORTE:
            return "América do Norte"
        if sigla in self.PAISES_AMERICA_CENTRAL:
            return "América Central"
        return "Sigla não encontrada em nenhuma lista de países."

    def verificar_continente_pelo_nome_da_cidade(self, cidade):
        sigla = self.obter_sigla(cidade)
        if sigla:
            return self.verificar_continente(sigla)
        return "Cidade não encontrada ou sigla do país não disponível."

    def obter_dados_meteo(self, latitude, longitude):
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "current_weather": True,
            "timezone": "auto",
            "hourly": "temperature_2m,relative_humidity_2m,dew_point_2m,"
                      "precipitation_probability,precipitation,rain,snowfall,"
                      "surface_pressure,windspeed_10m,winddirection_10m,visibility",
            "forecast_days": 1,
        }
        response = requests.get(url, params=params, timeout=10)
        return response.json()

    def _indice_hora_atual(self, dados_api):
        hourly = dados_api.get("hourly", {})
        horas_lista = hourly.get("time", [])
        hora_atual_str = dados_api.get("current_weather", {}).get("time", "")

        if hora_atual_str in horas_lista:
            return horas_lista.index(hora_atual_str)

        if hora_atual_str and len(hora_atual_str) >= 13:
            hora_arredondada = hora_atual_str[:13] + ":00"
            if hora_arredondada in horas_lista:
                return horas_lista.index(hora_arredondada)

        return 0

    def montar_weather_data(self, cidade, dados_api):
        hourly = dados_api.get("hourly", {})
        current = dados_api.get("current_weather", {})
        i = self._indice_hora_atual(dados_api)

        temperaturas = hourly.get("temperature_2m", [0] * 24)
        humidade = hourly.get("relative_humidity_2m", [0] * 24)
        pressao = hourly.get("surface_pressure", [1013] * 24)
        orvalho = hourly.get("dew_point_2m", [0] * 24)
        visibilidade = hourly.get("visibility", [10000] * 24)
        vento = hourly.get("windspeed_10m", [0] * 24)
        direcao_vento = hourly.get("winddirection_10m", [0] * 24)

        return {
            "city": cidade,
            "badge": "",
            "coords": f"Lat {dados_api.get('latitude', '?')}° • Lon {dados_api.get('longitude', '?')}°",
            "updated_min": 0,
            "temp": round(current.get("temperature", temperaturas[i])),
            "condition": "",
            "feels_like": round(temperaturas[i]),
            "max": round(max(temperaturas)),
            "min": round(min(temperaturas)),
            "pressure_trend": "+0.0 hPa/3h",
            "trend_points": pressao[max(0, i - 7):i + 1] or [1013],
            "metrics": [
                {"icon": "💨", "label": "VENTO", "value": f"{vento[i]:.0f} km/h",
                 "sub": f"Direção {direcao_vento[i]:.0f}°"},
                {"icon": "💧", "label": "HUMIDADE", "value": f"{humidade[i]:.0f}%", "sub": ""},
                {"icon": "🌡", "label": "PRESSÃO", "value": f"{pressao[i]:.0f} hPa", "sub": "Nível médio do mar"},
                {"icon": "☁", "label": "PONTO DE ORVALHO", "value": f"{orvalho[i]:.1f}°C", "sub": ""},
                {"icon": "👁", "label": "VISIBILIDADE", "value": f"{visibilidade[i] / 1000:.0f} km", "sub": ""},
            ],
        }

    def montar_hourly_data(self, dados_api):
        hourly = dados_api.get("hourly", {})
        horas_lista = hourly.get("time", [])
        temperaturas = hourly.get("temperature_2m", [])
        chuva_prob = hourly.get("precipitation_probability", [0] * len(temperaturas))
        vento = hourly.get("windspeed_10m", [0] * len(temperaturas))

        hora_atual = self._indice_hora_atual(dados_api)

        horas = []
        for offset in range(8):
            idx = hora_atual + offset
            if idx >= len(temperaturas):
                break
            label = "Agora" if offset == 0 else horas_lista[idx][11:16]
            horas.append({
                "time": label,
                "icon": "☀" if chuva_prob[idx] < 20 else ("🌧" if chuva_prob[idx] > 60 else "🌤"),
                "temp": round(temperaturas[idx]),
                "rain": round(chuva_prob[idx]),
                "wind": round(vento[idx]),
            })
        return horas

    def indice_calor(self, temperatura_c, humidade_pct):
        if temperatura_c < 27:
            return temperatura_c
        t_f = temperatura_c * 9 / 5 + 32
        r = humidade_pct
        hi_f = (-42.379 + 2.04901523 * t_f + 10.14333127 * r
                - 0.22475541 * t_f * r - 0.00683783 * t_f ** 2
                - 0.05481717 * r ** 2 + 0.00122874 * t_f ** 2 * r
                + 0.00085282 * t_f * r ** 2 - 0.00000199 * t_f ** 2 * r ** 2)
        return (hi_f - 32) * 5 / 9

    def classificar_indice_calor(self, indice_calor_c):
        """Categorias oficiais do NOAA para o índice de calor."""
        if indice_calor_c < 27:
            return None
        if indice_calor_c < 32:
            return ("Cuidado", "Fadiga possível com exposição prolongada ou atividade física.")
        if indice_calor_c < 39:
            return ("Cuidado Extremo", "Cãibras e exaustão pelo calor são possíveis.")
        if indice_calor_c < 51:
            return ("Perigo", "Exaustão pelo calor provável; golpe de calor possível.")
        return ("Perigo Extremo", "Golpe de calor iminente.")

    def sensacao_termica_vento(self, temperatura_c, vento_kmh):
        if temperatura_c > 10 or vento_kmh < 4.8:
            return temperatura_c
        return (13.12 + 0.6215 * temperatura_c - 11.37 * (vento_kmh ** 0.16)
                + 0.3965 * temperatura_c * (vento_kmh ** 0.16))

    def classificar_sensacao_termica(self, sensacao_c):
        """Categorias de risco de frio (escala usada pelo Environment Canada)."""
        if sensacao_c > 0:
            return None
        if sensacao_c > -10:
            return ("Risco Baixo", "Desconforto com exposição prolongada ao frio.")
        if sensacao_c > -28:
            return ("Risco Moderado", "Risco de queimadura de frio em pele exposta em 10-30 min.")
        if sensacao_c > -40:
            return ("Risco Alto", "Risco de queimadura de frio em pele exposta em 5-10 min.")
        return ("Risco Extremo", "Risco de queimadura de frio em pele exposta em menos de 2 min.")

    def classificar_vento_beaufort(self, vento_kmh):
        escala = [
            (5, "Aragem/Brisa fraca", None),
            (19, "Brisa ligeira a moderada", None),
            (38, "Brisa forte a vento fresco", None),
            (49, "Vento forte", None),
            (61, "Vento muito forte", "Aviso Amarelo"),
            (74, "Tempestade", "Aviso Laranja"),
            (88, "Tempestade forte", "Aviso Laranja"),
            (117, "Tempestade violenta", "Aviso Vermelho"),
        ]
        for limite, nome, nivel in escala:
            if vento_kmh <= limite:
                return nome, nivel
        return "Furacão", "Aviso Vermelho"

    def classificar_intensidade_chuva(self, precipitacao_mm_h):
        if precipitacao_mm_h < 0.1:
            return None
        if precipitacao_mm_h < 2.5:
            return "fraca"
        if precipitacao_mm_h < 7.6:
            return "moderada"
        if precipitacao_mm_h < 50:
            return "forte"
        return "torrencial"

    def gerar_alertas(self, cidade, temperatura, humidade, vento_kmh, precipitacao_mm, probabilidade_chuva):
        alertas = []

        categoria_calor = self.classificar_indice_calor(self.indice_calor(temperatura, humidade))
        if categoria_calor:
            nivel, descricao = categoria_calor
            hi = self.indice_calor(temperatura, humidade)
            alertas.append(f"🌡 {nivel} — índice de calor {hi:.0f}°C em {cidade}: {descricao}")

        categoria_frio = self.classificar_sensacao_termica(self.sensacao_termica_vento(temperatura, vento_kmh))
        if categoria_frio:
            nivel, descricao = categoria_frio
            wc = self.sensacao_termica_vento(temperatura, vento_kmh)
            alertas.append(f"🥶 {nivel} — sensação térmica {wc:.0f}°C em {cidade}: {descricao}")

        nome_vento, nivel_vento = self.classificar_vento_beaufort(vento_kmh)
        if nivel_vento:
            alertas.append(f"💨 {nivel_vento}: vento classificado como '{nome_vento}' "
                            f"({vento_kmh:.0f} km/h) em {cidade}.")

        intensidade_chuva = self.classificar_intensidade_chuva(precipitacao_mm)
        if intensidade_chuva in ("forte", "torrencial") and probabilidade_chuva >= 60:
            alertas.append(f"🌊 Risco de inundação/cheias repentinas em {cidade}: chuva {intensidade_chuva} "
                            f"prevista ({precipitacao_mm:.1f} mm/h, {probabilidade_chuva:.0f}% de probabilidade).")
        elif intensidade_chuva:
            alertas.append(f"🌧 Chuva {intensidade_chuva} prevista em {cidade} ({precipitacao_mm:.1f} mm/h).")

        if not alertas:
            alertas.append(f"✅ Sem condições meteorológicas extremas identificadas em {cidade}.")

        return alertas

    def obter_alertas_para_cidade(self, cidade):
        latitude, longitude = self.obter_coordenadas(cidade)
        if latitude is None or longitude is None:
            return None
        dados_api = self.obter_dados_meteo(latitude, longitude)
        hourly = dados_api.get("hourly", {})
        i = self._indice_hora_atual(dados_api)
        temperatura = hourly["temperature_2m"][i]
        humidade = hourly["relative_humidity_2m"][i]
        vento = hourly.get("windspeed_10m", [0])[i]
        precipitacao = hourly.get("precipitation", [0])[i]
        probabilidade_chuva = hourly.get("precipitation_probability", [0])[i]
        return self.gerar_alertas(cidade, temperatura, humidade, vento, precipitacao, probabilidade_chuva)

    @staticmethod
    def is_valid_date(date_str):
        try:
            date = datetime.strptime(date_str, "%d-%m-%Y")
        except ValueError:
            return False, "Date format should be DD-MM-YYYY."
        if date.year < 1940:
            return False, "Year must be 1940 or later."
        if date.month < 1 or date.month > 12:
            return False, "Month must be between 1 and 12."
        if date.day < 1 or date.day > 31:
            return False, "Day must be between 1 and 31."
        if date.month in [4, 6, 9, 11] and date.day > 30:
            return False, "Day must be between 1 and 30 for the selected month."
        if date.month == 2:
            leap = date.year % 4 == 0 and (date.year % 100 != 0 or date.year % 400 == 0)
            limite = 29 if leap else 28
            if date.day > limite:
                return False, f"Day must be between 1 and {limite} for February."
        return True, ""

    @staticmethod
    def arredondar_dados(df):
        return df.round(2)

    def obter_historico(self, latitude, longitude, start_date, end_date):
        url = "https://archive-api.open-meteo.com/v1/archive"
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "start_date": start_date,
            "end_date": end_date,
            "daily": ["temperature_2m_max", "temperature_2m_min", "precipitation_sum", "precipitation_hours"],
            "timezone": "Europe/Berlin",
        }
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()["daily"]
        daily_data = {
            "date": pd.date_range(start=start_date, end=end_date, freq="D"),
            "temperature_2m_max": data["temperature_2m_max"],
            "temperature_2m_min": data["temperature_2m_min"],
            "precipitation_sum": data["precipitation_sum"],
            "precipitation_hours": data["precipitation_hours"],
        }
        return self.arredondar_dados(pd.DataFrame(data=daily_data))

class Sidebar(tk.Frame):
    NAV_ITEMS = [
        ("dashboard", "Dashboard", "▦"),
        ("alerts", "Alertas Meteorológicos", "⚠"),
        ("historico", "Histórico", "📊"),
        ("graficos", "Gráficos", "📈"),
    ]

    def __init__(self, parent, on_navigate=None, width=230):
        super().__init__(parent, bg=Colors.bg_sidebar, width=width)
        self.pack_propagate(False)
        self.on_navigate = on_navigate
        self.active_key = "dashboard"
        self.nav_buttons = {}
        self._build_header()
        self._build_nav()

    def _build_header(self):
        header = tk.Frame(self, bg=Colors.bg_sidebar)
        header.pack(fill="x", pady=(24, 30), padx=20)
        logo_row = tk.Frame(header, bg=Colors.bg_sidebar)
        logo_row.pack(anchor="w")
        tk.Label(logo_row, text="☁", font=(FONT_FAMILY, 22), fg=Colors.accent,
                 bg=Colors.bg_sidebar).pack(side="left")
        title_col = tk.Frame(logo_row, bg=Colors.bg_sidebar)
        title_col.pack(side="left", padx=(8, 0))
        tk.Label(title_col, text="WeatherApp", font=(FONT_FAMILY, 14, "bold"),
                 fg=Colors.text_primary, bg=Colors.bg_sidebar).pack(anchor="w")

    def _build_nav(self):
        nav_frame = tk.Frame(self, bg=Colors.bg_sidebar)
        nav_frame.pack(fill="x", padx=12)
        for key, label, icon in self.NAV_ITEMS:
            row = tk.Frame(nav_frame, bg=Colors.bg_sidebar, cursor="hand2")
            row.pack(fill="x", pady=3)
            icon_lbl = tk.Label(row, text=icon, font=(FONT_FAMILY, 13),
                                 fg=Colors.text_secondary, bg=Colors.bg_sidebar, width=3)
            icon_lbl.pack(side="left", padx=(10, 4), pady=10)
            text_lbl = tk.Label(row, text=label, font=(FONT_FAMILY, 11),
                                 fg=Colors.text_secondary, bg=Colors.bg_sidebar, anchor="w")
            text_lbl.pack(side="left", fill="x", expand=True, pady=10)
            widgets = (row, icon_lbl, text_lbl)
            self.nav_buttons[key] = widgets
            for w in widgets:
                w.bind("<Button-1>", lambda e, k=key: self._handle_click(k))
        self._paint_active()

    def _handle_click(self, key):
        self.set_active(key)
        if self.on_navigate:
            self.on_navigate(key)

    def set_active(self, key):
        self.active_key = key
        self._paint_active()

    def _paint_active(self):
        for key, (row, icon_lbl, text_lbl) in self.nav_buttons.items():
            active = key == self.active_key
            bg = Colors.accent_soft if active else Colors.bg_sidebar
            fg = Colors.text_primary if active else Colors.text_secondary
            row.configure(bg=bg)
            icon_lbl.configure(bg=bg, fg=Colors.accent if active else Colors.text_secondary)
            text_lbl.configure(bg=bg, fg=fg)

class TopBar(tk.Frame):
    def __init__(self, parent, on_search=None, on_profile_click=None, nome_utilizador=""):
        super().__init__(parent, bg=Colors.bg_topbar, height=64)
        self.pack_propagate(False)
        self.on_search = on_search
        self.on_profile_click = on_profile_click
        self.nome_utilizador = nome_utilizador
        self._build()

    def _build(self):
        search_wrap = tk.Frame(self, bg=Colors.bg_card, highlightthickness=1,
                                highlightbackground=Colors.border)
        search_wrap.pack(side="left", padx=24, pady=14, ipady=4)
        tk.Label(search_wrap, text="🔍", font=(FONT_FAMILY, 10), fg=Colors.text_muted,
                 bg=Colors.bg_card).pack(side="left", padx=(10, 4))

        self.search_var = tk.StringVar()
        entry = tk.Entry(search_wrap, textvariable=self.search_var, width=40,
                          font=(FONT_FAMILY, 10), fg=Colors.text_primary,
                          bg=Colors.bg_card, insertbackground=Colors.text_primary, relief="flat")
        entry.pack(side="left", padx=(0, 10), ipady=3)
        entry.bind("<Return>", lambda e: self._search())

        placeholder = "Pesquisar cidade..."
        entry.insert(0, placeholder)
        entry.configure(fg=Colors.text_muted)

        def clear_placeholder(_):
            if entry.get() == placeholder:
                entry.delete(0, "end")
                entry.configure(fg=Colors.text_primary)

        def restore_placeholder(_):
            if not entry.get():
                entry.insert(0, placeholder)
                entry.configure(fg=Colors.text_muted)

        entry.bind("<FocusIn>", clear_placeholder)
        entry.bind("<FocusOut>", restore_placeholder)

        right = tk.Frame(self, bg=Colors.bg_topbar)
        right.pack(side="right", padx=24)

        profile_frame = tk.Frame(right, bg=Colors.bg_topbar, cursor="hand2")
        profile_frame.pack(side="left", padx=(14, 0))
        icon_lbl = tk.Label(profile_frame, text="👤", font=(FONT_FAMILY, 12),
                             fg=Colors.text_secondary, bg=Colors.bg_topbar)
        icon_lbl.pack(side="left")
        widgets_to_bind = [profile_frame, icon_lbl]
        if self.nome_utilizador:
            nome_lbl = tk.Label(profile_frame, text=self.nome_utilizador, font=(FONT_FAMILY, 10),
                                 fg=Colors.text_secondary, bg=Colors.bg_topbar)
            nome_lbl.pack(side="left", padx=(6, 0))
            widgets_to_bind.append(nome_lbl)
        if self.on_profile_click:
            for w in widgets_to_bind:
                w.bind("<Button-1>", lambda e: self.on_profile_click())

    def _search(self):
        query = self.search_var.get()
        if query and self.on_search:
            self.on_search(query)


class AlertBanner(tk.Frame):
    def __init__(self, parent, title, message, on_details=None):
        super().__init__(parent, bg=Colors.warning_bg, highlightthickness=1,
                          highlightbackground=Colors.warning)
        left = tk.Frame(self, bg=Colors.warning_bg)
        left.pack(side="left", fill="x", expand=True, padx=16, pady=12)
        tk.Label(left, text=f"⚠  {title}", font=(FONT_FAMILY, 10, "bold"),
                 fg=Colors.warning, bg=Colors.warning_bg).pack(anchor="w")
        tk.Label(left, text=message, font=(FONT_FAMILY, 9), fg=Colors.text_secondary,
                 bg=Colors.warning_bg, wraplength=700, justify="left").pack(anchor="w", pady=(2, 0))
        if on_details:
            details_btn = tk.Label(self, text="Detalhes ›", font=(FONT_FAMILY, 9, "bold"),
                                    fg=Colors.accent, bg=Colors.warning_bg, cursor="hand2")
            details_btn.pack(side="right", padx=16)
            details_btn.bind("<Button-1>", lambda e: on_details())


class MainWeatherCard(tk.Frame):
    def __init__(self, parent, data, on_refresh=None):
        super().__init__(parent, bg=Colors.bg_app)
        self.data = data
        self.on_refresh = on_refresh
        self._build()

    def _build(self):
        card = make_card(self)
        card.pack(fill="x")

        top = tk.Frame(card, bg=Colors.bg_card)
        top.pack(fill="x", padx=24, pady=(20, 0))
        loc_left = tk.Frame(top, bg=Colors.bg_card)
        loc_left.pack(side="left")
        tk.Label(loc_left, text=f"📍 {self.data['city']}", font=(FONT_FAMILY, 16, "bold"),
                 fg=Colors.text_primary, bg=Colors.bg_card).pack(anchor="w")
        tk.Label(loc_left, text=self.data["coords"], font=(FONT_FAMILY, 9),
                 fg=Colors.text_muted, bg=Colors.bg_card).pack(anchor="w", pady=(4, 0))

        right_top = tk.Frame(top, bg=Colors.bg_card)
        right_top.pack(side="right")
        refresh_btn = tk.Label(right_top, text="⟳ Atualizar", font=(FONT_FAMILY, 9),
                                fg=Colors.text_secondary, bg=Colors.bg_card, cursor="hand2")
        refresh_btn.pack(side="left")
        if self.on_refresh:
            refresh_btn.bind("<Button-1>", lambda e: self.on_refresh())

        mid = tk.Frame(card, bg=Colors.bg_card)
        mid.pack(fill="x", padx=24, pady=(10, 0))
        tk.Label(mid, text=f"{self.data['temp']}°C", font=(FONT_FAMILY, 52, "bold"),
                 fg=Colors.text_primary, bg=Colors.bg_card).pack(side="left")

        cond_col = tk.Frame(mid, bg=Colors.bg_card)
        cond_col.pack(side="left", padx=20, pady=(14, 0))
        tk.Label(cond_col, text=self.data["condition"], font=(FONT_FAMILY, 13, "bold"),
                 fg=Colors.text_primary, bg=Colors.bg_card).pack(anchor="w")
        detalhes = f"Sensação térmica {self.data['feels_like']}°C   •   Máx {self.data['max']}°C   Mín {self.data['min']}°C"
        tk.Label(cond_col, text=detalhes, font=(FONT_FAMILY, 9),
                 fg=Colors.text_secondary, bg=Colors.bg_card).pack(anchor="w", pady=(4, 0))

        metrics_row = tk.Frame(card, bg=Colors.bg_card)
        metrics_row.pack(fill="x", padx=24, pady=(20, 20))
        for i, m in enumerate(self.data["metrics"]):
            self._build_metric(metrics_row, m).pack(side="left", expand=True, fill="both",
                                                      padx=(0 if i == 0 else 8, 0))

    def _build_metric(self, parent, m):
        box = make_card(parent, bg=Colors.bg_card_alt)
        inner = tk.Frame(box, bg=Colors.bg_card_alt)
        inner.pack(fill="both", expand=True, padx=14, pady=12)
        tk.Label(inner, text=f"{m['icon']}  {m['label']}", font=(FONT_FAMILY, 9, "bold"),
                 fg=Colors.text_secondary, bg=Colors.bg_card_alt).pack(anchor="w")
        tk.Label(inner, text=m["value"], font=(FONT_FAMILY, 18, "bold"),
                 fg=Colors.text_primary, bg=Colors.bg_card_alt).pack(anchor="w", pady=(6, 0))
        tk.Label(inner, text=m["sub"], font=(FONT_FAMILY, 8),
                 fg=Colors.text_muted, bg=Colors.bg_card_alt).pack(anchor="w")
        return box


class HourlyForecast(tk.Frame):
    def __init__(self, parent, hours):
        super().__init__(parent, bg=Colors.bg_app)
        self.hours = hours
        self._build()

    def _build(self):
        header = tk.Frame(self, bg=Colors.bg_app)
        header.pack(fill="x", pady=(0, 8))
        tk.Label(header, text="🕐 Previsão Horária", font=(FONT_FAMILY, 12, "bold"),
                 fg=Colors.text_primary, bg=Colors.bg_app).pack(side="left")

        row = tk.Frame(self, bg=Colors.bg_app)
        row.pack(fill="x")
        if not self.hours:
            tk.Label(row, text="Sem dados horários disponíveis.", font=(FONT_FAMILY, 9),
                      fg=Colors.text_muted, bg=Colors.bg_app).pack(anchor="w")
            return
        for i, h in enumerate(self.hours):
            card = self._build_hour_card(row, h, active=(i == 0))
            card.pack(side="left", expand=True, fill="x", padx=(0 if i == 0 else 6, 0))

    def _build_hour_card(self, parent, h, active=False):
        bg = Colors.bg_card_alt if active else Colors.bg_card
        card = make_card(parent, bg=bg, height=150)
        card.pack_propagate(False)
        tk.Label(card, text=h["time"], font=(FONT_FAMILY, 8, "bold" if active else "normal"),
                 fg=Colors.tertiary if active else Colors.text_secondary, bg=bg).pack(pady=(8, 4))
        tk.Label(card, text=h["icon"], font=(FONT_FAMILY, 14), bg=bg).pack()
        tk.Label(card, text=f"{h['temp']}°", font=(FONT_FAMILY, 13, "bold"),
                 fg=Colors.text_primary, bg=bg).pack(pady=(2, 4))
        tk.Label(card, text=f"💧{h['rain']}%", font=(FONT_FAMILY, 7),
                 fg=Colors.text_muted, bg=bg).pack()
        tk.Label(card, text=f"{h['wind']}km/h", font=(FONT_FAMILY, 7),
                 fg=Colors.text_muted, bg=bg).pack(pady=(0, 6))
        return card


class SavedCities(tk.Frame):
    def __init__(self, parent, cities, on_manage=None, on_open=None, on_remove=None, columns=4):
        super().__init__(parent, bg=Colors.bg_app)
        self.cities = cities
        self.on_manage = on_manage
        self.on_open = on_open
        self.on_remove = on_remove
        self.columns = columns
        self._build()

    def _build(self):
        header = tk.Frame(self, bg=Colors.bg_app)
        header.pack(fill="x", pady=(0, 10))
        tk.Label(header, text="📌 Cidades Guardadas", font=(FONT_FAMILY, 12, "bold"),
                 fg=Colors.text_primary, bg=Colors.bg_app).pack(side="left")
        manage = tk.Label(header, text="+ ADICIONAR CIDADE", font=(FONT_FAMILY, 9, "bold"),
                           fg=Colors.accent, bg=Colors.bg_app, cursor="hand2")
        manage.pack(side="right")
        if self.on_manage:
            manage.bind("<Button-1>", lambda e: self.on_manage())

        if not self.cities:
            tk.Label(self, text="Ainda não guardaste nenhuma cidade.", font=(FONT_FAMILY, 9),
                     fg=Colors.text_muted, bg=Colors.bg_app).pack(anchor="w")
            return

        grid = tk.Frame(self, bg=Colors.bg_app)
        grid.pack(fill="x")
        for i in range(self.columns):
            grid.grid_columnconfigure(i, weight=1, uniform="city")
        for i, c in enumerate(self.cities):
            card = self._build_city_card(grid, c)
            card.grid(row=i // self.columns, column=i % self.columns,
                      padx=(0 if i % self.columns == 0 else 8, 0),
                      pady=(0 if i < self.columns else 10), sticky="nsew")

    def _build_city_card(self, parent, c):
        card = make_card(parent, cursor="hand2")
        inner = tk.Frame(card, bg=Colors.bg_card)
        inner.pack(fill="both", expand=True, padx=16, pady=14)

        top = tk.Frame(inner, bg=Colors.bg_card)
        top.pack(fill="x")
        name_col = tk.Frame(top, bg=Colors.bg_card)
        name_col.pack(side="left")
        tk.Label(name_col, text=c["name"], font=(FONT_FAMILY, 12, "bold"),
                 fg=Colors.text_primary, bg=Colors.bg_card).pack(anchor="w")
        tk.Label(name_col, text=c.get("region", ""), font=(FONT_FAMILY, 8),
                 fg=Colors.text_muted, bg=Colors.bg_card).pack(anchor="w")

        icons_col = tk.Frame(top, bg=Colors.bg_card)
        icons_col.pack(side="right")
        if self.on_remove:
            remove_btn = tk.Label(icons_col, text="🗑", font=(FONT_FAMILY, 11),
                                   fg=Colors.text_muted, bg=Colors.bg_card, cursor="hand2")
            remove_btn.pack(side="right", padx=(8, 0))
            remove_btn.bind("<Button-1>", lambda e, name=c["name"]: self.on_remove(name))
        tk.Label(icons_col, text=c.get("icon", "🌤"), font=(FONT_FAMILY, 18),
                 bg=Colors.bg_card).pack(side="right")

        tk.Label(inner, text=f"{c['temp']}°C", font=(FONT_FAMILY, 22, "bold"),
                 fg=Colors.text_primary, bg=Colors.bg_card).pack(anchor="w", pady=(10, 0))
        tk.Label(inner, text=c.get("condition", ""), font=(FONT_FAMILY, 9),
                 fg=Colors.text_secondary, bg=Colors.bg_card).pack(anchor="w")

        if self.on_open:
            detalhes_btn = tk.Label(inner, text="Ver detalhes ›", font=(FONT_FAMILY, 9, "bold"),
                                     fg=Colors.accent, bg=Colors.bg_card, cursor="hand2")
            detalhes_btn.pack(anchor="w", pady=(10, 0))
            detalhes_btn.bind("<Button-1>", lambda e, name=c["name"]: self.on_open(name))

            for w in (card, inner, top, name_col):
                w.bind("<Button-1>", lambda e, name=c["name"]: self.on_open(name))
        return card

class AccountSetupScreen(tk.Frame):
    def __init__(self, parent, conta_storage, on_saved):
        super().__init__(parent, bg=Colors.bg_app)
        self.conta_storage = conta_storage
        self.on_saved = on_saved
        self._build()

    def _build(self):
        wrapper = tk.Frame(self, bg=Colors.bg_app)
        wrapper.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(wrapper, text="☁ WeatherApp", font=(FONT_FAMILY, 26, "bold"),
                 fg=Colors.text_primary, bg=Colors.bg_app).pack(pady=(0, 4))
        tk.Label(wrapper, text="Antes de começar, conta-nos um pouco sobre ti",
                 font=(FONT_FAMILY, 11), fg=Colors.text_secondary,
                 bg=Colors.bg_app).pack(pady=(0, 24))

        card = make_card(wrapper)
        card.pack()
        form = tk.Frame(card, bg=Colors.bg_card)
        form.pack(padx=36, pady=30)

        self.entry_nome = self._campo(form, "Nome")
        self.entry_morada = self._campo(form, "Morada (cidade)")

        guardar_btn = tk.Label(form, text="Guardar e continuar", font=(FONT_FAMILY, 10, "bold"),
                                fg="white", bg=Colors.accent, cursor="hand2", pady=10)
        guardar_btn.pack(fill="x", pady=(16, 0))
        guardar_btn.bind("<Button-1>", lambda e: self._guardar())

    def _campo(self, parent, label_text):
        make_label(parent, label_text, size=9, color=Colors.text_secondary,
                   bg=Colors.bg_card).pack(anchor="w", pady=(10, 2))
        entry = tk.Entry(parent, font=(FONT_FAMILY, 10), width=32, bg=Colors.bg_card_alt,
                          fg=Colors.text_primary, insertbackground=Colors.text_primary, relief="flat")
        entry.pack(ipady=6)
        return entry

    def _guardar(self):
        nome = self.entry_nome.get().strip()
        morada = self.entry_morada.get().strip()

        if not nome or not morada:
            messagebox.showwarning("Campos em falta", "Preenche Nome e Morada antes de continuar.")
            return

        dados = self.conta_storage.guardar_conta(nome, morada)
        self.on_saved(dados)

class AlertsPage(tk.Frame):
    def __init__(self, parent, service: WeatherService, cidade_inicial=""):
        super().__init__(parent, bg=Colors.bg_app)
        self.service = service
        pad = 24

        header = tk.Frame(self, bg=Colors.bg_app)
        header.pack(fill="x", padx=pad, pady=(pad, 16))
        tk.Label(header, text="Alertas Meteorológicos", font=(FONT_FAMILY, 18, "bold"),
                 fg=Colors.text_primary, bg=Colors.bg_app).pack(anchor="w")
        tk.Label(header, text="Verifica se há condições meteorológicas extremas numa cidade.",
                 font=(FONT_FAMILY, 10), fg=Colors.text_secondary, bg=Colors.bg_app).pack(anchor="w", pady=(4, 0))

        search_row = tk.Frame(self, bg=Colors.bg_app)
        search_row.pack(fill="x", padx=pad, pady=(0, 16))
        self.entry_cidade = tk.Entry(search_row, font=(FONT_FAMILY, 10), bg=Colors.bg_card_alt,
                                      fg=Colors.text_primary, insertbackground=Colors.text_primary,
                                      relief="flat", width=30)
        self.entry_cidade.insert(0, cidade_inicial)
        self.entry_cidade.pack(side="left", ipady=6, padx=(0, 10))
        self.entry_cidade.bind("<Return>", lambda e: self._verificar())

        verificar_btn = tk.Label(search_row, text="Verificar", font=(FONT_FAMILY, 10, "bold"),
                                  fg="white", bg=Colors.accent, cursor="hand2", padx=16, pady=6)
        verificar_btn.pack(side="left")
        verificar_btn.bind("<Button-1>", lambda e: self._verificar())

        self.resultados_frame = tk.Frame(self, bg=Colors.bg_app)
        self.resultados_frame.pack(fill="both", expand=True, padx=pad, pady=(0, pad))

        if cidade_inicial:
            self._verificar()

    def _verificar(self):
        for w in self.resultados_frame.winfo_children():
            w.destroy()
        cidade = self.entry_cidade.get().strip()
        if not cidade:
            return

        tk.Label(self.resultados_frame, text="A verificar...", font=(FONT_FAMILY, 9),
                 fg=Colors.text_muted, bg=Colors.bg_app).pack(anchor="w")
        self.update_idletasks()

        alertas = self.service.obter_alertas_para_cidade(cidade)
        for w in self.resultados_frame.winfo_children():
            w.destroy()

        if alertas is None:
            tk.Label(self.resultados_frame, text="⚠ Não foi possível obter dados para esta cidade.",
                     font=(FONT_FAMILY, 10), fg=Colors.warning, bg=Colors.bg_app).pack(anchor="w")
            return

        for alerta in alertas:
            card = make_card(self.resultados_frame, bg=Colors.bg_card)
            card.pack(fill="x", pady=6)
            tk.Label(card, text=f"⚠ {alerta}", font=(FONT_FAMILY, 10), fg=Colors.text_primary,
                     bg=Colors.bg_card, wraplength=800, justify="left").pack(anchor="w", padx=16, pady=12)

class HistoricoPage(tk.Frame):
    def __init__(self, parent, service: WeatherService, cidade_inicial=""):
        super().__init__(parent, bg=Colors.bg_app)
        self.service = service
        pad = 24

        header = tk.Frame(self, bg=Colors.bg_app)
        header.pack(fill="x", padx=pad, pady=(pad, 16))
        tk.Label(header, text="Histórico Meteorológico", font=(FONT_FAMILY, 18, "bold"),
                 fg=Colors.text_primary, bg=Colors.bg_app).pack(anchor="w")
        tk.Label(header, text="Consulta temperaturas e precipitação registadas num intervalo de datas.",
                 font=(FONT_FAMILY, 10), fg=Colors.text_secondary, bg=Colors.bg_app).pack(anchor="w", pady=(4, 0))

        form_card = make_card(self)
        form_card.pack(fill="x", padx=pad, pady=(0, 16))
        form = tk.Frame(form_card, bg=Colors.bg_card)
        form.pack(padx=20, pady=16)

        self.entry_city = self._campo(form, "Cidade", cidade_inicial, 0)
        self.entry_start = self._campo(form, "Data Início (DD-MM-YYYY)", "", 1)
        self.entry_end = self._campo(form, "Data Fim (DD-MM-YYYY)", "", 2)

        buscar_btn = tk.Label(form, text="Consultar", font=(FONT_FAMILY, 10, "bold"),
                               fg="white", bg=Colors.accent, cursor="hand2", padx=16, pady=8)
        buscar_btn.grid(row=3, column=0, columnspan=2, pady=(14, 0), sticky="ew")
        buscar_btn.bind("<Button-1>", lambda e: self._consultar())

        table_card = make_card(self)
        table_card.pack(fill="both", expand=True, padx=pad, pady=(0, pad))

        columns = ("data", "temperaturamax", "temperaturamin", "precipitacao", "ph")
        self.tree = ttk.Treeview(table_card, columns=columns, show="headings", height=14)
        self.tree.heading("data", text="Data")
        self.tree.heading("temperaturamax", text="Temp. Máx (°C)")
        self.tree.heading("temperaturamin", text="Temp. Mín (°C)")
        self.tree.heading("precipitacao", text="Precipitação (mm)")
        self.tree.heading("ph", text="Horas de Precipitação")
        for col in columns:
            self.tree.column(col, width=150, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=16, pady=16)

        self.tree.tag_configure("linha_par", background=Colors.bg_card)
        self.tree.tag_configure("linha_impar", background=Colors.bg_card_alt)

    def _campo(self, parent, label_text, valor_inicial, row):
        make_label(parent, label_text, size=9, color=Colors.text_secondary,
                   bg=Colors.bg_card).grid(row=row, column=0, sticky="w", pady=6, padx=(0, 12))
        entry = tk.Entry(parent, font=(FONT_FAMILY, 10), width=26, bg=Colors.bg_card_alt,
                          fg=Colors.text_primary, insertbackground=Colors.text_primary, relief="flat")
        if valor_inicial:
            entry.insert(0, valor_inicial)
        entry.grid(row=row, column=1, sticky="w", ipady=5)
        return entry

    def _consultar(self):
        cidade = self.entry_city.get().strip()
        ok, msg = self.service.is_valid_date(self.entry_start.get().strip())
        if not ok:
            messagebox.showerror("Data de início inválida", msg)
            return
        ok, msg = self.service.is_valid_date(self.entry_end.get().strip())
        if not ok:
            messagebox.showerror("Data de fim inválida", msg)
            return
        try:
            start_date = datetime.strptime(self.entry_start.get().strip(), "%d-%m-%Y").strftime("%Y-%m-%d")
            end_date = datetime.strptime(self.entry_end.get().strip(), "%d-%m-%Y").strftime("%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Erro", "Erro na conversão das datas.")
            return

        latitude, longitude = self.service.obter_coordenadas(cidade)
        if latitude is None:
            messagebox.showerror("Erro", "Cidade não encontrada. Verifica o nome introduzido.")
            return

        try:
            df = self.service.obter_historico(latitude, longitude, start_date, end_date)
        except Exception as e:
            messagebox.showerror("Erro", str(e))
            return

        for i in self.tree.get_children():
            self.tree.delete(i)
        for i, (_, row_data) in enumerate(df.iterrows()):
            tag = "linha_par" if i % 2 == 0 else "linha_impar"
            self.tree.insert("", "end", values=list(row_data), tags=(tag,))


class GraficosPage(tk.Frame):
    def __init__(self, parent, service: WeatherService, cidade_inicial=""):
        super().__init__(parent, bg=Colors.bg_app)
        self.service = service
        pad = 24

        header = tk.Frame(self, bg=Colors.bg_app)
        header.pack(fill="x", padx=pad, pady=(pad, 16))
        tk.Label(header, text="Gráficos", font=(FONT_FAMILY, 18, "bold"),
                 fg=Colors.text_primary, bg=Colors.bg_app).pack(anchor="w")
        tk.Label(header, text="Evolução da temperatura, humidade e precipitação nas próximas 24 horas.",
                 font=(FONT_FAMILY, 10), fg=Colors.text_secondary, bg=Colors.bg_app).pack(anchor="w", pady=(4, 0))

        search_row = tk.Frame(self, bg=Colors.bg_app)
        search_row.pack(fill="x", padx=pad, pady=(0, 16))
        self.entry_cidade = tk.Entry(search_row, font=(FONT_FAMILY, 10), bg=Colors.bg_card_alt,
                                      fg=Colors.text_primary, insertbackground=Colors.text_primary,
                                      relief="flat", width=30)
        self.entry_cidade.insert(0, cidade_inicial)
        self.entry_cidade.pack(side="left", ipady=6, padx=(0, 10))
        self.entry_cidade.bind("<Return>", lambda e: self._gerar())

        gerar_btn = tk.Label(search_row, text="Gerar Gráficos", font=(FONT_FAMILY, 10, "bold"),
                              fg="white", bg=Colors.accent, cursor="hand2", padx=16, pady=6)
        gerar_btn.pack(side="left")
        gerar_btn.bind("<Button-1>", lambda e: self._gerar())

        self.grafico_container = tk.Frame(self, bg=Colors.bg_app)
        self.grafico_container.pack(fill="both", expand=True, padx=pad, pady=(0, pad))

        if cidade_inicial:
            self._gerar()

    def _gerar(self):
        for w in self.grafico_container.winfo_children():
            w.destroy()

        if plt is None or FigureCanvasTkAgg is None:
            tk.Label(self.grafico_container, text="⚠ matplotlib não está instalado (pip install matplotlib).",
                     font=(FONT_FAMILY, 10), fg=Colors.warning, bg=Colors.bg_app).pack(anchor="w")
            return

        cidade = self.entry_cidade.get().strip()
        latitude, longitude = self.service.obter_coordenadas(cidade)
        if latitude is None:
            tk.Label(self.grafico_container, text="⚠ Cidade não encontrada.",
                     font=(FONT_FAMILY, 10), fg=Colors.warning, bg=Colors.bg_app).pack(anchor="w")
            return

        dados_api = self.service.obter_dados_meteo(latitude, longitude)
        hourly = dados_api.get("hourly", {})
        horas = [t[11:16] for t in hourly.get("time", [])]
        temperaturas = hourly.get("temperature_2m", [])
        orvalho = hourly.get("dew_point_2m", [])
        humidade = hourly.get("relative_humidity_2m", [])
        chuva_prob = hourly.get("precipitation_probability", [])
        precipitacao = hourly.get("precipitation", [])

        fig = plt.Figure(figsize=(9, 7), dpi=100)
        fig.patch.set_facecolor(Colors.bg_card)

        def estilizar_eixo(ax):
            ax.set_facecolor(Colors.bg_card)
            ax.tick_params(colors=Colors.text_secondary, labelsize=8)
            for spine in ax.spines.values():
                spine.set_color(Colors.border)
            ax.legend(facecolor=Colors.bg_card_alt, labelcolor=Colors.text_primary,
                      fontsize=8, framealpha=0.6)
            passo = max(1, len(horas) // 8)
            ax.set_xticks(range(0, len(horas), passo))
            ax.set_xticklabels([horas[i] for i in range(0, len(horas), passo)])

        ax1 = fig.add_subplot(3, 1, 1)
        ax1.plot(horas, temperaturas, label="Temperatura (°C)", color=Colors.accent)
        ax1.plot(horas, orvalho, label="Ponto de Orvalho (°C)", color=Colors.tertiary)
        estilizar_eixo(ax1)

        ax2 = fig.add_subplot(3, 1, 2)
        ax2.plot(horas, humidade, label="Humidade (%)", color=Colors.accent)
        estilizar_eixo(ax2)

        ax3 = fig.add_subplot(3, 1, 3)
        ax3.plot(horas, chuva_prob, label="Probabilidade de Precipitação (%)", color=Colors.warning)
        ax3.plot(horas, precipitacao, label="Precipitação (mm)", color=Colors.tertiary)
        estilizar_eixo(ax3)

        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=self.grafico_container)
        canvas.draw()
        canvas.get_tk_widget().configure(bg=Colors.bg_card)
        canvas.get_tk_widget().pack(fill="both", expand=True)

class AccountPage(tk.Frame):
    def __init__(self, parent, conta_storage: ContaStorage, conta_atual, on_saved):
        super().__init__(parent, bg=Colors.bg_app)
        self.conta_storage = conta_storage
        self.on_saved = on_saved
        pad = 24

        header = tk.Frame(self, bg=Colors.bg_app)
        header.pack(fill="x", padx=pad, pady=(pad, 16))
        tk.Label(header, text="👤 A Minha Conta", font=(FONT_FAMILY, 18, "bold"),
                 fg=Colors.text_primary, bg=Colors.bg_app).pack(anchor="w")

        card = make_card(self)
        card.pack(padx=pad, pady=(0, pad), anchor="w")
        form = tk.Frame(card, bg=Colors.bg_card)
        form.pack(padx=30, pady=24)

        self.entry_nome = self._campo(form, "Nome", conta_atual.get("Nome", ""))
        self.entry_morada = self._campo(form, "Morada (cidade)", conta_atual.get("Morada", ""))

        guardar_btn = tk.Label(form, text="Guardar alterações", font=(FONT_FAMILY, 10, "bold"),
                                fg="white", bg=Colors.accent, cursor="hand2", pady=10)
        guardar_btn.pack(fill="x", pady=(16, 0))
        guardar_btn.bind("<Button-1>", lambda e: self._guardar())

    def _campo(self, parent, label_text, valor_inicial):
        make_label(parent, label_text, size=9, color=Colors.text_secondary,
                   bg=Colors.bg_card).pack(anchor="w", pady=(10, 2))
        entry = tk.Entry(parent, font=(FONT_FAMILY, 10), width=32, bg=Colors.bg_card_alt,
                          fg=Colors.text_primary, insertbackground=Colors.text_primary, relief="flat")
        entry.insert(0, valor_inicial)
        entry.pack(ipady=6)
        return entry

    def _guardar(self):
        nome = self.entry_nome.get().strip()
        morada = self.entry_morada.get().strip()
        if not nome or not morada:
            messagebox.showwarning("Campos em falta", "Preenche Nome e Morada antes de guardar.")
            return
        nova_conta = self.conta_storage.guardar_conta(nome, morada)
        self.on_saved(nova_conta)

class DashboardPage(tk.Frame):
    def __init__(self, parent, service: WeatherService, cidade_inicial, on_city_changed=None):
        super().__init__(parent, bg=Colors.bg_app)
        self.service = service
        self.cidades_storage = CidadesStorage()
        self.cities_data = self.cidades_storage.carregar_cidades()
        self.current_city = cidade_inicial
        self.on_city_changed = on_city_changed

        self.weather_section_frame = None
        self.saved_cities_widget = None
        self.saved_cities_container = None

        self._build()
        self.atualizar_meteorologia(cidade_inicial)

    def _build(self):
        canvas = tk.Canvas(self, bg=Colors.bg_app, highlightthickness=0)
        vscroll = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vscroll.set)
        canvas.pack(side="left", fill="both", expand=True)
        vscroll.pack(side="right", fill="y")

        content = tk.Frame(canvas, bg=Colors.bg_app)
        content_id = canvas.create_window((0, 0), window=content, anchor="nw")

        content.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(content_id, width=e.width))

        pad = 24
        self.weather_section_frame = tk.Frame(content, bg=Colors.bg_app)
        self.weather_section_frame.pack(fill="x", padx=pad, pady=(pad, 0))

        self.saved_cities_container = tk.Frame(content, bg=Colors.bg_app)
        self.saved_cities_container.pack(fill="x", padx=pad, pady=(24, 24))
        self.refresh_saved_cities()

    def atualizar_meteorologia(self, cidade):
        for w in self.weather_section_frame.winfo_children():
            w.destroy()

        latitude, longitude = self.service.obter_coordenadas(cidade)
        if latitude is None or longitude is None:
            aviso = "Cidade não encontrada" if OPENWEATHERMAP_API_KEY else \
                    "Falta configurar a OPENWEATHERMAP_API_KEY no topo do ficheiro."
            tk.Label(self.weather_section_frame, text=f"⚠ {aviso}", font=(FONT_FAMILY, 11),
                     fg=Colors.warning, bg=Colors.bg_app).pack(anchor="w", pady=20)
            return

        self.current_city = cidade
        if self.on_city_changed:
            self.on_city_changed(cidade)
        dados_api = self.service.obter_dados_meteo(latitude, longitude)
        weather_data = self.service.montar_weather_data(cidade, dados_api)
        hourly_data = self.service.montar_hourly_data(dados_api)

        MainWeatherCard(
            self.weather_section_frame, weather_data,
            on_refresh=lambda: self.atualizar_meteorologia(self.current_city),
        ).pack(fill="x", pady=(0, 20))

        HourlyForecast(self.weather_section_frame, hourly_data).pack(fill="x")

    def adicionar_cidade_guardada(self, dados_cidade):
        self.cities_data = self.cidades_storage.adicionar_cidade(dados_cidade)
        self.refresh_saved_cities()

    def remover_cidade_guardada(self, nome):
        self.cities_data = self.cidades_storage.remover_cidade(nome)
        self.refresh_saved_cities()

    def refresh_saved_cities(self):
        cidades_atualizadas = self._buscar_dados_atuais_das_cidades()

        if self.saved_cities_widget is not None:
            self.saved_cities_widget.destroy()
        self.saved_cities_widget = SavedCities(
            self.saved_cities_container, cidades_atualizadas,
            on_manage=self._adicionar_cidade_atual_aos_guardados,
            on_open=lambda name: self.atualizar_meteorologia(name),
            on_remove=self.remover_cidade_guardada,
        )
        self.saved_cities_widget.pack(fill="x")

    def _buscar_dados_atuais_das_cidades(self):
        cidades_atualizadas = []
        for cidade in self.cities_data:
            nome = cidade["name"]
            latitude, longitude = self.service.obter_coordenadas(nome)
            if latitude is None or longitude is None:
                cidades_atualizadas.append({
                    "name": nome,
                    "region": cidade.get("region", ""),
                    "icon": cidade.get("icon", "🌤"),
                    "temp": cidade.get("temp", "--"),
                    "condition": cidade.get("condition", "Sem dados atualizados"),
                })
                continue
            dados_api = self.service.obter_dados_meteo(latitude, longitude)
            weather_data = self.service.montar_weather_data(nome, dados_api)
            cidades_atualizadas.append({
                "name": nome,
                "region": cidade.get("region", ""),
                "icon": "🌤",
                "temp": weather_data["temp"],
                "condition": weather_data["condition"],
            })
        return cidades_atualizadas

    def _adicionar_cidade_atual_aos_guardados(self):
        latitude, longitude = self.service.obter_coordenadas(self.current_city)
        if latitude is None:
            messagebox.showerror("Erro", "Não foi possível obter dados desta cidade.")
            return
        self.adicionar_cidade_guardada({
            "name": self.current_city,
            "region": "",
        })

class WeatherApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Weather Application")
        self.root.geometry("1200x800")
        self.root.configure(bg=Colors.bg_app)

        self.service = WeatherService()
        self.conta_storage = ContaStorage()
        self.conta_atual = None
        self.dashboard_page = None
        self.sidebar = None
        self.current_city = ""

        self.load_theme()
        self.style = ttk.Style()
        try:
            self.style.theme_use("azure-dark")
        except tk.TclError:
            pass

        self.style.configure("Treeview", background="#10141f", fieldbackground="#10141f",
                              foreground=Colors.text_primary, rowheight=28, borderwidth=0)
        self.style.configure("Treeview.Heading", background=Colors.tertiary_soft,
                              foreground=Colors.text_primary, font=(FONT_FAMILY, 9, "bold"))
        self.style.map("Treeview", background=[("selected", Colors.warning)],
                       foreground=[("selected", "#000000")])

        self.set_app_icon(ICON_PATH)

        conta = self.conta_storage.carregar_conta()
        if conta:
            self._iniciar_dashboard(conta)
        else:
            self._mostrar_configuracao_conta()

    def load_theme(self):
        try:
            self.root.tk.call("source", "azure/azure.tcl")
            self.root.tk.call("set_theme", "dark")
        except tk.TclError:
            pass

    def set_app_icon(self, icon_path):
        try:
            if platform.system() == "Windows":
                self.root.iconbitmap(icon_path)
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("myweatherapp")
            elif ImageTk is not None:
                icon = ImageTk.PhotoImage(file=icon_path.replace(".ico", ".png"))
                self.root.iconphoto(True, icon)
        except (tk.TclError, FileNotFoundError, Exception) as e:
            print(f"Não foi possível carregar o ícone: {e}")

    def _mostrar_configuracao_conta(self):
        self._limpar_janela()
        AccountSetupScreen(self.root, self.conta_storage, on_saved=self._on_conta_guardada).pack(
            fill="both", expand=True)

    def _on_conta_guardada(self, conta):
        self._iniciar_dashboard(conta)

    def _limpar_janela(self):
        for widget in self.root.winfo_children():
            widget.destroy()

    def _iniciar_dashboard(self, conta):
        self._limpar_janela()
        self.conta_atual = conta
        self.current_city = conta["Morada"]

        outer = tk.Frame(self.root, bg=Colors.bg_app)
        outer.pack(fill="both", expand=True)

        self.sidebar = Sidebar(outer, on_navigate=self.handle_navigate)
        self.sidebar.pack(side="left", fill="y")

        right_col = tk.Frame(outer, bg=Colors.bg_app)
        right_col.pack(side="left", fill="both", expand=True)

        self.topbar = TopBar(
            right_col, on_search=self.handle_search,
            on_profile_click=lambda: self.mostrar_pagina("conta"),
            nome_utilizador=conta.get("Nome", ""),
        )
        self.topbar.pack(fill="x")

        self.page_container = tk.Frame(right_col, bg=Colors.bg_app)
        self.page_container.pack(fill="both", expand=True)

        self.mostrar_pagina("dashboard")

    def mostrar_pagina(self, key):
        for w in self.page_container.winfo_children():
            w.destroy()
        self.dashboard_page = None

        if key == "dashboard":
            self.dashboard_page = DashboardPage(
                self.page_container, self.service, self.current_city,
                on_city_changed=self._on_dashboard_city_changed,
            )
            self.dashboard_page.pack(fill="both", expand=True)
            self.sidebar.set_active("dashboard")

        elif key == "alerts":
            AlertsPage(self.page_container, self.service, self.current_city).pack(fill="both", expand=True)
            self.sidebar.set_active("alerts")

        elif key == "historico":
            HistoricoPage(self.page_container, self.service, self.current_city).pack(fill="both", expand=True)
            self.sidebar.set_active("historico")

        elif key == "graficos":
            GraficosPage(self.page_container, self.service, self.current_city).pack(fill="both", expand=True)
            self.sidebar.set_active("graficos")

        elif key == "conta":
            AccountPage(self.page_container, self.conta_storage, self.conta_atual,
                        on_saved=self._on_conta_atualizada).pack(fill="both", expand=True)
            self.sidebar.set_active(None)

    def handle_navigate(self, key):
        self.mostrar_pagina(key)
        
    def handle_search(self, query):
        self.mostrar_pagina("dashboard")
        self.dashboard_page.atualizar_meteorologia(query)

    def _on_dashboard_city_changed(self, cidade):
        self.current_city = cidade

    def _on_conta_atualizada(self, nova_conta):
        self.conta_atual = nova_conta
        self.current_city = nova_conta["Morada"]
        messagebox.showinfo("Conta", "Informações da conta atualizadas com sucesso.")
        self.mostrar_pagina("dashboard")


if __name__ == "__main__":
    root = tk.Tk()
    app = WeatherApp(root)
    root.mainloop()
