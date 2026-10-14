import unittest

from spanverdict.jsonio import InputError
from spanverdict.policy import fingerprint, validate_policy


def policy(**changes):
    return {'version': 1, 'name': 'support-agent', 'cases': ['refund'],
            'limits': {'error_spans': 0}, **changes}


class PolicyTests(unittest.TestCase):
    def test_defaults_and_fingerprint(self):
        value = validate_policy(policy())
        self.assertEqual(value['min_runs_per_case'], 1)
        self.assertEqual(fingerprint(value), fingerprint(validate_policy(value)))

    def test_unknown_fields_and_bad_versions(self):
        for value in (policy(limts={}), policy(version=True), policy(version=2), policy(limits={'total_token': 3})):
            with self.assertRaises(InputError):
                validate_policy(value)

    def test_invalid_cases_and_counts(self):
        for value in (policy(cases=[]), policy(cases=['refund', 'refund']), policy(cases=['<script>']),
                      policy(min_runs_per_case=True), policy(min_runs_per_case=0)):
            with self.assertRaises(InputError):
                validate_policy(value)

    def test_measurements_finite_and_typed(self):
        for value in (-1, float('inf'), float('nan'), True, '1', 1.2):
            with self.assertRaises(InputError):
                validate_policy(policy(limits={'input_tokens': value}))

    def test_tool_constraints(self):
        for tools in ({'allow':['lookup'], 'required':{'update':1}},
                      {'required':{'lookup':2}, 'max_calls':{'lookup':1}},
                      {'allow':['lookup','lookup']}, {'required':{'lookup':False}}, {'required': []}):
            with self.assertRaises(InputError):
                validate_policy(policy(tools=tools))

    def test_order_rules(self):
        for rule in ({'before':'lookup','after':'lookup'}, {'before':'lookup','after':'update','same_parent':1},
                     {'before':'lookup','after':'update','unknown':True}):
            with self.assertRaises(InputError):
                validate_policy(policy(order=[rule]))

    def test_regression_schema(self):
        for allowance in ({'relative':.1}, {'relative':.1,'absolute':-1}, {'relative':0,'absolute':0,'typo':1}):
            with self.assertRaises(InputError):
                validate_policy(policy(regressions={'duration_ms':allowance}))

    def test_empty_policy_and_disallowed_operations(self):
        for value in (policy(limits={}), policy(model_operations=['invoke_agent']), policy(model_operations=['execute_tool'])):
            with self.assertRaises(InputError):
                validate_policy(value)

    def test_input_not_mutated(self):
        original = policy()
        validate_policy(original)
        self.assertNotIn('tools', original)
