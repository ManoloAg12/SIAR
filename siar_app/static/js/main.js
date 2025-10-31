/*
  Este archivo (main.js) define las funciones 
  que se usarán en el dashboard (home.html).
*/

// Gráfico de consumo de agua
function initializeWaterChart() {
    const chartContainer = document.getElementById('waterChart');
    if (!chartContainer) return; // Salir si no estamos en la página del gráfico
    
    const chart = echarts.init(chartContainer);
    const option = {
        // (Toda la configuración de su gráfico ECharts)
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
                
                // FUTURO: Aquí enviaremos un 'fetch' a la API de Flask
                // para actualizar el estado del relé.
            }
        });
    });
}

// Actualización del tiempo
function initializeTimeUpdate() {
    function updateLastUpdateTime() {
        const lastUpdateElement = document.getElementById('lastUpdate');
        if (lastUpdateElement) {
            lastUpdateElement.textContent = 'Actualizado ahora'; 
        }
    }
    // (Se puede añadir un setInterval si se desea)
    updateLastUpdateTime(); 
    // setInterval(updateLastUpdateTime, 60000); // <-- Si quiere refresco automático
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

    // Si no encontramos los botones (ej. en la pág de login), no hacemos nada.
    if (!openButton || !modal || !cancelButton || !confirmButton || !closeXButton) {
        return;
    }

    // Obtenemos la URL del botón que modificamos en base.html
    const logoutUrl = openButton.getAttribute('data-url');

    const openModal = () => {
        modal.classList.remove('hidden');
    };

    const closeModal = () => {
        modal.classList.add('hidden');
    };

    // 1. Abrir el modal
    openButton.addEventListener('click', (e) => {
        e.preventDefault(); // Prevenir cualquier comportamiento por defecto
        openModal();
    });

    // 2. Cerrar con el botón "Cancelar"
    cancelButton.addEventListener('click', closeModal);

    // 3. Cerrar con la "X"
    closeXButton.addEventListener('click', closeModal);

    // 4. (Opcional) Cerrar si se hace clic en el fondo oscuro
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            closeModal();
        }
    });

    // 5. Confirmar y redirigir
    confirmButton.addEventListener('click', () => {
        // Redirigimos a la URL de logout
        window.location.href = logoutUrl;
    });
}

/* Este 'listener' global se asegura de que la lógica del modal 
  se active en todas las páginas que usen el layout (base.html).
*/
document.addEventListener('DOMContentLoaded', function() {
    initializeLogoutModal();
    
    /* NOTA: Las funciones específicas de la página (como 'initializeWaterChart')
       deben seguir llamándose desde el bloque <script> en 'home.html'
       para que solo se ejecuten en esa página. */
});