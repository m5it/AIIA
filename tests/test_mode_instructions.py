import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.HandleChat import _prune_mode_instructions

PLAN = "PLAN instructions: you are the architect."
BUILD = "BUILD instructions: you are the code agent."
SHORT = "SHORT instructions shared by both modes."
PLAN_PREFIX = '[PLAN MODE INSTRUCTIONS]'
BUILD_PREFIX = '[BUILD MODE INSTRUCTIONS]'


def _sys(content):
	return {'role': 'system', 'content': content}


def _prune(msgs, current=BUILD, other=PLAN, cur_prefix=BUILD_PREFIX, other_prefix=PLAN_PREFIX):
	return _prune_mode_instructions(msgs, current, other, cur_prefix, other_prefix)


def test_drops_plan_exact_and_keeps_build():
	msgs = [
		_sys(PLAN),
		{'role': 'user', 'content': 'hello'},
		{'role': 'assistant', 'content': 'hi'},
		{'role': 'tool', 'content': 'ok'},
		_sys(BUILD),
	]
	out, has = _prune(msgs)
	assert has is True
	assert [m['content'] for m in out] == ['hello', 'hi', 'ok', BUILD]


def test_drops_plan_tip_entry_keeps_build_tip_entry():
	msgs = [
		_sys(PLAN_PREFIX + '\n' + PLAN),
		_sys('[Context summary: some old state]'),
		_sys(BUILD_PREFIX + '\n' + BUILD),
	]
	out, has = _prune(msgs)
	# no exact-text build message, so caller must append — but the build tip stays
	assert has is False
	assert [m['content'] for m in out] == ['[Context summary: some old state]', BUILD_PREFIX + '\n' + BUILD]


def test_keeps_unrelated_system_messages():
	msgs = [_sys(PLAN), _sys('## Project Instructions (AGENTS.md)'), _sys(BUILD)]
	out, _ = _prune(msgs)
	assert [m['content'] for m in out] == ['## Project Instructions (AGENTS.md)', BUILD]


def test_shared_text_option2_dedupes_and_drops_plan_tip():
	msgs = [_sys(SHORT), _sys(SHORT), _sys(PLAN_PREFIX + '\n' + PLAN), _sys(BUILD_PREFIX + '\n' + BUILD)]
	out, has = _prune(msgs, current=SHORT, other=SHORT, cur_prefix=BUILD_PREFIX, other_prefix=PLAN_PREFIX)
	assert has is True
	contents = [m['content'] for m in out]
	assert contents.count(SHORT) == 1
	assert not any(c.startswith(PLAN_PREFIX) for c in contents)
	assert any(c.startswith(BUILD_PREFIX) for c in contents)


def test_no_current_returns_false():
	out, has = _prune([_sys(PLAN)])
	assert has is False
	assert out == []


def test_drops_other_mode_tool_reference_and_workflow_blocks():
	from src.HandleChat import _prune_mode_instructions
	msgs = [
		_sys(PLAN),
		_sys(BUILD),
		_sys('[PLAN MODE TOOL REFERENCE]\ntool docs'),
		_sys('[PLAN MODE WORKFLOW EXAMPLE]\nworkflow example'),
		_sys('[Context summary: keep me]'),
	]
	out, has = _prune_mode_instructions(
		msgs, BUILD, PLAN, BUILD_PREFIX, PLAN_PREFIX,
		'[PLAN MODE TOOL REFERENCE]', '[PLAN MODE WORKFLOW EXAMPLE]')
	assert has is True
	assert [m['content'] for m in out] == [BUILD, '[Context summary: keep me]']


def test_replace_system_prompt_targets_mode_instructions_not_summary():
	from src.HandleChat import HandleChat
	fake = _make_fake([
		_sys(BUILD),
		{'role': 'user', 'content': 'u'},
		_sys('[Context summary: old recap]'),
	])
	HandleChat._replace_system_prompt(fake, 'NEW BUILD TEXT')
	# The trailing summary is left alone; the standing mode message was replaced.
	assert fake.hHM.msgs[0]['content'] == 'NEW BUILD TEXT'
	assert fake.hHM.msgs[2]['content'] == '[Context summary: old recap]'
	assert fake.appended == []


def test_replace_system_prompt_uses_prefix_match_for_tip_entries():
	from src.HandleChat import HandleChat
	fake = _make_fake([
		_sys(BUILD_PREFIX + '\n' + BUILD),
		{'role': 'user', 'content': 'u'},
	])
	HandleChat._replace_system_prompt(fake, 'NEW')
	assert fake.hHM.msgs[0]['content'] == 'NEW'
	assert fake.hHM.msgs[1]['content'] == 'u'


def test_replace_system_prompt_appends_when_no_mode_message():
	from src.HandleChat import HandleChat
	fake = _make_fake([{'role': 'user', 'content': 'u'}])
	HandleChat._replace_system_prompt(fake, 'NEW')
	assert fake.appended == [('system', 'NEW')]
	assert fake.hHM.msgs[-1] == {'role': 'system', 'content': 'NEW'}


def test_malformed_entries_untouched():
	msgs = [None, _sys(PLAN), 'junk', _sys(BUILD)]
	out, has = _prune(msgs)
	assert has is True
	assert out == [None, 'junk', _sys(BUILD)]


def _make_fake(msgs, mode='build'):
	class FakePP:
		def _get_mode_instructions(self, mode):
			return BUILD if mode == 'build' else PLAN

	class Fake:
		def __init__(self):
			self.hPP = FakePP()
			self.Options = {'MODE': mode}
			self.hHM = type('H', (), {'msgs': msgs})()
			self.rewrote = []
			self.appended = []

		def _rewrite_history(self, msgs):
			self.rewrote.append(msgs)

		def Response(self, role, opts):
			self.appended.append((role, opts['content']))
			self.hHM.msgs.append({'role': role, 'content': opts['content']})

	return Fake()


def test_build_missing_append_in_method():
	from src.HandleChat import HandleChat
	fake = _make_fake([_sys(PLAN), {'role': 'user', 'content': 'x'}])
	HandleChat._set_mode_instructions(fake, 'build')
	assert fake.hHM.msgs == [{'role': 'user', 'content': 'x'}, _sys(BUILD)]
	assert fake.appended == [('system', BUILD)]
	assert len(fake.rewrote) == 1


def test_build_present_method_rewrites_in_place():
	from src.HandleChat import HandleChat
	fake = _make_fake([_sys(PLAN), _sys(BUILD), {'role': 'user', 'content': 'x'}])
	HandleChat._set_mode_instructions(fake, 'build')
	assert fake.hHM.msgs == [_sys(BUILD), {'role': 'user', 'content': 'x'}]
	assert fake.appended == []
	assert len(fake.rewrote) == 1


def test_method_handles_shared_text_option2():
	from src.HandleChat import HandleChat

	class FakePP2:
		def _get_mode_instructions(self, mode):
			return SHORT

	class Fake2:
		def __init__(self):
			self.hPP = FakePP2()
			self.hHM = type('H', (), {'msgs': [_sys(SHORT), _sys(SHORT)]})()
			self.rewrote = []
			self.appended = []

		def _rewrite_history(self, msgs):
			self.rewrote.append(msgs)

		def Response(self, role, opts):
			self.appended.append((role, opts['content']))
			self.hHM.msgs.append({'role': role, 'content': opts['content']})

	fake = Fake2()
	HandleChat._set_mode_instructions(fake, 'build')
	assert [m['content'] for m in fake.hHM.msgs] == [SHORT]
	assert fake.appended == []
