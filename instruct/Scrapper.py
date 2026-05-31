class Scrapper():
	name = "Scrapper"
	description = "Search the web"
	mode = "build"
	build_thinking_disabled = True
	max_iterations = 3
	blocks = {}

	def plan(self):
		return """
"""

	def build(self):
		return """
Use XML commands!

Write <WWW><url>https://www.google.com/search?q=m5it+github</url><links>true</links><js>true</js><browser>true</browser></WWW> to fetch the page. You are running within OurAI Framework!
"""
