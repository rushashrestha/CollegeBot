import { createClient } from '@supabase/supabase-js';

// Vite uses import.meta.env, not process.env
const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY;

// Add debug logging to check if env variables are loaded
console.log('Supabase URL:', supabaseUrl ? 'Loaded' : 'Missing');
console.log('Supabase Key:', supabaseAnonKey ? 'Loaded' : 'Missing');

if (!supabaseUrl || !supabaseAnonKey) {
  console.error('Missing Supabase environment variables:');
  console.error('VITE_SUPABASE_URL:', supabaseUrl);
  console.error('VITE_SUPABASE_ANON_KEY:', supabaseAnonKey ? '***' : 'Missing');
}

export const supabase = createClient(supabaseUrl, supabaseAnonKey);