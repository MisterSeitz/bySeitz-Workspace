# 📊 Table Generator

This Actor is a powerful utility that **converts data from multiple sources** into a clean, presentation-ready table. You can provide raw text, a direct URL to a file (like `.xlsx` or `.csv`), or even the **Run ID of another Apify Actor**, and this tool will automatically format it into **Markdown, HTML, or Confluence Wiki** markup.

## ✨ What can this Table Generator do?

This tool is more than a simple converter. It's a complete solution for formatting data for your reports, documentation, and websites.

  * **🔁 Works with any Actor:** Provide the Run ID of any Actor (e.g., a scraper) to instantly generate a table of its results.
  * **📥 Multiple Data Sources:** Accepts data from a **File URL**, **pasted Raw Text**, or an **Actor Run ID**.
  * **⚙️ Smart Parsing:** Automatically parses the most common data formats, including **Excel (.xlsx), CSV, JSON, and TSV**.
  * **📤 Multiple Output Formats:** Generates tables in **Markdown**, **HTML**, or **Confluence Wiki Markup**.
  * **🎯 Pro-Level Control:** Lets you **select specific columns** to include in your table and (for Markdown) **set the text alignment** for each column individually.
  * **🚀 Built on Apify:** As an Apify Actor, it runs in the cloud, can be scheduled, and can be integrated with other tools via the Apify API.

## 🚀 How do I use the Table Generator?

It's simple to get started:

1.  Go to the **Input** tab (you'll see a user-friendly form thanks to the emojis 😉).
2.  Select your data source:
      * **🔁 Source Actor Run ID:** Paste the Run ID of a previous Actor run.
      * **🌐 URL:** Paste a direct URL to an `.xlsx`, `.csv`, or `.json` file.
      * **📝 Raw Text:** Paste your data directly into the text field.
3.  (Optional) Specify which **`🎯 Select Columns`** you want to include (e.g., `Product,Price,SKU`).
4.  (Optional) Set your **`📏 Column Alignments`** for Markdown (e.g., `left,right,center`).
5.  Choose your desired **`📤 Output Format`** (Markdown, HTML, or Confluence).
6.  Click **"Start"** and wait for the run to finish.
7.  Go to the **"Output"** tab to get your generated table\!

## 💰 How much will it cost?

This Actor uses the **pay-per-event (PPE)** pricing model. You are charged a small fee for each table successfully generated.

A single run that produces one table counts as **one `apify-default-dataset-item` event**. The Apify Free plan includes a monthly platform credit, which means you can generate many tables for free before incurring any charges.

## 📥 Input and 📤 Output Examples

### Input Example

The Actor has a simple UI, but here is what a typical run using a File URL would look like in JSON:

```json
{
    "dataSource": "url",
    "fileUrl": "https://my-data.com/report.xlsx",
    "columns": "Product,Price,SKU",
    "columnAlignments": "left,right,left",
    "outputFormat": "markdown"
}
```

### Output Example

The Actor saves its result as a single item in the **Output** tab. You can download this data in JSON, CSV, Excel, etc.

```json
[
  {
    "output_format": "markdown",
    "generated_table": "| Product | Price | SKU |\n| :--- | ---: | :--- |\n| SuperSlippers | 29.99 | SLIP-001 |\n| MegaMug | 15.50 | MUG-002 |"
  }
]
```

## Advanced Tips: Automate Your Reports

The most powerful feature of this Actor is its ability to connect with other Actors. You can create a fully automated reporting pipeline:

1.  **Run any scraper** on the Apify Store (e.g., Google Maps Scraper).
2.  Once it's finished, copy its **Run ID**.
3.  Paste that ID into the `🔁 Source Actor Run ID` field of this Actor.
4.  This will automatically pull the dataset from that scraper and convert it into a clean table for your reports or project `README.md` files.

You can even **schedule** this Actor to run *after* your scraper finishes to have a formatted report ready for you every morning.

## ❓ FAQ & Support

  * **What if my Excel file has multiple sheets?**

      * Currently, the Actor only reads the **first sheet** of an Excel file.

  * **What if my data has nested JSON?**

      * The Actor works best with flat, 2D data (like a spreadsheet). If you use a `sourceRunId` with nested JSON, it will do its best, but complex objects might not look right. Use the `🎯 Select Columns` feature to pick the simple, top-level fields you need.

  * **Have questions or found a bug?**

      * Please use the **Issues** tab on the Actor's page in Apify Console to report bugs or request features.