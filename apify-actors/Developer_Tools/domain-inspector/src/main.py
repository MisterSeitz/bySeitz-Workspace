import asyncio
import re
from urllib.parse import urlparse
import dns.resolver
import whois
import httpx
import ssl
import socket
from datetime import datetime

from apify import Actor

async def main():
    """
    Main function for the Domain Inspector Actor.
    """
    async with Actor:
        Actor.log.info('Starting Domain Inspector Actor...')
        
        # --- Monetization ---
        # Charge a small fee for starting the run
        await Actor.charge(event_name='run_started')

        # Get and validate input
        actor_input = await Actor.get_input() or {}
        domains_to_check = actor_input.get('domains', [])
        record_types = actor_input.get('recordTypes', ['A', 'AAAA', 'MX', 'TXT', 'CNAME', 'NS', 'SOA'])
        perform_whois = actor_input.get('performWhois', False)
        perform_http_check = actor_input.get('performHttpCheck', False)
        perform_ssl_check = actor_input.get('performSslCheck', False)

        if not domains_to_check:
            Actor.log.warning('No domains provided in input. Exiting.')
            return

        Actor.log.info(f'Processing {len(domains_to_check)} domains.')

        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as http_client:
            for domain_input in domains_to_check:
                domain = clean_domain(domain_input)
                if not domain:
                    Actor.log.warning(f'Could not parse a valid domain from "{domain_input}". Skipping.')
                    continue

                Actor.log.info(f'--- Processing domain: {domain} ---')
                results = {'domain': domain}

                # --- Monetization ---
                # Charge for each domain processed
                await Actor.charge(event_name='domain_processed')

                # 1. DNS Lookups
                results['records'] = await get_dns_records(domain, record_types)

                # 2. WHOIS Lookup (if enabled)
                if perform_whois:
                    # --- Monetization ---
                    await Actor.charge(event_name='whois_lookup')
                    results['whois'] = await get_whois_data(domain)

                # 3. HTTP Status Check (if enabled)
                if perform_http_check:
                    # --- Monetization ---
                    await Actor.charge(event_name='http_check')
                    results['http_status'] = await get_http_status(http_client, domain)

                # 4. SSL Certificate Check (if enabled)
                if perform_ssl_check:
                    # --- Monetization ---
                    await Actor.charge(event_name='ssl_check')
                    results['ssl_info'] = await get_ssl_info(domain)
                
                # Push the results for this domain to the dataset
                await Actor.push_data(results)

        Actor.log.info(f'Domain inspection finished. {len(domains_to_check)} domains processed.')


def clean_domain(domain_input: str) -> str:
    """
    Cleans the input string to get a clean domain name.
    Handles 'google.com', 'www.google.com', 'http://google.com', 'https://www.google.com/path'.
    """
    if not domain_input:
        return ""
    
    domain = domain_input.strip().lower()
    
    # Add 'http://' if no scheme is present, to help urlparse
    if '://' not in domain:
        domain = 'http://' + domain
        
    try:
        parsed_url = urlparse(domain)
        hostname = parsed_url.hostname
        
        if not hostname:
            return ""

        # Remove 'www.' prefix if it exists
        if hostname.startswith('www.'):
            hostname = hostname[4:]
            
        return hostname.strip()
    except Exception:
        # Fallback for simple strings that fail parsing
        fallback_domain = re.sub(r'^(https|http)://', '', domain_input.strip().lower())
        fallback_domain = re.sub(r'^www\.', '', fallback_domain)
        fallback_domain = fallback_domain.split('/')[0]
        return fallback_domain.strip()

async def get_dns_records(domain: str, record_types: list[str]) -> dict:
    """
    Performs DNS lookups for a given domain and list of record types.
    """
    Actor.log.info(f'Querying DNS records for {domain}...')
    resolver = dns.resolver.Resolver()
    resolver.timeout = 5.0
    resolver.lifetime = 5.0
    results = {}

    for record_type in record_types:
        try:
            # Run the synchronous dns.resolver.resolve in a separate thread
            answers = await asyncio.to_thread(
                resolver.resolve, domain, record_type, raise_on_no_answer=False
            )
            
            records_data = []
            for rdata in answers:
                if record_type in ['A', 'AAAA']:
                    records_data.append(rdata.to_text())
                elif record_type == 'MX':
                    records_data.append({
                        'preference': rdata.preference,
                        'exchange': rdata.exchange.to_text(),
                    })
                elif record_type == 'TXT':
                    # Join multi-string TXT records
                    records_data.append(''.join(s.decode('utf-8') for s in rdata.strings))
                elif record_type == 'CNAME':
                    records_data.append(rdata.target.to_text())
                elif record_type == 'NS':
                    records_data.append(rdata.target.to_text())
                elif record_type == 'SOA':
                    records_data.append({
                        'mname': rdata.mname.to_text(),
                        'rname': rdata.rname.to_text(),
                        'serial': rdata.serial,
                        'refresh': rdata.refresh,
                        'retry': rdata.retry,
                        'expire': rdata.expire,
                        'minimum': rdata.minimum,
                    })
            
            results[record_type] = records_data

        except dns.resolver.NoAnswer:
            results[record_type] = []
        except dns.resolver.NXDOMAIN:
            Actor.log.warning(f'Domain does not exist: {domain}')
            results['error'] = 'NXDOMAIN: Domain does not exist.'
            return results # Stop processing this domain
        except Exception as e:
            Actor.log.warning(f'DNS query for {record_type} failed: {str(e)}')
            results[record_type] = f'Query failed: {str(e)}'
    
    return results

async def get_whois_data(domain: str):
    """
    Performs a WHOIS lookup for a given domain and returns a serializable dict.
    """
    Actor.log.info(f'Performing WHOIS lookup for {domain}...')
    try:
        # Run the synchronous whois.whois in a separate thread
        query_result = await asyncio.to_thread(whois.whois, domain)
        
        if not query_result:
            return {'error': 'No WHOIS data found.'}

        # whois.whois() returns a whois.Domain object which acts like a dict
        serializable_data = {}

        for key, value in query_result.items():
            # Skip internal/unhelpful fields
            if key == '_regex':
                continue

            if isinstance(value, list):
                serializable_data[key] = [
                    v.isoformat() if hasattr(v, 'isoformat') else v for v in value
                ]
            elif hasattr(value, 'isoformat'):
                serializable_data[key] = value.isoformat()
            else:
                serializable_data[key] = value
                
        return serializable_data
        
    except Exception as e:
        Actor.log.warning(f'WHOIS lookup failed for {domain}: {str(e)}')
        return {'error': str(e)}

async def get_http_status(client: httpx.AsyncClient, domain: str) -> dict:
    """
    Checks HTTP and HTTPS status codes for a given domain.
    """
    Actor.log.info(f'Checking HTTP status for {domain}...')
    results = {}
    
    for protocol in ['https', 'http']:
        url = f'{protocol}://{domain}'
        try:
            response = await client.head(url)
            results[protocol] = {
                'status_code': response.status_code,
                'url': str(response.url)
            }
        except httpx.ConnectError:
            results[protocol] = {'status_code': None, 'error': 'Connection Error'}
        except httpx.TimeoutException:
            results[protocol] = {'status_code': None, 'error': 'Timeout'}
        except Exception as e:
            results[protocol] = {'status_code': None, 'error': str(e)}
    
    return results

async def get_ssl_info(domain: str) -> dict:
    """
    Checks the SSL certificate for a given domain.
    """
    Actor.log.info(f'Checking SSL certificate for {domain}...')
    context = ssl.create_default_context()
    try:
        def blocking_ssl_check():
            with socket.create_connection((domain, 443), timeout=5) as sock:
                with context.wrap_socket(sock, server_hostname=domain) as ssock:
                    cert = ssock.getpeercert()
                    return cert

        cert = await asyncio.to_thread(blocking_ssl_check)
        
        issuer = dict(x[0] for x in cert.get('issuer', []))
        expires = datetime.strptime(cert.get('notAfter'), '%b %d %H:%M:%S %Y %Z').isoformat() + '+00:00'
        
        return {
            'issuer': issuer.get('organizationName', 'Unknown'),
            'expires': expires,
            'error': None
        }

    except ssl.SSLCertVerificationError as e:
        return {'issuer': None, 'expires': None, 'error': f'SSL verification error: {e.strerror}'}
    except socket.timeout:
        return {'issuer': None, 'expires': None, 'error': 'Connection timed out.'}
    except Exception as e:
        return {'issuer': None, 'expires': None, 'error': str(e)}