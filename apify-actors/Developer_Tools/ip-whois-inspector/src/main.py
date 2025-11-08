import asyncio
import socket
from apify import Actor
from ipwhois import IPWhois
import json
import dns.resolver
import dns.reversename
import os
import requests  # For downloading the database
import geoip2.database  # The new, modern library
import geoip2.errors  # For error handling
import tarfile  # To extract the .tar.gz file
import shutil  # For file operations

# --- CONSTANTS ---
# The URL is now built dynamically in download_and_prep_db()
DB_TAR_PATH = './GeoLite2-City.tar.gz'
DB_EXTRACT_DIR = './GeoLite2-City_DB'
# This is the path we expect to find *inside* the extracted folder
DB_FINAL_PATH = './GeoLite2-City.mmdb'

# A helper function to make the IPWhois object serializable
def make_serializable(obj):
    """Recursively converts a WHOIS object (which can have sets and other types) to a dict."""
    if isinstance(obj, dict):
        return {k: make_serializable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [make_serializable(i) for i in obj]
    if isinstance(obj, set):
        return list(obj)
    return obj

async def get_reverse_dns(ip_address: str):
    """
    Performs a Reverse DNS (PTR) lookup for a given IP address.
    """
    try:
        addr = dns.reversename.from_address(ip_address)
        hostname = await asyncio.to_thread(
            dns.resolver.resolve, addr, "PTR", raise_on_no_answer=False
        )
        if hostname:
            return {"hostname": str(hostname[0]).rstrip('.')}
        return {"hostname": None, "error": "No PTR record found."}
    except Exception as e:
        return {"hostname": None, "error": str(e)}

# --- UPDATED GEOLOCATION FUNCTION ---
async def get_geolocation(ip_address: str, reader: geoip2.database.Reader):
    """
    Performs an offline Geolocation lookup using the geoip2.database.Reader.
    """
    if not reader:
        return {"error": "GeoIP database reader is not initialized."}
    
    try:
        # The reader.city() method is synchronous, so we run it in a thread.
        response = await asyncio.to_thread(reader.city, ip_address)
        
        # Map the response object to a simple dict
        return {
            "country": response.country.iso_code,
            "country_name": response.country.name,
            "continent": response.continent.code,
            "city": response.city.name,
            "timezone": response.location.time_zone,
            "latitude": response.location.latitude,
            "longitude": response.location.longitude,
            "subdivisions": [sub.iso_code for sub in response.subdivisions],
        }
    except geoip2.errors.AddressNotFoundError:
        return {"error": f"IP address not found in database: {ip_address}"}
    except Exception as e:
        return {"error": str(e)}
# --- END UPDATED FUNCTION ---

async def scan_ports(ip_address: str, ports: list[int]):
    """
    Scans a list of ports on a given IP address to see if they are open.
    Runs checks concurrently for speed.
    """
    open_ports = []
    
    async def check_port(port):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1.0)
            connect_ex_func = s.connect_ex
            result = await asyncio.to_thread(connect_ex_func, (ip_address, int(port)))
            if result == 0:
                open_ports.append(int(port))
        except Exception:
            pass
        finally:
            s.close()

    tasks = [check_port(port) for port in ports if str(port).isdigit()]
    if tasks:
        await asyncio.gather(*tasks)
    
    return sorted(open_ports)

async def download_and_prep_db(license_key: str):
    """
    Downloads and extracts the GeoLite2-City database if it doesn't exist.
    Requires a MaxMind License Key.
    Returns the path to the .mmdb file.
    """
    # Check if the final file already exists
    if os.path.exists(DB_FINAL_PATH):
        Actor.log.info(f'GeoIP database already exists at {DB_FINAL_PATH}.')
        return DB_FINAL_PATH

    # --- NEW DYNAMIC URL ---
    # We build the URL using the provided license key
    DB_URL = f'https://download.maxmind.com/app/geoip_download?edition_id=GeoLite2-City&license_key={license_key}&suffix=tar.gz'

    try:
        # Don't log the full URL as it contains the secret key
        Actor.log.info('Downloading GeoIP database from MaxMind...')
        
        # Download the file
        r = requests.get(DB_URL, stream=True)
        r.raise_for_status()  # Will raise an error for 4xx/5xx responses (e.g., invalid key)
        
        with open(DB_TAR_PATH, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        
        Actor.log.info(f'Successfully downloaded {DB_TAR_PATH}. Extracting...')

        # Extract the .tar.gz file
        with tarfile.open(DB_TAR_PATH, 'r:gz') as tar:
            tar.extractall(path=DB_EXTRACT_DIR)
        
        Actor.log.info(f'Successfully extracted to {DB_EXTRACT_DIR}.')

        # Find the .mmdb file within the extracted folder and move it
        for root, dirs, files in os.walk(DB_EXTRACT_DIR):
            for file in files:
                if file.endswith('.mmdb'):
                    shutil.move(os.path.join(root, file), DB_FINAL_PATH)
                    Actor.log.info(f'Moved database to {DB_FINAL_PATH}.')
                    
                    # Clean up
                    os.remove(DB_TAR_PATH)
                    shutil.rmtree(DB_EXTRACT_DIR)
                    Actor.log.info('Cleanup complete.')
                    return DB_FINAL_PATH
        
        raise Exception('Could not find .mmdb file in extracted archive.')

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            Actor.log.error('Failed to download GeoIP database: HTTP 401 Unauthorized. Your MAXMIND_LICENSE_KEY is likely invalid or missing.')
        else:
            Actor.log.error(f'Failed to download GeoIP database: HTTP {e.response.status_code}')
        return None
    except Exception as e:
        Actor.log.error(f'Failed to download or process GeoIP database: {e}')
        # Clean up partial files
        if os.path.exists(DB_TAR_PATH):
            os.remove(DB_TAR_PATH)
        if os.path.exists(DB_EXTRACT_DIR):
            shutil.rmtree(DB_EXTRACT_DIR)
        return None


async def main():
    """
    Main function for the IP WHOIS Inspector Actor.
    """
    async with Actor:
        Actor.log.info('Starting IP WHOIS Inspector Actor...')
        
        try:
            await Actor.charge(event_name='run_started')
        except Exception as e:
            Actor.log.warning(f'Monetization event "run_started" failed: {e}')

        actor_input = await Actor.get_input() or {}
        ip_list = actor_input.get('ipAddresses', [])
        perform_reverse_dns = actor_input.get('performReverseDns', False)
        perform_geolocation = actor_input.get('performGeolocation', False)
        perform_port_scan = actor_input.get('performPortScan', False)
        ports_to_scan = actor_input.get('portsToScan', [80, 443, 22, 21, 3306])

        if not ip_list:
            Actor.log.warning('No IP addresses provided in input. Exiting.')
            return

        # --- UPDATED: Initialize GeoIP Database ---
        geoip_reader = None
        if perform_geolocation:
            # Get the license key from environment variables
            license_key = os.getenv('MAXMIND_LICENSE_KEY')
            
            if not license_key:
                Actor.log.error('Geolocation is enabled, but the MAXMIND_LICENSE_KEY environment variable is not set.')
                Actor.log.error('Please sign up for a free MaxMind GeoLite2 account and add your license key as an environment variable to the Actor settings.')
            else:
                # Download and prepare the DB if needed
                db_path = await download_and_prep_db(license_key)
                if db_path:
                    try:
                        # Open the database reader. This object will be passed around.
                        geoip_reader = geoip2.database.Reader(db_path)
                        Actor.log.info('GeoIP database reader initialized successfully.')
                    except Exception as e:
                        Actor.log.error(f'Failed to open GeoIP database at {db_path}: {e}')
                else:
                    Actor.log.warning('Geolocation is enabled, but database setup failed. Skipping.')
        # --- END UPDATED ---

        Actor.log.info(f'Processing {len(ip_list)} IP addresses.')

        for ip_address in ip_list:
            ip_address = ip_address.strip()
            if not ip_address:
                continue

            Actor.log.info(f'--- Processing IP: {ip_address} ---')
            results = {'ip': ip_address}

            try:
                try:
                    await Actor.charge(event_name='ip_processed')
                except Exception as e:
                    Actor.log.warning(f'Monetization event "ip_processed" failed: {e}')
                
                obj = IPWhois(ip_address)
                whois_data = await asyncio.to_thread(obj.lookup_rdap, {"depth": 1})
                results['whois_data'] = make_serializable(whois_data)

            except Exception as e:
                Actor.log.warning(f'WHOIS lookup failed for {ip_address}: {str(e)}')
                results['whois_data'] = {'error': str(e)}
            
            if perform_reverse_dns:
                Actor.log.info(f'Performing Reverse DNS for {ip_address}...')
                try:
                    await Actor.charge(event_name='reverse_dns_lookup')
                except Exception as e:
                    Actor.log.warning(f'Monetization event "reverse_dns_lookup" failed: {e}')
                
                results['reverse_dns'] = await get_reverse_dns(ip_address)
            
            if perform_geolocation:
                Actor.log.info(f'Performing Geolocation for {ip_address}...')
                try:
                    await Actor.charge(event_name='geolocation_lookup')
                except Exception as e:
                    Actor.log.warning(f'Monetization event "geolocation_lookup" failed: {e}')
                
                # --- UPDATED CALL ---
                results['geolocation'] = await get_geolocation(ip_address, geoip_reader)

            if perform_port_scan:
                Actor.log.info(f'Performing Port Scan for {ip_address}...')
                try:
                    await Actor.charge(event_name='port_scan')
                except Exception as e:
                    Actor.log.warning(f'Monetization event "port_scan" failed: {e}')
                
                results['open_ports'] = await scan_ports(ip_address, ports_to_scan)

            await Actor.push_data(results)

        # --- NEW: Close the GeoIP reader ---
        if geoip_reader:
            geoip_reader.close()
            Actor.log.info('GeoIP database reader closed.')

        Actor.log.info(f'IP inspection finished. {len(ip_list)} IPs processed.')