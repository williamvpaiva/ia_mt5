DO $$ 
BEGIN 
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='bots' AND column_name='excluded_days') THEN 
        ALTER TABLE bots ADD COLUMN excluded_days JSONB DEFAULT '[]'::jsonb; 
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='bots' AND column_name='start_time') THEN 
        ALTER TABLE bots ADD COLUMN start_time VARCHAR DEFAULT '09:00'; 
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='bots' AND column_name='end_time') THEN 
        ALTER TABLE bots ADD COLUMN end_time VARCHAR DEFAULT '17:50'; 
    END IF;
END $$;
