"""Add proxy categories and farming fields

Revision ID: 0f4151af27cb
Revises: final_boolean_fix
Create Date: 2025-05-30 09:35:32.969320

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0f4151af27cb'
down_revision: Union[str, None] = 'final_boolean_fix'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # 1. СНАЧАЛА создаем ENUM тип
    proxy_category_enum = postgresql.ENUM(
        'RESIDENTIAL', 'DATACENTER', 'ISP', 'NODEPAY', 'GRASS',
        name='proxycategory'
    )
    proxy_category_enum.create(op.get_bind(), checkfirst=True)

    # 2. ПОТОМ добавляем колонки
    with op.batch_alter_table('proxy_products', schema=None) as batch_op:
        batch_op.add_column(sa.Column('proxy_category',
                                      postgresql.ENUM('RESIDENTIAL', 'DATACENTER', 'ISP', 'NODEPAY', 'GRASS',
                                                      name='proxycategory', create_type=False),
                                      nullable=False, server_default='DATACENTER'))

        batch_op.add_column(sa.Column('price_per_gb', sa.DECIMAL(precision=10, scale=8), nullable=True))
        batch_op.add_column(sa.Column('uptime_guarantee', sa.DECIMAL(precision=5, scale=2), nullable=True))
        batch_op.add_column(sa.Column('speed_mbps', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('ip_pool_size', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('points_per_hour', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('farm_efficiency', sa.DECIMAL(precision=5, scale=2), nullable=True))
        batch_op.add_column(sa.Column('auto_claim', sa.Boolean(), nullable=False, server_default='false'))
        batch_op.add_column(sa.Column('multi_account_support', sa.Boolean(), nullable=False, server_default='false'))


def downgrade():
    # 1. СНАЧАЛА удаляем колонки
    with op.batch_alter_table('proxy_products', schema=None) as batch_op:
        batch_op.drop_column('multi_account_support')
        batch_op.drop_column('auto_claim')
        batch_op.drop_column('farm_efficiency')
        batch_op.drop_column('points_per_hour')
        batch_op.drop_column('ip_pool_size')
        batch_op.drop_column('speed_mbps')
        batch_op.drop_column('uptime_guarantee')
        batch_op.drop_column('price_per_gb')
        batch_op.drop_column('proxy_category')

    # 2. ПОТОМ удаляем ENUM тип
    proxy_category_enum = postgresql.ENUM(name='proxycategory')
    proxy_category_enum.drop(op.get_bind(), checkfirst=True)
