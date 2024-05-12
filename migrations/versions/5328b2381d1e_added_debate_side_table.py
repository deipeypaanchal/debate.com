"""Added debate_side table

Revision ID: 5328b2381d1e
Revises: 26d424de226e
Create Date: 2024-05-11 20:11:16.775218

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5328b2381d1e'
down_revision = '26d424de226e'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('category',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=50), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name')
    )
    op.create_table('debate_category',
    sa.Column('debate_id', sa.Integer(), nullable=False),
    sa.Column('category_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['category_id'], ['category.id'], ),
    sa.ForeignKeyConstraint(['debate_id'], ['debate.id'], ),
    sa.PrimaryKeyConstraint('debate_id', 'category_id')
    )
    op.create_table('debate_side',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('side', sa.String(length=100), nullable=False),
    sa.Column('debate_id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['debate_id'], ['debate.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('debate_side')
    op.drop_table('debate_category')
    op.drop_table('category')
    # ### end Alembic commands ###