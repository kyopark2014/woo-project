#!/usr/bin/env python3
"""
PDF to Text Converter using pymupdf4llm
Converts form1.pdf to trans.txt
"""

import pymupdf4llm
import os

def convert_pdf_to_text(pdf_path, output_path):
    """
    Convert PDF file to text using pymupdf4llm
    
    Args:
        pdf_path (str): Path to the input PDF file
        output_path (str): Path to the output text file
    """
    try:
        # Check if PDF file exists
        if not os.path.exists(pdf_path):
            print(f"Error: PDF file '{pdf_path}' not found.")
            return False
        
        print(f"Converting {pdf_path} to text...")
        
        # Convert PDF to markdown text using pymupdf4llm
        md_text = pymupdf4llm.to_markdown(pdf_path)
        
        # Write the converted text to output file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(md_text)
        
        print(f"Successfully converted PDF to text: {output_path}")
        print(f"Output file size: {len(md_text)} characters")
        
        return True
        
    except Exception as e:
        print(f"Error during conversion: {str(e)}")
        return False

def main():
    """Main function to execute the PDF conversion"""
    pdf_file = "form1.pdf"
    output_file = "form1.txt"
    
    print("PDF to Text Converter using pymupdf4llm")
    print("=" * 40)
    
    # Convert PDF to text
    success = convert_pdf_to_text(pdf_file, output_file)
    
    if success:
        print("\nConversion completed successfully!")
    else:
        print("\nConversion failed. Please check the error messages above.")

if __name__ == "__main__":
    main()
