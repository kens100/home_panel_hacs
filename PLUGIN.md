# 硬件端接入代码与报文说明

本插件支持通过 **MQTT** 方式接收硬件设备发送的数据。你需要将硬件设备连接到你的 MQTT 服务器（如 EMQX、Mosquitto），然后向以下 Topic 发送数据。

---

## 1. 发现与配置 (支持全自动配置)

本插件最新版已支持 **mDNS 自动发现** 与 **零配置 (Zero-conf)** 特性，极大简化了配置流程。

### 1.1 UI 自动配置流程 (推荐)

硬件端（ESP32）代码烧录运行并成功连接同一局域网的 Wi-Fi 后，会自动以 `_homepanel._tcp` 广播自己的存在。
1. 进入 Home Assistant，在**配置 -> 设备与服务 -> 集成**页面顶部，会自动弹出 **“发现新设备: Home Panel HACS”**。
2. 点击配置，在弹出的控制面板中填写你 Home Assistant 用的 **MQTT 服务器地址 (mqtt_server)**。
3. 点击确认后，HA 会自动通过设备提供的 API（`/api/config`）将 MQTT IP 下发给 ESP32 并使其保存、重启生效。
4. 此时设备已自动连上你的 MQTT 服务器，并且 Home Assistant 自动为您创建了相关实体，全程无需干预底层代码。

### 1.2 手动配置 (YAML / 手动发请求)

如果因网络层问题未能自动发现，你也可以：
1. **手动添加集成**：直接在 Home Assistant 集成列表搜索 `Home Panel HACS` 手动录入信息。
2. **硬件端手动配置**：向 ESP32 的 `/api/config` 发送 HTTP POST 请求。
   - `URL`: `http://<ESP32-IP>/api/config`
   - `POST Body` (x-www-form-urlencoded): `mqtt_server=你的MQTT-IP`。
3. 确保你的 Home Assistant 已配置 MQTT 集成，并且在插件配置中指定了 Topic（可在 UI 或 YAML 配置中自定义，默认为以下值）。

### 默认 Topic 配置：

| 传感器类型 | Topic | Payload 示例 |
|-----------|------|-------------|
| 温度传感器 | `home_panel/temperature` | `25.5` |
| 湿度传感器 | `home_panel/humidity` | `80%` |
| 门信号接收器 | `home_panel/door_signal` | `clicked` |
| 门状态传感器 | `home_panel/door_state` | `open` / `close` |

---

## 2. 硬件端 MQTT 报文格式

### 2.1 温湿度传感器

**温度传感器 - 发送数值：**
```bash
# Topic
home_panel/temperature

# Payload
25.5
```

**湿度传感器 - 发送数值（可带 %）：**
```bash
# Topic
home_panel/humidity

# Payload
80%
```

### 2.2 门信号接收器

当检测到开门动作（按钮触发）时发送：
```bash
# Topic
home_panel/door_signal

# Payload
clicked
```

### 2.3 门状态传感器

检测门的实际开闭状态：
```bash
# Topic
home_panel/door_state

# Payload
open
# 或
close
```

---

## 3. 门状态判断逻辑

插件会自动根据接入的传感器判断门状态：

1. **同时接入门状态传感器 + 门信号接收器**：使用门状态传感器的值作为最终状态
2. **仅接入门信号接收器**：根据门信号（clicked）判断门为打开状态
3. **都未接入**：状态显示为 unavailable

---

## 4. 硬件端代码示例 (ESP32/ESP8266)

### 4.1 温湿度传感器 (DHT11/DHT22)

```cpp
#include <WiFi.h>
#include <PubSubClient.h>
#include <DHT.h>

#define DHTPIN 4
#define DHTTYPE DHT11

const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";
const char* mqtt_server = "192.168.1.100";

DHT dht(DHTPIN, DHTTYPE);
WiFiClient espClient;
PubSubClient client(espClient);

void setup() {
  Serial.begin(115200);
  dht.begin();
  WiFi.begin(ssid, password);
  client.setServer(mqtt_server, 1883);
}

void loop() {
  if (!client.connected()) {
    client.connect("ESP8266_TempSensor");
  }
  client.loop();

  float temp = dht.readTemperature();
  float hum = dht.readHumidity();

  if (!isnan(temp)) {
    client.publish("home_panel/temperature", String(temp).c_str());
  }
  if (!isnan(hum)) {
    client.publish("home_panel/humidity", String(hum).c_str() + "%");
  }

  delay(5000);
}
```

### 4.2 门信号接收器 (按键/触摸模块)

```cpp
#include <WiFi.h>
#include <PubSubClient.h>

const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";
const char* mqtt_server = "192.168.1.100";

#define DOOR_BUTTON_PIN 5

WiFiClient espClient;
PubSubClient client(espClient);
bool lastState = false;

void setup() {
  pinMode(DOOR_BUTTON_PIN, INPUT_PULLUP);
  WiFi.begin(ssid, password);
  client.setServer(mqtt_server, 1883);
}

void loop() {
  if (!client.connected()) {
    client.connect("ESP8266_DoorSensor");
  }
  client.loop();

  bool currentState = digitalRead(DOOR_BUTTON_PIN) == LOW;

  if (currentState && !lastState) {
    client.publish("home_panel/door_signal", "clicked");
    Serial.println("Door opened!");
  }
  lastState = currentState;

  delay(100);
}
```

### 4.3 门状态传感器 (磁性磁簧开关)

```cpp
#include <WiFi.h>
#include <PubSubClient.h>

const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";
const char* mqtt_server = "192.168.1.100";

#define DOOR_SENSOR_PIN 5

WiFiClient espClient;
PubSubClient client(espClient);
bool lastState = false;

void setup() {
  pinMode(DOOR_SENSOR_PIN, INPUT_PULLUP);
  WiFi.begin(ssid, password);
  client.setServer(mqtt_server, 1883);
}

void loop() {
  if (!client.connected()) {
    client.connect("ESP8266_DoorState");
  }
  client.loop();

  bool currentState = digitalRead(DOOR_SENSOR_PIN) == LOW;

  if (currentState != lastState) {
    if (currentState) {
      client.publish("home_panel/door_state", "open");
    } else {
      client.publish("home_panel/door_state", "close");
    }
    lastState = currentState;
  }

  delay(100);
}
```

---

## 5. YAML 配置示例 (不推荐，请优先使用 UI 配置流)

```yaml
home_panel_hacs:
  name: "Home Panel"
  temperature_topic: "home_panel/temperature"
  humidity_topic: "home_panel/humidity"
  door_signal_topic: "home_panel/door_signal"
  door_state_topic: "home_panel/door_state"
```

---

## 6. 创建的实体

插件会自动创建以下实体：

| 实体 ID | 类型 | 描述 |
|--------|------|------|
| `sensor.home_panel_temperature` | Sensor | 温度 |
| `sensor.home_panel_humidity` | Sensor | 湿度 |
| `sensor.home_panel_door_signal` | Sensor | 门信号 |
| `binary_sensor.home_panel_door_state` | Binary Sensor | 门状态（来自传感器） |
| `binary_sensor.home_panel_door` | Binary Sensor | 综合门状态 |
