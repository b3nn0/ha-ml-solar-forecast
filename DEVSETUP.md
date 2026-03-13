## 🛠️ Hacking

To work on this integration, follow these steps:

### 1. Set Up Your Workspace

```bash
mkdir ~/coding && cd ~/coding
```

### 2. Clone Repositories

Clone HA Core and this repository:

```bash
git clone git@github.com:home-assistant/core.git homeassistant-core
git clone git@github.com:b3nn0/ha-ml-solar-forecast.git
```

### 3. Prepare Home Assistant Config

Create a persistent config directory and fetch historical data for testing:

```bash
mkdir -p homeassistant-config
ssh root@hass.local "sqlite3 /config/home-assistant_v2.db .dump" | sqlite3 homeassistant-config/home-assistant_v2.db
```

### 4. Configure Docker Mounts

Update `homeassistant-core/.devcontainer/devcontainer.json` with these mounts:

```json
"mounts": [
    "source=${localEnv:HOME}/coding/homeassistant-config,target=${containerWorkspaceFolder}/config,type=bind",
    "source=${localEnv:HOME}/coding/ha-ml-solar-forecast,target=${containerWorkspaceFolder}/ha-ml-solar-forecast,type=bind",
    "source=${localEnv:HOME}/coding/ha-ml-solar-forecast/custom_components/ml_solar_forecast,target=${containerWorkspaceFolder}/config/custom_components/ml_solar_forecast,type=bind",
]
```

### 5. Start Development Environment

1. Open `homeassistant-core` in VS Code
2. Click **"Reopen in Container"** if prompted (or press `Ctrl+Shift+P` and select the command)
3. Use the launch configurations to start Home Assistant
4. Access `http://localhost:8123` for onboarding and testing
5. Optional: For proper sensor updating and registry, you might want to use (Remote HomeAssistant)[https://github.com/custom-components/remote_homeassistant] in your dev environment.