CREATE DATABASE siar;

/* Almacena la lista de países para el formulario de registro */
CREATE TABLE tbl_paises (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) UNIQUE NOT NULL,
    codigo_iso CHAR(2) UNIQUE NOT NULL -- Ej: 'SV', 'GT', 'US'
);

/* Tabla de usuarios que administrarán el sistema */
CREATE TABLE tbl_usuarios (
    id SERIAL PRIMARY KEY,
    
    -- Campos del formulario
    nombre_completo VARCHAR(255) NOT NULL,
    email VARCHAR(120) UNIQUE NOT NULL,
    nombre_usuario VARCHAR(80) UNIQUE NOT NULL,
    password_hash VARCHAR(256) NOT NULL, -- Importante: Guardamos el HASH, no la contraseña
    telefono VARCHAR(20) NOT NULL,
    direccion TEXT NOT NULL,
    ciudad VARCHAR(100) NOT NULL,
    
    -- Relación con la tabla de países
    pais_id INTEGER REFERENCES tbl_paises(id),
    
    -- Metadatos
    fecha_creacion TIMESTAMPTZ DEFAULT NOW()
);

/* Insertamos datos de ejemplo en la tabla de países */
INSERT INTO tbl_paises (nombre, codigo_iso) VALUES
('El Salvador', 'SV'),
('Guatemala', 'GT'),
('Honduras', 'HN'),
('Nicaragua', 'NI'),
('Costa Rica', 'CR'),
('México', 'MX'),
('Estados Unidos', 'US'),
('España', 'ES'),
('Panamá', 'PA');