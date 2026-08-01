from tradutor.domain import PROTECTION_POLICY, ProtectionRule, is_protected, matches_rule

POLICY_TAGS = {"code", "pre", "svg", "math", "script", "style"}


def test_policy_covers_required_selectors():
    tags = {rule.tag for rule in PROTECTION_POLICY}
    assert tags == POLICY_TAGS


def test_matches_rule_tag_mismatch():
    rule = ProtectionRule("code")
    assert matches_rule(rule, "p", {}) is False


def test_matches_rule_empty_attrs():
    rule = ProtectionRule("code")
    assert matches_rule(rule, "code", {}) is True


def test_matches_rule_attrs_all_match():
    rule = ProtectionRule("div", (("class", "code"), ("data-x", "1")))
    assert matches_rule(rule, "div", {"class": "code", "data-x": "1", "extra": "2"}) is True


def test_matches_rule_attr_value_mismatch():
    rule = ProtectionRule("div", (("class", "code"),))
    assert matches_rule(rule, "div", {"class": "text"}) is False


def test_matches_rule_attr_missing():
    rule = ProtectionRule("div", (("class", "code"),))
    assert matches_rule(rule, "div", {}) is False


def test_is_protected_ignores_extra_attrs():
    assert is_protected("code", {"class": "x"})
    assert not is_protected("p", {"class": "code"})


def test_is_protected_policy_hit_short_circuits():
    assert is_protected("code")


def test_is_protected_policy_miss_full_scan():
    assert not is_protected("p")


def test_is_protected_none_attrs():
    assert not is_protected("p", None)


def test_is_protected_empty_attrs_mapping():
    assert is_protected("pre", {})
