import os
import shutil

from config import Options

def _confirm_factory_reset():
	print()
	print("=" * 60)
	print("  FACTORY RESET - WARNING")
	print("=" * 60)
	print()
	print("This will permanently delete:")
	print("  - All chat history       (history/ directory)")
	print("  - All saved plans        (plans/ directory)")
	print("  - Session counter        (sessid.aiia)")
	print("  - Project HISTORY.md     (working directory)")
	print("  - Project PLAN.md        (working directory)")
	print("  - All saved tips         (~/.config/aiia/tips/)")
	print("  - Background activity log (background.log)")
	print("  - Web cookies            (cookies.json)")
	print("  - Terminal audit log     (terminal_audit.log)")
	print()
	print("This cannot be undone.")
	print()
	ans = input("Continue? [y/N]: ").strip().lower()
	return ans in ('y', 'yes')

def reset_to_factory():
	global Options
	print("\nResetting to factory defaults...")
	removed = 0
	#
	# 1. State file — reset session counter and mode
	state_path = Options.get('AI_FILE_STATE', 'state.aiia')
	try:
		tmp = state_path + '.tmp'
		_default_state = '{"sess_id":0,"mode":"plan"}'
		with open(tmp, 'w') as f:
			f.write(_default_state)
		os.replace(tmp, state_path)
		print("  Reset state.aiia       -> sess_id=0, mode=plan")
		removed += 1
	except Exception as e:
		print("  Failed to reset state.aiia: {}".format(e))
	# Remove legacy per-file .aiia state files
	framework_dir = Options.get('path', '').rstrip('/')
	for fname in ('sessid.aiia', 'mode.aiia', 'model.aiia', 'persona.aiia',
				  'used_models.aiia', 'tokens.aiia'):
		fpath = os.path.join(framework_dir, fname)
		if os.path.exists(fpath):
			try:
				os.remove(fpath)
				print("  Removed legacy {} -> {}".format(fname, fpath))
			except Exception as e:
				print("  Failed to remove {}: {}".format(fname, e))
	#
	# 2. History directory
	history_dir = os.path.join(Options.get('path', ''), Options.get('history_path', 'history'))
	if os.path.isdir(history_dir):
		try:
			shutil.rmtree(history_dir)
			os.makedirs(history_dir, exist_ok=True)
			print("  Cleared history        -> {}".format(history_dir))
			removed += 1
		except Exception as e:
			print("  Failed to clear history: {}".format(e))
	#
	# 3. Plans directory
	plans_dir = os.path.join(Options.get('path', ''), Options.get('plans_path', 'plans'))
	if os.path.isdir(plans_dir):
		try:
			shutil.rmtree(plans_dir)
			os.makedirs(plans_dir, exist_ok=True)
			print("  Cleared plans          -> {}".format(plans_dir))
			removed += 1
		except Exception as e:
			print("  Failed to clear plans: {}".format(e))
	#
	# 4. Project HISTORY.md and PLAN.md (only if working_dir differs from framework)
	working_dir = Options.get('working_dir')
	framework_dir = Options.get('path', '').rstrip('/')
	if working_dir and working_dir != framework_dir:
		for fname in ('HISTORY.md', 'PLAN.md'):
			fpath = os.path.join(working_dir, fname)
			if os.path.exists(fpath):
				try:
					os.remove(fpath)
					print("  Removed project {}  -> {}".format(fname, fpath))
					removed += 1
				except Exception as e:
					print("  Failed to remove {}: {}".format(fname, e))
	#
	# 5. Tips directory
	tips_path = Options.get('TIPS_PATH', os.path.expanduser('~/.config/aiia/tips'))
	if os.path.isdir(tips_path):
		try:
			shutil.rmtree(tips_path)
			print("  Cleared tips           -> {}".format(tips_path))
			removed += 1
		except Exception as e:
			print("  Failed to clear tips: {}".format(e))
	#
	# 5b. Background log
	bg_log_path = Options.get('BACKGROUND_LOG')
	if bg_log_path and os.path.exists(bg_log_path):
		try:
			os.remove(bg_log_path)
			print("  Cleared background.log -> {}".format(bg_log_path))
		except Exception as e:
			print("  Failed to remove background.log: {}".format(e))
	#
	# 6. Cookie files
	for cookie_path in ['cookies.json', 'tools/koslenium_driver/www/cookies.json', 'tools/cookies.json']:
		fpath = os.path.join(Options.get('path', ''), cookie_path)
		if os.path.exists(fpath):
			try:
				os.remove(fpath)
				print("  Removed cookies        -> {}".format(fpath))
				removed += 1
			except Exception as e:
				print("  Failed to remove {}: {}".format(fpath, e))
	#
	# 7. Terminal audit log
	audit_path = os.path.join(Options.get('path', ''), 'tools/koslenium_driver/www/terminal_audit.log')
	if os.path.exists(audit_path):
		try:
			os.remove(audit_path)
			print("  Removed audit log      -> {}".format(audit_path))
			removed += 1
		except Exception as e:
			print("  Failed to remove audit log: {}".format(e))
	#
	print()
	if removed > 0:
		print("Factory reset complete. {} item(s) cleared.".format(removed))
	else:
		print("Nothing to reset — already clean.")
	print("Run `aiia` to start a fresh session.")
