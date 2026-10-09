"""create geospatial_files and features

Revision ID: 0001
Revises:
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

# JSONB on PostgreSQL, plain JSON elsewhere (SQLite dev fallback).
json_type = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    op.create_table(
        "geospatial_files",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("stored_filename", sa.String(255), nullable=False),
        sa.Column(
            "file_type",
            sa.Enum("KML", "SHAPEFILE", name="filetype", native_enum=False, length=16),
            nullable=False,
        ),
        sa.Column("file_size", sa.BigInteger(), nullable=False),
        sa.Column("original_crs", sa.String(255)),
        sa.Column("projected_crs", sa.String(255)),
        sa.Column("feature_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "status",
            sa.Enum(
                "PROCESSING", "COMPLETED", "FAILED",
                name="filestatus", native_enum=False, length=16,
            ),
            nullable=False,
        ),
        sa.Column("error_message", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_geospatial_files_status", "geospatial_files", ["status"])
    op.create_index("ix_geospatial_files_created_at", "geospatial_files", ["created_at"])

    op.create_table(
        "features",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "file_id",
            sa.Uuid(),
            sa.ForeignKey("geospatial_files.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("feature_index", sa.Integer(), nullable=False),
        sa.Column("geometry_type", sa.String(32), nullable=False),
        sa.Column("geometry", json_type),
        sa.Column("properties", json_type, nullable=False),
        sa.Column("measurement_status", sa.String(16), nullable=False),
        sa.Column("measurement_type", sa.String(16)),
        sa.Column("measurement_value", sa.Float()),
        sa.Column("measurement_unit", sa.String(8)),
        sa.UniqueConstraint("file_id", "feature_index", name="uq_feature_file_index"),
    )
    op.create_index("ix_features_file_id", "features", ["file_id"])
    op.create_index("ix_features_geometry_type", "features", ["geometry_type"])


def downgrade() -> None:
    op.drop_table("features")
    op.drop_table("geospatial_files")
