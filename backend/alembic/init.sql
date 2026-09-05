-- SIH26011 — 3D ULPIN System database schema (Section 6, complete DDL)
-- Mounted into postgres as /docker-entrypoint-initdb.d/init.sql

-- Enable PostGIS
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_sfcgal;  -- ST_3DIntersection / ST_Volume for detect_3d_conflicts()
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- ENUM TYPES
-- ============================================
DO $$ BEGIN
    CREATE TYPE user_role AS ENUM ('admin', 'surveyor', 'urban_planner', 'citizen', 'validator');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE parcel_type AS ENUM ('surface', 'multi_storey', 'underground', 'air_right', 'mixed');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE parcel_status AS ENUM ('draft', 'verified', 'disputed', 'archived');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE building_type AS ENUM ('residential', 'commercial', 'industrial', 'mixed', 'infrastructure');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE unit_type AS ENUM ('apartment', 'shop', 'office', 'parking', 'storage', 'utility', 'air_right', 'pipeline', 'tunnel');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE rights_type AS ENUM ('full_ownership', 'lease', 'easement', 'air_right', 'subsurface', 'joint');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE owner_type AS ENUM ('individual', 'government', 'corporation', 'trust', 'religious');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE source_type AS ENUM ('drone_image', 'lidar', 'gis_shapefile', 'floor_plan', 'gnss_log', 'dem', 'survey_sketch');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE processing_status AS ENUM ('uploaded', 'queued', 'processing', 'completed', 'failed');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE job_type AS ENUM ('building_extraction', 'floor_segmentation', 'vertical_delineation', 'topology_validation', 'ulpin_generation', 'conflict_detection');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE job_status AS ENUM ('pending', 'running', 'completed', 'failed', 'cancelled');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE conflict_type AS ENUM ('overlap', 'gap', 'boundary_mismatch', 'air_right_violation', 'utility_intrusion', 'ownership_dispute');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE severity_level AS ENUM ('low', 'medium', 'high', 'critical');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE alert_status AS ENUM ('open', 'under_review', 'resolved', 'escalated');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- ============================================
-- TABLES
-- ============================================
CREATE TABLE users (
    user_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role user_role NOT NULL DEFAULT 'citizen',
    department VARCHAR(100),
    full_name VARCHAR(255),
    phone VARCHAR(20),
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    last_login TIMESTAMP WITH TIME ZONE
);

CREATE TABLE owners (
    owner_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    owner_type owner_type NOT NULL DEFAULT 'individual',
    name VARCHAR(255) NOT NULL,
    name_local VARCHAR(255),
    aadhaar_hash VARCHAR(64) UNIQUE,
    pan_hash VARCHAR(64),
    contact JSONB DEFAULT '{}',
    guardian_name VARCHAR(255),
    date_of_birth DATE,
    is_verified BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE parcels (
    parcel_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ulpin VARCHAR(50) UNIQUE NOT NULL,
    legacy_survey_no VARCHAR(50),
    village_code VARCHAR(10),
    geom_2d GEOMETRY(Polygon, 4326),
    geom_3d GEOMETRY(PolyhedralSurfaceZ, 4326),
    area_sqm DECIMAL(12,2),
    parcel_type parcel_type NOT NULL DEFAULT 'surface',
    status parcel_status NOT NULL DEFAULT 'draft',
    metadata JSONB DEFAULT '{}',
    created_by UUID REFERENCES users(user_id),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE buildings (
    building_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    parcel_id UUID NOT NULL REFERENCES parcels(parcel_id) ON DELETE CASCADE,
    building_name VARCHAR(200),
    footprint GEOMETRY(Polygon, 4326),
    height_m DECIMAL(8,2),
    floors_above_ground INT NOT NULL DEFAULT 1,
    floors_below_ground INT NOT NULL DEFAULT 0,
    construction_year INT,
    building_type building_type NOT NULL DEFAULT 'residential',
    extracted_by_ml BOOLEAN NOT NULL DEFAULT false,
    confidence_score DECIMAL(3,2),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE units (
    unit_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    building_id UUID NOT NULL REFERENCES buildings(building_id) ON DELETE CASCADE,
    parent_parcel_id UUID REFERENCES parcels(parcel_id),
    unit_ulpin VARCHAR(50) UNIQUE NOT NULL,
    volume_3d GEOMETRY(PolyhedralSurfaceZ, 4326) NOT NULL,
    floor_number INT,
    floor_label VARCHAR(20),
    unit_type unit_type NOT NULL DEFAULT 'apartment',
    area_sqm DECIMAL(10,2),
    volume_cubm DECIMAL(12,2),
    height_min_m DECIMAL(8,2),
    height_max_m DECIMAL(8,2),
    status parcel_status NOT NULL DEFAULT 'draft',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE ownership_records (
    ownership_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    unit_id UUID NOT NULL REFERENCES units(unit_id) ON DELETE CASCADE,
    owner_id UUID NOT NULL REFERENCES owners(owner_id),
    rights_type rights_type NOT NULL DEFAULT 'full_ownership',
    share_percentage DECIMAL(5,2) NOT NULL DEFAULT 100.00,
    valid_from DATE NOT NULL,
    valid_to DATE,
    registration_doc_url TEXT,
    registered_by UUID REFERENCES users(user_id),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT valid_date_range CHECK (valid_to IS NULL OR valid_to > valid_from)
);

CREATE TABLE data_sources (
    source_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_type source_type NOT NULL,
    file_url TEXT NOT NULL,
    file_size_bytes BIGINT,
    metadata JSONB DEFAULT '{}',
    uploaded_by UUID REFERENCES users(user_id),
    parcel_id UUID REFERENCES parcels(parcel_id),
    processing_status processing_status NOT NULL DEFAULT 'uploaded',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE processing_jobs (
    job_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_id UUID REFERENCES data_sources(source_id),
    parcel_id UUID REFERENCES parcels(parcel_id),
    job_type job_type NOT NULL,
    status job_status NOT NULL DEFAULT 'pending',
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    confidence_score DECIMAL(4,3),
    result_metadata JSONB DEFAULT '{}',
    error_message TEXT,
    worker_node VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE conflict_alerts (
    alert_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    unit_a_id UUID NOT NULL REFERENCES units(unit_id),
    unit_b_id UUID NOT NULL REFERENCES units(unit_id),
    conflict_type conflict_type NOT NULL,
    overlap_volume_cubm DECIMAL(12,4),
    severity severity_level NOT NULL DEFAULT 'medium',
    status alert_status NOT NULL DEFAULT 'open',
    detected_by_job_id UUID REFERENCES processing_jobs(job_id),
    assigned_to UUID REFERENCES users(user_id),
    resolution_notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMP WITH TIME ZONE,
    CONSTRAINT different_units CHECK (unit_a_id != unit_b_id)
);

-- ============================================
-- INDEXES
-- ============================================
CREATE INDEX idx_parcels_ulpin ON parcels(ulpin);
CREATE INDEX idx_parcels_village ON parcels(village_code);
CREATE INDEX idx_parcels_status ON parcels(status);
CREATE INDEX idx_parcels_geom_2d ON parcels USING GIST(geom_2d);
CREATE INDEX idx_parcels_geom_3d ON parcels USING GIST(geom_3d);
CREATE INDEX idx_buildings_parcel ON buildings(parcel_id);
CREATE INDEX idx_buildings_footprint ON buildings USING GIST(footprint);
CREATE INDEX idx_buildings_type ON buildings(building_type);
CREATE INDEX idx_units_building ON units(building_id);
CREATE INDEX idx_units_ulpin ON units(unit_ulpin);
CREATE INDEX idx_units_volume_3d ON units USING GIST(volume_3d);
CREATE INDEX idx_units_type ON units(unit_type);
CREATE INDEX idx_units_status ON units(status);
CREATE INDEX idx_ownership_unit ON ownership_records(unit_id);
CREATE INDEX idx_ownership_owner ON ownership_records(owner_id);
CREATE INDEX idx_ownership_dates ON ownership_records(valid_from, valid_to);
CREATE INDEX idx_ownership_rights ON ownership_records(rights_type);
CREATE INDEX idx_owners_aadhaar ON owners(aadhaar_hash) WHERE aadhaar_hash IS NOT NULL;
CREATE INDEX idx_owners_type ON owners(owner_type);
CREATE INDEX idx_sources_type ON data_sources(source_type);
CREATE INDEX idx_sources_parcel ON data_sources(parcel_id);
CREATE INDEX idx_sources_status ON data_sources(processing_status);
CREATE INDEX idx_jobs_source ON processing_jobs(source_id);
CREATE INDEX idx_jobs_status ON processing_jobs(status);
CREATE INDEX idx_jobs_type ON processing_jobs(job_type);
CREATE INDEX idx_conflicts_unit_a ON conflict_alerts(unit_a_id);
CREATE INDEX idx_conflicts_unit_b ON conflict_alerts(unit_b_id);
CREATE INDEX idx_conflicts_status ON conflict_alerts(status);
CREATE INDEX idx_conflicts_severity ON conflict_alerts(severity);
CREATE INDEX idx_conflicts_assigned ON conflict_alerts(assigned_to);

-- ============================================
-- FUNCTIONS & TRIGGERS
-- ============================================
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_parcels_updated_at
BEFORE UPDATE ON parcels
FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- 3D conflict detection function
-- Overlap volume = footprint-envelope intersection area (m2, via geography)
-- x vertical overlap (m). (SFCGAL ST_Volume only reads Solid geometries, which
-- PostGIS cannot build from WKT; unit volumes are extruded boxes, so this is
-- exact for them and keeps overlap_volume_cubm in cubic meters as the DDL
-- requires.)
CREATE OR REPLACE FUNCTION detect_3d_conflicts(p_unit_id UUID)
RETURNS TABLE(
    conflicting_unit_id UUID,
    conflict_type TEXT,
    overlap_volume NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    WITH target AS (
        SELECT
            volume_3d,
            ST_Envelope(volume_3d)::geometry AS fp,
            ST_ZMin(volume_3d) AS z0,
            ST_ZMax(volume_3d) AS z1
        FROM units
        WHERE unit_id = p_unit_id
    )
    SELECT
        u.unit_id,
        'overlap'::TEXT,
        ROUND((
            ST_Area(ST_Intersection(t.fp, ST_Envelope(u.volume_3d)::geometry)::geography) *
            GREATEST(LEAST(t.z1, ST_ZMax(u.volume_3d)) - GREATEST(t.z0, ST_ZMin(u.volume_3d)), 0)
        )::NUMERIC, 4)
    FROM units u
    CROSS JOIN target t
    WHERE u.unit_id != p_unit_id
        AND ST_3DIntersects(u.volume_3d, t.volume_3d)
        AND ST_Intersects(t.fp, ST_Envelope(u.volume_3d)::geometry)
        AND (
            ST_Area(ST_Intersection(t.fp, ST_Envelope(u.volume_3d)::geometry)::geography) *
            GREATEST(LEAST(t.z1, ST_ZMax(u.volume_3d)) - GREATEST(t.z0, ST_ZMin(u.volume_3d)), 0)
        ) > 0.001;
END;
$$ LANGUAGE plpgsql;
