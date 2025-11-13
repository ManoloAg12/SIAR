/**
 * siar_app/static/js/estado.js
 * Funciones para actualizar dinámicamente el estado del dashboard.
 */

/**
 * Esta función construye el HTML para la tarjeta de estado.
 * (La copié de su código)
 */
/**
 * ¡NUEVA FUNCIÓN!
 * Construye el HTML para el indicador de estado PEQUEÑO en la barra de navegación.
 */
function buildNavStatusIndicatorHTML(status) {
    if (status === 'regando') {
        return `
        <div class="w-8 h-8 flex items-center justify-center bg-blue-100 rounded-full status-active">
            <i class="ri-drop-line text-blue-600 text-sm"></i>
        </div>
        <span class="text-sm text-gray-600">Regando...</span>`;
    } else if (status === 'online') {
        return `
        <div class="w-8 h-8 flex items-center justify-center bg-green-100 rounded-full">
            <i class="ri-wifi-line text-green-600 text-sm"></i>
        </div>
        <span class="text-sm text-gray-600">En línea</span>`;
    } else { 
        // 'offline', 'offline_manual', 'Error', 'No Asignado', etc.
        return `
        <div class="w-8 h-8 flex items-center justify-center bg-red-100 rounded-full">
            <i class="ri-wifi-off-line text-red-600 text-sm"></i>
        </div>
        <span class="text-sm text-gray-600">Inhabilitado</span>`;
    }
}


function buildStatusCardHTML(status) {
    if (status === 'regando') {
        return `
        <div class="flex items-center justify-between">
            <div><p class="text-sm font-medium text-gray-600">Estado del Sistema</p><p class="text-2xl font-bold text-blue-600 mt-1">Regando</p></div>
            <div class="w-12 h-12 flex items-center justify-center bg-blue-100 rounded-full status-active"><i class="ri-drop-line text-blue-600 text-2xl"></i></div>
        </div>`;
    } else if (status === 'online') {
        return `
        <div class="flex items-center justify-between">
            <div><p class="text-sm font-medium text-gray-600">Estado del Sistema</p><p class="text-2xl font-bold text-green-600 mt-1">Conectado</p></div>
            <div class="w-12 h-12 flex items-center justify-center bg-green-100 rounded-full"><i class="ri-play-circle-fill text-green-600 text-2xl"></i></div>
        </div>`;
    } else {
        // Estado 'offline' o cualquier otro 
        return `
        <div class="flex items-center justify-between">
            <div><p class="text-sm font-medium text-gray-600">Estado del Sistema</p><p class="text-2xl font-bold text-red-600 mt-1">Inhabilitado</p></div>
            <div class="w-12 h-12 flex items-center justify-center bg-red-100 rounded-full"><i class="ri-wifi-off-line text-red-600 text-2xl"></i></div>
        </div>`;
    }
}

/**
 * Función de actualización principal.
 * Llama a la API de JSON y actualiza todos los elementos.
 */
/**
 * Función de actualización principal.
 * Llama a la API de JSON y actualiza todos los elementos de estado.
 * ¡VERSIÓN CORREGIDA (sin el switch de dispositivo)!
 */
/**
 * Función de actualización principal.
 * ¡VERSIÓN ACTUALIZADA! Ahora también actualiza el botón "Aplicar Perfil".
 */
/**
 * Función de actualización principal.
 * Llama a la API de JSON y actualiza todos los elementos de estado.
 * ¡VERSIÓN ACTUALIZADA! Ahora también actualiza el switch de "Modo Automático".
 */
async function runDynamicUpdate() {
    // console.log("Actualizando estados (vía JSON)...");
    try {
        const response = await fetch('/api/get_dynamic_status');
        if (!response.ok) throw new Error('Respuesta de red no fue OK');
        
        // Espera el JSON: {..., "device_status": "...", "is_raining": true/false}
        const data = await response.json(); 

        // --- (Su código existente para BBDD, Tarjeta de Estado, y Nav-bar va aquí) ---
        // 1. Actualizar el estado de la BBDD
        const dbWrapper = document.getElementById('status-bbdd-wrapper');
        if (dbWrapper) {
            dbWrapper.textContent = `Estado BBDD: ${data.db_status}`;
        }
        
        // 2. Actualizar la tarjeta de estado del sistema (la principal)
        const cardWrapper = document.getElementById('status-sistema-card-wrapper');
        if (cardWrapper) {
            cardWrapper.innerHTML = buildStatusCardHTML(data.device_status);
        }

        // 3. Actualizar el indicador de la barra de navegación
        const navIndicator = document.getElementById('nav-status-indicator');
        if (navIndicator) {
            navIndicator.innerHTML = buildNavStatusIndicatorHTML(data.device_status);
        }
        
        // 4. Actualizar la tarjeta "Mis Dispositivos"
        if (data.device_id) {
            // ... (Todo su código para "device-status-text" y "api-key-container" va aquí) ...
            const deviceId = data.device_id;
            const deviceText = document.getElementById('device-status-text-' + deviceId);
            if (deviceText) {
                deviceText.textContent = `Estado: ${data.device_status_text}`;
            }
            const apiKeyContainer = document.getElementById(`api-key-container-${deviceId}`);
            if (apiKeyContainer) {
                const mostrarKey = (data.device_status === 'offline_manual' || data.device_status === 'offline');
                if (mostrarKey) { apiKeyContainer.classList.remove('hidden'); }
                else { apiKeyContainer.classList.add('hidden'); }
            }
            const applyButton = document.querySelector(`.open-apply-modal-btn[data-device-id="${deviceId}"]`);
            if (applyButton) {
                const deviceIsActiveBtn = (data.device_status === 'online' || data.device_status === 'regando');
                const isRainingBtn = data.is_raining;
                const isDisabledBtn = (isRainingBtn || !deviceIsActiveBtn);
                applyButton.disabled = isDisabledBtn;
                if (isDisabledBtn) {
                    applyButton.classList.add('bg-gray-400', 'cursor-not-allowed', 'opacity-70');
                    applyButton.classList.remove('bg-blue-500', 'hover:bg-blue-600');
                } else {
                    applyButton.classList.remove('bg-gray-400', 'cursor-not-allowed', 'opacity-70');
                    applyButton.classList.add('bg-blue-500', 'hover:bg-blue-600');
                }
            }
        }

        // --- ¡NUEVO BLOQUE AÑADIDO! ---
        // 5. Actualizar dinámicamente el switch de "Programación Automática"
        const autoSwitch = document.querySelector('.custom-switch[data-config="modo_automatico"]');
        if (autoSwitch) {
            // Leer los datos FRESCOS de la API
            const deviceIsActive = (data.device_status === 'online' || data.device_status === 'regando');
            const isRaining = data.is_raining;
            const isDisabled = (isRaining || !deviceIsActive);

            // Actualizar los atributos data-* para que la función initializeSwitches()
            // (que se activa al hacer clic) tenga la información más reciente.
            autoSwitch.dataset.isRaining = isRaining;
            autoSwitch.dataset.deviceStatus = data.device_status;

            // Actualizar la apariencia visual (gris/deshabilitado o normal)
            if (isDisabled) {
                autoSwitch.classList.add('opacity-50', 'cursor-not-allowed');
                autoSwitch.classList.remove('active'); // Forzarlo a apagado
            } else {
                autoSwitch.classList.remove('opacity-50', 'cursor-not-allowed');
                // Nota: No lo forzamos a 'active' aquí, 
                // eso depende de si el modo automático está guardado.
                // El 'active' se actualizará si el usuario aplica un perfil.
            }
        }
        // --- FIN DEL BLOQUE NUEVO ---

    } catch (error) {
        console.error('Error al actualizar dinámicamente:', error);
    }
}

/**
 * Añade el 'listener' al botón "Actualizar"
 */
function initializeRefreshButton() {
    const btn = document.getElementById('btn-actualizar-dash');
    if (btn) {
        btn.addEventListener('click', () => {
            runDynamicUpdate(); // Llama a la función principal
            window.location.reload();
        });
    }
}

/**
 * Inicia el 'polling' automático para refrescar los estados.
 */
function startAutomaticPolling(intervalMilliseconds = 10000) {
    console.log(`Iniciando polling automático cada ${intervalMilliseconds}ms`);
    
    // 1. Ejecutar inmediatamente al cargar la página
    runDynamicUpdate();
    
    // 2. Luego, establecer un intervalo para que se repita
    setInterval(() => {
        console.log("Polling: Actualizando estados...");
        runDynamicUpdate();
    }, intervalMilliseconds); // 10000ms = 10 segundos
}