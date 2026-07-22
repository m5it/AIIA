import os, json

class ReadPDF():
	#
	def __init__(self):
		print("ReadPDF() STARTING")
		self.info = {
			"name":"ReadPDF",
			"description":"Extract text and metadata from PDF files. Supports page ranges and text extraction.",
			"parameters":{
				"returnType":"string",
				"required":["fileName"],
				"properties":{
					"fileName":{
						"type":"string",
						"description":"Path to the PDF file."
					},
					"fromPage":{
						"type":"integer",
						"description":"(Optional) Start page number (1-indexed). Default: 1."
					},
					"toPage":{
						"type":"integer",
						"description":"(Optional) End page number (inclusive). Default: last page."
					},
					"limit":{
						"type":"integer",
						"description":"(Optional) Max characters to return. Default: 50000. Set to 0 for unlimited."
					},
				},
			},
		}
	#
	def run(self, fileName, fromPage=None, toPage=None, limit=50000, opts={}):
		print("ReadPDF.run() fileName: {}, fromPage: {}, toPage: {}, limit: {}".format(fileName, fromPage, toPage, limit))
		#
		try:
			import pypdf
		except ImportError:
			return "Error: pypdf is not installed. Run: pip install pypdf>=4.0.0"
		#
		full_path = fileName if os.path.isabs(fileName) else os.path.join(os.getcwd(), fileName)
		if not os.path.exists(full_path):
			return "Error: File '{}' not found.".format(fileName)
		#
		try:
			reader = pypdf.PdfReader(full_path)
		except Exception as e:
			return "Error: Failed to open PDF: {}".format(e)
		#
		num_pages = len(reader.pages)
		if num_pages == 0:
			return "Error: PDF has no pages."
		#
		# Determine page range
		fp = 1
		if fromPage is not None:
			try:
				fp = int(fromPage)
			except (ValueError, TypeError):
				fp = 1
		tp = num_pages
		if toPage is not None:
			try:
				tp = int(toPage)
			except (ValueError, TypeError):
				tp = num_pages
		fp = max(1, fp)
		tp = min(num_pages, tp)
		if fp > tp:
			return "Error: fromPage ({}) is after toPage ({}).".format(fp, tp)
		#
		try:
			ml = int(limit)
		except (ValueError, TypeError):
			ml = 50000
		#
		# Metadata
		meta = reader.metadata
		metadata_parts = []
		if meta:
			for key, val in vars(meta).items():
				clean_key = key.replace('/', '')
				if val and str(val).strip():
					metadata_parts.append("  {}: {}".format(clean_key, val))
		metadata_str = "\n".join(metadata_parts) if metadata_parts else "  (no metadata)"
		#
		# Extract text
		text_parts = []
		total_chars = 0
		reached_limit = False
		#
		for i in range(fp - 1, tp):
			try:
				page = reader.pages[i]
				page_text = page.extract_text()
				if page_text:
					page_header = "\n--- Page {} ---\n".format(i + 1)
					text_parts.append(page_header)
					text_parts.append(page_text)
					total_chars += len(page_text)
					if ml > 0 and total_chars >= ml:
						reached_limit = True
						break
			except Exception as e:
				text_parts.append("\n--- Page {} (error: {}) ---\n".format(i + 1, e))
		#
		text_body = "".join(text_parts)
		if ml > 0 and len(text_body) > ml:
			text_body = text_body[:ml] + "\n\n... (truncated at {} characters)".format(ml)
		#
		result = (
			"=== PDF Info ===\n"
			"File: {}\n"
			"Total pages: {}\n"
			"Pages read: {}-{}\n".format(fileName, num_pages, fp, tp) +
			("(truncated)\n" if reached_limit else "") +
			"\n=== Metadata ===\n"
			"{}\n"
			"\n=== Content ===\n"
			"{}"
		).format(metadata_str, text_body)
		#
		return result
