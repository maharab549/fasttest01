from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_message_attachments'
down_revision = None  # Update this to your latest revision
branch_labels = None
depends_on = None


def upgrade():
    # Add new columns to messages table
    op.add_column('messages', sa.Column('attachment_type', sa.String(), nullable=True))
    op.add_column('messages', sa.Column('attachment_url', sa.String(), nullable=True))
    op.add_column('messages', sa.Column('attachment_filename', sa.String(), nullable=True))
    op.add_column('messages', sa.Column('attachment_size', sa.Integer(), nullable=True))
    op.add_column('messages', sa.Column('attachment_thumbnail', sa.String(), nullable=True))
    
    # Make content nullable for media-only messages
    op.alter_column('messages', 'content',
               existing_type=sa.Text(),
               nullable=True)


def downgrade():
    # Remove columns
    op.drop_column('messages', 'attachment_thumbnail')
    op.drop_column('messages', 'attachment_size')
    op.drop_column('messages', 'attachment_filename')
    op.drop_column('messages', 'attachment_url')
    op.drop_column('messages', 'attachment_type')
    
    # Make content non-nullable again
    op.alter_column('messages', 'content',
               existing_type=sa.Text(),
               nullable=False)



