#include <ESP8266WiFi.h>
#include <ESP8266HTTPClient.h>
#include <SPI.h>
#include <MFRC522.h>

#define RST_PIN D1
#define SS_PIN  D2

MFRC522 rfid(SS_PIN, RST_PIN);

const char* ssid = "IOOOO";           // <-- Your Wi-Fi SSID
const char* password = "123456789";   // <-- Your Wi-Fi Password
const char* serverName = "http://10.207.13.96:8000"; // <-- Your backend IP

WiFiClient client;

void setup() {
  Serial.begin(115200);
  SPI.begin();
  rfid.PCD_Init();
  Serial.println("\n🚀 Starting HTMS Node...");
  connectWiFi();
}

void loop() {
  // Wait for RFID card
  if (!rfid.PICC_IsNewCardPresent() || !rfid.PICC_ReadCardSerial()) {
    delay(200);
    return;
  }

  // Step 1: Read UID
  String uidStr = "";
  for (byte i = 0; i < rfid.uid.size; i++) {
    uidStr += String(rfid.uid.uidByte[i], HEX);
  }
  uidStr.toUpperCase();

  Serial.println("\n==========================");
  Serial.print("Card UID: ");
  Serial.println(uidStr);
  Serial.println("==========================");

  // Step 2: Fetch card info from backend
  String cardUrl = String(serverName) + "/api/card/" + uidStr;
  HTTPClient http;
  http.begin(client, cardUrl);
  int httpCode = http.GET();

  if (httpCode != 200) {
    Serial.print("❌ Card lookup failed (code ");
    Serial.print(httpCode);
    Serial.println(")");
    http.end();
    delay(5000);
    return;
  }

  String cardInfo = http.getString();
  http.end();

  Serial.println("📋 Card Info:");
  Serial.println(cardInfo);

  // Step 3: Parse basic fields manually
  String amountStr = extractValue(cardInfo, "tariff");
  String balanceStr = extractValue(cardInfo, "balance");
  String vehicleStr = extractValue(cardInfo, "vehicle_type");

  Serial.println("==========================");
  Serial.print("Vehicle: ");
  Serial.println(vehicleStr);
  Serial.print("Tariff: ");
  Serial.println(amountStr);
  Serial.print("Balance: ");
  Serial.println(balanceStr);
  Serial.println("==========================");

  // Step 4: Create JSON payload for /api/toll
  String payload = "{\"tagUID\":\"" + uidStr + "\"}";

  // Step 5: POST transaction
  http.begin(client, String(serverName) + "/api/toll");
  http.addHeader("Content-Type", "application/json");
  int httpResponseCode = http.POST(payload);
  String response = http.getString();

  Serial.println("📡 Sent to backend...");
  Serial.print("Response Code: ");
  Serial.println(httpResponseCode);
  Serial.println("Response:");
  Serial.println(response);
  Serial.println("-----------------------------------");

  http.end();
  delay(5000);
}

// ======================
// Helper Functions
// ======================

void connectWiFi() {
  Serial.print("Connecting to Wi-Fi: ");
  Serial.println(ssid);
  WiFi.begin(ssid, password);
  int retry = 0;
  while (WiFi.status() != WL_CONNECTED && retry < 30) {
    delay(500);
    Serial.print(".");
    retry++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n✅ Wi-Fi Connected!");
    Serial.print("IP Address: ");
    Serial.println(WiFi.localIP());
    Serial.println("---------------------------");
    Serial.println("Place your RFID card near the reader...");
  } else {
    Serial.println("\n⚠️ Wi-Fi Connection Failed. Rebooting...");
    delay(2000);
    ESP.restart();
  }
}

// Extracts simple JSON key-value pair from API response
String extractValue(String json, String key) {
  int keyIndex = json.indexOf(key);
  if (keyIndex == -1) return "N/A";
  int colonIndex = json.indexOf(":", keyIndex);
  int commaIndex = json.indexOf(",", colonIndex);
  if (commaIndex == -1) commaIndex = json.indexOf("}", colonIndex);
  String value = json.substring(colonIndex + 1, commaIndex);
  value.trim();
  value.replace("\"", "");
  return value;
}
