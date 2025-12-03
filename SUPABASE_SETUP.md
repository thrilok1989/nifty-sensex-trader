# Supabase Setup Guide for NIFTY/SENSEX Trader

This guide will help you set up Supabase integration for storing and managing your trading data.

## Prerequisites

- A Supabase account (free tier is sufficient to get started)
- Your trading application running

## Step 1: Create a Supabase Project

1. Go to [https://supabase.com](https://supabase.com)
2. Sign in or create a new account
3. Click on "New Project"
4. Fill in the project details:
   - **Name**: nifty-sensex-trader (or any name you prefer)
   - **Database Password**: Choose a strong password
   - **Region**: Choose the closest region to you (e.g., `ap-south-1` for India)
5. Click "Create new project"
6. Wait for the project to be provisioned (takes ~2 minutes)

## Step 2: Run the Database Schema

1. In your Supabase project dashboard, click on the **SQL Editor** (left sidebar)
2. Click on **New Query**
3. Copy the entire contents of `supabase_schema.sql` file
4. Paste it into the SQL Editor
5. Click **Run** (or press Ctrl+Enter)
6. You should see a success message indicating all tables have been created

## Step 3: Get Your Supabase Credentials

1. In your Supabase project, click on **Settings** (gear icon in left sidebar)
2. Click on **API** in the settings menu
3. You'll find two important values:
   - **Project URL**: Something like `https://xxxxxxxxxxxxx.supabase.co`
   - **anon/public key**: A long string starting with `eyJ...`

## Step 4: Configure Credentials in Your App

### Option A: Using Streamlit Secrets (Recommended)

1. Create or edit the file `.streamlit/secrets.toml` in your project directory
2. Add the following section:

```toml
[SUPABASE]
URL = "your_supabase_project_url_here"
KEY = "your_supabase_anon_key_here"
```

3. Replace the placeholder values with your actual credentials from Step 3

### Option B: Using Environment Variables

Set the following environment variables:

```bash
export SUPABASE_URL="your_supabase_project_url_here"
export SUPABASE_KEY="your_supabase_anon_key_here"
```

## Step 5: Verify the Connection

1. Restart your Streamlit application
2. Check the console/terminal for messages:
   - ✅ Success: `"✅ Supabase client initialized successfully"`
   - ⚠️ Warning: `"⚠️ Supabase is disabled - credentials not configured"`
   - ❌ Error: Check your credentials and try again

## Database Tables Created

The schema creates the following tables:

### 1. `atm_zone_bias`
Stores detailed ATM zone analysis for NIFTY/SENSEX with:
- Strike-wise PCR (Put-Call Ratio) for ATM ±5 strikes
- Open Interest, OI Change, and Volume for CE/PE
- Individual strike bias (BULLISH, BEARISH, NEUTRAL)

### 2. `option_chain_snapshots`
Stores complete option chain snapshots with:
- Overall PCR metrics (OI, OI Change, Volume)
- Total CE/PE Open Interest
- Overall market bias and scores
- Complete JSONB data for detailed analysis

### 3. `trading_signals`
Tracks all trading signals including:
- Signal type (VOB, HTF, etc.)
- Entry, Stop Loss, Target prices
- Signal status (active, triggered, closed)
- P&L tracking

### 4. `bias_analysis_history`
Historical bias analysis data:
- Overall bias scores
- Component bias scores (technical, option chain, volume, sentiment)
- Fast/Medium/Slow indicator scores

## Database Views

### `latest_atm_zone_bias`
Quick access to the most recent ATM zone bias data for each symbol.

### `latest_option_chain`
Quick access to the most recent option chain snapshot for each symbol/expiry.

## Maintenance

### Clean Old Data

The schema includes a function to clean data older than a specified number of days:

```sql
-- Clean data older than 30 days (default)
SELECT * FROM clean_old_data();

-- Clean data older than 7 days
SELECT * FROM clean_old_data(7);
```

You can run this manually in the SQL Editor or set up a scheduled job using Supabase Edge Functions.

## Data Access Examples

### Query Latest ATM Zone Bias for NIFTY
```sql
SELECT * FROM latest_atm_zone_bias
WHERE symbol = 'NIFTY'
ORDER BY strike_offset;
```

### Get PCR History for Last 24 Hours
```sql
SELECT
    timestamp,
    symbol,
    pcr_oi,
    pcr_oi_change,
    pcr_volume,
    overall_bias
FROM option_chain_snapshots
WHERE symbol = 'NIFTY'
  AND timestamp >= NOW() - INTERVAL '24 hours'
ORDER BY timestamp DESC;
```

### View Active Trading Signals
```sql
SELECT * FROM trading_signals
WHERE status = 'active'
ORDER BY timestamp DESC;
```

## Security Considerations

The current setup uses Row Level Security (RLS) with open access policies (`FOR ALL USING (true)`). This is suitable for personal use or development.

**For production use**, you should:

1. Implement proper authentication
2. Create specific RLS policies based on user roles
3. Use service role keys for server-side operations
4. Rotate your API keys regularly

## Troubleshooting

### Connection Issues
- Verify your Project URL and API key are correct
- Check if your Supabase project is active (not paused)
- Ensure you have internet connectivity

### Import Errors
- Make sure you have installed the Supabase client: `pip install supabase>=2.0.0`
- Restart your Python kernel/application after installation

### Table Not Found Errors
- Verify the SQL schema was executed successfully
- Check the Tables section in Supabase dashboard to confirm tables exist

### Performance Issues
- The schema includes indexes on common query patterns
- For large datasets, consider adding more specific indexes
- Use the cleanup function to remove old data regularly

## Support

For issues specific to:
- **Supabase**: Check [Supabase Documentation](https://supabase.com/docs)
- **This Application**: Open an issue in the project repository

## Next Steps

Once Supabase is set up:
1. The application will automatically start storing ATM zone bias data
2. View the ATM Zone Bias tables in the Streamlit app
3. Historical data will accumulate for analysis
4. Use the Supabase dashboard to query and analyze your data

Enjoy enhanced data persistence and analysis capabilities! 🚀
