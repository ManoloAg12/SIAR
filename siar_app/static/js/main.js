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
function initializeWaterChart() {
    const chartContainer = document.getElementById('waterChart');
    if (!chartContainer) return; 
    
    const chart = echarts.init(chartContainer);
    const option = {
        animation: false,
        grid: { top: 20, right: 20, bottom: 40, left: 50, containLabel: false },
        xAxis: {
            type: 'category',
            data: ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sab', 'Dom'],
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
            data: [180, 220, 195, 245, 210, 165, 230],
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
                return params[0].name + '<br/>Consumo: ' + params[0].value + 'L';
            }
        }
    };
    chart.setOption(option);
    
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