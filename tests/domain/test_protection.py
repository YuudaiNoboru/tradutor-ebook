from tradutor.domain import PROTECTION_POLICY, ProtectionRule, is_protected, matches_rule

POLICY_TAGS = {"code", "pre", "svg", "math", "script", "style", "img", "picture", "hr"}
POLICY_CLASSES = {"programlisting", "sourcecode", "codelisting", "code", "screen"}


def test_policy_covers_required_selectors():
    tags = {rule.tag for rule in PROTECTION_POLICY if rule.tag is not None}
    classes = {c for rule in PROTECTION_POLICY for c in rule.classes}
    assert tags == POLICY_TAGS
    assert classes == POLICY_CLASSES


def test_matches_rule_tag_mismatch():
    rule = ProtectionRule("code")
    assert matches_rule(rule, "p", {}) is False


def test_matches_rule_empty_attrs():
    rule = ProtectionRule("code")
    assert matches_rule(rule, "code", {}) is True


def test_matches_rule_attrs_all_match():
    rule = ProtectionRule("div", (("data-code", "1"), ("data-x", "1")))
    assert matches_rule(rule, "div", {"data-code": "1", "data-x": "1", "extra": "2"}) is True


def test_matches_rule_attr_value_mismatch():
    rule = ProtectionRule("div", (("data-type", "code"),))
    assert matches_rule(rule, "div", {"data-type": "text"}) is False


def test_matches_rule_attr_missing():
    rule = ProtectionRule("div", (("data-type", "code"),))
    assert matches_rule(rule, "div", {}) is False


def test_matches_rule_classes_subset():
    rule = ProtectionRule(classes=("programlisting",))
    assert matches_rule(rule, "p", {"class": "programlisting"}) is True
    assert matches_rule(rule, "div", {"class": "highlight programlisting line-numbers"}) is True
    assert matches_rule(rule, "p", {"class": "other"}) is False
    assert matches_rule(rule, "p", {}) is False


def test_matches_rule_empty_rule_returns_false():
    rule = ProtectionRule()
    assert matches_rule(rule, "p", {"class": "test"}) is False


def test_is_protected_media_tags():
    assert is_protected("img")
    assert is_protected("picture")
    assert is_protected("hr")


def test_is_protected_semantic_classes():
    assert is_protected("p", {"class": "programlisting"})
    assert is_protected("pre", {"class": "sourcecode"})
    assert is_protected("div", {"class": "codelisting"})
    assert is_protected("p", {"class": "code"})
    assert is_protected("span", {"class": "screen"})


def test_is_protected_ignores_extra_attrs():
    assert is_protected("code", {"class": "x"})
    assert not is_protected("p", {"class": "unrelated"})


def test_is_protected_policy_hit_short_circuits():
    assert is_protected("code")


def test_is_protected_policy_miss_full_scan():
    assert not is_protected("p")


def test_is_protected_none_attrs():
    assert not is_protected("p", None)


def test_is_protected_empty_attrs_mapping():
    assert is_protected("pre", {})
