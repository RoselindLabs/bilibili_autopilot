import unittest

from local_bilibili_autopilot.plugin import BilibiliAutopilotPlugin


class PlatformScopeTests(unittest.TestCase):
    def test_real_sdk_registers_qq_history_only(self):
        components = BilibiliAutopilotPlugin().get_components()
        tools = [c for c in components if c['type'] == 'TOOL']
        self.assertEqual([c['name'] for c in tools], ['bilibili_autopilot_history'])
        self.assertIn(tools[0]['metadata']['platforms'], ('qq', ['qq']))
        for component in components:
            if component['type'] == 'HOOK_HANDLER':
                self.assertFalse(component['metadata'].get('platforms'))
