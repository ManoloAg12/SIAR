/*
  Este archivo (main.js) define TODAS las funciones 
  que usará la aplicación.
*/

// Gráfico de consumo de agua
function initializeWaterChart() {
    const chartContainer = document.getElementById('waterChart');
    if (!chartContainer) return; // Salir si no estamos en la página del gráfico
    
    const chart = echarts.init(chartContainer);
    const option = {
        // (Configuración de ECharts)
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

// Control de interruptores
function initializeSwitches() {
    const switches = document.querySelectorAll('.custom-switch');
    switches.forEach(switch_ => {
        switch_.addEventListener('click', function() {
            this.classList.toggle('active');
            const zone = this.getAttribute('data-zone');
            if (zone) {
                const isActive = this.classList.contains('active');
                console.log(`Zona ${zone} ${isActive ? 'activada' : 'desactivada'}`);
            }
        });
    });
}

// Actualización del tiempo
function initializeTimeUpdate() {
    const lastUpdateElement = document.getElementById('lastUpdate');
    if (lastUpdateElement) {
        lastUpdateElement.textContent = 'Actualizado ahora'; 
    }
}

/* ============================================= */
/* === LÓGICA PARA EL MODAL DE CERRAR SESIÓN === */
/* ============================================= */

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

    openButton.addEventListener('click', (e) => {
        e.preventDefault(); 
        openModal();
    });

    cancelButton.addEventListener('click', closeModal);
    closeXButton.addEventListener('click', closeModal);
    modal.addEventListener('click', (e) => {
        if (e.target === modal) closeModal();
    });
    confirmButton.addEventListener('click', () => {
        window.location.href = logoutUrl;
    });
}

/* ============================================= */
/* === LÓGICA PARA APLICAR PERFILES DE RIEGO === */
/* (ESTA ES LA FUNCIÓN QUE FALTABA)             */
/* ============================================= */

function initializeProfileApplier() {
    const applyButtons = document.querySelectorAll('.apply-profile-btn');
    
    applyButtons.forEach(button => {
        button.addEventListener('click', function() {
            const perfilId = this.dataset.id;
            
            if (!confirm('¿Está seguro de que desea aplicar este perfil de riego? Se sobrescribirá la configuración actual.')) {
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

/* ============================================= */
/* === LÓGICA PARA EL MODAL DE CREAR PERFIL ==== */
/* (ESTA TAMBIÉN FALTABA)                        */
/* ============================================= */

function initializeProfileModal() {
    const openButton = document.getElementById('openProfileModal');
    const modal = document.getElementById('newProfileModal');
    const cancelButton = document.getElementById('cancelProfileModal');
    const closeXButton = document.getElementById('closeProfileModal');
    const form = document.getElementById('profileForm');

    if (!openButton || !modal || !cancelButton || !form || !closeXButton) {
        return;
    }

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
                window.location.reload(); // Recarga la página para ver el nuevo perfil
            } else {
                alert('Error al crear el perfil: ' + data.message);
            }
        })
        .catch(error => {
            console.error('Error en fetch:', error);
            alert('Error de conexión al crear el perfil.');
        });
    });
}