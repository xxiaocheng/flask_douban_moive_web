"""empty message

Revision ID: ac618f83a4cf
Revises: ba0d27712d8f
Create Date: 2020-02-18 02:57:32.919482

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = "ac618f83a4cf"
down_revision = "ba0d27712d8f"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index("name", table_name="image")
    op.drop_table("image")
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "image",
        sa.Column(
            "id", mysql.INTEGER(display_width=11), autoincrement=True, nullable=False
        ),
        sa.Column("created_at", mysql.DATETIME(), nullable=True),
        sa.Column("updated_at", mysql.DATETIME(), nullable=True),
        sa.Column(
            "name", mysql.VARCHAR(collation="utf8mb4_bin", length=20), nullable=True
        ),
        sa.Column("image", sa.BLOB(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        mysql_collate="utf8mb4_bin",
        mysql_default_charset="utf8mb4",
        mysql_engine="InnoDB",
    )
    op.create_index("name", "image", ["name"], unique=True)
    # ### end Alembic commands ###
