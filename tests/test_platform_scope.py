import unittest

from local_bilibili_autopilot.plugin import BilibiliAutopilotPlugin


def platforms(component):
    if 'platforms' in component:  # SDK 2.23+, including an explicit empty scope
        return component['platforms']
    return component['metadata'].get('platforms')


class PlatformScopeTests(unittest.TestCase):
    def test_real_sdk_registers_qq_history_only(self):
        components = BilibiliAutopilotPlugin().get_components()
        tools = [c for c in components if c['type'] == 'TOOL']
        self.assertEqual([c['name'] for c in tools], ['bilibili_autopilot_history'])
        self.assertIn(platforms(tools[0]), ('qq', ['qq']))
        hooks = [c for c in components if c['type'] == 'HOOK_HANDLER']
        self.assertCountEqual([c['name'] for c in hooks], ['inject_history_facts', 'track_history_turn'])
        for hook in hooks:
            self.assertIn(platforms(hook), (None, []), hook['name'])
