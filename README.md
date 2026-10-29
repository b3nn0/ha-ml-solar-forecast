# 🌞 ML Solar Forecast Integration

A **machine learning-powered solar forecast** integration for Home Assistant, designed to predict solar panel output with high accuracy using [weather data by Open-Meteo.com](https://open-meteo.com/) and your historic solar output.
This approach works especially well if you
- have a very complex setup with different orientations and tilt
- have a dynamic setup with trackers
- have complex time dependent shading on your panels
- have a weather service with systematic errors for your location (e.g. if it just won't get the fog in the mornings right)

For simple installations, there is no major benefit over classic forecasting solutions - but also no real downside, except occasionally slightly higher CPU usage.

## 📌 Overview

This integration provides **solar power predictions** based on historical weather data, solar irradiance, and other environmental factors, as well as your own historic solar output, read directly from Home Assistant's statistics. Training and prediction run inside Home Assistant.

⚠️ **Early development** – This integration is still maturing and may contain bugs or limitations.



## 🔧 Requirements

- Home Assistant
- Python dependencies are installed automatically by Home Assistant when the integration is set up.



## 🛠️ Installation

### **1. Manual Installation**
1. **Clone this repository** into your `custom_components` folder:
   ```bash
   cd /config/custom_components
   git clone https://github.com/b3nn0/ha-ml-solar-forecast ml_solar_forecast
   ```
1. **Restart Home Assistant**.
1. **Configure the integration** via **Settings > Devices & Services > Add Integration**.

### **2. HACS (Recommended)**
1. Add this repository as a custom repository to HACS
1. Search for **"ML Solar Forecast"** in HACS.
1. Install and restart Home Assistant.



## 📊 Configuration

### **Basic Setup**
- Add the integration via **Settings > Devices & Services > Add Integration** and follow the prompts.
- Go to the energy dashboard and edit it via the button in the top right
- Find your solar generation and add the ML Solar Forecast as a forecast

### **Other use cases**
- This integration adds a new service action `ml_solar_forecast.get_forecast` that gives access to the raw data for use in templates or scripts (timestamp -> Watts with 15 minute resolution).



## TODO
- Add helpful sensors and service to get current forecast


## 🤝 Contributing

Contributions are welcome! Please open an **issue** or **pull request** for:
- Bug fixes
- New features
- Documentation improvements
- Performance optimizations

### 🙌 Inspiration & Acknowledgments

This project was inspired by the excellent work of **[OpenMeteoSolarForecast](https://github.com/rany2/ha-open-meteo-solar-forecast)**, which provides a robust foundation for solar forecasting in Home Assistant.


## 📜 License
This project is licensed under **MIT**.
