CREATE TABLE property_listings (
    -- Primary key and basic identification
    id INTEGER PRIMARY KEY,
    property_type VARCHAR(50) NOT NULL,
    type VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL,
    zoning VARCHAR(50) NOT NULL,
    construction_type VARCHAR(50),
    
    -- Area measurements (using NUMERIC for precise decimal values)
    floor_area NUMERIC(10,2),
    plot_area NUMERIC(10,2),
    floor_area_range_min NUMERIC(10,2),
    floor_area_range_max NUMERIC(10,2),
    plot_area_range_min NUMERIC(10,2),
    plot_area_range_max NUMERIC(10,2),
    
    -- Room counts
    number_of_rooms INTEGER,
    number_of_bedrooms INTEGER,
    energy_label VARCHAR(10),
    
    -- Price information
    rent_price NUMERIC(10,2),
    rent_price_condition VARCHAR(50),
    rent_price_type VARCHAR(50),
    rent_price_range_min NUMERIC(10,2),
    rent_price_range_max NUMERIC(10,2),
    
    -- Address information
    address_country VARCHAR(2) NOT NULL,
    address_province VARCHAR(100),
    address_city VARCHAR(100) NOT NULL,
    address_municipality VARCHAR(100),
    address_district VARCHAR(100),
    address_neighbourhood VARCHAR(100),
    address_street VARCHAR(255),
    address_number VARCHAR(20),  -- Changed from INTEGER to VARCHAR to handle non-numeric parts
    address_suffix VARCHAR(10),
    address_postal_code VARCHAR(10),
    address_is_bag BOOLEAN,
    
    -- Agent and media information
    agent_name VARCHAR(255),
    detail_url TEXT,
    media_types TEXT,
    
    -- Timestamps and metadata
    publish_date TIMESTAMP,
    blikvanger_enabled BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_property_city (address_city),
    INDEX idx_property_type (property_type),
    INDEX idx_rent_price (rent_price)
);

--------------------------------------------------------------

CREATE TABLE property_details (
    -- Primary key and relationship
    property_id INTEGER PRIMARY KEY REFERENCES property_listings(id),
    
    -- Price and financial information
    price NUMERIC(10,2),
    deposit NUMERIC(10,2),
    
    -- Area measurements
    living_area NUMERIC(10,2),
    external_area NUMERIC(10,2),
    volume NUMERIC(10,2),
    
    -- Property characteristics
    house_type VARCHAR(100),
    construction_year INTEGER,
    energy_label VARCHAR(10),
    
    -- Features
    balcony TEXT,
    storage TEXT,
    parking TEXT,
    status VARCHAR(50),
    
    -- Systems and installations
    insulation TEXT,
    heating TEXT,
    hot_water TEXT,
    
    -- Detailed information
    description TEXT,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create function to automatically update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for both tables
CREATE TRIGGER update_property_listings_updated_at
    BEFORE UPDATE ON property_listings
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_property_details_updated_at
    BEFORE UPDATE ON property_details
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
