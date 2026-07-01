"""Add reference to appointments

Revision ID: 00fd855d6e18
Revises: 
Create Date: 2026-07-01 16:30:16.232151

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
import secrets

# revision identifiers, used by Alembic.
revision = '00fd855d6e18'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = inspect(conn)
    
    # Step 1: Check if column exists; if not, add it as nullable
    columns = [col['name'] for col in inspector.get_columns('appointments')]
    if 'reference' not in columns:
        with op.batch_alter_table('appointments', schema=None) as batch_op:
            batch_op.add_column(sa.Column('reference', sa.String(length=20), nullable=True))
    else:
        print("Column 'reference' already exists, skipping add.")
    
    # Step 2: Drop any existing index on 'reference' (to avoid duplicate entry errors)
    indexes = [idx['name'] for idx in inspector.get_indexes('appointments')]
    if 'ix_appointments_reference' in indexes:
        with op.batch_alter_table('appointments', schema=None) as batch_op:
            batch_op.drop_index('ix_appointments_reference')
        print("Dropped existing index 'ix_appointments_reference'.")
    
    # Step 3: Backfill NULL or empty references with unique values
    result = conn.execute(sa.text("SELECT id FROM appointments WHERE reference IS NULL OR reference = ''"))
    rows = result.fetchall()
    for row in rows:
        while True:
            ref = 'APT-' + secrets.token_hex(3).upper()
            check = conn.execute(
                sa.text("SELECT id FROM appointments WHERE reference = :ref"),
                {"ref": ref}
            ).fetchone()
            if not check:
                break
        conn.execute(
            sa.text("UPDATE appointments SET reference = :ref WHERE id = :id"),
            {"ref": ref, "id": row[0]}
        )
    print(f"Backfilled {len(rows)} appointments with unique references.")
    
    # Step 4: Create unique index on reference
    with op.batch_alter_table('appointments', schema=None) as batch_op:
        batch_op.create_index('ix_appointments_reference', ['reference'], unique=True)
    
    # Step 5: Make column non-nullable – use MODIFY with the full column definition to avoid MySQL error
    # (We need to specify the type again; it's VARCHAR(20))
    conn.execute(sa.text("ALTER TABLE appointments MODIFY reference VARCHAR(20) NOT NULL"))


def downgrade():
    with op.batch_alter_table('appointments', schema=None) as batch_op:
        batch_op.drop_index('ix_appointments_reference')
        batch_op.drop_column('reference')