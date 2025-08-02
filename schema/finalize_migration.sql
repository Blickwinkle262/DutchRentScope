-- #################################################################
-- #                                                               #
-- #                FINALIZE MIGRATION SCRIPT                      #
-- #                                                               #
-- #################################################################
-- This script should be run ONLY AFTER you have successfully:
-- 1. Created the new tables using `optimized_tables.sql`.
-- 2. Migrated your data using `migrate.sql`.
-- 3. Verified that the data in the `new_...` tables is correct.
--
-- WARNING: This script contains DESTRUCTIVE operations (DROP TABLE).
-- PLEASE BACK UP YOUR DATABASE BEFORE RUNNING THIS.

-- #################################################################
-- #                  FINALIZE RENT TABLES                         #
-- #################################################################

-- Step 1: Drop the old rent tables
DROP TABLE IF EXISTS rent_details;
DROP TABLE IF EXISTS rent_listings;

-- Step 2: Rename the new tables to their final names
ALTER TABLE new_rent_listings RENAME TO rent_listings;
ALTER TABLE new_rent_listing_snapshots RENAME TO rent_listing_snapshots;
ALTER TABLE new_active_rent_listings RENAME TO active_rent_listings;

-- #################################################################
-- #                  FINALIZE BUY TABLES                          #
-- #################################################################

-- Step 1: Drop the old buy tables
DROP TABLE IF EXISTS buy_details;
DROP TABLE IF EXISTS buy_listings;

-- Step 2: Rename the new tables to their final names
ALTER TABLE new_buy_listings RENAME TO buy_listings;
ALTER TABLE new_buy_listing_snapshots RENAME TO buy_listing_snapshots;
ALTER TABLE new_active_buy_listings RENAME TO active_buy_listings;

-- Note: The application code is already written to work with the final
-- table names (e.g., `rent_listings`), so after this script is run,
-- the application will work seamlessly with the newly migrated data.
