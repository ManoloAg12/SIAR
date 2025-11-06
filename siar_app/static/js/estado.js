/**
 * siar_app/static/js/estado.js
 * Funciones para actualizar dinámicamente el estado del dashboard.
 */

/**
 * Esta función construye el HTML para la tarjeta de estado.
 * (La copié de su código)
 */
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
            <div><p class="text-sm font-medium text-gray-600">Estado del Sistema</p><p class="text-2xl font-bold text-red-600 mt-1">Desconectado</p></div>
            <div class="w-12 h-12 flex items-center justify-center bg-red-100 rounded-full"><i class="ri-wifi-off-line text-red-600 text-2xl"></i></div>
        </div>`;
    }
}

/**
 * Función de actualización principal.
 * Llama a la API de JSON y actualiza todos los elementos.
 */
async function runDynamicUpdate() {
    console.log("Actualizando estados (vía JSON)...");
    try {
        // 1. Llamar a nuestra API de JSON
        const response = await fetch('/api/get_dynamic_status');
        if (!response.ok) throw new Error('Respuesta de red no fue OK');
        
        const data = await response.json(); // Espera el JSON: {"device_status": "...", "db_status": "..."}

        // 2. Actualizar el estado de la BBDD
        const dbWrapper = document.getElementById('status-bbdd-wrapper');
        if (dbWrapper) {
            dbWrapper.textContent = `Estado BBDD: ${data.db_status}`;
        }
        
        // 3. Actualizar la tarjeta de estado del sistema
        const cardWrapper = document.getElementById('status-sistema-card-wrapper');
        if (cardWrapper) {
            cardWrapper.innerHTML = buildStatusCardHTML(data.device_status);
        }
        
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
            alert('Panel de estado actualizado.');
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