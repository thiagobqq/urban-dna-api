CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TYPE problem_type AS ENUM (
    'buraco_asfalto',
    'vazamento_agua',
    'vazamento_esgoto',
    'poste_sem_luz',
    'fiacao_exposta',
    'bueiro_entupido',
    'calcada_quebrada',
    'semaforo_defeito'
);

CREATE TYPE priority_level AS ENUM (
    'emergencia',
    'urgente',
    'alta',
    'media',
    'baixa'
);

CREATE TYPE team_type AS ENUM (
    'asfalto',
    'hidraulica',
    'eletrica',
    'saneamento',
    'geral'
);

CREATE TABLE IF NOT EXISTS maintenance_points (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    latitude DECIMAL(10, 8) NOT NULL,
    longitude DECIMAL(11, 8) NOT NULL,
    location GEOGRAPHY(POINT, 4326),
    address TEXT NOT NULL,
    neighborhood VARCHAR(100),
    region VARCHAR(50),
    
    problem_type problem_type NOT NULL,
    priority priority_level NOT NULL,
    team_type team_type NOT NULL,
    problem_size VARCHAR(20) CHECK (problem_size IN ('pequeno', 'medio', 'grande')),
    estimated_time_minutes INTEGER NOT NULL,
    urgency_score DECIMAL(10, 2) DEFAULT 0.0,
    
    complaints_count INTEGER DEFAULT 0,
    affects_traffic BOOLEAN DEFAULT FALSE,
    affects_commerce BOOLEAN DEFAULT FALSE,
    near_critical_location BOOLEAN DEFAULT FALSE,
    main_road BOOLEAN DEFAULT FALSE,
    
    status VARCHAR(30) DEFAULT 'aberto',
    requires_road_block BOOLEAN DEFAULT FALSE,
    dependencies INTEGER[],
    materials JSONB,
    
    photos JSONB,
    observations TEXT,
    metadata JSONB
);

CREATE INDEX idx_maintenance_location ON maintenance_points USING GIST(location);
CREATE INDEX idx_maintenance_priority ON maintenance_points(priority);
CREATE INDEX idx_maintenance_team ON maintenance_points(team_type);
CREATE INDEX idx_maintenance_status ON maintenance_points(status);
CREATE INDEX idx_maintenance_neighborhood ON maintenance_points(neighborhood);

CREATE TABLE IF NOT EXISTS distance_cache (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    point_a_id UUID REFERENCES maintenance_points(id),
    point_b_id UUID REFERENCES maintenance_points(id),
    distance_km DECIMAL(10, 3),
    travel_time_minutes INTEGER,
    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(point_a_id, point_b_id)
);

CREATE TABLE IF NOT EXISTS optimized_routes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    team_type team_type,
    route_date DATE,
    total_points INTEGER,
    total_distance_km DECIMAL(10, 3),
    total_time_minutes INTEGER,
    route_order JSONB,
    statistics JSONB
);