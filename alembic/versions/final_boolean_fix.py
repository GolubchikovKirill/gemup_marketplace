"""Final boolean defaults fix

Revision ID: final_boolean_fix
Revises: 74a33b705652
Create Date: 2025-05-26 19:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'final_boolean_fix'
down_revision = '74a33b705652'
branch_labels = None
depends_on = None

def upgrade():
    op.alter_column('users', 'is_guest',
                    existing_type=sa.Boolean(),
                    nullable=False,
                    server_default='false')
    
    op.alter_column('users', 'is_active',
                    existing_type=sa.Boolean(),
                    nullable=False,
                    server_default='true')
    
    op.alter_column('users', 'is_verified',
                    existing_type=sa.Boolean(),
                    nullable=False,
                    server_default='false')
    
    op.alter_column('proxy_products', 'is_active',
                    existing_type=sa.Boolean(),
                    nullable=False,
                    server_default='true')
    
    op.alter_column('proxy_products', 'is_featured',
                    existing_type=sa.Boolean(),
                    nullable=False,
                    server_default='false')
    
    op.execute("UPDATE users SET is_guest = false WHERE is_guest IS NULL")
    op.execute("UPDATE users SET is_active = true WHERE is_active IS NULL")
    op.execute("UPDATE users SET is_verified = false WHERE is_verified IS NULL")
    op.execute("UPDATE proxy_products SET is_active = true WHERE is_active IS NULL")
    op.execute("UPDATE proxy_products SET is_featured = false WHERE is_featured IS NULL")

def downgrade():
    op.alter_column('users', 'is_guest',
                    existing_type=sa.Boolean(),
                    nullable=True,
                    server_default=None)
    
    op.alter_column('users', 'is_active',
                    existing_type=sa.Boolean(),
                    nullable=True,
                    server_default=None)
    
    op.alter_column('users', 'is_verified',
                    existing_type=sa.Boolean(),
                    nullable=True,
                    server_default=None)
    
    op.alter_column('proxy_products', 'is_active',
                    existing_type=sa.Boolean(),
                    nullable=True,
                    server_default=None)
    
    op.alter_column('proxy_products', 'is_featured',
                    existing_type=sa.Boolean(),
                    nullable=True,
                    server_default=None)
