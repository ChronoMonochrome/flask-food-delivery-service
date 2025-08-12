"""Migrate to order_new table with integer ids

Revision ID: d052c655f9af
Revises: 2aad3acb8612
Create Date: 2025-08-12 15:29:04.677237

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql
from sqlalchemy.sql import text

# revision identifiers, used by Alembic.
revision = 'd052c655f9af'
down_revision = '2aad3acb8612'
branch_labels = None
depends_on = None


def upgrade():
    # Drop old tables first to avoid foreign key constraint issues
    op.drop_table('order_item')
    op.drop_table('delivery_info')
    
    # Drop indexes on 'order' table before dropping
    with op.batch_alter_table('order', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('yookassa_payment_id_2'))
        batch_op.drop_index(batch_op.f('yookassa_payment_id'))

    op.drop_table('order')
    
    # Create the new tables with the updated schema and relationships
    op.create_table('order_new',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.String(length=100), nullable=False),
        sa.Column('total', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default=text("'pending'")),
        sa.Column('display_status', sa.Boolean(), nullable=False, server_default=text('true')),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('estimated_delivery', sa.DateTime(), nullable=True),
        sa.Column('yookassa_payment_id', sa.String(length=255), nullable=True),
        sa.Column('confirmation_url', sa.String(length=500), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('yookassa_payment_id')
    )
    op.create_table('delivery_info_new',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('order_id', sa.Integer(), nullable=False),
        sa.Column('address', sa.String(length=255), nullable=False),
        sa.Column('apartment', sa.String(length=50), nullable=True),
        sa.Column('floor', sa.String(length=50), nullable=True),
        sa.Column('phone', sa.String(length=50), nullable=False),
        sa.Column('payment_method', sa.String(length=50), nullable=False),
        sa.Column('comment', sa.String(length=500), nullable=True),
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.Column('postcode', sa.String(length=20), nullable=True),
        sa.Column('city_name', sa.String(length=255), nullable=True),
        sa.Column('street_name', sa.String(length=255), nullable=True),
        sa.Column('house_number', sa.String(length=50), nullable=True),
        sa.Column('delivery_price', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.ForeignKeyConstraint(['order_id'], ['order_new.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('order_id')
    )
    op.create_table('order_new_item',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('order_new_id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.String(length=36), nullable=True),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('selected_addons_data', sa.JSON(), nullable=True),
        sa.Column('selected_recommendation_data', sa.JSON(), nullable=True),
        sa.Column('custom_wok_data', sa.JSON(), nullable=True),
        sa.Column('custom_price', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('custom_name', sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(['order_new_id'], ['order_new.id'], ),
        sa.ForeignKeyConstraint(['product_id'], ['product.id'], ),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    # Drop the new tables first
    op.drop_table('order_new_item')
    op.drop_table('delivery_info_new')
    op.drop_table('order_new')

    # Recreate the old tables with the original schema
    op.create_table('order',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('total', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('estimated_delivery', sa.DateTime(), nullable=True),
        sa.Column('yookassa_payment_id', sa.String(length=255), nullable=True),
        sa.Column('confirmation_url', sa.String(length=500), nullable=True),
        sa.Column('user_id', sa.String(length=100), nullable=False),
        sa.Column('display_status', sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('yookassa_payment_id')
    )

    op.create_table('delivery_info',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('order_id', sa.String(length=36), nullable=False),
        sa.Column('address', sa.String(length=255), nullable=False),
        sa.Column('apartment', sa.String(length=50), nullable=True),
        sa.Column('floor', sa.String(length=50), nullable=True),
        sa.Column('phone', sa.String(length=50), nullable=False),
        sa.Column('payment_method', sa.String(length=50), nullable=False),
        sa.Column('comment', sa.String(length=500), nullable=True),
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.Column('postcode', sa.String(length=20), nullable=True),
        sa.Column('street_name', sa.String(length=255), nullable=True),
        sa.Column('house_number', sa.String(length=50), nullable=True),
        sa.Column('city_name', sa.String(length=255), nullable=True),
        sa.Column('delivery_price', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.ForeignKeyConstraint(['order_id'], ['order.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_table('order_item',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('order_id', sa.String(length=36), nullable=False),
        sa.Column('product_id', sa.String(length=36), nullable=True),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('selected_addons_data', sa.JSON(), nullable=True),
        sa.Column('selected_recommendation_data', sa.JSON(), nullable=True),
        sa.Column('custom_wok_data', sa.JSON(), nullable=True),
        sa.Column('custom_price', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('custom_name', sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(['order_id'], ['order.id'], ),
        sa.ForeignKeyConstraint(['product_id'], ['product.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('delivery_info', schema=None) as batch_op:
        batch_op.create_index('order_id', ['order_id'], unique=True)
    
    with op.batch_alter_table('order', schema=None) as batch_op:
        batch_op.create_index('yookassa_payment_id', ['yookassa_payment_id'], unique=True)
        batch_op.create_index('yookassa_payment_id_2', ['yookassa_payment_id'], unique=True)
