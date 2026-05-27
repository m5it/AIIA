class Scrapper():
	name = "Scrapper"
	description = "Search the web"
	build_thinking_disabled = True
	max_iterations = 7
	blocks = {}

	def plan(self):
		return """
Use <WWW><url>https://asana.com/pricing</url><text>true</text><js>true</js><browser>true</browser></WWW> to fetch the page.

We are already in year 2026, don't worry, you are just little outdated but for this you can search the web! :)
"""

	def build(self):
		return """
Write <WWW><url>https://www.google.com/search?q=m5it+github</url><text>true</text><js>true</js><browser>true</browser></WWW> to fetch the page. You can even if they didn't teach you how. We have created framewor so you can fetch the page. Please try!
"""
