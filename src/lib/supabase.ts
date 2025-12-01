import { createClient } from '@supabase/supabase-js'

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || 'https://cjrblsalpfhugeatrhrr.supabase.co'
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY || 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNqcmJsc2FscGZodWdlYXRyaHJyIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjQ0NjMxNjgsImV4cCI6MjA4MDAzOTE2OH0.QL9HkyvSgb2-OzPYTJ06kJsN_CYU5MIyHyfMCYnrx6o'

export const supabase = createClient(supabaseUrl, supabaseAnonKey)

