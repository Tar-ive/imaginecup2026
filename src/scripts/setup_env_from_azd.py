#!/usr/bin/env python3
"""
Auto-populate .env file from azd environment variables.
Run this after azd deployment to automatically configure database connection.
"""
import os
import subprocess
import sys

def main():
    print("🔍 Extracting Azure SQL configuration from azd environment...")

    try:
        # Get all azd environment variables
        result = subprocess.run(
            ['azd', 'env', 'get-values'],
            capture_output=True,
            text=True,
            check=True
        )

        # Parse azd output
        azd_vars = {}
        for line in result.stdout.split('\n'):
            if '=' in line:
                key, value = line.strip().split('=', 1)
                # Remove quotes if present
                azd_vars[key.strip('"')] = value.strip('"')

        # Extract SQL connection details
        sql_server = azd_vars.get('AZURE_SQL_SERVER', '')
        sql_database = azd_vars.get('AZURE_SQL_DATABASE', '')
        sql_username = azd_vars.get('AZURE_SQL_USERNAME', 'sqladmin')
        sql_password = azd_vars.get('AZURE_SQL_PASSWORD', '')

        if not sql_server or not sql_database:
            print("⚠️  Warning: Could not find AZURE_SQL_SERVER or AZURE_SQL_DATABASE in azd environment")
            print("Available variables:")
            for key in azd_vars.keys():
                print(f"  - {key}")
            sys.exit(1)

        # Write to .env file
        env_path = os.path.join(os.getcwd(), '.env')
        with open(env_path, 'w') as f:
            f.write(f'AZURE_SQL_SERVER={sql_server}\n')
            f.write(f'AZURE_SQL_DATABASE={sql_database}\n')
            f.write(f'AZURE_SQL_USERNAME={sql_username}\n')
            f.write(f'AZURE_SQL_PASSWORD={sql_password}\n')
            f.write(f'AZURE_SQL_DRIVER=ODBC Driver 18 for SQL Server\n')
            f.write(f'CSV_URL=https://raw.githubusercontent.com/luminati-io/eCommerce-dataset-samples/main/amazon-products.csv\n')

        print(f"✅ .env file created successfully at {env_path}")
        print(f"\nConfiguration:")
        print(f"  Server: {sql_server}")
        print(f"  Database: {sql_database}")
        print(f"  Username: {sql_username}")
        print(f"  Password: {'*' * len(sql_password)}")

    except subprocess.CalledProcessError as e:
        print(f"❌ Error running azd command: {e}")
        print(f"Make sure you're logged in with 'azd auth login'")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
