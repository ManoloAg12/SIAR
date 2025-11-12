/*
  Este archivo (main.js) define TODAS las funciones 
  principales de la aplicación.
*/

// ===== ¡NUEVA FUNCIÓN AÑADIDA! =====
/**
 * Actualiza el texto (Activo/Desactivado) en la tarjeta de programación.
 * @param {boolean} newState - El nuevo estado (true para Activo, false para Desactivado).
 */
function updateModoAutomaticoStatus(newState) {
    const statusSpan = document.getElementById('modo-automatico-status');
    if (!statusSpan) return;

    if (newState) {
        statusSpan.innerHTML = '(<b class="text-green-600">Activo</b>)';
    } else {
        statusSpan.innerHTML = '(<b class="text-red-600">Desactivado</b>)';
    }
}

// ===== ¡NUEVA FUNCIÓN AÑADIDA! =====
/**
 * Actualiza la tarjeta de programación completa (llamada después de aplicar perfil)
 */
async function updateProgramacionCard() {
    console.log("Actualizando tarjeta de programación...");
    try {
        const response = await fetch('/api/get_programacion_card');
        if (!response.ok) throw new Error('Fallo al obtener el HTML');
        
        const newHTML = await response.text();
        
        const wrapper = document.getElementById('programacion-automatica-wrapper');
        if (wrapper) {
            wrapper.innerHTML = newHTML;
            // ¡IMPORTANTE! Reinicializamos los switches dentro de la tarjeta
            initializeSwitches(); 
        }
    } catch (error) {
        console.error('Error al actualizar la tarjeta:', error);
    }
}


// Gráfico de consumo de agua
// En siar_app/static/js/main.js

// Gráfico de consumo de agua (¡VERSIÓN DINÁMICA!)
function initializeWaterChart() {
    const chartContainer = document.getElementById('waterChart');
    if (!chartContainer) return; 
    
    // 1. Inicializar el gráfico de ECharts
    const chart = echarts.init(chartContainer);
    
    // 2. Definir la plantilla de opciones (el estilo)
    const optionTemplate = {
        animation: true, // Ponemos animación
        grid: { top: 20, right: 20, bottom: 40, left: 50, containLabel: false },
        xAxis: {
            type: 'category',
            data: [], // <--- Se llenará con la API
            axisLine: { show: false }, axisTick: { show: false },
            axisLabel: { color: '#6b7280', fontSize: 12 }
        },
        yAxis: {
            type: 'value',
            axisLine: { show: false }, axisTick: { show: false },
            splitLine: { lineStyle: { color: '#f3f4f6', width: 1 } },
            axisLabel: { color: '#6b7280', fontSize: 12, formatter: '{value}L' }
        },
        series: [{
            data: [], // <--- Se llenará con la API
            type: 'line', smooth: true, symbol: 'none',
            lineStyle: { color: '#57B5E7', width: 3 },
            areaStyle: {
                color: {
                    type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
                    colorStops: [{ offset: 0, color: 'rgba(87, 181, 231, 0.1)' }, { offset: 1, color: 'rgba(87, 181, 231, 0.01)' }]
                }
            }
        }],
        tooltip: {
            trigger: 'axis',
            backgroundColor: 'rgba(255, 255, 255, 0.9)',
            borderColor: '#e5e7eb', borderWidth: 1,
            textStyle: { color: '#1f2937' },
            formatter: function(params) {
                // params[0].name es la etiqueta del día (ej: "Jue 06")
                return params[0].name + '<br/>Consumo: ' + params[0].value + 'L';
            }
        }
    };
    
    // 3. Mostrar el gráfico vacío (mientras cargan los datos)
    chart.setOption(optionTemplate);
    
    // 4. Crear la función para buscar y actualizar los datos
    async function updateChartData() {
        try {
            const response = await fetch('/api/consumo_semanal');
            if (!response.ok) {
                throw new Error('Error de red al cargar el gráfico');
            }
            
            const chartData = await response.json(); // Espera: {labels: [...], data: [...]}
            
            if (chartData.labels && chartData.data) {
                // 5. Actualizar el gráfico con los datos reales
                chart.setOption({
                    xAxis: {
                        data: chartData.labels
                    },
                    series: [{
                        data: chartData.data
                    }]
                });
            }
            
        } catch (error) {
            console.error("Error en updateChartData:", error);
            // (Opcional: mostrar un error en el gráfico)
        }
    }
    
    // 6. Llamar a la función al iniciar
    updateChartData();
    
    // 7. (Opcional) Refrescar el gráfico cada 60 segundos
    setInterval(updateChartData, 60000); 

    // 8. Ajustar el tamaño
    window.addEventListener('resize', function() {
        chart.resize();
    });
}


// ===== FUNCIÓN DE SWITCHES (MODIFICADA CON BLOQUEO POR LLUVIA Y ESTADO) =====
function initializeSwitches() {
    // Buscamos solo el switch de modo automático
    const switches = document.querySelectorAll('.custom-switch[data-config="modo_automatico"]');
    
    switches.forEach(switch_ => {
        
        // Su lógica de 'onclick' está perfecta.
        // Se encarga de ENVIAR el cambio al servidor.
        switch_.onclick = function() {
            
            // El usuario intenta prenderlo (pasar de gris a azul)
            const wantsToActivate = !this.classList.contains('active'); 

            if (wantsToActivate) {
                // --- ¡NUEVA LÓGICA DE BLOQUEO POR ESTADO! ---
                const deviceStatus = this.dataset.deviceStatus;
                if (deviceStatus !== 'online' && deviceStatus !== 'regando') {
                    alert("¡Dispositivo Desconectado!\n\nNo se puede activar el modo automático si el dispositivo no está en línea.");
                    return; // Detener la ejecución
                }
                // --- FIN DE LÓGICA DE BLOQUEO POR ESTADO ---

                // --- LÓGICA DE BLOQUEO POR LLUVIA (Existente) ---
                const isRaining = this.dataset.isRaining === 'True';
                if (isRaining) {
                    alert("¡Alerta de Lluvia!\n\nNo se puede activar el modo automático mientras el sistema detecta lluvia.");
                    return; // Detener la ejecución
                }
                // --- FIN DE LÓGICA DE BLOQUEO POR LLUVIA ---
            }

            // Si no hay bloqueos, o si el usuario está APAGANDO el switch, continuar.
            this.classList.toggle('active');
            const newState = this.classList.contains('active');
            
            // Actualizamos el texto inmediatamente (UI Optimista)
            updateModoAutomaticoStatus(newState);

            fetch('/api/toggle_modo_automatico', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ new_state: newState })
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'ok') {
                    console.log('Modo automático actualizado a: ' + newState);
                    // El texto ya se actualizó, así que solo confirmamos.
                } else {
                    alert('Error al actualizar el modo: ' + data.message);
                    // Revertimos el cambio si falló
                    this.classList.toggle('active'); 
                    updateModoAutomaticoStatus(!newState);
                }
            })
            .catch(error => {
                console.error('Error en fetch:', error);
                alert('Error de conexión.');
                // Revertimos el cambio si falló
                this.classList.toggle('active'); 
                updateModoAutomaticoStatus(!newState);
            });
        };
    });
}

/*
  Esta es la nueva función que actualiza el texto "Activo" / "Desactivado"
  basado en el estado que recibe (true/false).
*/
function updateModoAutomaticoStatus(isActive) {
    // 1. Buscamos el SPAN por el ID que usted definió en el HTML
    const statusElement = document.getElementById('modo-automatico-status');
    
    if (!statusElement) {
        // console.warn("No se encontró el elemento 'modo-automatico-status' para actualizar.");
        return; // Salir si no existe
    }

    // 2. Cambiamos el HTML interno según el estado
    if (isActive) {
        // Si el nuevo estado es 'true' (activo)
        statusElement.innerHTML = '(<b class="text-green-600">Activo</b>)';
    } else {
        // Si el nuevo estado es 'false' (desactivado)
        statusElement.innerHTML = '(<b class="text-red-600">Desactivado</b>)';
    }
}

/**
 * ¡NUEVA FUNCIÓN DE SONDEO (POLLING)!
 * Esta función consulta la API de estado y actualiza el switch
 * y el texto de forma dinámica.
 */
function pollSystemStatus() {
    const switchElement = document.querySelector('.custom-switch[data-config="modo_automatico"]');
    if (!switchElement) {
        return; // No estamos en la página del dashboard
    }

    fetch('/api/system_status')
        .then(response => response.json())
        .then(data => {
            if (data.status === 'error') {
                console.warn("Error al sondear estado: " + data.message);
                return;
            }

            const deviceIsActive = (data.device_status === 'online' || data.device_status === 'regando');
            const switchIsDisabled = (data.is_raining || !deviceIsActive);

            // 1. Actualizar los data-attributes para que el 'onclick' tenga la info más reciente
            switchElement.dataset.isRaining = data.is_raining; // 'True' o 'False'
            switchElement.dataset.deviceStatus = data.device_status;

            // 2. Actualizar estado visual (Habilitado/Deshabilitado)
            if (switchIsDisabled) {
                switchElement.classList.add('opacity-50', 'cursor-not-allowed');
                // Forzamos a que esté "apagado" si llueve o está desconectado
                if (switchElement.classList.contains('active')) {
                    switchElement.classList.remove('active');
                }
            } else {
                // Si no debe estar deshabilitado, quitamos las clases de bloqueo
                switchElement.classList.remove('opacity-50', 'cursor-not-allowed');
            }

            // 3. Sincronizar el switch (Azul/Gris) con el estado de la BBDD
            // Solo si no está deshabilitado
            if (!switchIsDisabled) {
                if (data.modo_automatico) {
                    switchElement.classList.add('active');
                } else {
                    switchElement.classList.remove('active');
                }
            }
            
            // 4. Sincronizar el texto (Activo/Desactivado)
            // El texto debe reflejar el estado de la BBDD, pero también el bloqueo
            const effectiveState = data.modo_automatico && !switchIsDisabled;
            updateModoAutomaticoStatus(effectiveState);

            // --- ¡EXTRA! Actualizar otros elementos ---
            // Aquí puede actualizar el widget de "Estado del Sistema" también
            // (Esta lógica es un ejemplo, habría que darle IDs a esos elementos en home.html)
            const deviceStatusText = document.getElementById('device-status-text');
            if (deviceStatusText) {
                if (data.device_status === 'regando') deviceStatusText.innerText = 'Regando';
                else if (data.device_status === 'online') deviceStatusText.innerText = 'En Espera';
                else deviceStatusText.innerText = 'Desconectado';
            }

        })
        .catch(error => {
            console.error('Error en sondeo de estado:', error);
            // Si falla el sondeo (ej. se cae el server), deshabilitar el switch
            switchElement.classList.add('opacity-50', 'cursor-not-allowed');
            switchElement.classList.remove('active');
            updateModoAutomaticoStatus(false);
        });
}
document.addEventListener('DOMContentLoaded', function() {
    // 1. Inicializar el modal de logout (en todas las páginas)
    initializeLogoutModal();
    
    // 2. Inicializar los switches (solo se activará en 'home.html')
    initializeSwitches();

    // 3. ¡NUEVO! Iniciar el sondeo (polling)
    // Ejecuta la función 1 vez al cargar, y luego cada 5 segundos.
    pollSystemStatus(); 
    setInterval(pollSystemStatus, 5000); // 5000ms = 5 segundos

    /* NOTA: Las funciones específicas (como 'initializeWaterChart')
       deben seguir llamándose desde el bloque <script> en 'home.html' */
});
// Actualización del tiempo
function initializeTimeUpdate() {
    const lastUpdateElement = document.getElementById('lastUpdate');
    if (lastUpdateElement) {
        lastUpdateElement.textContent = 'Actualizado ahora'; 
    }
}

// === LÓGICA MODAL CERRAR SESIÓN ===
function initializeLogoutModal() {
    const openButton = document.getElementById('openLogoutModal');
    const modal = document.getElementById('logoutModal');
    const cancelButton = document.getElementById('cancelLogout');
    const confirmButton = document.getElementById('confirmLogout');
    const closeXButton = document.getElementById('closeModalX');

    if (!openButton || !modal || !cancelButton || !confirmButton || !closeXButton) {
        return;
    }

    const logoutUrl = openButton.getAttribute('data-url');
    const openModal = () => modal.classList.remove('hidden');
    const closeModal = () => modal.classList.add('hidden');

    openButton.addEventListener('click', (e) => { e.preventDefault(); openModal(); });
    cancelButton.addEventListener('click', closeModal);
    closeXButton.addEventListener('click', closeModal);
    modal.addEventListener('click', (e) => { if (e.target === modal) closeModal(); });
    confirmButton.addEventListener('click', () => { window.location.href = logoutUrl; });
}

// === LÓGICA APLICAR PERFILES DE RIEGO ===
function initializeProfileApplier() {
    const applyButtons = document.querySelectorAll('.apply-profile-btn');
    
    applyButtons.forEach(button => {
        button.addEventListener('click', function() {
            const perfilId = this.dataset.id;
            
            if (!confirm('¿Está seguro de que desea aplicar este perfil de riego?')) {
                return;
            }

            fetch('/api/aplicar_perfil', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ perfil_id: perfilId })
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'ok') {
                    alert('¡Perfil aplicado con éxito!');
                    // ¡ACTUALIZA LA TARJETA DINÁMICAMENTE!
                    updateProgramacionCard(); 
                } else {
                    alert('Error al aplicar el perfil: ' + data.message);
                }
            })
            .catch(error => {
                console.error('Error en fetch:', error);
                alert('Error de conexión al aplicar el perfil.');
            });
        });
    });
}

// === LÓGICA MODAL CREAR PERFIL ====
function initializeProfileModal() {
    const openButton = document.getElementById('openProfileModal');
    const modal = document.getElementById('newProfileModal');
    if (!openButton || !modal) return;
    
    const cancelButton = document.getElementById('cancelProfileModal');
    const closeXButton = document.getElementById('closeProfileModal');
    const form = document.getElementById('profileForm');

    const openModal = () => modal.classList.remove('hidden');
    const closeModal = () => modal.classList.add('hidden');

    openButton.addEventListener('click', openModal);
    cancelButton.addEventListener('click', closeModal);
    closeXButton.addEventListener('click', closeModal);

    form.addEventListener('submit', function(e) {
        e.preventDefault(); 
        const formData = new FormData(form);

        fetch('/api/crear_perfil', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'ok') {
                alert('¡Perfil creado con éxito!');
                window.location.reload(); // Recarga para ver el nuevo perfil
            } else {
                alert('Error al crear el perfil: ' + data.message);
            }
        })
        .catch(error => console.error('Error en fetch:', error));
    });
}

// === LÓGICA BOTÓN DE COPIAR API KEY ===
function initializeCopyButtons() {
    const copyButtons = document.querySelectorAll('.copy-api-key-btn');
    
    copyButtons.forEach(button => {
        button.addEventListener('click', function() {
            const keyToCopy = this.dataset.key;
            navigator.clipboard.writeText(keyToCopy).then(() => {
                alert('¡API Key copiada al portapapeles!');
            }).catch(err => {
                alert('Error al copiar la clave.');
            });
        });
    });
}

// === LÓGICA MODAL CREAR DISPOSITIVO ====
function initializeDeviceModal() {
    const openButton = document.getElementById('openDeviceModal');
    const modal = document.getElementById('newDeviceModal');
    if (!openButton || !modal) return; 

    const cancelButton = document.getElementById('cancelDeviceModal');
    const closeXButton = document.getElementById('closeDeviceModal');
    const form = document.getElementById('deviceForm');

    const openModal = () => modal.classList.remove('hidden');
    const closeModal = () => modal.classList.add('hidden');

    openButton.addEventListener('click', openModal);
    cancelButton.addEventListener('click', closeModal);
    closeXButton.addEventListener('click', closeModal);

    form.addEventListener('submit', function(e) {
        e.preventDefault(); 
        const formData = new FormData(form);

        fetch('/api/crear_dispositivo', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'ok') {
                alert('¡Dispositivo creado con éxito!');
                window.location.reload(); 
            } else {
                alert('Error al crear el dispositivo: ' + data.message);
            }
        })
        .catch(error => console.error('Error en fetch:', error));
    });
}

/* ================================================ */
/* === LÓGICA PARA ACTUALIZAR HUMEDAD DINÁMICA === */
/* ================================================ */

function initializeHumidityUpdater() {
    const humidityElement = document.getElementById('humidityValue');
    
    // Salir si no estamos en la página del home (donde existe el id)
    if (!humidityElement) return; 

    // Función asíncrona para buscar los datos
    async function fetchHumidity() {
        try {
            // 1. Consultamos nuestro nuevo endpoint
            const response = await fetch('/api/ultima_humedad');
            
            if (!response.ok) {
                throw new Error('Error de red al consultar la humedad');
            }
            
            const data = await response.json();
            
            // 2. Actualizamos el texto del elemento
            let valor = data.humedad;
            if (typeof valor === 'number') {
                humidityElement.textContent = valor + '%';
            } else {
                humidityElement.textContent = '--%'; // Muestra '--%' si no hay datos
            }

        } catch (error) {
            console.error("Error en fetchHumidity:", error);
            // Si falla, mostramos 'Error' para saber que algo ocurrió
            humidityElement.textContent = 'Error';
        }
    }

    // 1. Ejecutamos la función una vez al cargar la página
    fetchHumidity();

    // 2. Configuramos un intervalo para que se repita cada 10 segundos
    // Puede ajustar este tiempo (en milisegundos)
    setInterval(fetchHumidity, 3000); // 10000 ms = 10 segundos
}


/* ================================================ */
/* === LÓGICA PARA ACTUALIZAR ACTIVIDAD RECIENTE === */
/* ================================================ */

function initializeActivityUpdater() {
    const container = document.getElementById('recentActivityContainer');
    if (!container) return; // Salir si no estamos en home

    // --- Helper para asignar iconos bonitos ---
    function getIconForEvent(tipo) {
        // Valores por defecto
        let iconClass = 'ri-information-line';
        let bgClass = 'bg-gray-100';
        let textClass = 'text-gray-600';

        // Personalización basada en el tipo de evento
        if (tipo.includes('riego_auto')) {
            iconClass = 'ri-check-line';
            bgClass = 'bg-green-100';
            textClass = 'text-green-600';
        } else if (tipo.includes('sensor') || tipo.includes('humedad')) {
            iconClass = 'ri-water-percent-line';
            bgClass = 'bg-blue-100';
            textClass = 'text-blue-600';
        } else if (tipo.includes('error')) {
            iconClass = 'ri-error-warning-line';
            bgClass = 'bg-red-100';
            textClass = 'text-red-600';
        } else if (tipo.includes('online')) {
            iconClass = 'ri-wifi-line';
            bgClass = 'bg-cyan-100';
            textClass = 'text-cyan-600';
        }
        
        return { iconClass, bgClass, textClass };
    }
    // --- Fin del Helper ---


    async function fetchActivity() {
        try {
            const response = await fetch('/api/actividad_reciente');
            if (!response.ok) {
                throw new Error('Error de red al consultar actividad');
            }
            
            const data = await response.json(); // Esperamos una lista []

            // 1. Limpiamos el contenedor
            container.innerHTML = '';

            // 2. Verificamos si hay eventos
            if (data.length === 0) {
                // --- ESTA ES LA LÍNEA MODIFICADA ---
                container.innerHTML = '<p class="text-sm text-gray-500 text-center">aun no hay datos para mostrar</p>';
                return;
            }

            // 3. Recorremos los eventos y creamos el HTML
            data.forEach(evento => {
                const icon = getIconForEvent(evento.tipo_evento);
                
                // Esta es la plantilla HTML que se insertará
                const eventHTML = `
                <div class="flex items-start space-x-3">
                    <div class="w-8 h-8 flex items-center justify-center ${icon.bgClass} rounded-full mt-1 flex-shrink-0">
                        <i class="${icon.iconClass} ${icon.textClass}"></i>
                    </div>
                    <div class="flex-1">
                        <p class="text-sm font-medium text-gray-900">${evento.descripcion}</p>
                        <p class="text-xs text-gray-600">${evento.timestamp}</p>
                    </div>
                </div>
                `;
                
                // Añadimos el nuevo HTML al contenedor
                container.innerHTML += eventHTML;
            });

        } catch (error) {
            console.error("Error en fetchActivity:", error);
            container.innerHTML = '<p class="text-sm text-red-500 text-center">Error al cargar la actividad.</p>';
        }
    }

    // 1. Ejecutamos la función una vez al cargar
    fetchActivity();

    // 2. Repetimos cada 10 segundos
    setInterval(fetchActivity, 10000); 
}

// En siar_app/static/js/main.js
// (Añada esta función junto a sus otras, como initializeActivityUpdater)

/* ================================================ */
/* === LÓGICA PARA LOS SWITCHES DE HABILITAR/DESHABILITAR DISPOSITIVO === */
/* ================================================ */

function initializeDeviceSwitches() {
    const switches = document.querySelectorAll('.device-toggle-switch');
    
    switches.forEach(sw => {
        sw.addEventListener('click', function() {
            // Estado actual (antes del clic)
            const wasActive = this.classList.contains('active'); 
            // Nuevo estado (el que queremos)
            const newState = !wasActive; 
            const deviceId = this.dataset.deviceId;

            let confirmMessage = newState ? 
                "¿Está seguro de HABILITAR este dispositivo? El sistema comenzará a vigilarlo." :
                "¿Está seguro de DESHABILITAR este dispositivo (modo mantenimiento)? El dispositivo se forzará a 'offline'.";
            
            if (!confirm(confirmMessage)) {
                return; // El usuario canceló
            }

            // Llamamos a la nueva API
            fetch('/api/set_device_manual_status', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    device_id: deviceId,
                    new_state: newState // true = Habilitar, false = Deshabilitar
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'ok') {
                    // ¡Éxito!
                    // La forma más simple de actualizar la UI (el switch Y
                    // la API key) es recargar la página.
                    window.location.reload(); 
                } else {
                    alert('Error al cambiar el estado: ' + data.message);
                }
            })
            .catch(err => {
                console.error('Error en fetch:', err);
                alert('Error de conexión.');
            });
        });
    });
}

/* ================================================ */
/* === LÓGICA PARA ACTUALIZAR CONSUMO DE AGUA (REAL) === */
/* ================================================ */

function initializeWaterUpdater() {
    const waterElement = document.getElementById('waterConsumptionValue');
    
    // Salir si no estamos en la página del home
    if (!waterElement) return; 

    async function fetchWaterConsumption() {
        try {
            // 1. Consultamos el endpoint /api/consumo_agua
            // (Este endpoint ya lo creamos en routes.py)
            const response = await fetch('/api/consumo_agua');
            
            if (!response.ok) {
                throw new Error('Error de red al consultar el consumo');
            }
            
            const data = await response.json();
            
            // 2. Actualizamos el texto del elemento
            let valor = data.consumo_total;
            if (typeof valor === 'number') {
                waterElement.textContent = valor + 'L'; // Ej: "120.5L"
            } else {
                waterElement.textContent = '--L';
            }

        } catch (error) {
            console.error("Error en fetchWaterConsumption:", error);
            waterElement.textContent = 'Error';
        }
    }

    // 1. Ejecutamos la función una vez al cargar
    fetchWaterConsumption();

    // 2. Repetimos cada 10 segundos (igual que las otras tarjetas)
    setInterval(fetchWaterConsumption, 10000); 
}

/* ================================================ */
/* === LÓGICA MODAL: APLICAR PERFIL A DISPOSITIVO === */
/* ================================================ */
function initializeAplicarPerfilModal() {
    const modal = document.getElementById('applyProfileToDeviceModal');
    if (!modal) return;

    const openButtons = document.querySelectorAll('.open-apply-modal-btn');
    const closeButton = document.getElementById('closeApplyModal');
    const cancelButton = document.getElementById('cancelApplyModal');
    const form = document.getElementById('applyProfileForm');
    const deviceNameEl = document.getElementById('modalDeviceName');
    const deviceIdInput = document.getElementById('modalDeviceId');
    const profileSelect = document.getElementById('profileSelect');

    const openModal = (deviceId, deviceName) => {
        deviceNameEl.textContent = `Dispositivo: ${deviceName}`;
        deviceIdInput.value = deviceId; // Guardamos el ID en el input oculto
        profileSelect.value = ""; // Reseteamos el dropdown
        modal.classList.remove('hidden');
    };

    const closeModal = () => modal.classList.add('hidden');

    // Asignar evento a todos los botones "Aplicar Perfil"
    openButtons.forEach(btn => {
        btn.addEventListener('click', function() {
            const deviceId = this.dataset.deviceId;
            const deviceName = this.dataset.deviceName;
            openModal(deviceId, deviceName);
        });
    });

    // Eventos para cerrar el modal
    closeButton.addEventListener('click', closeModal);
    cancelButton.addEventListener('click', closeModal);

    // Evento para enviar el formulario
    form.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const perfilId = profileSelect.value;
        const deviceId = deviceIdInput.value;

        if (!perfilId) {
            alert('Por favor, seleccione un perfil.');
            return;
        }

        console.log(`Aplicando perfil ${perfilId} al dispositivo ${deviceId}`);
        
        fetch('/api/aplicar_perfil', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                perfil_id: perfilId,
                device_id: deviceId // <-- ¡Enviamos el ID del dispositivo!
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'ok') {
                alert(data.message); // Ej: "Perfil 'Huerto' aplicado a 'Jardin Central'."
                closeModal();
                window.location.reload(); // Recargamos para ver el cambio
            } else {
                alert('Error al aplicar: ' + data.message);
            }
        })
        .catch(err => {
            console.error('Error en fetch:', err);
            alert('Error de conexión.');
        });
    });
}

/* ================================================ */
/* === LÓGICA BOTÓN ENVIAR REPORTE POR CORREO === */
/* ================================================ */
function initializeSendReportButton() {
    const btn = document.getElementById('btn-send-report');
    if (!btn) return;

    const defaultHTML = btn.innerHTML; // Guardar el estado original

    btn.addEventListener('click', function() {
        if (!confirm('¿Está seguro de que desea enviar un reporte completo de la bitácora a su correo?')) {
            return;
        }

        // 1. Poner estado de "Cargando"
        btn.innerHTML = '<i class="ri-loader-4-line animate-spin mr-2"></i>Enviando...';
        btn.disabled = true;

        fetch('/api/send_report_email', {
            method: 'POST'
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'ok') {
                // 2. Poner estado de "Éxito"
                btn.innerHTML = '<i class="ri-check-line mr-2"></i>¡Reporte Enviado!';
            } else {
                // 3. Poner estado de "Error"
                alert('Error al enviar: ' + data.message);
                btn.innerHTML = '<i class="ri-error-warning-line mr-2"></i>Error';
            }
            
            // 4. Resetear el botón después de 4 segundos
            setTimeout(() => {
                btn.innerHTML = defaultHTML;
                btn.disabled = false;
            }, 4000);
        })
        .catch(err => {
            console.error('Error fetch:', err);
            alert('Error de conexión con el servidor.');
            btn.innerHTML = defaultHTML;
            btn.disabled = false;
        });
    });
}

/* ================================================ */
/* === LÓGICA MODAL: AÑADIR HORARIO === */
/* ================================================ */

function initializeHorarioModal() {
    const modal = document.getElementById('newHorarioModal');
    // Botón para abrir el modal
    const openButton = document.getElementById('openHorarioModal');
    
    if (!modal || !openButton) return; // Salir si los elementos no están

    const closeButton = document.getElementById('closeHorarioModal');
    const cancelButton = document.getElementById('cancelHorarioModal');
    const form = document.getElementById('horarioForm');

    const openModal = () => modal.classList.remove('hidden');
    const closeModal = () => modal.classList.add('hidden');

    // Asignar eventos
    openButton.addEventListener('click', openModal);
    closeButton.addEventListener('click', closeModal);
    cancelButton.addEventListener('click', closeModal);

    // Enviar formulario
    form.addEventListener('submit', function(e) {
        e.preventDefault();
        
        // Recopilamos los días seleccionados
        const formData = new FormData(form);
        const diasSeleccionados = formData.getAll('dias_semana');
        
        if (diasSeleccionados.length === 0) {
            alert('Debe seleccionar al menos un día de la semana.');
            return;
        }

        fetch('/api/crear_horario', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'ok') {
                alert('¡Horario creado con éxito!');
                window.location.reload(); // Recargar para ver el nuevo horario
            } else {
                alert('Error al crear el horario: ' + data.message);
            }
        })
        .catch(err => {
            console.error('Error en fetch (crear_horario):', err);
            alert('Error de conexión con el servidor.');
        });
    });
}

// ==========================================================
    // === LÓGICA MODAL: APLICAR PERFIL (AHORA ES AÑADIR HORARIO)
    // ==========================================================
    // (Esta función debe estar definida antes de 'DOMContentLoaded' o dentro del script)
    function initializeAplicarPerfilModal() {
        const modal = document.getElementById('applyProfileToDeviceModal');
        if (!modal) return;

        const openButtons = document.querySelectorAll('.open-apply-modal-btn');
        const closeButton = document.getElementById('closeApplyModal');
        const cancelButton = document.getElementById('cancelApplyModal');
        const form = document.getElementById('applyProfileForm');
        const deviceNameEl = document.getElementById('modalDeviceName');
        const deviceIdInput = document.getElementById('modalDeviceId');
        const profileSelect = document.getElementById('profileSelect');
        const checkboxes = form.querySelectorAll('input[type="checkbox"]');
        const timeInput = form.querySelector('input[type="time"]');

        const openModal = (deviceId, deviceName) => {
            deviceNameEl.textContent = `Dispositivo: ${deviceName}`;
            deviceIdInput.value = deviceId; // Guardamos el ID en el input oculto
            
            // Reseteamos el formulario
            profileSelect.value = ""; 
            timeInput.value = "";
            checkboxes.forEach(cb => cb.checked = false);
            
            modal.classList.remove('hidden');
        };

        const closeModal = () => modal.classList.add('hidden');

        openButtons.forEach(btn => {
            btn.addEventListener('click', function() {
                const deviceId = this.dataset.deviceId;
                const deviceName = this.dataset.deviceName;
                openModal(deviceId, deviceName);
            });
        });

        closeButton.addEventListener('click', closeModal);
        cancelButton.addEventListener('click', closeModal);

        // --- ¡LÓGICA DE ENVÍO MODIFICADA! ---
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const formData = new FormData(form);
            const diasSeleccionados = formData.getAll('dias_semana');

            if (diasSeleccionados.length === 0) {
                alert('Debe seleccionar al menos un día de la semana.');
                return;
            }
            
            // Ya no usamos JSON, usamos FormData
            // El 'device_id' ya está en el FormData gracias al input oculto.

            // Cambiamos el endpoint de /api/aplicar_perfil a /api/crear_horario
            fetch('/api/crear_horario', {
                method: 'POST',
                body: formData // Enviamos el formulario completo
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'ok') {
                    alert(data.message); // Ej: "Horario creado"
                    closeModal();
                    window.location.reload(); // Recargamos para ver el cambio
                } else {
                    alert('Error al crear horario: ' + data.message);
                }
            })
            .catch(err => {
                console.error('Error en fetch (crear_horario):', err);
                alert('Error de conexión.');
            });
        });
    }