-- Optimized table structures for SCD-Type-2 and idempotent writes.
-- Version 3: Uses temporary `new_` prefixed names for a safe migration process.

-- #################################################################
-- #                                                               #
-- #                  TABLES FOR RENT LISTINGS                     #
-- #                                                               #
-- #################################################################

CREATE TABLE IF NOT EXISTS new_rent_listings (
    listing_id INTEGER PRIMARY KEY,
    property_type VARCHAR(100),
    address_street VARCHAR(255),
    address_number VARCHAR(20),
    address_suffix VARCHAR(50),
    address_postal_code VARCHAR(20),
    address_city VARCHAR(100),
    address_province VARCHAR(100),
    address_country VARCHAR(50),
    latitude NUMERIC(10, 7),
    longitude NUMERIC(10, 7),
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    current_snapshot_id INTEGER
);

CREATE TABLE IF NOT EXISTS new_rent_listing_snapshots (
    snapshot_id SERIAL PRIMARY KEY,
    listing_id INTEGER NOT NULL,
    snapshot_ts TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    row_hash VARCHAR(64) NOT NULL,
    status VARCHAR(100),
    price NUMERIC(10, 2),
    floor_area NUMERIC(10,2),
    plot_area NUMERIC(10,2),
    number_of_rooms INTEGER,
    energy_label VARCHAR(50),
    details_jsonb JSONB,
    UNIQUE (listing_id, row_hash)
);

CREATE TABLE IF NOT EXISTS new_active_rent_listings (
    listing_id INTEGER PRIMARY KEY,
    next_update_ts TIMESTAMPTZ NOT NULL
);

-- #################################################################
-- #                   TABLES FOR BUY LISTINGS                     #
-- #################################################################

CREATE TABLE IF NOT EXISTS new_buy_listings (
    listing_id INTEGER PRIMARY KEY,
    property_type VARCHAR(100),
    address_street VARCHAR(255),
    address_number VARCHAR(20),
    address_suffix VARCHAR(50),
    address_postal_code VARCHAR(20),
    address_city VARCHAR(100),
    address_province VARCHAR(100),
    address_country VARCHAR(50),
    latitude NUMERIC(10, 7),
    longitude NUMERIC(10, 7),
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    current_snapshot_id INTEGER
);

CREATE TABLE IF NOT EXISTS new_buy_listing_snapshots (
    snapshot_id SERIAL PRIMARY KEY,
    listing_id INTEGER NOT NULL,
    snapshot_ts TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    row_hash VARCHAR(64) NOT NULL,
    status VARCHAR(100),
    price NUMERIC(10, 2),
    floor_area NUMERIC(10,2),
    plot_area NUMERIC(10,2),
    number_of_rooms INTEGER,
    energy_label VARCHAR(50),
    details_jsonb JSONB,
    UNIQUE (listing_id, row_hash)
);

CREATE TABLE IF NOT EXISTS new_active_buy_listings (
    listing_id INTEGER PRIMARY KEY,
    next_update_ts TIMESTAMPTZ NOT NULL
);

-- #################################################################
-- #                  CONSTRAINTS AND INDEXES                      #
-- #################################################################

-- --- RENT CONSTRAINTS ---
ALTER TABLE new_rent_listing_snapshots
    ADD CONSTRAINT fk_new_rent_snapshots_to_listings
    FOREIGN KEY (listing_id) REFERENCES new_rent_listings(listing_id) ON DELETE CASCADE;

ALTER TABLE new_rent_listings
    ADD CONSTRAINT fk_new_rent_listings_to_snapshots
    FOREIGN KEY (current_snapshot_id) REFERENCES new_rent_listing_snapshots(snapshot_id) ON DELETE SET NULL;

ALTER TABLE new_active_rent_listings
    ADD CONSTRAINT fk_new_active_rent_to_listings
    FOREIGN KEY (listing_id) REFERENCES new_rent_listings(listing_id) ON DELETE CASCADE;

-- --- BUY CONSTRAINTS ---
ALTER TABLE new_buy_listing_snapshots
    ADD CONSTRAINT fk_new_buy_snapshots_to_listings
    FOREIGN KEY (listing_id) REFERENCES new_buy_listings(listing_id) ON DELETE CASCADE;

ALTER TABLE new_buy_listings
    ADD CONSTRAINT fk_new_buy_listings_to_snapshots
    FOREIGN KEY (current_snapshot_id) REFERENCES new_buy_listing_snapshots(snapshot_id) ON DELETE SET NULL;

ALTER TABLE new_active_buy_listings
    ADD CONSTRAINT fk_new_active_buy_to_listings
    FOREIGN KEY (listing_id) REFERENCES new_buy_listings(listing_id) ON DELETE CASCADE;

-- --- INDEXES ---
CREATE INDEX IF NOT EXISTS idx_new_rent_listing_snapshots_latest ON new_rent_listing_snapshots (listing_id, snapshot_ts DESC);
CREATE INDEX IF NOT EXISTS idx_new_active_rent_listings_next_update ON new_active_rent_listings (next_update_ts);
CREATE INDEX IF NOT EXISTS idx_new_buy_listing_snapshots_latest ON new_buy_listing_snapshots (listing_id, snapshot_ts DESC);
CREATE INDEX IF NOT EXISTS idx_new_active_buy_listings_next_update ON new_active_buy_listings (next_update_ts);
