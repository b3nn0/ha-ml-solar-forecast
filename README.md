# 🌞 ML Solar Forecast Integration

A **machine learning-powered solar forecast** integration for Home Assistant, designed to predict solar panel output with high accuracy using [weather data by Open-Meteo.com](https://open-meteo.com/) and your historic solar output.
This approach works especially well if you
- have a very complex setup with different orientations and tilt
- have a dynamic setup with trackers
- have complex time dependent shading on your panels
- have a weather service with systematic errors for your location (e.g. if it just won't get the fog in the mornings right)

For simple installations, there is no major benefit over classic forecasting solutions - but also no real downside, except occasionally slightly higher CPU usage.

## 📌 Overview

This integration leverages **LightGBM** to provide **solar power predictions** based on historical weather data, solar irradiance, and other environmental factors, as well as your own historic solar output, read directly from Home Assistant's statistics..

⚠️ **Early Alpha / Proof of Concept** – This integration is in active development and may contain bugs or limitations. Use at your own risk! It is probably best to not use it yet.



## 🔧 Requirements

### **1. Home Assistant Machine Learner Addon**
This integration requires the **[HA Machine Learner Addon](https://github.com/b3nn0/hassio-addon-machinelearner)** to run the forecasting models.
Once [this](https://github.com/home-assistant/wheels-custom-integrations/pull/748) pull request is merged, the addon will become obsolete eventually.



## 🛠️ Installation

### **1. Manual Installation (HACS)**
1. Install the HA Machine learner app from [here](https://github.com/b3nn0/hassio-addon-machinelearner).
1. **Clone this repository** into your `custom_components` folder:
   ```bash
   cd /config/custom_components
   git clone https://github.com/b3nn0/ha-ml-solar-forecast ml_solar_forecast
   ```
1. **Restart Home Assistant**.
1. **Configure the integration** via **Settings > Devices & Services > Add Integration**.

### **2. HACS (Recommended)**
1. Install the HA Machine learner app from [here](https://github.com/b3nn0/hassio-addon-machinelearner).
1. Add this repository as a cusom repository to HACS
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
- Get LightGBM approved to HA wheels and change integration to use that instead ([#748](https://github.com/home-assistant/wheels-custom-integrations/pull/748))
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

