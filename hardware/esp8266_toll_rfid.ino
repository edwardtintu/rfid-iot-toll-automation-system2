#include <ESP8266WiFi.h>
#include <ESP8266HTTPClient.h>
#include <SPI.h>
#include <MFRC522.h>
#include <Hash.h>
#include <Crypto.h>
#include <SHA256.h>
#include <HMAC.h>

#define RST_PIN D1
#define SS_PIN  D2
#define READER_ID "TOLL_READER_01"
#define READER_SECRET "R3@d3r_S3cr3t_001"
#define KEY_VERSION 1  // Key version for synchronization

unsigned long deviceEpochTime = 0;  // Global time variable for Unix timestamp

// Struct to store toll events for offline buffering
struct TollEvent {
  String uid;
  String reader_id;
  String timestamp;
  String nonce;
  String signature;
};

// Buffer for offline events (RAM buffer for prototype)
TollEvent buffer[10];
int bufferIndex = 0;

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
  // First, try to sync any buffered events if online
  if (WiFi.status() == WL_CONNECTED && bufferIndex > 0) {
    HTTPClient http;
    for (int i = 0; i < bufferIndex; i++) {
      // Create payload for buffered event
      String payload = "{"
        "\"tagUID\":\"" + buffer[i].uid + "\","
        "\"reader_id\":\"" + buffer[i].reader_id + "\","
        "\"timestamp\":\"" + buffer[i].timestamp + "\","
        "\"nonce\":\"" + buffer[i].nonce + "\","
        "\"signature\":\"" + buffer[i].signature + "\","
        "\"key_version\":\"" + String(KEY_VERSION) + "\""
        "}";

      http.begin(client, String(serverName) + "/api/toll");
      http.addHeader("Content-Type", "application/json");
      int httpResponseCode = http.POST(payload);
      String response = http.getString();

      Serial.println("📡 Syncing buffered event...");
      Serial.print("Response Code: ");
      Serial.println(httpResponseCode);
      Serial.println("Response:");
      Serial.println(response);

      http.end();
    }
    bufferIndex = 0;  // Clear buffer after successful sync
    Serial.println("✅ All buffered events synced");
  }

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

  // Step 1.5: Hash UID for privacy
  String hashedUID = hashUID(uidStr);

  Serial.println("\n==========================");
  Serial.print("Card UID: ");
  Serial.println(uidStr);
  Serial.print("Hashed UID: ");
  Serial.println(hashedUID);
  Serial.println("==========================");

  // Step 2: Fetch card info from backend (using hashed UID)
  String cardUrl = String(serverName) + "/api/card/" + hashedUID;
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

  // Step 4: Generate timestamp and nonce for cryptographic authentication
  unsigned long timestamp = deviceEpochTime + (millis() / 1000);   // Unix timestamp with uptime offset
  String nonce = String(random(100000, 999999));

  // Step 5: Generate HMAC-SHA256 signature using hashed UID
  String tsStr = String(timestamp);
  String signature = generateHMAC(hashedUID, String(READER_ID), tsStr, nonce);

  // Step 6: Create JSON payload for /api/toll with cryptographic authentication
  String payload = "{"
    "\"tag_hash\":\"" + hashedUID + "\","
    "\"reader_id\":\"" + String(READER_ID) + "\","
    "\"timestamp\":\"" + tsStr + "\","
    "\"nonce\":\"" + nonce + "\","
    "\"signature\":\"" + signature + "\","
    "\"key_version\":\"" + String(KEY_VERSION) + "\""
    "}";

  // Step 5: POST transaction (if online) or buffer (if offline)
  if (WiFi.status() == WL_CONNECTED) {
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
  } else {
    // Buffer the event for later transmission
    if (bufferIndex < 10) {
      buffer[bufferIndex].uid = uidStr;
      buffer[bufferIndex].reader_id = String(READER_ID);
      buffer[bufferIndex].timestamp = tsStr;
      buffer[bufferIndex].nonce = nonce;
      buffer[bufferIndex].signature = signature;
      bufferIndex++;
      Serial.println("📦 Event buffered (offline)");
    } else {
      Serial.println("⚠️ Buffer full, event lost");
    }
  }

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

    // Sync time from server after successful Wi-Fi connection
    Serial.println("Syncing time from server...");
    syncTimeFromServer();
    if (deviceEpochTime > 0) {
      Serial.print("✅ Time synced: ");
      Serial.println(deviceEpochTime);
    } else {
      Serial.println("⚠️ Time sync failed, using fallback");
      deviceEpochTime = millis() / 1000;  // fallback
    }

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

// Generate HMAC-SHA256 signature for authentication
String generateHMAC(String uid, String readerId, String timestamp, String nonce) {
  String message = uid + readerId + timestamp + nonce;

  byte hmacResult[32];
  SHA256 sha256;
  HMAC hmac(sha256, (const byte*)READER_SECRET, strlen(READER_SECRET));
  hmac.doUpdate((const byte*)message.c_str(), message.length());
  hmac.doFinal(hmacResult, sizeof(hmacResult));

  String signature = "";
  for (int i = 0; i < 32; i++) {
    if (hmacResult[i] < 16) signature += "0";
    signature += String(hmacResult[i], HEX);
  }
  return signature;
}

// Hash UID for privacy protection
String hashUID(String uid) {
  byte hash[32];
  SHA256 sha256;
  sha256.doUpdate((const byte*)uid.c_str(), uid.length());
  sha256.doFinal(hash, sizeof(hash));

  String result = "";
  for (int i = 0; i < 32; i++) {
    if (hash[i] < 16) result += "0";
    result += String(hash[i], HEX);
  }
  return result;
}

// Time sync function to get Unix timestamp from backend
void syncTimeFromServer() {
  HTTPClient http;
  http.begin(client, String(serverName) + "/api/time");
  int code = http.GET();
  if (code == 200) {
    String body = http.getString();
    deviceEpochTime = body.toInt();
  }
  http.end();
}
