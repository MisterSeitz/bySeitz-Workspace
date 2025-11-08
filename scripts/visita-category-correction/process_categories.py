import pandas as pd
import numpy as np
import re
import time
import sys

# --- CONFIGURATION ---
# --- 1. File Paths ---
INPUT_FILE = '2025-11-01-job_listing_category-04c54cef-c21e-caef-55a2-8a7b1e7114d1.csv' 
OUTPUT_FILE = 'visita_categories_CORRECTED.csv'
IMAGE_SHOPPING_LIST_FILE = 'image_shopping_list.txt'

# --- 2. AI & API Settings ---
# Paste your Gemini API Key here
GEMINI_API_KEY = "AIzaSyDZUKKwpBNdWD_kFzgWCXL7m1iCzcPXPQs" 

# Set to True to use the Gemini API for classification and descriptions
ENABLE_AI_FEATURES = True 

# Set to True to generate descriptions for empty fields
# (Requires ENABLE_AI_FEATURES = True)
GENERATE_DESCRIPTIONS = True

# Set to True to classify remaining top-level categories
# (Requires ENABLE_AI_FEATURES = True)
CLASSIFY_REMAINING = True

# Delay between API calls to avoid rate limiting
API_RATE_LIMIT_DELAY = 1 # 1 second

# --- 3. Data Logic Settings ---
# Your 4 defined listing types
VALID_TYPES = [
    "Businesses & Services",
    "Community Spaces",
    "Wards",
    "Municipalities"
]

# List of strings to consider "unclassified" or "messy"
# We will try to fix these by inheriting from the parent.
PROBLEM_TYPES = [
    'Businesses & Services, All Businesses & Spaces',
    'All Businesses & Spaces',
    'Community Spaces, All Businesses & Spaces'
]
# --- END OF CONFIGURATION ---


# --- AI MODEL SETUP ---
model = None
if ENABLE_AI_FEATURES:
    try:
        from google.generativeai import GenerativeModel, configure, generation_types
        
        if GEMINI_API_KEY == "YOUR_GEMINI_API_KEY_GOES_HERE":
            print("WARNING: Please paste your Gemini API Key into the 'GEMINI_API_KEY' variable on line 16.")
        else:
            configure(api_key=GEMINI_API_KEY)
            model = GenerativeModel('gemini-1.5-flash-latest')
            print("Gemini AI features enabled.")
    except ImportError:
        print("ERROR: 'google-generativeai' library not found.")
        print("Please install it: pip install google-generativeai")
        ENABLE_AI_FEATURES = False
    except Exception as e:
        print(f"ERROR: Could not configure Gemini. AI features disabled. {e}")
        ENABLE_AI_FEATURES = False

if not ENABLE_AI_FEATURES:
    print("AI features are disabled. Running in rule-based logic-only mode.")


# --- AI FUNCTIONS ---

def classify_with_ai(category_name, full_hierarchy):
    """
    Uses the Gemini model to classify a category name.
    """
    if not model:
        print(f"  [AI Skipped]: Classifying '{category_name}'. Defaulting to 'Businesses & Services'.")
        return "Businesses & Services" # Default if AI is not enabled

    print(f"  [AI Task]: Classifying '{category_name}'...")
    
    prompt = f"""
    Classify the following WordPress listing category into ONE of these four types:
    1. Businesses & Services
    2. Community Spaces
    3. Wards
    4. Municipalities

    Category Name: "{category_name}"
    Full Path: "{full_hierarchy}"
    
    Rules:
    - 'Hospital', 'Police Station', 'Library', 'School', 'Church', 'Park' are 'Community Spaces'.
    - 'Local Municipality', 'Metropolitan Municipality' are 'Municipalities'.
    - 'Cafe', 'Plumber', 'Retail Store', 'Law Firm' are 'Businesses & Services'.
    - Only return the single, correct type. Do not add any other text.

    Correct Listing Type:
    """
    
    try:
        # Set safety settings to be less restrictive for this classification task
        response = model.generate_content(
            prompt,
            safety_settings={
                'HATE_SPEECH': 'BLOCK_NONE',
                'HARASSMENT': 'BLOCK_NONE',
                'SEXUALLY_EXPLICIT': 'BLOCK_NONE',
                'DANGEROUS_CONTENT': 'BLOCK_NONE'
            }
        )
        time.sleep(API_RATE_LIMIT_DELAY) # Rate limit
        classified_type = response.text.strip()
        
        # Validate response
        if classified_type in VALID_TYPES:
            return classified_type
        else:
            print(f"    Warning: AI returned an invalid type: '{classified_type}'. Defaulting.")
            return "Businesses & Services" # Default on invalid response
            
    except generation_types.StopCandidateException as e:
        print(f"    Error: AI stopped generation for '{category_name}' (Safety/Content). {e}. Defaulting.")
        return "Businesses & Services"
    except Exception as e:
        print(f"    Error classifying {category_name}: {e}. Defaulting.")
        return "Businesses & Services" # Default on error

def generate_description_ai(category_name, full_hierarchy):
    """
    Uses the Gemini model to generate an SEO-friendly description.
    """
    if not model:
        print(f"  [AI Skipped]: Generating description for '{category_name}'.")
        return "" # Return empty string if AI is not enabled

    print(f"  [AI Task]: Generating description for '{category_name}'...")
    
    prompt = f"""
    You are an SEO expert for a South African directory site "Visita".
    Write a 1-2 sentence, engaging, professional, and helpful description for the listing category: "{category_name}".
    The full category path is: "{full_hierarchy}".
    
    - Do not use hashtags.
    - Write for a general public audience.
    - Do not repeat the category name in the description if possible.
    
    Example for "Cafe":
    "Discover the best cafés in South Africa on Visita. Find cozy spots for exceptional coffee, light meals, and delightful pastries in your area."

    Description:
    """
    
    try:
        response = model.generate_content(
            prompt,
            safety_settings={
                'HATE_SPEECH': 'BLOCK_NONE',
                'HARASSMENT': 'BLOCK_NONE',
                'SEXUALLY_EXPLICIT': 'BLOCK_NONE',
                'DANGEROUS_CONTENT': 'BLOCK_NONE'
            }
        )
        time.sleep(API_RATE_LIMIT_DELAY) # Rate limit
        return response.text.strip().replace('"', '') # Clean up quotes
    except generation_types.StopCandidateException as e:
        print(f"    Error: AI stopped generation for '{category_name}' (Safety/Content). {e}. Skipping.")
        return ""
    except Exception as e:
        print(f"    Error generating description for {category_name}: {e}")
        return "" # Return empty on error


# --- RULE-BASED CORRECTION FUNCTIONS ---

def load_data(filepath):
    """Loads the CSV file into a pandas DataFrame."""
    try:
        df = pd.read_csv(filepath)
        print(f"Successfully loaded {len(df)} rows from {filepath}")
        return df
    except FileNotFoundError:
        print(f"ERROR: Input file not found at {filepath}")
        return None
    except Exception as e:
        print(f"ERROR: Could not read CSV. {e}")
        return None

def fix_parent_ids(df):
    """
    Converts the 'Parent' column from names (strings) to IDs (integers).
    WordPress importers require the parent's Term ID, not its name.
    """
    print("Fixing parent IDs...")
    # 1. Create a mapping of category names to their record_id
    # We use .fillna('') to handle any potential NaN values in the Name column
    name_to_id_map = pd.Series(
        df.record_id.values, 
        index=df.Name.fillna('')
    ).to_dict()

    # 2. Create a new 'parent_id' column by mapping the 'Parent' name to its ID
    # .map() will automatically handle '0' (which isn't in the map) by returning NaN
    df['parent_id_corrected'] = df['Parent'].map(name_to_id_map)

    # 3. Clean up:
    # - Fill NaN values (which were '0' or unmapped parents) with 0
    # - Convert the column to integer
    df['parent_id_corrected'] = df['parent_id_corrected'].fillna(0).astype(int)
    
    print("Parent ID correction complete.")
    return df

def clean_listing_type(type_string):
    """
    Rule-based function to clean a single 'Listing Type(s)' string.
    It prioritizes 'Municipalities' > 'Wards' > 'Community Spaces'.
    """
    if not isinstance(type_string, str):
        return np.nan # Return NaN (Not a Number) for empty/invalid data

    if "Municipalities" in type_string:
        return "Municipalities"
    if "Wards" in type_string:
        return "Wards"
    if "Community Spaces" in type_string:
        return "Community Spaces"
    if "Businesses & Services" in type_string:
        return "Businesses & Services"

    # If it's none of the above (e.g., empty, or "both"), mark as NaN
    # so it can be fixed by the parent propagation.
    return np.nan

def propagate_types_from_parents(df):
    """
    This is the core logic. It propagates the correct listing type from
    parents to children, fixing thousands of rows without AI.
    """
    print("Correcting 'Listing Type(s)' using hierarchy...")
    
    # 1. First pass: Clean all types using the rule-based function
    df['type_corrected'] = df['Listing Type(s)'].apply(clean_listing_type)
    
    # 2. Create maps for quick lookup
    # Map record_id to its (cleaned) type
    id_to_type_map = pd.Series(
        df.type_corrected.values, 
        index=df.record_id
    ).to_dict()
    
    # Map record_id to its parent_id
    id_to_parent_map = pd.Series(
        df.parent_id_corrected.values, 
        index=df.record_id
    ).to_dict()

    # 3. Propagation Loop
    # We loop 5 times (for deep hierarchies).
    # Each pass, children of corrected parents will be corrected.
    print("  Propagating types down the hierarchy (5 passes)...")
    for i in range(1, 6):
        print(f"    Pass {i}...")
        changes_made = 0
        
        # Find all rows that are *still* unclassified (NaN)
        unclassified_mask = df['type_corrected'].isnull()
        
        if not unclassified_mask.any():
            print("    No unclassified rows left. Stopping early.")
            break

        # Get the indices of unclassified rows (using .index is safer)
        unclassified_indices = df[unclassified_mask].index
        
        for idx in unclassified_indices:
            # Check if index exists before proceeding
            if idx not in df.index:
                continue
                
            row = df.loc[idx]
            parent_id = id_to_parent_map.get(row['record_id'])

            if parent_id and parent_id != 0:
                parent_type = id_to_type_map.get(parent_id)
                
                # If the parent has a valid, classified type...
                if pd.notnull(parent_type) and parent_type in VALID_TYPES:
                    # ...apply it to the child
                    df.at[idx, 'type_corrected'] = parent_type
                    id_to_type_map[row['record_id']] = parent_type # Update map for next pass
                    changes_made += 1
        
        if changes_made == 0:
            print(f"    No changes made in pass {i}. Hierarchy is stable.")
            break
        else:
            print(f"    Corrected {changes_made} rows by inheritance.")

    print("Hierarchy propagation complete.")
    return df

def handle_unclassified_toplevel(df):
    """
    Finds any remaining unclassified rows (which must be top-level)
    and uses the AI to classify them, if enabled.
    """
    print("Finding remaining unclassified top-level categories...")
    
    # Find any rows that are *still* NaN
    final_unclassified_mask = df['type_corrected'].isnull()
    
    if final_unclassified_mask.any():
        num_unclassified = final_unclassified_mask.sum()
        print(f"  Found {num_unclassified} unclassified rows.")
        
        if ENABLE_AI_FEATURES and CLASSIFY_REMAINING:
            print("  Applying AI classification...")
            unclassified_indices = df[final_unclassified_mask].index
            
            for idx in unclassified_indices:
                row = df.loc[idx]
                # Get classification from our real AI function
                classified_type = classify_with_ai(
                    row['Name'], 
                    row['Full hierarchy']
                )
                df.at[idx, 'type_corrected'] = classified_type
        else:
            print("  AI classification is disabled. Defaulting to 'Businesses & Services'.")
            df['type_corrected'] = df['type_corrected'].fillna("Businesses & Services")
            
    else:
        print("  No unclassified rows remain. Skipping AI step.")
        
    return df

def generate_image_shopping_list(df):
    """Generates a text file listing all categories that need an image."""
    print("Generating image shopping list...")
    
    # Find rows where 'Image' is NaN (empty)
    missing_image_mask = df['Image'].isnull()
    categories_needing_images = df[missing_image_mask]['Name'].unique()
    
    if len(categories_needing_images) > 0:
        try:
            with open(IMAGE_SHOPPING_LIST_FILE, 'w', encoding='utf-8') as f:
                f.write("# Image Shopping List\n")
                f.write(f"# Found {len(categories_needing_images)} categories missing an 'Image' URL.\n")
                f.write("# Find images for these, upload to WP Media, get URLs, and add to the CSV.\n\n")
                for name in categories_needing_images:
                    f.write(f"{name}\n")
            print(f"Successfully saved {len(categories_needing_images)} items to {IMAGE_SHOPPING_LIST_FILE}")
        except Exception as e:
            print(f"ERROR: Could not write image list. {e}")
    else:
        print("  All categories seem to have images. No list generated.")

def main():
    """Main function to run the correction process."""
    print("--- Starting Visita Category Correction Script ---")
    
    if "google.generativeai" not in sys.modules and ENABLE_AI_FEATURES:
        print("AI features were enabled, but the library failed to import.")
        print("Script will stop. Please install 'google-generativeai' or set ENABLE_AI_FEATURES = False.")
        return
        
    df = load_data(INPUT_FILE)
    if df is None:
        return

    # Step 1: Fix Parent Name -> Parent ID
    df = fix_parent_ids(df)
    
    # Step 2: Clean and propagate Listing Types
    df = propagate_types_from_parents(df)
    
    # Step 3: Use AI for any stragglers (if enabled)
    df = handle_unclassified_toplevel(df)
    
    # Step 4: Generate image checklist
    generate_image_shopping_list(df)
    
    # --- (OPTIONAL) Description Generation ---
    if ENABLE_AI_FEATURES and GENERATE_DESCRIPTIONS:
        print("Starting optional AI description generation...")
        
        # Find rows where Description is null/NaN
        desc_mask = df['Description'].isnull()
        empty_desc_indices = df[desc_mask].index
        total_to_generate = len(empty_desc_indices)
        
        if total_to_generate > 0:
            print(f"  Found {total_to_generate} rows needing descriptions.")
            for i, idx in enumerate(empty_desc_indices):
                row = df.loc[idx]
                new_desc = generate_description_ai(row['Name'], row['Full hierarchy'])
                df.at[idx, 'Description'] = new_desc
                if (i % 10 == 0) or (i == total_to_generate - 1): # Log progress
                    print(f"    Generated {i+1} / {total_to_generate} descriptions...")
            print("  Description generation complete.")
        else:
            print("  No empty descriptions found to generate.")
    else:
        print("AI description generation is disabled. Skipping.")
    # --- End of optional block ---
    
    # Step 5: Save the final, corrected file
    try:
        # We rename the corrected columns to what WP Sheet Editor expects
        df = df.rename(columns={
            'parent_id_corrected': 'parent_id_for_import',
            'type_corrected': 'listing_type_corrected'
        })
        
        # Select key columns for the new CSV
        output_columns = [
            'record_id', 
            'Name', 
            'Slug', 
            'parent_id_for_import', # The new, correct parent ID
            'listing_type_corrected', # The new, correct listing type
            'Description',
            'Icon',
            'Image',
            'Full hierarchy'
        ]
        
        # Filter for columns that actually exist in the original file
        # This handles if the input CSV changes slightly
        final_columns = [col for col in df.columns if col in output_columns]
        # Add our new columns if they aren't in the list
        if 'parent_id_for_import' not in final_columns:
            final_columns.append('parent_id_for_import')
        if 'listing_type_corrected' not in final_columns:
            final_columns.append('listing_type_corrected')

        
        df.to_csv(OUTPUT_FILE, index=False, columns=final_columns, encoding='utf-8')
        print(f"\n--- SUCCESS! ---")
        print(f"Corrected file saved to: {OUTPUT_FILE}")
        print(f"Image checklist saved to: {IMAGE_SHOPPING_LIST_FILE}")
        
    except Exception as e:
        print(f"\n--- ERROR ---")
        print(f"Could not save output file. {e}")

if __name__ == "__main__":
    main()