#!/usr/bin/env python3
"""
PDF Review Script
Identifies PDFs containing specified keywords, copies them to a review folder,
and generates a report with page numbers where keywords were found.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path
import PyPDF2
import fitz  # PyMuPDF
import re
from collections import defaultdict
import argparse


class PDFReviewScript:
    def __init__(self, input_dir, keywords_file, review_folder="review"):
        self.input_dir = Path(input_dir)
        self.keywords_file = Path(keywords_file)
        self.review_folder = Path(review_folder)
        self.keywords = self.load_keywords()
        self.matches = defaultdict(list)

        # Create review folder if it doesn't exist
        self.review_folder.mkdir(exist_ok=True)

    def load_keywords(self):
        """Load keywords from file (one per line)"""
        try:
            with open(self.keywords_file, "r", encoding="utf-8") as f:
                keywords = [line.strip().lower() for line in f if line.strip()]
            print(f"Loaded {len(keywords)} keywords from {self.keywords_file}")
            return keywords
        except FileNotFoundError:
            print(f"Keywords file {self.keywords_file} not found!")
            sys.exit(1)

    def run_ocr_on_pdf(self, pdf_path):
        """Run OCRmyPDF on a PDF file"""
        output_path = pdf_path.with_suffix(".ocr.pdf")
        temp_path = pdf_path.with_suffix(".temp.pdf")

        try:
            # Run OCRmyPDF
            cmd = [
                "ocrmypdf",
                "--skip-text",  # Only OCR pages without text
                "--optimize",
                "1",
                "--output-type",
                "pdf",
                str(pdf_path),
                str(temp_path),
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                # Replace original with OCR'd version
                shutil.move(str(temp_path), str(pdf_path))
                print(f"OCR completed for {pdf_path.name}")
                return True
            else:
                print(f"OCR failed for {pdf_path.name}: {result.stderr}")
                # Clean up temp file if it exists
                if temp_path.exists():
                    temp_path.unlink()
                return False

        except FileNotFoundError:
            print("OCRmyPDF not found. Please install it first:")
            print("pip install ocrmypdf")
            sys.exit(1)
        except Exception as e:
            print(f"Error running OCR on {pdf_path.name}: {e}")
            return False

    def extract_text_from_pdf(self, pdf_path):
        """Extract text from PDF using PyMuPDF"""
        try:
            doc = fitz.open(str(pdf_path))
            pages_text = {}

            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                text = page.get_text().lower()
                pages_text[page_num + 1] = text  # Page numbers start from 1

            doc.close()
            return pages_text

        except Exception as e:
            print(f"Error extracting text from {pdf_path.name}: {e}")
            return {}

    def find_keywords_in_text(self, pages_text, pdf_name):
        """Find keywords in extracted text and return matches with page numbers"""
        matches = []

        for page_num, text in pages_text.items():
            page_matches = []
            for keyword in self.keywords:
                # Use word boundaries to match whole words
                pattern = r"\b" + re.escape(keyword) + r"\b"
                if re.search(pattern, text, re.IGNORECASE):
                    page_matches.append(keyword)

            if page_matches:
                matches.append({"page": page_num, "keywords": page_matches})

        return matches

    def process_pdf(self, pdf_path):
        """Process a single PDF file"""
        print(f"Processing {pdf_path.name}...")

        # Run OCR first
        ocr_success = self.run_ocr_on_pdf(pdf_path)

        # Extract text
        pages_text = self.extract_text_from_pdf(pdf_path)

        if not pages_text:
            print(f"No text extracted from {pdf_path.name}")
            return False

        # Find keyword matches
        matches = self.find_keywords_in_text(pages_text, pdf_path.name)

        if matches:
            self.matches[pdf_path.name] = matches

            # Copy file to review folder
            review_path = self.review_folder / pdf_path.name
            shutil.copy2(str(pdf_path), str(review_path))
            print(f"Copied {pdf_path.name} to review folder")

            return True

        return False

    def generate_report(self):
        """Generate a text report of matches"""
        report_path = self.review_folder / "review_report.txt"

        with open(report_path, "w", encoding="utf-8") as f:
            f.write("PDF REVIEW REPORT\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Generated on: {Path().cwd()}\n")
            f.write(f"Keywords searched: {len(self.keywords)}\n")
            f.write(f"PDFs requiring review: {len(self.matches)}\n\n")

            for pdf_name, matches in self.matches.items():
                f.write(f"FILE: {pdf_name}\n")
                f.write("-" * 40 + "\n")

                for match in matches:
                    f.write(f"  Page {match['page']}: {', '.join(match['keywords'])}\n")

                f.write("\n")

            # Summary by keyword
            f.write("\nKEYWORD SUMMARY\n")
            f.write("=" * 30 + "\n")

            keyword_counts = defaultdict(int)
            for matches in self.matches.values():
                for match in matches:
                    for keyword in match["keywords"]:
                        keyword_counts[keyword] += 1

            for keyword, count in sorted(keyword_counts.items()):
                f.write(f"{keyword}: {count} occurrences\n")

        print(f"Report generated: {report_path}")

    def run(self):
        """Main execution method"""
        print(f"Starting PDF review process...")
        print(f"Input directory: {self.input_dir}")
        print(f"Review folder: {self.review_folder}")

        # Find all PDF files
        pdf_files = list(self.input_dir.glob("*.pdf"))

        if not pdf_files:
            print("No PDF files found in input directory!")
            return

        print(f"Found {len(pdf_files)} PDF files")

        processed_count = 0
        matched_count = 0

        for pdf_file in pdf_files:
            if self.process_pdf(pdf_file):
                matched_count += 1
            processed_count += 1

        print(f"\nProcessing complete!")
        print(f"Processed: {processed_count} files")
        print(f"Matches found: {matched_count} files")

        if matched_count > 0:
            self.generate_report()
        else:
            print("No keyword matches found in any PDF files.")


def create_sample_keywords_file():
    """Create a sample keywords file"""
    keywords = [
        "confidential",
        "urgent",
        "review required",
        "attention",
        "important",
        "deadline",
        "action needed",
    ]

    with open("pdf-scan-words-keywords.txt", "w") as f:
        for keyword in keywords:
            f.write(keyword + "\n")

    print("Sample keywords.txt file created")


def main():
    parser = argparse.ArgumentParser(description="PDF Review Script")
    parser.add_argument("input_dir", nargs="?", help="Directory containing PDF files")
    parser.add_argument(
        "keywords_file", nargs="?", help="File containing keywords (one per line)"
    )
    parser.add_argument(
        "--review-folder", default="review", help="Output folder for matched PDFs"
    )
    parser.add_argument(
        "--create-sample", action="store_true", help="Create sample keywords file"
    )

    args = parser.parse_args()

    # Handle create-sample case first
    if args.create_sample:
        create_sample_keywords_file()
        return

    # Validate that required arguments are provided for normal operation
    if not args.input_dir or not args.keywords_file:
        parser.error(
            "input_dir and keywords_file are required unless using --create-sample"
        )

    # Validate inputs
    if not Path(args.input_dir).exists():
        print(f"Input directory {args.input_dir} does not exist!")
        sys.exit(1)

    if not Path(args.keywords_file).exists():
        print(f"Keywords file {args.keywords_file} does not exist!")
        print("Use --create-sample to create a sample keywords file")
        sys.exit(1)

    # Run the script
    script = PDFReviewScript(args.input_dir, args.keywords_file, args.review_folder)
    script.run()


if __name__ == "__main__":
    main()
