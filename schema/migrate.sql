-- #################################################################
-- #                                                               #
-- #                  DATA MIGRATION SCRIPT                        #
-- #                                                               #
-- #################################################################
-- This script migrates data from the old table structure to the new
-- SCD-Type-2 structure.
--
-- PRE-REQUISITES:
-- 1. The original tables (rent_listings, rent_details, etc.) must exist and contain data.
-- 2. The new tables (new_rent_listings, etc. as defined in optimized_tables.sql) must be created and empty.
--
-- NOTE: Run the 'rent' and 'buy' sections separately.

-- #################################################################
-- #                  MIGRATE RENT DATA                            #
-- #################################################################

-- Step 1: Populate the new dimension table `new_rent_listings` with unique listings
-- We take the earliest record for each property_id as the source for static data.
INSERT INTO new_rent_listings (
    listing_id, property_type, address_street, address_number, address_suffix,
    address_postal_code, address_city, address_province, address_country,
    first_seen_at, last_seen_at
)
SELECT
    property_id,
    property_type,
    address_street,
    address_number,
    address_suffix,
    address_postal_code,
    address_city,
    address_province,
    address_country,
    MIN(created_at), -- first_seen_at
    MAX(created_at)  -- last_seen_at (will be updated by snapshots later)
FROM rent_listings -- Reading from the original table
GROUP BY property_id, property_type, address_street, address_number, address_suffix,
         address_postal_code, address_city, address_province, address_country
ON CONFLICT (listing_id) DO NOTHING;

-- Step 2: Populate the `new_rent_listing_snapshots` table from old listings and details
-- Each row in the old tables becomes a snapshot in the new structure.
INSERT INTO new_rent_listing_snapshots (
    listing_id, snapshot_ts, row_hash, status, price, floor_area, plot_area,
    number_of_rooms, energy_label, details_jsonb
)
SELECT
    l.property_id,
    l.created_at, -- Use the old record's creation time as the snapshot timestamp
    -- Generate a pseudo-hash. For real-world migration, a more robust hash
    -- of all volatile fields would be better.
    MD5(CONCAT(l.status, l.rent_price::text, d.description)),
    l.status,
    l.rent_price,
    l.floor_area,
    l.plot_area,
    l.number_of_rooms,
    l.energy_label,
    -- Combine all other details into the JSONB field
    jsonb_build_object(
        'construction_year', d.construction_year,
        'deposit', d.deposit,
        'living_area', d.living_area,
        'volume', d.volume,
        'house_type', d.house_type,
        'description', d.description,
        'listed_since', d.listed_since
        -- Add other fields from rent_details as needed
    )
FROM rent_listings l
LEFT JOIN rent_details d ON l.record_id = d.listing_record_id
ON CONFLICT (listing_id, row_hash) DO NOTHING;

-- Step 3: Update the `current_snapshot_id` in the new `new_rent_listings` table
-- This links each listing to its most recent snapshot.
WITH latest_snapshots AS (
    SELECT
        listing_id,
        MAX(snapshot_ts) as max_ts
    FROM new_rent_listing_snapshots
    GROUP BY listing_id
)
UPDATE new_rent_listings rl
SET current_snapshot_id = (
    SELECT s.snapshot_id
    FROM new_rent_listing_snapshots s
    JOIN latest_snapshots ls ON s.listing_id = ls.listing_id AND s.snapshot_ts = ls.max_ts
    WHERE s.listing_id = rl.listing_id
    LIMIT 1
);


-- #################################################################
-- #                   MIGRATE BUY DATA                            #
-- #################################################################

-- Step 1: Populate `new_buy_listings`
INSERT INTO new_buy_listings (
    listing_id, property_type, address_street, address_number, address_suffix,
    address_postal_code, address_city, address_province, address_country,
    first_seen_at, last_seen_at
)
SELECT
    property_id,
    property_type,
    address_street,
    address_number,
    address_suffix,
    address_postal_code,
    address_city,
    address_province,
    address_country,
    MIN(created_at),
    MAX(created_at)
FROM buy_listings
GROUP BY property_id, property_type, address_street, address_number, address_suffix,
         address_postal_code, address_city, address_province, address_country
ON CONFLICT (listing_id) DO NOTHING;

-- Step 2: Populate `new_buy_listing_snapshots`
INSERT INTO new_buy_listing_snapshots (
    listing_id, snapshot_ts, row_hash, status, price, floor_area, plot_area,
    number_of_rooms, energy_label, details_jsonb
)
SELECT
    l.property_id,
    l.created_at,
    MD5(CONCAT(l.status, l.asking_price::text, d.description)),
    l.status,
    l.asking_price,
    l.floor_area,
    l.plot_area,
    l.number_of_rooms,
    l.energy_label,
    jsonb_build_object(
        'construction_year', d.construction_year,
        'deposit', d.deposit,
        'living_area', d.living_area,
        'volume', d.volume,
        'house_type', d.house_type,
        'description', d.description,
        'listed_since', d.listed_since
    )
FROM buy_listings l
LEFT JOIN buy_details d ON l.record_id = d.listing_record_id
ON CONFLICT (listing_id, row_hash) DO NOTHING;

-- Step 3: Update `current_snapshot_id` in `new_buy_listings`
WITH latest_snapshots AS (
    SELECT
        listing_id,
        MAX(snapshot_ts) as max_ts
    FROM new_buy_listing_snapshots
    GROUP BY listing_id
)
UPDATE new_buy_listings bl
SET current_snapshot_id = (
    SELECT s.snapshot_id
    FROM new_buy_listing_snapshots s
    JOIN latest_snapshots ls ON s.listing_id = ls.listing_id AND s.snapshot_ts = ls.max_ts
    WHERE s.listing_id = bl.listing_id
    LIMIT 1
);
