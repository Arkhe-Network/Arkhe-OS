-- Schema para o Arkhe(n) SaaS
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    organization_id UUID REFERENCES organizations(id),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    description TEXT,
    organization_id UUID REFERENCES organizations(id),
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE handovers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    coherence FLOAT NOT NULL,
    phase FLOAT NOT NULL,
    gamma_b JSONB,
    timestamp TIMESTAMP DEFAULT NOW(),
    stability_index FLOAT,
    metadata JSONB,
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Índices para consultas rápidas
CREATE INDEX idx_handovers_coherence ON handovers(coherence);
CREATE INDEX idx_handovers_project ON handovers(project_id);
CREATE INDEX idx_handovers_timestamp ON handovers(timestamp DESC);