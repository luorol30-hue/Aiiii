CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  email TEXT UNIQUE,
  phone TEXT UNIQUE,
  password_hash TEXT,
  google_subject TEXT UNIQUE,
  full_name TEXT NOT NULL,
  role TEXT NOT NULL DEFAULT 'farmer',
  locale TEXT NOT NULL DEFAULT 'en',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE farms (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  owner_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  country TEXT NOT NULL,
  region TEXT,
  latitude NUMERIC(9, 6),
  longitude NUMERIC(9, 6),
  area_hectares NUMERIC(12, 3),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE farm_fields (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  farm_id UUID NOT NULL REFERENCES farms(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  boundary_geojson JSONB,
  soil_type TEXT,
  area_hectares NUMERIC(12, 3),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE crops (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name TEXT NOT NULL,
  variety TEXT,
  scientific_name TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE crop_cycles (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  field_id UUID NOT NULL REFERENCES farm_fields(id) ON DELETE CASCADE,
  crop_id UUID NOT NULL REFERENCES crops(id),
  planted_at DATE NOT NULL,
  expected_harvest_at DATE,
  harvested_at DATE,
  status TEXT NOT NULL DEFAULT 'active',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE soil_tests (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  field_id UUID NOT NULL REFERENCES farm_fields(id) ON DELETE CASCADE,
  tested_at TIMESTAMPTZ NOT NULL,
  ph NUMERIC(4, 2),
  nitrogen_ppm NUMERIC(10, 2),
  phosphorus_ppm NUMERIC(10, 2),
  potassium_ppm NUMERIC(10, 2),
  organic_carbon_pct NUMERIC(5, 2),
  moisture_pct NUMERIC(5, 2),
  lab_report_url TEXT,
  raw_result JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE sensor_devices (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  field_id UUID NOT NULL REFERENCES farm_fields(id) ON DELETE CASCADE,
  provider TEXT NOT NULL,
  external_device_id TEXT NOT NULL,
  device_type TEXT NOT NULL,
  installed_at TIMESTAMPTZ,
  status TEXT NOT NULL DEFAULT 'active',
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  UNIQUE(provider, external_device_id)
);

CREATE TABLE sensor_readings (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  device_id UUID NOT NULL REFERENCES sensor_devices(id) ON DELETE CASCADE,
  measured_at TIMESTAMPTZ NOT NULL,
  metric TEXT NOT NULL,
  value NUMERIC(14, 4) NOT NULL,
  unit TEXT NOT NULL,
  raw_payload JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE disease_detections (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  farm_id UUID REFERENCES farms(id) ON DELETE SET NULL,
  field_id UUID REFERENCES farm_fields(id) ON DELETE SET NULL,
  crop_id UUID REFERENCES crops(id) ON DELETE SET NULL,
  image_url TEXT NOT NULL,
  model_name TEXT NOT NULL,
  disease_label TEXT NOT NULL,
  confidence NUMERIC(6, 5) NOT NULL,
  affected_area_pct NUMERIC(6, 3),
  severity TEXT NOT NULL,
  weather_snapshot JSONB,
  soil_snapshot JSONB,
  recommendation JSONB NOT NULL,
  raw_prediction JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE treatments (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  disease_detection_id UUID REFERENCES disease_detections(id) ON DELETE SET NULL,
  crop_cycle_id UUID REFERENCES crop_cycles(id) ON DELETE SET NULL,
  treatment_type TEXT NOT NULL,
  product_name TEXT,
  dosage TEXT,
  applied_at TIMESTAMPTZ,
  notes TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE fertilizer_plans (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  crop_cycle_id UUID NOT NULL REFERENCES crop_cycles(id) ON DELETE CASCADE,
  generated_from_soil_test_id UUID REFERENCES soil_tests(id) ON DELETE SET NULL,
  plan JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE irrigation_plans (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  crop_cycle_id UUID NOT NULL REFERENCES crop_cycles(id) ON DELETE CASCADE,
  plan JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE weather_history (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  farm_id UUID REFERENCES farms(id) ON DELETE CASCADE,
  provider TEXT NOT NULL,
  latitude NUMERIC(9, 6) NOT NULL,
  longitude NUMERIC(9, 6) NOT NULL,
  observed_at TIMESTAMPTZ NOT NULL,
  payload JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE yield_predictions (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  crop_cycle_id UUID REFERENCES crop_cycles(id) ON DELETE SET NULL,
  disease_detection_id UUID REFERENCES disease_detections(id) ON DELETE SET NULL,
  model_name TEXT NOT NULL,
  predicted_yield_tonnes_per_hectare NUMERIC(12, 4),
  impact_pct NUMERIC(7, 3),
  features JSONB NOT NULL,
  raw_prediction JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE reports (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  farm_id UUID REFERENCES farms(id) ON DELETE SET NULL,
  report_type TEXT NOT NULL,
  title TEXT NOT NULL,
  file_url TEXT NOT NULL,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE notifications (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  channel TEXT NOT NULL,
  title TEXT NOT NULL,
  body TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',
  payload JSONB NOT NULL DEFAULT '{}'::jsonb,
  sent_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE subscriptions (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  provider TEXT NOT NULL,
  external_subscription_id TEXT,
  plan_name TEXT NOT NULL,
  status TEXT NOT NULL,
  current_period_end TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE chat_history (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  farm_id UUID REFERENCES farms(id) ON DELETE SET NULL,
  role TEXT NOT NULL,
  content TEXT NOT NULL,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE ai_predictions (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  prediction_type TEXT NOT NULL,
  model_name TEXT NOT NULL,
  input_refs JSONB NOT NULL,
  output JSONB NOT NULL,
  confidence NUMERIC(6, 5),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE market_prices (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  crop_id UUID REFERENCES crops(id) ON DELETE SET NULL,
  market_name TEXT NOT NULL,
  region TEXT,
  price NUMERIC(14, 4) NOT NULL,
  currency TEXT NOT NULL,
  unit TEXT NOT NULL,
  observed_at TIMESTAMPTZ NOT NULL,
  source TEXT NOT NULL,
  raw_payload JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE equipment (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  farm_id UUID NOT NULL REFERENCES farms(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  equipment_type TEXT NOT NULL,
  manufacturer TEXT,
  model TEXT,
  purchased_at DATE,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_farms_owner ON farms(owner_id);
CREATE INDEX idx_fields_farm ON farm_fields(farm_id);
CREATE INDEX idx_detections_user_created ON disease_detections(user_id, created_at DESC);
CREATE INDEX idx_reports_user_created ON reports(user_id, created_at DESC);
CREATE INDEX idx_notifications_user_created ON notifications(user_id, created_at DESC);
CREATE INDEX idx_sensor_readings_device_time ON sensor_readings(device_id, measured_at DESC);
CREATE INDEX idx_weather_history_location_time ON weather_history(latitude, longitude, observed_at DESC);
