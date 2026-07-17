import time, datetime

class CurrentTime():
	def __init__(self):
		self.info = {
			"name":"CurrentTime",
			"description":"Get the current date and time. Useful for timestamps, changelogs, and date-sensitive operations.",
			"parameters":{
				"returnType":"string",
				"required":[],
				"properties":{
					"format":{
						"type":"string",
						"description":"Output format: 'iso' (2026-07-11T15:30:00), 'unix' (epoch seconds), 'date' (2026-07-11), 'time' (15:30:00), or 'readable' (default: July 11, 2026 15:30:00)"
					},
					"timezone":{
						"type":"string",
						"description":"Timezone like 'UTC', 'US/Eastern', or omit for local time"
					},
				},
			},
		}
	def run(self, format="readable", timezone="", opts={}):
		now = datetime.datetime.now(datetime.timezone.utc)
		if timezone and timezone.strip().lower() != 'utc':
			try:
				import zoneinfo
				tz = zoneinfo.ZoneInfo(timezone.strip())
				now = now.astimezone(tz)
			except Exception:
				return "Error: unknown timezone '{}'".format(timezone)
		fmt = (format or '').strip().lower()
		if fmt == 'iso':
			return now.isoformat()
		elif fmt == 'unix':
			return str(int(time.time()))
		elif fmt == 'date':
			return now.strftime('%Y-%m-%d')
		elif fmt == 'time':
			return now.strftime('%H:%M:%S')
		else:
			return now.strftime('%B %d, %Y %H:%M:%S {}'.format(
				now.strftime('%Z') if timezone else ''))

class currenttime(CurrentTime): pass
