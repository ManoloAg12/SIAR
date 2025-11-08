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

// ===== FUNCIÓN DE SWITCHES (MODIFICADA) =====
function initializeSwitches() {
    const switches = document.querySelectorAll('.custom-switch');
    
    switches.forEach(switch_ => {
        // Usamos un listener de 'click' que sea único para evitar duplicados
        switch_.onclick = function() {
            this.classList.toggle('active');
            const newState = this.classList.contains('active');
            const configType = this.dataset.config;
            const horarioId = this.dataset.horarioId;

            if (configType === 'modo_automatico') {
                fetch('/api/toggle_modo_automatico', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ new_state: newState })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'ok') {
                        // ¡Éxito! Actualiza el texto
                        updateModoAutomaticoStatus(newState);
                        console.log('Modo automático actualizado a: ' + newState);
                    } else {
                        // Falla: revierte el switch
                        alert('Error al actualizar el modo: ' + data.message);
                        this.classList.toggle('active');
                    }
                })
                .catch(error => {
                    console.error('Error en fetch:', error);
                    alert('Error de conexión.');
                    this.classList.toggle('active');
                });
            }
        };
    });
}

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