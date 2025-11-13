#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <WiFiUdp.h>        // <--- Para obtener la hora
#include <NTPClient.h>      // <--- Para obtener la hora

// --- 1. CONFIGURACIÓN OBLIGATORIA (SUS DATOS) ---
const char* SSID_WIFI = "Laptod_M.A";
const char* PASSWORD_WIFI = "minombre";
const char* IP_SERVIDOR = "192.168.10.69";
const int PUERTO_SERVIDOR = 5000;
const char* DEVICE_API_KEY = "697571ddf0d1ed9434478eaad02cddbf0f70e4d1b53ab797731d0ad05c5dec56";

// --- 2. CONFIGURACIÓN DE PINES ---
const int PIN_SENSOR_HUMEDAD = 33;
const int PIN_RELE_BOMBA = 4; // <--- Pin para controlar la bomba (GPIO4)

// --- CALIBRACIÓN SENSOR ---
const int VALOR_AIRE_SECO = 2850;
const int VALOR_SUMERGIDO_AGUA = 1350;

// --- 2.5. INTERVALOS ---
const long INTERVALO_LOGICA_PRINCIPAL_MS = 5000; // 5 segundos
const long INTERVALO_CONFIG_MS = 60000; // 1 minuto
const long INTERVALO_NTP_MS = 900000; // 15 minutos

unsigned long tiempoAnteriorLogica = 0;
unsigned long tiempoAnteriorConfig = 0;
unsigned long tiempoAnteriorNTP = 0;

// --- 2.6. LÓGICA DE RIEGO ---
const int COOLDOWN_RIEGO_MINUTOS = 1; 
unsigned long tiempoUltimoRiego = 0;
bool estaRegando = false; 
const int DURACION_RIEGO_EMERGENCIA_SEG = 3; // 10 segundos

// --- 3. VARIABLES GLOBALES ---
String url_base_api;
WiFiClient client;
HTTPClient http;

// --- Objetos para la Hora (NTP) ---
WiFiUDP ntpUDP;
NTPClient ntpClient(ntpUDP, "pool.ntp.org", -21600); // GMT-6 (El Salvador)

// --- Variables para la Configuración (descargada del servidor) ---
// Valores por defecto "seguros" iniciales
int g_umbral_min_emergencia = -1;  // <--- VALOR SEGURO
int g_umbral_max_ahorro = 101; // <--- VALOR SEGURO
bool g_modo_programado_activo = false;
#define MAX_HORARIOS 5
struct Horario {
  int hora;
  int minuto;
  String dias;
  int duracion;
} g_horarios[MAX_HORARIOS];
int g_num_horarios = 0;

// --- Variables para la Hora Actual ---
int g_dia_semana_actual = 0; // 1=Lunes, 7=Domingo
int g_hora_actual = 0;
int g_minuto_actual = 0;


// ==========================================================
// --- FUNCIÓN: LEER SENSOR DE HUMEDAD ---
// ==========================================================
float leerHumedad() {
  int valorRaw = analogRead(PIN_SENSOR_HUMEDAD);
  float porcentaje = map(valorRaw, VALOR_AIRE_SECO, VALOR_SUMERGIDO_AGUA, 0, 100);
  if (porcentaje < 0) porcentaje = 0;
  if (porcentaje > 100) porcentaje = 100;
  Serial.println("Humedad calculada: " + String(porcentaje) + "%");
  return porcentaje;
}

// ==========================================================
// --- FUNCIÓN: ENVIAR LECTURA DE HUMEDAD (LATIDO) ---
// ==========================================================
void enviarHumedad(float humedad) {
  StaticJsonDocument<128> jsonDoc;
  jsonDoc["humedad"] = humedad;
  jsonDoc["device_key"] = DEVICE_API_KEY;

  String jsonOutput;
  serializeJson(jsonDoc, jsonOutput);

  String url = url_base_api + "/api/lectura";
  http.begin(url);
  http.addHeader("Content-Type", "application/json");

  int httpCode = http.POST(jsonOutput);
  if (httpCode == 201) {
    Serial.println("API: Latido de humedad enviado OK.");
  } else {
    Serial.printf("API: Error al enviar latido. Código: %d\n", httpCode);
  }
  http.end();
}

// ==========================================================
// --- FUNCIÓN: ENVIAR ESTADO ---
// ==========================================================
void enviarEstado(const char* estado) {
  StaticJsonDocument<100> jsonDoc;
  jsonDoc["device_key"] = DEVICE_API_KEY;
  jsonDoc["status"] = estado;

  String jsonOutput;
  serializeJson(jsonDoc, jsonOutput);

  String url = url_base_api + "/api/device/status";
  http.begin(url);
  http.addHeader("Content-Type", "application/json");

  int httpCode = http.POST(jsonOutput);
  if (httpCode == 200) {
    Serial.printf("API: Estado actualizado a '%s' OK.\n", estado);
  } else {
    Serial.printf("API: Error al actualizar estado. Código: %d\n", httpCode);
  }
  http.end();
}

// ==========================================================
// --- FUNCIÓN: REPORTAR RIEGO TERMINADO ---
// ==========================================================
void reportarRiegoTerminado(int duracion, const char* tipo, float humedad) {
  StaticJsonDocument<128> jsonDoc;
  jsonDoc["device_key"] = DEVICE_API_KEY;
  jsonDoc["duracion_seg"] = duracion;

  if (strcmp(tipo, "sensor") == 0) {
    jsonDoc["humedad_actual"] = humedad;
  }

  String jsonOutput;
  serializeJson(jsonDoc, jsonOutput);

  String url = url_base_api + "/api/log_riego";
  http.begin(url);
  http.addHeader("Content-Type", "application/json");

  int httpCode = http.POST(jsonOutput);
  if (httpCode == 200) {
    Serial.println("API: Reporte de riego enviado OK.");
  } else {
    Serial.printf("API: Error al reportar riego. Código: %d\n", httpCode);
  }
  http.end();
}

// ==========================================================
// --- FUNCIÓN: CONTROLAR EL RIEGO ---
// ==========================================================
void activarRiego(int duracionSeg, const char* tipoRiego, float humedadParaLog) {
  if (estaRegando) return; 
  
  estaRegando = true;
  Serial.printf("--- INICIANDO RIEGO (%s) POR %d SEGUNDOS ---\n", tipoRiego, duracionSeg);

  // 1. Notificar al servidor "estoy regando"
  enviarEstado("regando");
  delay(500); 

  // 2. Activar la bomba (Asumiendo relé ACTIVO EN ALTO)
  digitalWrite(PIN_RELE_BOMBA, HIGH);

  // 3. Esperar (BLOQUEANDO EL LOOP)
  delay(duracionSeg * 1000);

  // 4. Desactivar la bomba
  digitalWrite(PIN_RELE_BOMBA, LOW);
  Serial.println("--- RIEGO FINALIZADO ---");

  // 5. Notificar al servidor "ya no estoy regando"
  enviarEstado("online");

  // 6. Reportar el ciclo de riego a la bitácora
  reportarRiegoTerminado(duracionSeg, tipoRiego, humedadParaLog);

  // 7. Actualizar el cooldown y liberar el bloqueo
  tiempoUltimoRiego = millis();
  estaRegando = false;
}


// ==========================================================
// --- FUNCIÓN: OBTENER HORA (NTP) (¡CORREGIDA!) ---
// ==========================================================
void actualizarHoraActual() {
  // Esta función AHORA solo lee la hora de la biblioteca NTP
  // NO llama a ntpClient.update() aquí.
  
  int ntpDia = ntpClient.getDay(); // 0=Domingo, 1=Lunes, ..., 6=Sábado
  
  // Mapeamos el día (D=0 a D=7)
  g_dia_semana_actual = (ntpDia == 0) ? 7 : ntpDia; 
  
  g_hora_actual = ntpClient.getHours();
  g_minuto_actual = ntpClient.getMinutes();

  // Imprimimos la hora local que se usará para la lógica
  Serial.printf("Hora local leída: Día: %d, Hora: %02d:%02d\n", g_dia_semana_actual, g_hora_actual, g_minuto_actual);
}

// ==========================================================
// --- FUNCIÓN: OBTENER CONFIGURACIÓN (¡CORREGIDA!) ---
// ==========================================================
void obtenerConfiguracionDelServidor() {
  if (WiFi.status() != WL_CONNECTED) return;
  
  String url = url_base_api + "/api/configuracion?device_key=" + String(DEVICE_API_KEY);
  Serial.println("API: Obteniendo configuración de: " + url);

  http.begin(url);
  int httpCode = http.GET();

  if (httpCode == 200) {
    String payload = http.getString();
    Serial.println("Configuración recibida: " + payload);

    DynamicJsonDocument jsonDoc(1024);
    DeserializationError error = deserializeJson(jsonDoc, payload);

    if (error) {
      Serial.println("Error al parsear JSON de configuración");
      return;
    }

    // --- ¡LÓGICA DE LECTURA CORREGIDA! ---
    
    // 1. Leer valores de emergencia.
    // Si la clave "umbral_min" NO existe, usará -1 (seguro).
    // Si la clave "umbral_max" NO existe, usará 101 (seguro).
    g_umbral_min_emergencia = jsonDoc["umbral_min"] | -1;  // <-- ¡CAMBIO CRÍTICO!
    g_umbral_max_ahorro = jsonDoc["umbral_max"] | 101; // <-- ¡CAMBIO CRÍTICO!

    // 2. Leer modo programado (esto siempre existirá)
    g_modo_programado_activo = jsonDoc["modo_programado_activo"] | false;

    // --- FIN DE MODIFICACIÓN ---


    // 3. Leer la lista de horarios
    JsonArray horariosArray = jsonDoc["horarios"];
    g_num_horarios = 0; // Reseteamos el contador

    for (JsonObject horarioJson : horariosArray) {
      if (g_num_horarios >= MAX_HORARIOS) break; 

      String horaStr = horarioJson["hora"]; // "08:00"
      
      g_horarios[g_num_horarios].hora = horaStr.substring(0, 2).toInt();
      g_horarios[g_num_horarios].minuto = horaStr.substring(3, 5).toInt();
      g_horarios[g_num_horarios].dias = horarioJson["dias"].as<String>(); // "1,3,5"
      g_horarios[g_num_horarios].duracion = horarioJson["duracion"]; // 15
      
      g_num_horarios++;
    }
    
    Serial.printf("Configuración cargada: %d horarios. Modo prog: %d. Umbral Min: %d\n", 
                  g_num_horarios, g_modo_programado_activo, g_umbral_min_emergencia);

  } else {
    Serial.printf("API: Error al obtener config. Código: %d\n", httpCode);
  }
  http.end();
}


// ==========================================================
// --- FUNCIÓN: LÓGICA DE DECISIÓN DE RIEGO ---
// ==========================================================
void revisarLogicaRiego(float humedadActual) {
  // 1. Chequeos de seguridad
  if (estaRegando) {
    // Serial.println("Lógica: Omitida (Riego en progreso)");
    return;
  }

  // 2. Chequeo de Cooldown
  unsigned long tiempoDesdeUltimoRiego = millis() - tiempoUltimoRiego;
  unsigned long cooldownMs = (unsigned long)COOLDOWN_RIEGO_MINUTOS * 60 * 1000;
  
  if (tiempoUltimoRiego != 0 && (tiempoDesdeUltimoRiego < cooldownMs)) {
    Serial.println("Lógica: Omitida (En Cooldown)");
    return;
  }

  // --- LÓGICA DE EMERGENCIA (SENSOR) ---
  if (humedadActual < g_umbral_min_emergencia) {
    Serial.println("LÓGICA: ¡RIEGO DE EMERGENCIA ACTIVADO!");
    Serial.printf("(Humedad %0.1f%% < Umbral Min %d%%)\n", humedadActual, g_umbral_min_emergencia);
    
    activarRiego(DURACION_RIEGO_EMERGENCIA_SEG, "sensor", humedadActual);
    return; 
  }

  // --- LÓGICA PROGRAMADA (HORARIOS) ---
  if (!g_modo_programado_activo) {
    // Serial.println("Lógica: Omitida (Modo programado desactivado)");
    return;
  }

  // 2. Recorrer los horarios descargados
  for (int i = 0; i < g_num_horarios; i++) {
    
    // 2.1. ¿Es hoy un día para regar?
    if (g_horarios[i].dias.indexOf(String(g_dia_semana_actual)) == -1) {
      continue; // No es el día, pasar al siguiente horario
    }

    // 2.2. ¿Es la hora de regar?
    if (g_horarios[i].hora == g_hora_actual && g_horarios[i].minuto == g_minuto_actual) {
      
      Serial.printf("LÓGICA: Horario %d coincidente.\n", i);

      // 2.3. ¡Lógica de AHORRO!
      if (humedadActual > g_umbral_max_ahorro) {
        Serial.printf("LÓGICA: Riego OMITIDO por humedad alta (Ahorro). (%0.1f%% > %d%%)\n", humedadActual, g_umbral_max_ahorro);
        tiempoUltimoRiego = millis(); 
        return; 
      }

      // 2.4. ¡REGAR!
      Serial.println("LÓGICA: ¡RIEGO PROGRAMADO ACTIVADO!");
      activarRiego(g_horarios[i].duracion, "programado", 0.0); // 0.0 para 'programado'
      return; // Salir (solo un riego programado por ciclo)
    }
  }
}


// ==========================================================
// --- FUNCIÓN: CONECTAR WIFI ---
// ==========================================================
void conectarWiFi() {
  Serial.print("Conectando a WiFi: " + String(SSID_WIFI));
  WiFi.begin(SSID_WIFI, PASSWORD_WIFI);

  int intentos = 0;
  while (WiFi.status() != WL_CONNECTED && intentos < 20) {
    delay(500);
    Serial.print(".");
    intentos++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\nWiFi Conectado. IP: " + WiFi.localIP().toString());
  } else {
    Serial.println("\nFallo al conectar WiFi. Reiniciando en 5 seg...");
    delay(5000);
    ESP.restart();
  }
}

// ==========================================================
// --- FUNCIÓN DE CONFIGURACIÓN INICIAL (setup) ---
// ==========================================================
void setup() {
  Serial.begin(115200);
  Serial.println("\nIniciando Controlador SIAR (ESP32)...");

  // Configurar pines
  pinMode(PIN_SENSOR_HUMEDAD, INPUT);
  pinMode(PIN_RELE_BOMBA, OUTPUT);
  digitalWrite(PIN_RELE_BOMBA, LOW); // Asegurarse que la bomba esté apagada

  // 1. Conectar a WiFi
  conectarWiFi();

  // Construir la URL base
  url_base_api = "http://" + String(IP_SERVIDOR) + ":" + String(PUERTO_SERVIDOR);

  // 2. Iniciar NTP para obtener la hora
  ntpClient.begin();
  ntpClient.update(); // <-- Hacemos una actualización inicial aquí
  actualizarHoraActual(); // <-- Leemos la hora actualizada

  // 3. Obtener la configuración inicial del servidor
  // (Esta función ahora es segura y usa los valores -1 y 101)
  obtenerConfiguracionDelServidor();

  // 4. Enviar estado "online"
  // (Lo quitamos, el primer latido en el loop se encargará)
  // delay(1000); 
  // enviarEstado("online"); 
  
  Serial.println("Setup finalizado. Iniciando bucle de lecturas...");

  // Inicializar timers
  unsigned long t = millis();
  tiempoAnteriorLogica = t;
  tiempoAnteriorConfig = t;
  tiempoAnteriorNTP = t;
  tiempoUltimoRiego = 0; 
}

// ==========================================================
// --- BUCLE PRINCIPAL (loop) (¡CORREGIDO!) ---
// ==========================================================
void loop() {
  
  // 1. Mantener WiFi Conectado
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi desconectado. Reconectando...");
    conectarWiFi();
  }

  // 2. Si estamos regando (en el delay de activarRiego), no hacemos nada más
  if (estaRegando) {
    return;
  }
  
  unsigned long tiempoActual = millis();

  // --- Timer 1: Sincronizar Hora (NTP) ---
  if (tiempoActual - tiempoAnteriorNTP >= INTERVALO_NTP_MS) { // <-- 15 MINUTOS
    tiempoAnteriorNTP = tiempoActual;
    Serial.println("NTP: Sincronizando hora con el servidor de tiempo...");
    ntpClient.update(); // <-- SOLO ACTUALIZAMOS LA BIBLIOTECA
  }
  
  // --- Timer 2: Sincronizar Configuración del Servidor ---
  if (tiempoActual - tiempoAnteriorConfig >= INTERVALO_CONFIG_MS) { // <-- 1 MINUTO
    tiempoAnteriorConfig = tiempoActual;
    obtenerConfiguracionDelServidor();
  }
  
  // --- Timer 3: Lógica Principal (Lectura, Latido y Riego) ---
  if (tiempoActual - tiempoAnteriorLogica >= INTERVALO_LOGICA_PRINCIPAL_MS) { // <-- 5 SEGUNDOS
    tiempoAnteriorLogica = tiempoActual;
    
    Serial.println("\n--- Nuevo Ciclo Lógico ---");

    // ¡CORRECCIÓN!
    // 1. Actualizar las variables de hora (g_hora, g_minuto) CADA CICLO
    //    (Esto lee la hora local de la biblioteca NTP, no llama a internet)
    actualizarHoraActual(); // <-- MOVIDO AQUÍ

    // 2. Leer el sensor
    float humedadActual = leerHumedad();

    // 3. Enviar la lectura (Latido)
    enviarHumedad(humedadActual);

    // 4. Revisar si debemos regar (con la hora y humedad actualizadas)
    revisarLogicaRiego(humedadActual);
  }
}