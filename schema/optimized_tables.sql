-- Optimized table structures for SCD-Type-2 and idempotent writes.
-- Version 5: Final version based on m_response.py as the source of truth for listings table.

-- #################################################################
-- #                                                               #
-- #                  TABLES FOR RENT LISTINGS                     #
-- #                                                               #
-- #################################################################

CREATE TABLE IF NOT EXISTS new_rent_listings (
    listing_id INTEGER PRIMARY KEY,
    address_country VARCHAR(50),
    address_province VARCHAR(100),
    address_city VARCHAR(100),
    address_municipality VARCHAR(100),
    address_district VARCHAR(100),
    address_neighbourhood VARCHAR(100),
    address_street VARCHAR(255),
    address_number VARCHAR(20),
    address_suffix VARCHAR(50),
    address_postal_code VARCHAR(20),
    address_is_bag BOOLEAN,
    latitude NUMERIC(10, 7),
    longitude NUMERIC(10, 7),
    property_type VARCHAR(100),
    construction_year INTEGER,
    living_area NUMERIC(10, 2),
    plot_area NUMERIC(10, 2),
    number_of_rooms INTEGER,
    number_of_bedrooms INTEGER,
    energy_label VARCHAR(10),
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
    address_country VARCHAR(50),
    address_province VARCHAR(100),
    address_city VARCHAR(100),
    address_municipality VARCHAR(100),
    address_district VARCHAR(100),
    address_neighbourhood VARCHAR(100),
    address_street VARCHAR(255),
    address_number VARCHAR(20),
    address_suffix VARCHAR(50),
    address_postal_code VARCHAR(20),
    address_is_bag BOOLEAN,
    latitude NUMERIC(10, 7),
    longitude NUMERIC(10, 7),
    property_type VARCHAR(100),
    construction_year INTEGER,
    living_area NUMERIC(10, 2),
    plot_area NUMERIC(10, 2),
    number_of_rooms INTEGER,
    number_of_bedrooms INTEGER,
    energy_label VARCHAR(10),
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


-- #################################################################
-- #                   TABLE FOR HOUSE IMAGES                      #
-- #################################################################

CREATE TABLE IF NOT EXISTS house_images (
    id SERIAL PRIMARY KEY,
    listing_id INTEGER NOT NULL,
    offering_type VARCHAR(10) NOT NULL,
    image_url VARCHAR(1024) NOT NULL,
    local_path VARCHAR(1024),
    downloaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (image_url)
);

CREATE INDEX IF NOT EXISTS idx_house_images_listing_id ON house_images (listing_id);
