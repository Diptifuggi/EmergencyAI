"""Add PostGIS location geometry column, index, and sync trigger.

Revision ID: 20260831_add_postgis_geometry
Revises: 20260827_add_location_metadata
"""

from alembic import op
import sqlalchemy as sa


revision = "20260831_add_postgis_geometry"
down_revision = "20260827_add_location_metadata"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    
    # Check if PostGIS extension is available
    res = conn.execute(sa.text("SELECT count(*) FROM pg_available_extensions WHERE name = 'postgis';"))
    has_postgis = res.scalar() > 0
    
    if not has_postgis:
        print("WARNING: PostGIS extension is NOT available in PostgreSQL pg_available_extensions. Skipping PostGIS column/trigger setup.")
        return
        
    print("PostGIS extension is available. Setting up PostGIS POINT geometry, index, and triggers...")
    
    # 1. Enable PostGIS
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
    
    # 2. Add location_geom column if it doesn't exist
    inspector = sa.inspect(conn)
    columns = {column["name"] for column in inspector.get_columns("emergency_calls")}
    
    if "location_geom" not in columns:
        op.execute("ALTER TABLE emergency_calls ADD COLUMN location_geom geometry(Point, 4326);")
        print("Added location_geom geometry column.")
        
    # 3. Create spatial index if not already present
    # Check if index exists
    indexes = inspector.get_indexes("emergency_calls")
    index_names = {idx["name"] for idx in indexes}
    
    if "ix_emergency_calls_location_geom" not in index_names:
        op.execute("CREATE INDEX ix_emergency_calls_location_geom ON emergency_calls USING gist(location_geom);")
        print("Created spatial index on location_geom.")
        
    # 4. Create trigger function and trigger to automatically set location_geom
    op.execute("""
        CREATE OR REPLACE FUNCTION update_emergency_location_geom()
        RETURNS TRIGGER AS $$
        BEGIN
            IF NEW.latitude IS NOT NULL AND NEW.longitude IS NOT NULL THEN
                NEW.location_geom := ST_SetSRID(ST_Point(NEW.longitude, NEW.latitude), 4326);
            ELSE
                NEW.location_geom := NULL;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    
    # Check if trigger already exists (safe execution)
    trigger_check = conn.execute(sa.text("""
        SELECT count(*) 
        FROM pg_trigger 
        WHERE tgname = 'trg_update_emergency_location_geom';
    """))
    has_trigger = trigger_check.scalar() > 0
    
    if not has_trigger:
        op.execute("""
            CREATE TRIGGER trg_update_emergency_location_geom
            BEFORE INSERT OR UPDATE ON emergency_calls
            FOR EACH ROW
            EXECUTE FUNCTION update_emergency_location_geom();
        """)
        print("Created trigger trg_update_emergency_location_geom.")


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = {column["name"] for column in inspector.get_columns("emergency_calls")}
    
    # 1. Drop trigger
    op.execute("DROP TRIGGER IF EXISTS trg_update_emergency_location_geom ON emergency_calls;")
    
    # 2. Drop function
    op.execute("DROP FUNCTION IF EXISTS update_emergency_location_geom();")
    
    # 3. Drop index
    op.execute("DROP INDEX IF EXISTS ix_emergency_calls_location_geom;")
    
    # 4. Drop column
    if "location_geom" in columns:
        op.execute("ALTER TABLE emergency_calls DROP COLUMN location_geom;")
