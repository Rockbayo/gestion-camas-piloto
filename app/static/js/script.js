// Scripts personalizados para Sistema de Camas Piloto

// Función para inicializar los elementos al cargar la página
document.addEventListener('DOMContentLoaded', function() {
    // Inicializar tooltips de Bootstrap
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Inicializar popovers de Bootstrap
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function(popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Auto-cerrar alertas después de 5 segundos
    setTimeout(function() {
        const alerts = document.querySelectorAll('.alert:not(.alert-important)');
        alerts.forEach(function(alert) {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);

    // Configurar campos de fecha para que usen el selector de fecha nativo
    const dateInputs = document.querySelectorAll('input[type="date"]');
    dateInputs.forEach(function(input) {
        if (!input.value) {
            input.valueAsDate = new Date();
        }
    });

    // Hacer que las filas de las tablas sean clickeables si tienen el atributo data-href
    const clickableRows = document.querySelectorAll('tr[data-href]');
    clickableRows.forEach(function(row) {
        row.addEventListener('click', function() {
            window.location.href = this.dataset.href;
        });
        row.style.cursor = 'pointer';
    });
});

// Función para confirmar acciones peligrosas
function confirmarAccion(mensaje, formId) {
    if (confirm(mensaje)) {
        document.getElementById(formId).submit();
    }
    return false;
}

// Función para cargar datos dependientes en formularios
function cargarOpcionesDependientes(url, sourceSelectId, targetSelectId, placeholderText) {
    const sourceSelect = document.getElementById(sourceSelectId);
    const targetSelect = document.getElementById(targetSelectId);
    
    if (!sourceSelect || !targetSelect) return;
    
    sourceSelect.addEventListener('change', function() {
        const selectedValue = this.value;
        
        if (!selectedValue) {
            targetSelect.innerHTML = `<option value="">${placeholderText}</option>`;
            targetSelect.disabled = true;
            return;
        }
        
        // Hacer la petición AJAX
        fetch(`${url}/${selectedValue}`)
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    targetSelect.innerHTML = `<option value="">${placeholderText}</option>`;
                    
                    data.options.forEach(option => {
                        const optionElement = document.createElement('option');
                        optionElement.value = option.id;
                        optionElement.textContent = option.text;
                        targetSelect.appendChild(optionElement);
                    });
                    
                    targetSelect.disabled = false;
                } else {
                    console.error('Error al cargar las opciones:', data.error);
                }
            })
            .catch(error => {
                console.error('Error en la petición:', error);
            });
    });
}

// Función para formatear números con separador de miles
function formatearNumero(numero) {
    return numero.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ".");
}

// Función para validar formularios antes de enviar
function validarFormulario(formId) {
    const form = document.getElementById(formId);
    
    // Validación nativa de HTML5
    if (!form.checkValidity()) {
        form.classList.add('was-validated');
        return false;
    }
    
    return true;
}