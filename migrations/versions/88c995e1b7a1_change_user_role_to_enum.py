"""change user role to enum

Revision ID: 88c995e1b7a1
Revises: 3fbb5afb7a96
Create Date: 2026-02-26 23:43:36.593308

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '88c995e1b7a1'
down_revision = '3fbb5afb7a96'
branch_labels = None
depends_on = None


from sqlalchemy.dialects import postgresql

def upgrade():
    user_role_enum = postgresql.ENUM('super_admin', 'admin', 'landlord', 'tenant', name='user_role_enum')
    user_role_enum.create(op.get_bind())
    
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.alter_column('role',
               existing_type=sa.VARCHAR(length=20),
               type_=sa.Enum('super_admin', 'admin', 'landlord', 'tenant', name='user_role_enum'),
               existing_nullable=False,
               postgresql_using='role::text::user_role_enum')

def downgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.alter_column('role',
               existing_type=sa.Enum('super_admin', 'admin', 'landlord', 'tenant', name='user_role_enum'),
               type_=sa.VARCHAR(length=20),
               existing_nullable=False)

    user_role_enum = postgresql.ENUM('super_admin', 'admin', 'landlord', 'tenant', name='user_role_enum')
    user_role_enum.drop(op.get_bind())
