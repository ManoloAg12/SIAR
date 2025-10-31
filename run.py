from siar_app import create_app

# Creamos una instancia de la aplicación llamando a nuestra factory
app = create_app()

if __name__ == '__main__':
    """
    Punto de entrada principal para ejecutar el servidor.
    """
    
    # host='0.0.0.0' es crucial. Permite que otros dispositivos
    # en su red local (como el ESP32) puedan acceder al servidor.
    # debug=True activa el modo de depuración para ver errores.
    app.run(host='0.0.0.0', port=5000, debug=True)