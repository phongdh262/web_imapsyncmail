-- Migration: Add progress column to mailboxes table
-- Run this on production database before deploying new code

ALTER TABLE mailboxes ADD COLUMN progress INT DEFAULT 0;

-- Update existing running mailboxes to have 0 progress
UPDATE mailboxes SET progress = 0 WHERE progress IS NULL;

-- Optional: Update completed mailboxes to have 100 progress
UPDATE mailboxes SET progress = 100 WHERE status = 'success';

-- Migration: Add password_hash column to jobs table for password protection
ALTER TABLE jobs ADD COLUMN password_hash VARCHAR(255) DEFAULT NULL;
