-- Drop existing tables to ensure a clean slate
-- DROP TABLE IF EXISTS rent_details CASCADE;
-- DROP TABLE IF EXISTS buy_details CASCADE;
-- DROP TABLE IF EXISTS rent_listings CASCADE;
-- DROP TABLE IF EXISTS buy_listings CASCADE;
-- DROP TABLE IF EXISTS house_images CASCADE;

-- Schema for "rent" properties

CREATE TABLE IF NOT EXISTS rent_listings (
    record_id SERIAL PRIMARY KEY,
    property_id INTEGER,
    property_type VARCHAR(100),
    type VARCHAR(100),
    status VARCHAR(100),
    zoning VARCHAR(100),
    construction_type VARCHAR(100),
    floor_area NUMERIC(10,2),
    plot_area NUMERIC(10,2),
    floor_area_range_min NUMERIC(10,2),
    floor_area_range_max NUMERIC(10,2),
    plot_area_range_min NUMERIC(10,2),
    plot_area_range_max NUMERIC(10,2),
    number_of_rooms INTEGER,
    number_of_bedrooms INTEGER,
    energy_label VARCHAR(50),
    rent_price NUMERIC(10,2),
    rent_price_condition VARCHAR(100),
    rent_price_type VARCHAR(100),
    rent_price_range_min NUMERIC(10,2),
    rent_price_range_max NUMERIC(10,2),
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
    agent_name VARCHAR(255),
    detail_url TEXT,
    media_types TEXT,
    publish_date VARCHAR(255),
    blikvanger_enabled BOOLEAN,
    crawl_date VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS rent_details (
    record_id SERIAL PRIMARY KEY,
    listing_record_id INTEGER REFERENCES rent_listings(record_id),
    property_id INTEGER,
    price NUMERIC(10,2),
    deposit NUMERIC(10,2),
    living_area NUMERIC(10,2),
    external_area NUMERIC(10,2),
    volume NUMERIC(10,2),
    house_type VARCHAR(100),
    construction_year INTEGER,
    energy_label VARCHAR(50),
    balcony TEXT,
    storage TEXT,
    parking TEXT,
    status VARCHAR(100),
    insulation TEXT,
    heating TEXT,
    hot_water TEXT,
    description TEXT,
    listed_since VARCHAR(255),
    date_of_rental VARCHAR(255),
    term VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Schema for "buy" properties

CREATE TABLE IF NOT EXISTS buy_listings (
    record_id SERIAL PRIMARY KEY,
    property_id INTEGER,
    property_type VARCHAR(100),
    type VARCHAR(100),
    status VARCHAR(100),
    zoning VARCHAR(100),
    construction_type VARCHAR(100),
    floor_area NUMERIC(10,2),
    plot_area NUMERIC(10,2),
    floor_area_range_min NUMERIC(10,2),
    floor_area_range_max NUMERIC(10,2),
    plot_area_range_min NUMERIC(10,2),
    plot_area_range_max NUMERIC(10,2),
    number_of_rooms INTEGER,
    number_of_bedrooms INTEGER,
    energy_label VARCHAR(50),
    asking_price NUMERIC(10,2),
    asking_price_range_min NUMERIC(10,2),
    asking_price_range_max NUMERIC(10,2),
    price_type VARCHAR(100),
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
    agent_name VARCHAR(255),
    detail_url TEXT,
    media_types TEXT,
    publish_date VARCHAR(255),
    blikvanger_enabled BOOLEAN,
    crawl_date VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS buy_details (
    record_id SERIAL PRIMARY KEY,
    listing_record_id INTEGER REFERENCES buy_listings(record_id),
    property_id INTEGER,
    price NUMERIC(10,2),
    deposit NUMERIC(10,2),
    living_area NUMERIC(10,2),
    external_area NUMERIC(10,2),
    volume NUMERIC(10,2),
    house_type VARCHAR(100),
    construction_year INTEGER,
    energy_label VARCHAR(50),
    balcony TEXT,
    storage TEXT,
    parking TEXT,
    status VARCHAR(100),
    insulation TEXT,
    heating TEXT,
    hot_water TEXT,
    description TEXT,
    listed_since VARCHAR(255),
    date_of_rental VARCHAR(255),
    term VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE IF NOT EXISTS house_images (
    id SERIAL PRIMARY KEY,
    house_id INTEGER NOT NULL,
    offering_type VARCHAR(10) NOT NULL,
    image_url VARCHAR(1024),
    local_path VARCHAR(1024),
    downloaded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(image_url)
);

-- Create function to automatically update the updated_at column
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for all tables
DROP TRIGGER IF EXISTS update_rent_listings_updated_at ON rent_listings;
CREATE TRIGGER update_rent_listings_updated_at
    BEFORE UPDATE ON rent_listings
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_rent_details_updated_at ON rent_details;
CREATE TRIGGER update_rent_details_updated_at
    BEFORE UPDATE ON rent_details
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_buy_listings_updated_at ON buy_listings;
CREATE TRIGGER update_buy_listings_updated_at
    BEFORE UPDATE ON buy_listings
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_buy_details_updated_at ON buy_details;
CREATE TRIGGER update_buy_details_updated_at
    BEFORE UPDATE ON buy_details
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
