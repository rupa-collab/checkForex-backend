"""initial schema

Revision ID: 0001_initial
Revises: 
Create Date: 2026-03-19
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "user",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("email", sa.Text, nullable=False, unique=True),
        sa.Column("password_hash", sa.Text, nullable=False),
        sa.Column("is_verified", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "verificationtoken",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("user.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token", sa.Text, nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "usersettings",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("user.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("base_currency", sa.Text, nullable=False, server_default="INR"),
        sa.Column("tracked_currencies", sa.Text, nullable=False, server_default="USD,GBP"),
        sa.Column("tracked_metals", sa.Text, nullable=False, server_default="XAU,XAG"),
        sa.Column("thresholds_json", sa.Text, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("api_usage_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("api_usage_month", sa.Text, nullable=False, server_default=""),
    )


def downgrade():
    op.drop_table("usersettings")
    op.drop_table("verificationtoken")
    op.drop_table("user")
