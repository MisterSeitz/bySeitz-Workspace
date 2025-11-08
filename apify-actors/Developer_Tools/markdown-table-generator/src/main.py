import json
import csv
import io
import pandas as pd
from apify import Actor
from html import escape as html_escape # For HTML generation

async def main() -> None:
    """
    Main function for the Table Generator Actor.
    V6.2: Corrected PPE to use a custom event name.
    """
    async with Actor:
        Actor.log.info('🚀 Starting Table Generator...')
        actor_input = await Actor.get_input() or {}

        # Get workflow field
        source_run_id = actor_input.get('sourceRunId', '').strip()
        
        # Get source fields
        data_source = actor_input.get('dataSource', 'rawText')
        raw_data = actor_input.get('rawData', '')
        file_url = actor_input.get('fileUrl', '')
        file_type = actor_input.get('fileType', 'auto')
        
        # Get formatting fields
        has_header = actor_input.get('dataHasHeader', True)
        columns_string = actor_input.get('columns', '')
        column_alignments_str = actor_input.get('columnAlignments', 'left')
        output_format = actor_input.get('outputFormat', 'markdown')

        df = None
        
        try:
            # Step 1: Load data into a pandas DataFrame
            if source_run_id:
                Actor.log.info(f"🔁 Fetching data from source Actor Run ID: {source_run_id}...")
                try:
                    dataset_items = await Actor.apify_client.dataset(source_run_id).list_items()
                    df = pd.DataFrame(dataset_items.items)
                    has_header = True
                except Exception as e:
                    raise ValueError(f"Could not load dataset from Run ID '{source_run_id}'. Is the ID correct and do you have access? Error: {e}")
            
            elif data_source == 'url':
                header_setting = 'infer' if has_header else None
                if not file_url:
                    raise ValueError("Data Source is 'URL', but no 'fileUrl' was provided.")
                Actor.log.info(f"🌐 Fetching data from URL: {file_url}")
                
                if file_url.endswith('.csv'):
                    df = pd.read_csv(file_url, header=header_setting)
                elif file_url.endswith('.json'):
                    df = pd.read_json(file_url)
                elif file_url.endswith('.xlsx'):
                    df = pd.read_excel(file_url, header=0 if has_header else None)
                elif file_url.endswith('.tsv'):
                    df = pd.read_csv(file_url, sep='\t', header=header_setting)
                else:
                    df = pd.read_csv(file_url, header=header_setting)
            
            elif data_source == 'rawText':
                header_setting = 'infer' if has_header else None
                if not raw_data:
                    raise ValueError("Data Source is 'Raw Text', but no 'rawData' was provided.")
                Actor.log.info(f"⚙️ Parsing raw text data (type: {file_type})...")
                data_file = io.StringIO(raw_data)
                
                if file_type == 'csv' or (file_type == 'auto' and ',' in raw_data):
                    df = pd.read_csv(data_file, header=header_setting)
                elif file_type == 'json' or (file_type == 'auto' and raw_data.strip().startswith('[')):
                    df = pd.read_json(data_file)
                elif file_type == 'tsv' or (file_type == 'auto' and '\t' in raw_data):
                    df = pd.read_csv(data_file, sep='\t', header=header_setting)
                else:
                    df = pd.read_csv(data_file, header=header_setting)
            else:
                raise ValueError(f"Unsupported dataSource: {data_source}")

            if df is None or df.empty:
                Actor.log.warning("⚠️ No data was loaded (file empty or format incorrect).")
                await Actor.set_status_message('⚠️ No data processed')
                return

            # Step 2: Apply Formatting & Column Selection
            df = df.fillna('')
            
            if columns_string:
                Actor.log.info(f"🎯 Filtering for columns: {columns_string}")
                selected_columns = [col.strip() for col in columns_string.split(',')]
                
                available_cols = list(df.columns)
                missing_cols = [col for col in selected_columns if col not in available_cols]
                
                if missing_cols:
                    Actor.log.warning(f"⚠️ The following columns were not found: {', '.join(missing_cols)}. Available columns: {', '.join(available_cols)}")
                    selected_columns = [col for col in selected_columns if col in available_cols]

                if not selected_columns:
                     raise ValueError(f"None of the specified columns ({columns_string}) were found.")
                
                df = df[selected_columns]

            headers = list(df.columns)
            rows = df.values.tolist()
            
            if not has_header and not source_run_id:
                 headers = [f"Column {i+1}" for i in range(len(headers))]

            # Step 3: Generate Table String
            table_string = ""
            
            if output_format == 'markdown':
                Actor.log.info("⚙️ Generating Markdown table...")
                align_map = {'left': ':---', 'center': ':---:', 'right': '---:'}
                alignments = []
                parsed_aligns = [align.strip() for align in column_alignments_str.split(',')]

                if len(parsed_aligns) == 1:
                    align_str = align_map.get(parsed_aligns[0], align_map['left'])
                    alignments = [align_str] * len(headers)
                else:
                    for i in range(len(headers)):
                        if i < len(parsed_aligns):
                            align_str = align_map.get(parsed_aligns[i], align_map['left'])
                            alignments.append(align_str)
                        else:
                            alignments.append(align_map['left']) 
                
                table_string = generate_markdown_table(headers, rows, alignments)
            
            elif output_format == 'html':
                Actor.log.info("⚙️ Generating HTML table...")
                table_string = generate_html_table(headers, rows)
            
            elif output_format == 'confluence':
                Actor.log.info("⚙️ Generating Confluence Wiki table...")
                table_string = generate_confluence_table(headers, rows)
            
            # Step 4: Save the output and charge the event
            Actor.log.info("Pushing data to dataset and charging 'generated_table' event...")
            
            # --- THIS IS THE FIX ---
            # Use a custom event name as the second positional argument.
            await Actor.push_data(
                {'output_format': output_format, 'generated_table': table_string},
                'generated_table'
            )
            # --- END OF FIX ---
            
            Actor.log.info(f'✨ {output_format.upper()} table generated and saved to Dataset.')
            await Actor.set_status_message('✨ Table generation complete')

        except Exception as e:
            Actor.log.exception(f'❌ Error processing data: {e}')
            await Actor.fail()

def generate_markdown_table(headers: list, rows: list, alignments: list) -> str:
    """Generates a Markdown table string."""
    def escape_md(cell_value: any) -> str:
        return str(cell_value).replace('|', '\|')

    header_row = f"| {' | '.join([escape_md(h) for h in headers])} |"
    align_row = f"| {' | '.join(alignments)} |"
    data_rows = []
    for row in rows:
        data_rows.append(f"| {' | '.join([escape_md(cell) for cell in row])} |")

    return "\n".join([header_row, align_row] + data_rows)

def generate_html_table(headers: list, rows: list) -> str:
    """Generates an HTML table string."""
    parts = ['<table border="1" style="border-collapse: collapse; width: 100%;">', '  <thead>', '    <tr>']
    
    for header in headers:
        parts.append(f'      <th style="border: 1px solid #ddd; padding: 8px;">{html_escape(str(header))}</th>')
    parts.extend(['    </tr>', '  </thead>', '  <tbody>'])
    
    for row in rows:
        parts.append('    <tr>')
        for cell in row:
            parts.append(f'      <td style="border: 1px solid #ddd; padding: 8px;">{html_escape(str(cell))}</td>')
        parts.append('    </tr>')
        
    parts.extend(['  </tbody>', '</table>'])
    return "\n".join(parts)

def generate_confluence_table(headers: list, rows: list) -> str:
    """Generates a Confluence Wiki Markup table string."""
    parts = []
    
    header_row = f"|| {' || '.join([str(h) for h in headers])} ||"
    parts.append(header_row)
    
    for row in rows:
        data_row = f"| {' | '.join([str(cell) for cell in row])} |"
        parts.append(data_row)
        
    return "\n".join(parts)